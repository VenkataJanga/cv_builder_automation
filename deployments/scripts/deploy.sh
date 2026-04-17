#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-local}"

if [[ "$MODE" == "local" ]]; then
	echo "Starting local stack via docker compose"
	cd "$(dirname "$0")/../local"
	docker compose --env-file ./.env up -d
	echo "Local stack started. API: http://localhost:8000"
	exit 0
fi

if [[ "$MODE" == "aks" ]]; then
	echo "Applying AKS manifests"
	cd "$(dirname "$0")/../aks"
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml
	kubectl apply -f ingress.yaml
	kubectl apply -f hpa.yaml
	echo "AKS deployment manifests applied"
	exit 0
fi

echo "Unsupported deployment mode: $MODE"
echo "Usage: deployments/scripts/deploy.sh [local|aks]"
exit 1
