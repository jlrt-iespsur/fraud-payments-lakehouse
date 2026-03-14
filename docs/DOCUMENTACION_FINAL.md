# Documento final del proyecto

## 1. Objetivo

Disenar e implementar un sistema de deteccion de pagos fraudulentos en arquitectura Lakehouse con:

- Kafka para ingesta de eventos.
- Spark para procesamiento streaming y batch.
- Iceberg sobre MinIO para almacenamiento Bronze, Silver y Gold.
- Trino para consulta SQL.
- Superset para visualizacion.
- Airflow para orquestacion manual.
- Neo4j para analisis de relaciones y fraude conectado.

El proyecto se ha preparado para ejecutarse en local con Docker Compose, una red comun y scripts operativos de arranque, reinicio y limpieza.

## 2. Alcance entregado

Se han creado los siguientes bloques:

- `docker-compose.yml` con todos los servicios conectados a la red `lakehouse`.
- Generador sintetico de eventos de pagos hacia Kafka.
- Job Spark Streaming para Bronze.
- Job Spark batch para Silver con limpieza, casting y enriquecimiento temporal.
- Job Spark batch para Gold con reglas y tabla `fraud_alerts`.
- Tabla `graph_payments` preparada para exportacion a Neo4j.
- DAG manual de Airflow para compactacion, exportacion de snapshot y carga en Neo4j.
- Consultas Cypher de investigacion.
- Kafka UI para inspeccion visual de topics y mensajes.
- Spark UI expuesta para seguimiento visual del job de streaming.
- Scripts generales de arranque, reinicio, limpieza y ejecucion de jobs.
- SQL de ayuda para Trino y Superset.
- Manual operativo para uso y exposicion en [MANUAL_DE_USO.md](../docs/MANUAL_DE_USO.md).
- Informe de resultados y conclusiones en [INFORME_RESULTADOS_Y_CONCLUSIONES.md](../docs/INFORME_RESULTADOS_Y_CONCLUSIONES.md).
- Anexo de incidencias y correcciones en [ANEXO_SOLUCIONES_A_POSIBLES_ERRORES.md](../docs/ANEXO_SOLUCIONES_A_POSIBLES_ERRORES.md).
- Referencias oficiales y proyectos comparables en [docs/REFERENCIAS.md](../docs/REFERENCIAS.md).

## 3. Arquitectura propuesta

### Flujo de datos

1. El generador publica eventos JSON de pago en el topic `payments`.
2. Spark Structured Streaming consume Kafka y persiste la capa Bronze en Iceberg.
3. Un job batch genera Silver desde Bronze:
   - tipado correcto
   - deduplicacion
   - variables derivadas por ventana temporal
4. Un job batch genera Gold desde Silver:
   - reglas de riesgo
   - `fraud_alerts`
   - `graph_payments`
5. Trino consulta las tablas Iceberg.
6. Superset consume Trino para el dashboard.
7. Airflow, al lanzarse manualmente, compacta Iceberg y genera una exportacion tabular para Neo4j.
8. Neo4j carga nodos y relaciones para investigacion.

### Decision de catalogo Iceberg

Se ha elegido `JdbcCatalog` de Iceberg apoyado en PostgreSQL y warehouse S3-compatible en MinIO. El motivo es reducir complejidad operacional: evita levantar Hive Metastore o REST catalog adicionales y sigue un camino documentado por Iceberg y Trino.

### Aclaracion sobre AWS y MinIO

Aunque en la configuracion aparecen variables como `AWS_REGION`, el proyecto no usa AWS real ni requiere cuenta de Amazon.

La razon es tecnica:

- MinIO implementa una API compatible con S3
- Iceberg usa el SDK de AWS para hablar con almacenes tipo S3
- ese SDK exige una region explicita aunque el endpoint sea local

Por eso se fija `us-east-1` como valor estable para que Spark e Iceberg puedan operar contra MinIO sin intentar autodetectar una region inexistente.

### Decision sobre la imagen de Spark

Se usa una imagen local definida en [docker/spark/Dockerfile](../docker/spark/Dockerfile) en lugar de una tag versionada publica de Bitnami.

Motivo:

- las tags versionadas publicas de Bitnami han dejado de ser estables o accesibles de la misma forma desde los cambios de catalogo anunciados por Bitnami en 2025
- el proyecto necesita mantener compatibilidad con Spark 3.5.x y Scala 2.12 para los paquetes usados en `spark-submit`
- construir localmente la imagen fija el comportamiento y evita depender de una tag externa que puede desaparecer

### Tablas previstas

- Bronze: `iceberg.payments.bronze_payments`
- Silver: `iceberg.payments.silver_payments`
- Gold alertas: `iceberg.payments.fraud_alerts`
- Gold grafo: `iceberg.payments.graph_payments`

## 4. Implementacion por partes

### Parte 1. Generacion de eventos en Kafka

Archivo principal:

- [payment_event_generator.py](../apps/generator/payment_event_generator.py)

Campos generados:

- `event_time`
- `payment_id`
- `customer_id`
- `card_id`
- `merchant_id`
- `device_id`
- `ip`
- `country`
- `amount`
- `currency`
- `status`
- `mcc`

Campos adicionales para trazabilidad del dataset sintetico:

- `payment_group_id`
- `attempt_number`
- `scenario`

Comportamientos simulados:

- pagos normales
- reintentos sobre pagos declinados
- patrones sospechosos con mayor importe, paises variados y dispositivos compartidos
- duplicados esporadicos para poder validar la deduplicacion de Silver

Ejecucion:

```bash
./scripts/run_generator.sh --events 5000 --sleep-ms 150
```

### Parte 2. Bronze

Archivo principal:

- [bronze_to_iceberg.py](../apps/spark/bronze_to_iceberg.py)

Funcion:

- lee del topic Kafka `payments`
- parsea JSON
- conserva el esquema operativo de llegada
- anade solo `ingestion_ts` como metadato tecnico
- escribe en Iceberg con checkpoint local

Ejecucion:

```bash
./scripts/run_bronze.sh
```

Nota:

- el job es de larga duracion y se mantiene escuchando Kafka
- el checkpoint queda en `runtime/checkpoints/bronze`
- mientras esta corriendo, la Spark UI queda accesible en `http://localhost:4040`
- la pestana principal para la demo es `Structured Streaming`, donde se pueden revisar `Input Rate`, `Process Rate`, `Input Rows` y `Batch Duration`
- el proyecto expone `4040-4050` para poder ver varias UIs de Spark si Bronze, Silver y Gold se ejecutan a la vez

### Parte 3. Silver

Archivo principal:

- [silver_enrichment.py](../apps/spark/silver_enrichment.py)

Transformaciones:

- conversion de `event_time` a timestamp
- deduplicacion por `payment_id`
- calculo de:
  - `tx_by_card_5m`
  - `distinct_merchants_10m`
  - `distinct_countries_1h`
  - `distinct_cards_per_device`
  - `declined_ratio_1h`

Ejecucion:

```bash
./scripts/run_silver.sh
```

Seguimiento recomendado:

- terminal: debe finalizar sin error y devolver el prompt
- Spark UI: si Bronze sigue vivo, Silver suele quedar en `http://localhost:4041`
- Trino: validar recuento de `silver_payments` y revisar columnas derivadas

### Parte 4. Gold

Archivo principal:

- [gold_fraud_detection.py](../apps/spark/gold_fraud_detection.py)

Reglas implementadas:

- alta velocidad por tarjeta en 5 minutos
- demasiados comercios distintos en 10 minutos
- demasiados paises distintos en 1 hora
- dispositivo compartido por demasiadas tarjetas
- ratio elevado de transacciones rechazadas
- importe alto

Salidas:

- `fraud_alerts`
- `graph_payments`

Ejecucion:

```bash
./scripts/run_gold.sh
```

Seguimiento recomendado:

- terminal: debe finalizar sin error
- Spark UI: si ya hay otros jobs Spark vivos, Gold suele aparecer en el siguiente puerto libre
- Trino: consultar `fraud_alerts` y validar `risk_score` y `reasons_text`

### Parte 5. Consulta y visualizacion

Archivos de apoyo:

- [iceberg.properties](../config/trino/catalog/iceberg.properties)
- [dashboard_queries.sql](../superset/dashboard_queries.sql)
- [verification.sql](../sql/trino/verification.sql)

Interfaces de apoyo visual:

- Kafka UI en `http://localhost:8082`
- Spark UI en `http://localhost:4040`

Uso recomendado en demo:

- Kafka UI:
  - cluster `local`
  - menu `Topics`
  - topic `payments`
  - pestana `Messages`
- Spark UI:
  - pestana `Structured Streaming`
  - abrir el `run id`
  - observar `Input Rate`, `Process Rate`, `Input Rows` y `Batch Duration`

URI recomendada para Superset:

```text
trino://trino@trino:8080/iceberg/payments
```

Pasos manuales en Superset:

1. Entrar como admin en `http://localhost:8088`.
2. Ir a `Settings -> Data -> Database Connections`.
3. Crear conexion con la URI anterior.
4. Registrar `iceberg.payments.silver_payments` y `iceberg.payments.fraud_alerts` como datasets.
5. Crear visualizaciones:
   - KPI total transacciones
   - KPI total alertas
   - serie temporal por hora
   - top merchants por riesgo
   - top cards por riesgo
6. Guardarlas en un dashboard llamado `Fraud Monitoring`.

Motivo por el que esta parte se deja guiada y no autoimportada:

- Superset es principalmente una herramienta GUI y el repositorio no dispone de un entorno ya levantado para capturar IDs, UUIDs y exportables reales del dashboard.
- Se dejan queries y pasos exactos para crear el dashboard sin improvisacion.

### Parte 6. Orquestacion bajo demanda con Airflow

Archivos:

- [fraud_graph_pipeline.py](../airflow/dags/fraud_graph_pipeline.py)
- [lakehouse_tasks.py](../orchestration/lakehouse_tasks.py)

Caracteristicas del DAG:

- `schedule=None`
- ejecucion manual
- parametros:
  - `source_table`
  - `start_ts`
  - `end_ts`
  - `graph_name`

Tareas:

1. compactar la tabla Iceberg con `ALTER TABLE ... EXECUTE optimize`
2. generar el dataset de exportacion de grafo filtrado por rango temporal
3. exportar CSVs a `runtime/exports/<graph_name>` y `runtime/neo4j/import/<graph_name>`
4. cargar el grafo en Neo4j

### Parte 7. Grafo en Neo4j

Archivos:

- [constraints.cypher](../neo4j/cypher/constraints.cypher)
- [load_graph.cypher](../neo4j/cypher/load_graph.cypher)
- [investigation_queries.cypher](../neo4j/cypher/investigation_queries.cypher)

Modelo:

- nodos `Customer`
- nodos `Card`
- nodos `Device`
- nodos `Merchant`
- nodos `Payment`

Relaciones:

- `(:Customer)-[:OWNS_CARD]->(:Card)`
- `(:Card)-[:USED_ON]->(:Device)`
- `(:Card)-[:AUTHORIZED]->(:Payment)`
- `(:Payment)-[:AT_MERCHANT]->(:Merchant)`

Consultas incluidas:

- dispositivos compartidos por multiples tarjetas
- tarjetas usadas en multiples paises
- comercios conectados a multiples entidades sospechosas
- agrupaciones anomalias por dispositivo compartido

## 5. Puesta en marcha

### 5.1 Arranque de toda la plataforma

```bash
cp .env.example .env
./scripts/start_all.sh
```

### 5.2 Pipeline de datos

Terminal 1:

```bash
./scripts/run_bronze.sh
```

Terminal 2:

```bash
./scripts/run_generator.sh --events 5000 --sleep-ms 150
```

Terminal 3:

```bash
./scripts/run_silver.sh
./scripts/run_gold.sh
```

### 5.3 Reinicio completo

```bash
./scripts/restart_all.sh
```

### 5.4 Limpieza total

```bash
./scripts/clean_all.sh
```

## 6. Consultas de verificacion

Con el cliente de Trino:

```bash
docker compose exec trino trino
```

Y despues:

```sql
SHOW TABLES FROM iceberg.payments;
SELECT count(*) FROM iceberg.payments.bronze_payments;
SELECT count(*) FROM iceberg.payments.silver_payments;
SELECT count(*) FROM iceberg.payments.fraud_alerts;
SELECT * FROM iceberg.payments.fraud_alerts ORDER BY risk_score DESC LIMIT 20;
```

## 7. Notas operativas

- Todas las piezas estan en la misma red Docker `lakehouse`.
- `scripts/start_all.sh` crea directorios runtime si faltan.
- MinIO inicializa automaticamente el bucket `lakehouse`.
- Kafka crea automaticamente el topic `payments`.
- El dashboard de Superset queda documentado pero requiere ejecucion GUI manual.
- El DAG de Airflow queda listo para lanzarse manualmente desde la UI.

## 8. Limitaciones y validacion pendiente

Hay una limitacion importante que conviene dejar explicita:

- En este entorno de trabajo no se ha levantado la plataforma Docker completa ni se han descargado las imagenes, por lo que no he podido validar en caliente el `docker-compose`, la compatibilidad exacta de todas las tags ni la conectividad final entre servicios.

Eso implica:

- la arquitectura y los ficheros estan preparados con base en documentacion oficial y patrones ya usados en proyectos similares
- la primera ejecucion real debe validar:
  - disponibilidad exacta de las tags de imagen
  - permisos de montaje de volumentes
  - acceso de Spark a paquetes Maven al ejecutar `spark-submit --packages`
  - arranque correcto de Superset y Airflow con sus imagenes extendidas

Si alguno de esos puntos falla en tu maquina, la correccion debe hacerse sobre el error concreto observado, no especulando antes.

## 9. Referencias usadas

### Documentacion oficial

- Spark Structured Streaming + Kafka Integration Guide: <https://spark.apache.org/docs/3.5.6/structured-streaming-kafka-integration.html>
- Spark Structured Streaming Programming Guide: <https://spark.apache.org/docs/3.5.0/structured-streaming-programming-guide.html>
- Iceberg Spark configuration: <https://iceberg.apache.org/docs/latest/spark-configuration/>
- Iceberg Structured Streaming: <https://iceberg.apache.org/docs/1.9.2/docs/spark-structured-streaming/>
- Iceberg JDBC catalog: <https://iceberg.apache.org/docs/1.4.3/jdbc/>
- Trino Iceberg connector: <https://trino.io/docs/current/connector/iceberg>
- Superset database connections: <https://superset.apache.org/docs/6.0.0/configuration/databases>
- Airflow Params: <https://airflow.apache.org/docs/apache-airflow/2.10.5/core-concepts/params.html>
- MinIO container single-node deployment: <https://min.io/docs/minio/container/operations/install-deploy-manage/deploy-minio-single-node-single-drive.html>
- Neo4j `LOAD CSV`: <https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/>

### Proyectos y demos similares consultados

- Elkoumy real-time data lake: <https://github.com/Elkoumy/real_time_data_lake>
- fortiql data-forge: <https://github.com/fortiql/data-forge>
- abeltavares real-time-data-pipeline: <https://github.com/abeltavares/real-time-data-pipeline>
- minio openlake: <https://github.com/minio/openlake>
- Neo4j fraud demo: <https://neo4j.com/developer/demos/fraud-demo/>
- Neo4j bank fraud detection graph gist: <https://neo4j.com/graphgists/bank-fraud-detection/>

## 10. Siguiente validacion recomendada

El orden mas razonable para verificar el proyecto en una maquina con Docker y red es:

1. levantar infraestructura con `./scripts/start_all.sh`
2. comprobar UI y salud basica de MinIO, Trino, Superset, Airflow y Neo4j
3. arrancar Bronze
4. generar eventos
5. construir Silver
6. construir Gold
7. lanzar queries de Trino
8. crear dashboard en Superset
9. ejecutar el DAG manual y revisar Neo4j

Ese orden minimiza el numero de variables a la vez y permite aislar fallos de integracion con rapidez.
