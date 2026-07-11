# Portfolio CMS

Petit CMS de portfolio en Flask + SQLite. Une interface d'admin permet de
rédiger articles, tags et pages, d'uploader des photos, de prévisualiser,
puis de **générer un site statique** publiable n'importe où (aucune
dépendance Python côté visiteur).

Deux façons de le faire tourner :

- en **app Flask locale**, depuis les sources (pour développer, ou
  s'auto-héberger en confiance) ;
- en **paquet desktop autonome** (exécutable, pas de Python à installer) —
  ce que la plupart des utilisateurs veulent.

**Pas d'authentification** : usage local uniquement, à ne jamais exposer
au-delà de `127.0.0.1`/un réseau de confiance — détails dans
[docs/app.md](docs/app.md).

```
Admin Flask ──(Publier)──▶ project/output/ (HTML statique) ──▶ n'importe quel hébergeur
     │
     └── SQLite (project/instance/portfolio.sqlite) + project/uploads/ (images)
```

## Documentation

| | |
|---|---|
| [docs/app.md](docs/app.md) | Fonctionnement du CMS : architecture, modèle de données, sauvegarde, publication GitLab Pages, hébergement. |
| [docs/dev.md](docs/dev.md) | Installation et lancement en local pour développer. |
| [docs/desktop.md](docs/desktop.md) | Lancer le paquet desktop déjà construit (Linux/Windows/macOS). |
| [docs/builder.md](docs/builder.md) | Construire le paquet desktop (PyInstaller, build multi-plateforme via GitHub Actions). |

## Démarrage rapide (dev)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PORTFOLIO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
flask --app cms.app init-db
flask --app cms.app run             # http://127.0.0.1:5000
```

Détails dans [docs/dev.md](docs/dev.md).
