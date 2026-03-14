# Documento final del proyecto

## 1. Objetivo

Diseñar e implementar un sistema de detección de pagos fraudulentos en arquitectura Lakehouse con:

- Kafka para ingesta de eventos.
- Spark para procesamiento streaming y batch.
- Iceberg sobre MinIO para almacenamiento Bronze, Silver y Gold.
- Trino para consulta SQL.
- Superset para visualización.
- Airflow para orquestación manual.
- Neo4j para análisis de relaciones y fraude conectado.

El proyecto se ha preparado para ejecutarse en local con Docker Compose, una red común y scripts operativos de arranque, reinicio y limpieza.

## 2. Alcance entregado

Se han creado los siguientes bloques:

- `docker-compose.yml` con todos los servicios conectados a la red `lakehouse`.
- Generador sintético de eventos de pagos hacia Kafka.
- Job Spark Streaming para Bronze.
- Job Spark batch para Silver con limpieza, casting y enriquecimiento temporal.
- Job Spark batch para Gold con reglas y tabla `fraud_alerts`.
- Tabla `graph_payments` preparada para exportación a Neo4j.
- DAG manual de Airflow para compactación, exportación de snapshot y carga en Neo4j.
- Consultas Cypher de investigación.
- Kafka UI para inspección visual de topics y mensajes.
- Spark UI expuesta para seguimiento visual del job de streaming.
- Scripts generales de arranque, reinicio, limpieza y ejecución de jobs.
- SQL de ayuda para Trino y Superset.
- Manual operativo para uso y exposición en [MANUAL_DE_USO.md](../docs/MANUAL_DE_USO.md).
- Informe de resultados y conclusiones en [INFORME_RESULTADOS_Y_CONCLUSIONES.md](../docs/INFORME_RESULTADOS_Y_CONCLUSIONES.md).
- Anexo de incidencias y correcciones en [ANEXO_SOLUCIONES_A_POSIBLES_ERRORES.md](../docs/ANEXO_SOLUCIONES_A_POSIBLES_ERRORES.md).
- Referencias oficiales y proyectos comparables en [docs/REFERENCIAS.md](../docs/REFERENCIAS.md).

## 3. Arquitectura propuesta

### Flujo de datos

1. El generador publica eventos JSON de pago en el topic `payments`.
2. Spark Structured Streaming consume Kafka y persiste la capa Bronze en Iceberg.
3. Un job batch genera Silver desde Bronze:
   - tipado correcto
   - deduplicación
   - variables derivadas por ventana temporal
4. Un job batch genera Gold desde Silver:
   - reglas de riesgo
   - `fraud_alerts`
   - `graph_payments`
5. Trino consulta las tablas Iceberg.
6. Superset consume Trino para el dashboard.
7. Airflow, al lanzarse manualmente, compacta Iceberg y genera una exportación tabular para Neo4j.
8. Neo4j carga nodos y relaciones para investigación.

### Decisión de catálogo Iceberg

Se ha elegido `JdbcCatalog` de Iceberg apoyado en PostgreSQL y warehouse S3-compatible en MinIO. El motivo es reducir complejidad operacional: evita levantar Hive Metastore o REST catalog adicionales y sigue un camino documentado por Iceberg y Trino.

### Aclaración sobre AWS y MinIO

Aunque en la configuración aparecen variables como `AWS_REGION`, el proyecto no usa AWS real ni requiere cuenta de Amazon.

La razón es técnica:

- MinIO implementa una API compatible con S3
- Iceberg usa el SDK de AWS para hablar con almacenes tipo S3
- ese SDK exige una región explícita aunque el endpoint sea local

Por eso se fija `us-east-1` como valor estable para que Spark e Iceberg puedan operar contra MinIO sin intentar autodetectar una región inexistente.

### Decisión sobre la imagen de Spark

Se usa una imagen local definida en [docker/spark/Dockerfile](../docker/spark/Dockerfile) en lugar de una tag versionada pública de Bitnami.

Motivo:

- las tags versionadas públicas de Bitnami han dejado de ser estables o accesibles de la misma forma desde los cambios de catálogo anunciados por Bitnami en 2025
- el proyecto necesita mantener compatibilidad con Spark 3.5.x y Scala 2.12 para los paquetes usados en `spark-submit`
- construir localmente la imagen fija el comportamiento y evita depender de una tag externa que puede desaparecer

### Tablas previstas

- Bronze: `iceberg.payments.bronze_payments`
- Silver: `iceberg.payments.silver_payments`
- Gold alertas: `iceberg.payments.fraud_alerts`
- Gold grafo: `iceberg.payments.graph_payments`

## 4. Scripts operativos

### `start_all.sh`

Es el script de arranque general del proyecto.

Para qué sirve:

- crear la estructura mínima de `runtime`
- construir las imágenes necesarias
- levantar la infraestructura base
- ejecutar inicializaciones de MinIO, Kafka, Airflow y Superset

Cuándo conviene usarlo:

- al clonar el proyecto
- al arrancar desde cero
- antes de una demo o una validación completa

### `restart_all.sh`

Reinicia la plataforma sin borrar la persistencia local.

Para qué sirve:

- bajar y volver a levantar todos los servicios
- recuperar un estado estable si varios contenedores han quedado tocados

Cuándo conviene usarlo:

- si Airflow, Trino o Superset se han quedado en un estado raro
- si quieres reiniciar todo sin hacer una limpieza completa

### `clean_all.sh`

Limpia el entorno local y deja el proyecto listo para empezar desde cero.

Para qué sirve:

- borrar datos persistidos y checkpoints
- eliminar exportaciones previas
- resetear el entorno para una prueba limpia

Cuándo conviene usarlo:

- si necesitas una ejecución totalmente limpia
- si sospechas que hay residuos de pruebas anteriores
- antes de una validación final reproducible

### `run_bronze.sh`

Lanza el job de Spark Streaming que consume Kafka y escribe Bronze en Iceberg.

Cuándo conviene usarlo:

- después de `start_all.sh`
- antes de generar eventos
- mientras quieras mantener viva la ingesta

Comportamiento esperado:

- se queda en ejecución
- debe ir en una terminal aparte

### `run_generator.sh`

Ejecuta el generador de eventos sintéticos.

Cuándo conviene usarlo:

- cuando Bronze ya está escuchando
- cuando necesitas poblar Kafka con nuevos eventos

Comportamiento esperado:

- termina al alcanzar el número de eventos indicado
- permite ajustar volumen y ritmo con `--events` y `--sleep-ms`

### `run_silver.sh`

Construye la capa Silver a partir de Bronze.

Cuándo conviene usarlo:

- después de haber generado suficientes eventos
- cuando Bronze ya haya escrito datos en Iceberg

Comportamiento esperado:

- es un job batch
- termina y devuelve el prompt

### `run_gold.sh`

Construye la capa Gold a partir de Silver.

Cuándo conviene usarlo:

- después de `run_silver.sh`
- cuando quieres recalcular alertas y preparar el dataset de grafo

Comportamiento esperado:

- es un job batch
- termina y devuelve el prompt

### Orden recomendado de uso

Para una ejecución normal:

1. `./scripts/start_all.sh`
2. `./scripts/run_bronze.sh`
3. `./scripts/run_generator.sh --events 5000 --sleep-ms 150`
4. `./scripts/run_silver.sh`
5. `./scripts/run_gold.sh`

Para mantenimiento:

1. `./scripts/restart_all.sh` si solo quieres reiniciar
2. `./scripts/clean_all.sh` si quieres empezar completamente desde cero

## 5. Implementación por partes

### Parte 1. Generación de eventos en Kafka

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

Campos adicionales para trazabilidad del dataset sintético:

- `payment_group_id`
- `attempt_number`
- `scenario`

Comportamientos simulados:

- pagos normales
- reintentos sobre pagos declinados
- patrones sospechosos con mayor importe, países variados y dispositivos compartidos
- duplicados esporádicos para poder validar la deduplicación de Silver

Ejecución:

```bash
./scripts/run_generator.sh --events 5000 --sleep-ms 150
```

### Parte 2. Bronze

Archivo principal:

- [bronze_to_iceberg.py](../apps/spark/bronze_to_iceberg.py)

Función:

- lee del topic Kafka `payments`
- parsea JSON
- conserva el esquema operativo de llegada
- añade solo `ingestion_ts` como metadato técnico
- escribe en Iceberg con checkpoint local

Ejecución:

```bash
./scripts/run_bronze.sh
```

Nota:

- el job es de larga duración y se mantiene escuchando Kafka
- el checkpoint queda en `runtime/checkpoints/bronze`
- mientras está corriendo, la Spark UI queda accesible en `http://localhost:4040`
- la pestaña principal para la demo es `Structured Streaming`, donde se pueden revisar `Input Rate`, `Process Rate`, `Input Rows` y `Batch Duration`
- el proyecto expone `4040-4050` para poder ver varias UIs de Spark si Bronze, Silver y Gold se ejecutan a la vez

### Parte 3. Silver

Archivo principal:

- [silver_enrichment.py](../apps/spark/silver_enrichment.py)

Transformaciones:

- conversión de `event_time` a timestamp
- deduplicación por `payment_id`
- cálculo de:
  - `tx_by_card_5m`
  - `distinct_merchants_10m`
  - `distinct_countries_1h`
  - `distinct_cards_per_device`
  - `declined_ratio_1h`

Ejecución:

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
- demasiados países distintos en 1 hora
- dispositivo compartido por demasiadas tarjetas
- ratio elevado de transacciones rechazadas
- importe alto

Salidas:

- `fraud_alerts`
- `graph_payments`

Ejecución:

```bash
./scripts/run_gold.sh
```

Seguimiento recomendado:

- terminal: debe finalizar sin error
- Spark UI: si ya hay otros jobs Spark vivos, Gold suele aparecer en el siguiente puerto libre
- Trino: consultar `fraud_alerts` y validar `risk_score` y `reasons_text`

### Parte 5. Consulta y visualización

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
  - menú `Topics`
  - topic `payments`
  - pestaña `Messages`
- Spark UI:
  - pestaña `Structured Streaming`
  - abrir el `run id`
  - observar `Input Rate`, `Process Rate`, `Input Rows` y `Batch Duration`

URI recomendada para Superset:

```text
trino://trino@trino:8080/iceberg/payments
```

Pasos manuales en Superset:

1. Entrar como admin en `http://localhost:8088`.
2. Ir a `Settings -> Data -> Database Connections`.
3. Crear conexión con la URI anterior.
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
- Se dejan queries y pasos exactos para crear el dashboard sin improvisación.

### Parte 6. Orquestación bajo demanda con Airflow

Archivos:

- [fraud_graph_pipeline.py](../airflow/dags/fraud_graph_pipeline.py)
- [lakehouse_tasks.py](../orchestration/lakehouse_tasks.py)

Características del DAG:

- `schedule=None`
- ejecución manual
- parámetros:
  - `source_table`
  - `start_ts`
  - `end_ts`
  - `graph_name`

Tareas:

1. compactar la tabla Iceberg con `ALTER TABLE ... EXECUTE optimize`
2. generar el dataset de exportación de grafo filtrado por rango temporal
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

- dispositivos compartidos por múltiples tarjetas
- tarjetas usadas en múltiples países
- comercios conectados a múltiples entidades sospechosas
- agrupaciones de comportamiento anómalo por dispositivo compartido

## 6. Puesta en marcha

### 6.1 Arranque de toda la plataforma

```bash
cp .env.example .env
./scripts/start_all.sh
```

### 6.2 Pipeline de datos

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

### 6.3 Reinicio completo

```bash
./scripts/restart_all.sh
```

### 6.4 Limpieza total

```bash
./scripts/clean_all.sh
```

## 7. Consultas de verificación

Con el cliente de Trino:

```bash
docker compose exec trino trino
```

Y después:

```sql
SHOW TABLES FROM iceberg.payments;
SELECT count(*) FROM iceberg.payments.bronze_payments;
SELECT count(*) FROM iceberg.payments.silver_payments;
SELECT count(*) FROM iceberg.payments.fraud_alerts;
SELECT * FROM iceberg.payments.fraud_alerts ORDER BY risk_score DESC LIMIT 20;
```

## 8. Notas operativas

- Todas las piezas están en la misma red Docker `lakehouse`.
- `scripts/start_all.sh` crea directorios runtime si faltan.
- MinIO inicializa automáticamente el bucket `lakehouse`.
- Kafka crea automáticamente el topic `payments`.
- El dashboard de Superset queda documentado pero requiere ejecución GUI manual.
- El DAG de Airflow queda listo para lanzarse manualmente desde la UI.

## 9. Limitaciones y consideraciones operativas

La plataforma ya se ha validado en local, pero conviene dejar claras varias limitaciones del entorno de demo:

- el proyecto está pensado para ejecución local y demostración académica, no como despliegue de producción
- con `8 GB` de RAM totales, no siempre es razonable mantener todos los servicios pesados levantados a la vez
- tareas como la compactación de Iceberg pueden exigir más recursos que el resto del flujo
- Superset sigue requiriendo parte de la configuración desde interfaz gráfica

En la práctica, lo más importante es esto:

- el pipeline Bronze, Silver y Gold ha sido validado
- Trino, Airflow y Neo4j también se han validado en una ejecución real
- si en otra máquina aparece algún fallo, la corrección debe hacerse sobre el error concreto observado, no suponiendo causas antes de mirar logs

Comprobaciones que conviene repetir al publicar o clonar en otro equipo:

- disponibilidad de imágenes y build local
- permisos de montaje de volúmenes
- descarga de paquetes Maven en Spark
- memoria asignada a Docker Desktop
- estabilidad de Trino, Airflow y Neo4j si el equipo va justo de recursos

## 10. Referencias usadas

### Documentación oficial

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

## 11. Siguiente validación recomendada

El orden más razonable para verificar el proyecto en una máquina con Docker y red es:

1. levantar infraestructura con `./scripts/start_all.sh`
2. comprobar UI y funcionamiento de MinIO, Trino, Superset, Airflow y Neo4j
3. arrancar Bronze
4. generar eventos
5. construir Silver
6. construir Gold
7. lanzar queries de Trino
8. crear dashboard en Superset
9. ejecutar el DAG manual y revisar Neo4j

Ese orden minimiza el número de variables a la vez y permite aislar fallos de integración con rapidez.
