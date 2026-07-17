# Le builder — paquet desktop autonome

Comment fabriquer l'exécutable desktop à partir des sources. Pour
simplement **lancer** un exécutable déjà construit, voir
[desktop.md](desktop.md) — ce document est pour qui construit le paquet, pas
pour qui l'utilise.

## Principe

`builder/desktop_launcher.py` est un petit lanceur (démarre Flask, ouvre le
navigateur par défaut sur `http://127.0.0.1:5000` via le module stdlib
`webbrowser` — aucun toolkit GUI, pas de fenêtre native) qui remplace
`flask --app cms.app run` pour un usage sans venv Python ni ligne de
commande. `builder/desktop.spec` (PyInstaller) le fige en exécutable
autonome, avec `cms/templates` et `cms/static` embarqués. Une petite console
reste ouverte pendant que le serveur tourne (voir [desktop.md](desktop.md)) —
zéro dépendance de toolkit GUI (ni GTK/WebKit sur Linux, ni pythonnet sur
Windows, ni pyobjc sur macOS), contrairement à une version antérieure basée
sur `pywebview` (fenêtre native) qui imposait ces trois-là et causait des
plantages au runtime sur Linux (conflit de version entre libs bundlées et
libs système du poste cible — piège vécu, documenté dans CLAUDE.md avant
d'être contourné par ce changement d'architecture plutôt que patché plus
avant).

Ce paquet est un figé destiné au partage, pas un outil d'itération : pour
développer/tester des changements, reste sur `flask --app cms.app run
--debug` (ou `python3 builder/desktop_launcher.py`) depuis les sources —
voir [dev.md](dev.md).

## Construire en local

```bash
source .venv/bin/activate
pip install pyinstaller      # outil de build, pas une dépendance runtime :
                              # ne pas l'ajouter à requirements.txt
pyinstaller builder/desktop.spec
```

Résultat : `dist/PortfolioCMS/` (à zipper pour le partager) — `PortfolioCMS`
(exécutable à lancer) + `_internal/` (Python, dépendances, `cms/templates`/
`cms/static` embarqués — ne pas y toucher). `project/` (`instance/`,
`uploads/`, `output/`) est créé à côté de l'exécutable (pas dans
`_internal/`) au premier lancement — pour repartir d'un site vierge, il
suffit de renommer/retirer ce dossier ; pour changer de site, on le
remplace par un autre dossier `project/` exporté ailleurs.

`pyinstaller` ne fait pas de cross-compilation : ce qui tourne sur Linux ne
produit un exécutable QUE pour Linux. Pour Windows/macOS, voir le build
GitHub Actions ci-dessous.

### Piège connu : chemin des `datas` dans `desktop.spec`

`app.py` vit dans le package `cms/` : Flask résout `templates`/`static`
relativement à l'emplacement du module `cms.app` lui-même. En figé
(PyInstaller), ça veut dire que ces dossiers doivent être placés sous
`_internal/cms/templates` et `_internal/cms/static` — **pas**
`_internal/templates` — sans quoi l'app démarre mais toute page plante en
`TemplateNotFound`. `builder/desktop.spec` gère déjà ça correctement
(`datas=[(..., "cms/templates"), (..., "cms/static")]`) ; à revérifier si le
`cms/app.py` bouge encore de place un jour.

## Build multi-plateforme (GitHub Actions)

Un workflow **par plateforme**
(`.github/workflows/build-desktop-{linux,windows,macos-intel,macos-arm}.yml`),
pour ne lancer que celui dont on a besoin plutôt que de reconstruire les 4 à
chaque fois — chacun sur le runner GitHub correspondant, avec son propre
`pyinstaller builder/desktop.spec` (pas de cross-compilation). Déclenchement
**manuel uniquement** : onglet *Actions* du dépôt GitHub → choisir le
workflow (ex. *Build desktop package (Windows)*) → *Run workflow*. Une fois
le run terminé, le zip (`portfolio-cms-linux-x64`, `-windows-x64`,
`-macos-x64` ou `-macos-arm64`) est téléchargeable dans la section
*Artifacts* du run (rétention par défaut : 90 jours) — un seul niveau de zip
(le conteneur ajouté par GitHub au téléchargement), pas de zip imbriqué.

**Publier directement dans une Release GitHub** (optionnel) : au moment de
*Run workflow*, remplir le champ *Tag de release GitHub* (ex. `v1.0.0`) —
sinon le laisser vide pour se limiter à l'artefact du run, comportement par
défaut inchangé. Si rempli, le workflow crée (ou met à jour, si elle existe
déjà) la Release correspondant à ce tag et y attache son zip. Lancer les 4
workflows avec le **même tag** accumule les 4 zips sur une seule Release (un
workflow n'écrase jamais les assets déposés par les autres).

Linux confirmé fonctionnel en local (build + lancement réel, voir
CLAUDE.md) depuis le retrait de pywebview ; Windows et macOS (Intel/ARM) à
revérifier via le vrai pipeline CI suite à ce changement (l'ancienne
confirmation portait sur la version pywebview, désormais obsolète).

## Signature de code (pas encore fait)

Pas de signature de code pour l'instant : au premier lancement, Windows
affichera un avertissement SmartScreen et macOS bloquera via Gatekeeper (voir
[desktop.md](desktop.md) pour comment l'utilisateur final contourne ça). À
envisager seulement si la friction devient un problème pour de vrais
utilisateurs : certificat de signature Windows + compte Apple Developer
(99$/an, requis pour la notarisation macOS).
