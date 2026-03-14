# Fraud Payments Lakehouse

Plataforma de deteccion de fraude en pagos con arquitectura Lakehouse, procesamiento casi en tiempo real y vista relacional y de grafo sobre el mismo dominio.

## Resumen

El proyecto implementa un flujo completo para:

- generar eventos sinteticos de pago en Kafka
- persistir una capa Bronze en Iceberg sobre MinIO con Spark Streaming
- enriquecer el dato en Silver con variables temporales y de comportamiento
- calcular alertas interpretables en Gold con `risk_score` y motivos
- consultar el Lakehouse mediante Trino
- orquestar exportaciones con Airflow
- investigar relaciones sospechosas con Neo4j

## Arquitectura

```text
Generator -> Kafka -> Spark Bronze -> Iceberg/MinIO
                                 -> Spark Silver -> Iceberg/MinIO
                                 -> Spark Gold   -> Iceberg/MinIO

Trino ------> consultas SQL sobre Iceberg
Superset ---> analitica y dashboards
Airflow ----> compactacion/exportacion de dataset de grafo
Neo4j ------> investigacion relacional y de patrones sospechosos
```

## Stack tecnologico

- Apache Kafka
- Apache Spark 3.5
- Apache Iceberg
- MinIO
- Trino
- Apache Airflow
- Apache Superset
- Neo4j
- PostgreSQL
- Docker Compose

## Estructura del repositorio

```text
.
├── airflow/                 # DAGs de orquestacion
├── apps/
│   ├── generator/           # Generador sintetico de eventos
│   └── spark/               # Jobs Bronze, Silver y Gold
├── config/                  # Configuracion de Trino y otros servicios
├── docker/                  # Dockerfiles personalizados
├── docs/                    # Manuales, memoria, presentacion y anexos
├── neo4j/cypher/            # Carga y consultas Cypher
├── orchestration/           # Tareas reutilizables de Airflow
├── scripts/                 # Scripts de operacion
├── sql/                     # Consultas de validacion
└── superset/                # Consultas auxiliares de dashboard
```

## Requisitos

- Docker Desktop
- Docker Compose
- macOS, Linux o Windows con virtualizacion activa
- Recomendado: al menos 8 GB de RAM asignables a Docker

Si trabajas con 8 GB totales de RAM, es recomendable operar por fases y parar servicios no necesarios durante la demo.

## Puesta en marcha

1. Prepara variables de entorno:

```bash
cp .env.example .env
```

2. Arranca toda la plataforma:

```bash
./scripts/start_all.sh
```

3. Ejecuta el flujo principal:

```bash
./scripts/run_bronze.sh
./scripts/run_generator.sh --events 5000 --sleep-ms 150
./scripts/run_silver.sh
./scripts/run_gold.sh
```

Alternativamente:

```bash
make setup-env
make start
make bronze
make generator
make silver
make gold
```

## Interfaces disponibles

- MinIO: `http://localhost:9001`
- Trino: `http://localhost:8080`
- Kafka UI: `http://localhost:8082`
- Spark UI: `http://localhost:4040-4050`
- Superset: `http://localhost:8088`
- Airflow: `http://localhost:8081`
- Neo4j Browser: `http://localhost:7474`

Credenciales por defecto para demo local:

- Airflow: `admin / admin`
- Superset: `admin / admin`
- Neo4j: `neo4j / neo4j_password`

## Flujo operativo recomendado

### 1. Capa Bronze

- Mantener `./scripts/run_bronze.sh` activo
- Ver mensajes en Kafka UI:
  - `local -> Topics -> payments -> Messages`
- Ver micro-batches en Spark UI:
  - `Structured Streaming`

### 2. Capa Silver

- Ejecutar `./scripts/run_silver.sh`
- Consultar con Trino:

```sql
SELECT count(*) FROM iceberg.payments.silver_payments;
```

### 3. Capa Gold

- Ejecutar `./scripts/run_gold.sh`
- Validar alertas:

```sql
SELECT count(*) FROM iceberg.payments.fraud_alerts;
SELECT payment_id, card_id, risk_score, reasons_text
FROM iceberg.payments.fraud_alerts
ORDER BY risk_score DESC
LIMIT 20;
```

### 4. Grafo de investigacion

- Lanzar el DAG `fraud_graph_pipeline` en Airflow
- Validar nodos y relaciones en Neo4j Browser

## Resultados validados en la demo de referencia

- Bronze: `7443` registros
- Silver: `7299` registros
- Gold (`fraud_alerts`): `7049` alertas

## Operacion y mantenimiento

Parar servicios pesados cuando no se necesiten:

```bash
docker compose stop spark generator kafka-ui superset
```

Detener toda la plataforma:

```bash
docker compose down
```

Limpiar runtime local:

```bash
./scripts/clean_all.sh
```

## Documentacion

- [Manual de uso](docs/MANUAL_DE_USO.md)
- [Documentacion tecnica completa](docs/DOCUMENTACION_FINAL.md)
- [Informe de resultados y conclusiones](docs/INFORME_RESULTADOS_Y_CONCLUSIONES.md)
- [Anexo de soluciones a errores](docs/ANEXO_SOLUCIONES_A_POSIBLES_ERRORES.md)
- [Presentacion del proyecto](docs/PRESENTACION_PROYECTO.html)
- [Referencias](docs/REFERENCIAS.md)

## Seguridad

Este repositorio esta orientado a demostracion y entorno local. No uses las credenciales de ejemplo en entornos reales.

## Licencia

Este proyecto se distribuye bajo licencia [MIT](LICENSE).
