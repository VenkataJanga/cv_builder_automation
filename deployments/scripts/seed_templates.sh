#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ -f scripts/seed_templates.py ]]; then
	PYTHONPATH=. python scripts/seed_templates.py
	echo "Templates seeded"
else
	echo "No scripts/seed_templates.py found. Skipping template seed step."
fi
