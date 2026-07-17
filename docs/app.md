# L'app — fonctionnement

Ce document décrit ce que fait le CMS (architecture, modèle de données,
publication) une fois qu'il tourne — pour l'installer en local, voir
[dev.md](dev.md) ; pour l'exécutable de bureau, voir [desktop.md](desktop.md).

## Architecture

- **Admin (privé, sans authentification)** : app Flask, CRUD complet, upload
  d'images (vignettes générées via Pillow), prévisualisation.
- **Génération statique** : `cms/build.py` rend les templates
  `cms/templates/public/*` vers `project/output/`. Construction **atomique**
  (build dans un dossier temporaire puis bascule), pour ne jamais servir un
  site à moitié régénéré.
- **Templates partagés** : les *mêmes* templates servent à la preview et au
  build ; seule la fabrication des URLs diffère (`public_render.Linker`).
  → aucune divergence possible entre l'aperçu et le site final.

```
Admin Flask ──(Publier)──▶ project/output/ (HTML statique) ──▶ n'importe quel hébergeur statique
     │
     └── SQLite (project/instance/portfolio.sqlite) + project/uploads/ (images)
```

Pas de proxy amont (nginx/HAProxy) : décision assumée, pas provisoire. Les
URLs du site généré sont relatives à `index.html`, pour permettre
l'ouverture directe de `project/output/` en `file://` sans serveur.

Tout ce qui est propre à un site (base, uploads, site publié) vit sous
`project/`, séparé du code de l'app — même en dev, pas seulement dans le
paquet desktop (voir [desktop.md](desktop.md)).

**Pas d'authentification** : usage local uniquement, à ne jamais exposer
au-delà de `127.0.0.1`/un réseau de confiance — voir « Hébergement »
ci-dessous.

## Modèle de données

- **Home** (singleton) : titre du site (édité depuis `/seo/edit`, voir SEO
  ci-dessous), titre de la page d'accueil, présentation, image de couverture
  et galerie (optionnelles), bascule pour afficher/masquer la liste des
  projets
- **Tag** : nom, présentation, ordre (nav)
- **Article** : titre, image de couverture (obligatoire dès le 2ᵉ
  enregistrement), tags, poids (tri décroissant), texte, galerie d'images
- **Page libre** : titre, image (optionnelle), texte, ordre (nav), galerie
  d'images

Navigation générée : Accueil · \<tags\> · \<pages libres\>.

## SEO

Réglages globaux depuis `/seo/edit` (lien « Site » dans la topbar) — pas de
champ SEO par article : chaque page réutilise déjà son propre titre, son
texte (pour la description) et son image pour son partage sur les réseaux.
C'est aussi là qu'est édité le **titre du site** (`Home.site_titre` — nom
affiché dans l'onglet du navigateur, l'en-tête et le pied de page de toutes
les pages), un réglage global plutôt qu'un champ de la page d'accueil.

- **URL publique du site** (`base_url`, ex. `https://mon-site.gitlab.io/portfolio`,
  sans slash final) : nécessaire pour `sitemap.xml` et les URLs canoniques/
  Open Graph au build. Vide = pas de sitemap, sans erreur.
- **Description**/**image de partage par défaut** : utilisées seulement si
  une page n'a rien à en tirer (ex. accueil sans présentation/image).
- **Compte Twitter/X**, **directive robots**, **vérification Google Search
  Console** (colle le contenu de la balise fournie par Google).

URLs du site publié : `tag/<slug>.html`, `projets/<slug>.html`,
`<slug>.html` pour les pages libres, `index.html` pour l'accueil.

## Configuration (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `PORTFOLIO_SECRET_KEY` | *(à définir en prod)* | clé de session Flask |
| `PORTFOLIO_BASE_DIR` | dossier du code | déplace `project/` **et** la cible git de « Publier » ensemble — voir [dev.md](dev.md) |
| `PORTFOLIO_DB` | `project/instance/portfolio.sqlite` | chemin de la base |
| `PORTFOLIO_UPLOADS` | `project/uploads/` | images sources |
| `PORTFOLIO_OUTPUT` | `project/output/` | site statique généré |
| `PORTFOLIO_IMG_LARGE`/`_MEDIUM`/`_SMALL` | `1920`/`700`/`480` | largeur max des déclinaisons |
| `PORTFOLIO_MAX_UPLOAD` | `67108864` (64 Mo) | taille max d'un upload (octets) |

## Sauvegarde

Tout tient dans `project/` :

```bash
sqlite3 project/instance/portfolio.sqlite ".backup backup.sqlite"   # copie cohérente à chaud
rsync -a project/uploads/ /backup/uploads/                          # images
```

## Publication automatique sur GitLab Pages

Le bouton **Publier** peut, en plus de régénérer `project/output/`, committer
et pousser ce contenu vers un dépôt GitLab qui héberge le site via GitLab
Pages — utile pour l'app desktop, où l'utilisateur n'a ni git ni ligne de
commande. Toute la mise en place se fait **depuis l'interface web de
GitLab** : le CMS initialise, committe et pousse lui-même le dépôt (via
**dulwich**, une implémentation Git pure Python).

### 1. Créer le dépôt sur GitLab

*New project → Create blank project.* Visibilité au choix (Private
convient : le code/la base restent privés, seule la Pages sera rendue
publique à l'étape suivante). Peu importe si tu coches ou non
« Initialize repository with a README » — le CMS gère aussi bien un dépôt
vide qu'un dépôt déjà initialisé.

### 2. Le pipeline de publication

Rien à faire ici : le CMS écrit lui-même `.gitlab-ci.yml` à la racine du
dépôt au premier **Publier**, s'il n'existe pas déjà (voir `GITLAB_CI_YML`
dans `cms/git_publish.py`) — pas besoin de le créer à la main depuis GitLab.
Le site étant généré **en local** par `cms/build.py` (pas en CI, pas de
Python/pip à installer côté GitLab), ce job n'a rien à construire : il
republie juste le dossier `project/output/` déjà prêt, commité tel quel :

```yaml
pages:
  image: busybox:stable
  stage: deploy
  script:
    - rm -rf public
    - cp -r project/output public
  artifacts:
    paths:
      - public
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

S'il faut le personnaliser (domaine, étape supplémentaire...), l'éditer
directement dans GitLab : le CMS ne l'écrit que s'il est absent, il
n'écrasera jamais une version déjà présente dans le dépôt.

### 3. Activer Pages

*Settings → General → Visibility, project features, permissions*, régler
**Pages** sur *Everyone* — le site publié doit rester accessible même si le
dépôt (code, base, uploads) est privé.

### 4. Débloquer la branche par défaut pour le push automatique

GitLab protège `main` par défaut, ce qui bloque le mécanisme de
récupération du CMS après un historique local perdu/recréé (voir plus bas) :
*Settings → Repository → Protected branches*, retirer la protection sur
`main` (ou l'assouplir pour autoriser le force-push). Ce dépôt n'est qu'un
miroir de contenu pour l'hébergement, pas un historique de dev à protéger.

### 5. Créer un token d'accès

*Settings → Access Tokens → Add new token*, scope **`write_repository`**,
expiration au choix. Copier la valeur générée (affichée une seule fois) —
voir aussi `SECRETS.md` (local, jamais commité) pour la conserver au cas où.

### 6. Renseigner l'admin

Dans le CMS, `/git/edit` (lien dans la topbar) : coller l'URL du dépôt
(`https://gitlab.com/<groupe>/<projet>.git`) et le token, puis enregistrer.
Le token n'est jamais réécrit ailleurs : il n'est utilisé qu'au moment du
push, injecté dans l'URL authentifiée le temps de l'appel.

### Le pipe complet, une fois configuré

1. Rédaction dans l'admin, puis clic sur **Publier**.
2. `cms/build.py` régénère `project/output/` (build atomique).
3. `cms/git_publish.py` initialise `.git` si besoin (premier lancement),
   committe `project/instance/` + `project/uploads/` + `project/output/`, et
   pousse — avec repli automatique en force-push si l'historique local
   diverge de celui du remote (dépôt local recréé après un redéploiement,
   par exemple).
4. Le job `pages` de GitLab CI republie `project/output/` en `public/`.
5. Site à jour sur `https://<groupe>.gitlab.io/<projet>/` (ou le domaine
   personnalisé configuré dans GitLab), en général en quelques dizaines de
   secondes.

Tant que `remote`/`token` ne sont pas renseignés dans `/git/edit`, **Publier**
se comporte comme avant : build local uniquement, aucune tentative de push.

## Hébergement

Le CMS a deux parties distinctes, qui n'ont pas besoin du même hébergement :

- **Site public (`project/output/`)** : HTML/CSS statique pur, ne nécessite
  aucun hébergeur Python. N'importe quel hébergeur bas de gamme (même
  orienté PHP, le PHP est simplement ignoré) fait l'affaire, ou plus
  simple/gratuit : GitHub Pages, GitLab Pages, Cloudflare Pages, Netlify.
  C'est tout l'intérêt de la génération statique : zéro dépendance Python
  côté visiteur.
- **Admin (Flask)** : **local uniquement**, via l'app desktop (voir
  [desktop.md](desktop.md)). ⚠️ **Ne jamais l'héberger sur un serveur
  accessible depuis internet sans protection** : sans authentification,
  quiconque atteint l'adresse a un accès complet. Besoin d'édition à
  distance un jour ? Protéger l'accès **au niveau du serveur web** (Basic
  Auth) plutôt que de réintroduire une authentification dans l'app.

## Pistes d'évolution (volontairement non incluses)

- Page contact, export Markdown de secours.
- Multi-plateforme complet pour le paquet desktop (macOS pas encore testé —
  voir [builder.md](builder.md)).
- Signature de code des paquets desktop (Windows/macOS) — voir
  [builder.md](builder.md).
