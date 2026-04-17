#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if ! command -v python >/dev/null 2>&1; then
	echo "python is required to run migrations"
	exit 1
fi

PYTHONPATH=. python -m alembic -c alembic.ini upgrade head
echo "Migrations applied successfully"
