#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose down -v --remove-orphans || true
rm -rf \
  runtime/postgres \
  runtime/minio \
  runtime/checkpoints \
  runtime/exports \
  runtime/airflow/logs \
  runtime/superset \
  runtime/neo4j/data \
  runtime/neo4j/import/*

mkdir -p \
  runtime/postgres \
  runtime/minio \
  runtime/checkpoints/bronze \
  runtime/exports \
  runtime/airflow/logs \
  runtime/superset \
  runtime/neo4j/data \
  runtime/neo4j/import

echo "Entorno eliminado. Puedes arrancar desde cero con ./scripts/start_all.sh"
