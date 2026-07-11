# Dev — installation locale

Pour ce que fait le CMS une fois lancé, voir [app.md](app.md).

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export PORTFOLIO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
flask --app cms.app init-db
flask --app cms.app run             # http://127.0.0.1:5000
```

Rédiger, puis cliquer **Publier** (ou `flask --app cms.app publish`). Le
site statique est écrit dans `project/output/`.

Pour itérer avec le rechargement automatique : `flask --app cms.app run
--debug`.

## Structure du code

- `cms/` — le package de l'app Flask (voir [app.md](app.md) pour ce qu'il
  fait). Imports internes en relatif (`from .config import ...`) : lancer
  toujours via `flask --app cms.app ...` ou `python -m cms.xxx` depuis la
  racine du dépôt, pas `python cms/app.py` directement.
- `builder/` — packaging de l'exécutable desktop (PyInstaller), voir
  [builder.md](builder.md).
- `project/` — données d'**un** site (base, uploads, site publié), jamais de
  code ici. Les variables d'environnement (voir [app.md](app.md)) permettent
  de pointer vers un autre dossier `project/` si besoin.

## Variables d'environnement

Voir le tableau dans [app.md](app.md) — les mêmes variables s'appliquent en
dev, juste positionnées à la main (`export ...`) plutôt que par
`builder/desktop_launcher.py`.

## Développer contre un autre site (`PORTFOLIO_BASE_DIR`)

Pour lancer ce checkout de code contre les données réelles d'un autre site
cloné à côté (ex. `../marc-geneix/`, dépôt content-only avec son propre
`project/` et son propre `.git`) :

```bash
PORTFOLIO_BASE_DIR=../marc-geneix flask --app cms.app run
```

`PROJECT_DIR` (donc `project/instance`, `project/uploads`, `project/output`)
se recalcule automatiquement sous `PORTFOLIO_BASE_DIR` — pas besoin de
positionner `PORTFOLIO_DB`/`PORTFOLIO_UPLOADS`/`PORTFOLIO_OUTPUT` en plus.

⚠️ **Ne pas pointer seulement `PORTFOLIO_DB`/`PORTFOLIO_UPLOADS`/
`PORTFOLIO_OUTPUT` vers un autre site sans `PORTFOLIO_BASE_DIR`** (via un
lien symbolique `project -> ../autre-site/project`, par exemple) : le
bouton **Publier** cible toujours `BASE_DIR` pour le `git push`
(`cms/git_publish.py`), qui resterait ce checkout de code — pas le dépôt de
contenu de l'autre site. Avec un remote/token déjà configurés dans
`GitConfig` (chargé depuis la base de l'autre site via le lien symbolique),
cliquer Publier pousserait alors le mauvais dépôt vers le remote GitLab de
l'autre site, avec repli en force-push si les historiques divergent.
`PORTFOLIO_BASE_DIR` évite ce piège en déplaçant `project/` **et** la cible
git ensemble.

## Base existante / migrations

Ce projet n'a pas de système de migration formel (pas d'Alembic) : les
changements de schéma sur une base de dev déjà peuplée (ajout de colonne,
changement de contrainte...) se font à la main via `sqlite3`
(`ALTER TABLE`, ou reconstruction de table pour SQLite qui ne sait pas tout
modifier en place).
