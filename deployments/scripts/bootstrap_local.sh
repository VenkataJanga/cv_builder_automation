#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(dirname "$0")/../.."
LOCAL_DIR="$ROOT_DIR/deployments/local"

cd "$LOCAL_DIR"

if [[ ! -f .env ]]; then
	cp env.example .env
	echo "Created deployments/local/.env from env.example"
fi

docker compose --env-file ./.env up -d
echo "Local environment started"
