# Dev — installation locale

Pour ce que fait le CMS une fois lancé, voir [app.md](app.md).

## Installation

```bash
./dev.sh                # http://127.0.0.1:5000
./dev.sh ../autre-site   # contre les données d'un autre site cloné à côté
```

Crée le venv, installe les dépendances, initialise la base si besoin,
lance en mode debug — voir les commentaires en tête de `dev.sh` pour le
détail. Rédiger, puis cliquer **Publier** (ou `flask --app cms.app
publish`) : le site statique est écrit dans `project/output/`.

## Structure du code

- `cms/` — le package de l'app Flask (voir [app.md](app.md) pour ce qu'il
  fait). Imports internes en relatif (`from .config import ...`) : lancer
  toujours via `./dev.sh`, `flask --app cms.app ...` ou `python -m cms.xxx`
  depuis la racine du dépôt, pas `python cms/app.py` directement.
- `builder/` — packaging de l'exécutable desktop (PyInstaller), voir
  [builder.md](builder.md).
- `project/` — données d'**un** site (base, uploads, site publié), jamais de
  code ici.

## Variables d'environnement

Voir le tableau dans [app.md](app.md). `dev.sh` positionne
`PORTFOLIO_SECRET_KEY` et `PORTFOLIO_BASE_DIR` (si un argument lui est
passé) ; les autres se positionnent à la main (`export ...`) si besoin.

⚠️ **Ne pas pointer seulement `PORTFOLIO_DB`/`PORTFOLIO_UPLOADS`/
`PORTFOLIO_OUTPUT` vers un autre site sans `PORTFOLIO_BASE_DIR`** (via un
lien symbolique `project -> ../autre-site/project`, par exemple) :
**Publier** cible toujours `BASE_DIR` pour le `git push` — donc ce checkout
de code, pas le dépôt de l'autre site — avec le remote/token de l'autre
site chargés depuis sa base. Résultat : Publier pousserait le mauvais
contenu vers le GitLab de l'autre site (avec repli en force-push si les
historiques divergent). `./dev.sh ../autre-site` évite ce piège en
déplaçant `project/` et la cible git ensemble.

## Base existante / migrations

Ce projet n'a pas de système de migration formel (pas d'Alembic) : les
changements de schéma sur une base de dev déjà peuplée (ajout de colonne,
changement de contrainte...) se font à la main via `sqlite3`
(`ALTER TABLE`, ou reconstruction de table pour SQLite qui ne sait pas tout
modifier en place).
