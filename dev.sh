#!/usr/bin/env bash
# Launch the CMS locally in Flask debug mode (auto-reload). See docs/dev.md.
# Usage: ./dev.sh [dossier-du-site]   (ex: ./dev.sh ../julientaubarchitecte)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

site_dir="${1:-}"

if [ -n "$site_dir" ]; then
    export PORTFOLIO_BASE_DIR
    PORTFOLIO_BASE_DIR="$(cd "$site_dir" && pwd)"
    base_dir="$PORTFOLIO_BASE_DIR"
else
    base_dir="$(pwd)"
fi

if [ ! -d .venv ]; then
    echo "Création du venv…"
    python3 -m venv .venv
fi
.venv/bin/python3 -m pip install -q -r requirements.txt

project_dir="$base_dir/project"
instance_dir="$project_dir/instance"
secret_file="$instance_dir/secret_key"
mkdir -p "$instance_dir" "$project_dir/uploads"

if [ -f "$secret_file" ]; then
    PORTFOLIO_SECRET_KEY="$(cat "$secret_file")"
else
    PORTFOLIO_SECRET_KEY="$(.venv/bin/python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    echo "$PORTFOLIO_SECRET_KEY" > "$secret_file"
fi
export PORTFOLIO_SECRET_KEY

if [ ! -f "$instance_dir/portfolio.sqlite" ]; then
    echo "Base absente, initialisation…"
    .venv/bin/python3 -m flask --app cms.app init-db
fi

echo "Lancement sur http://127.0.0.1:5000 (Ctrl+C pour arrêter)"
exec .venv/bin/python3 -m flask --app cms.app run --debug
