#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p \
  runtime/postgres \
  runtime/minio \
  runtime/checkpoints/bronze \
  runtime/exports \
  runtime/airflow \
  runtime/superset \
  runtime/neo4j/data \
  runtime/neo4j/import

docker compose up -d --build postgres minio kafka spark neo4j generator kafka-ui
docker compose up --build minio-init kafka-init airflow-init superset-init
docker compose up -d --build trino airflow-webserver airflow-scheduler superset

cat <<'EOF'
Servicios disponibles:
- MinIO:     http://localhost:9001
- Trino:     http://localhost:8080
- Kafka UI:  http://localhost:8082
- Spark UI:  http://localhost:4040-4050
- Superset:  http://localhost:8088
- Airflow:   http://localhost:8081
- Neo4j:     http://localhost:7474

Siguientes pasos recomendados:
1. ./scripts/run_bronze.sh
2. ./scripts/run_generator.sh --events 5000 --sleep-ms 150
3. ./scripts/run_silver.sh
4. ./scripts/run_gold.sh
EOF
