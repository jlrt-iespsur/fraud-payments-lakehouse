# Anexo - Soluciones a posibles errores

Este anexo recoge errores reales observados durante la puesta en marcha del proyecto y la forma de resolverlos.

## 1. Docker no puede resolver Docker Hub

### Síntoma

Al ejecutar `./scripts/start_all.sh` aparecen errores como:

```text
Get "https://registry-1.docker.io/v2/": ... dial tcp: lookup registry-1.docker.io: no such host
```

### Causa probable

- no hay conexión a Internet
- el equipo se ha quedado sin wifi
- hay un problema temporal de DNS

### Solución

1. comprobar conectividad de red
2. volver a ejecutar `./scripts/start_all.sh`

### Observación

Si en un segundo intento Docker ya descarga imágenes, el problema no era del proyecto sino de red.

## 2. La imagen `bitnami/spark:3.5.1` no existe

### Síntoma

Error al arrancar:

```text
manifest for bitnami/spark:3.5.1 not found
```

### Causa probable

- la tag pública ya no está disponible
- dependencia a una imagen externa inestable

### Solución aplicada

Se sustituyó la imagen por una imagen local propia definida en:

- [docker/spark/Dockerfile](../docker/spark/Dockerfile)

### Observación

Esto evita depender de tags externas que pueden desaparecer.

## 3. Airflow no permite instalar dependencias con `pip` como root

### Síntoma

Durante el build de Airflow aparece:

```text
You are running pip as root. Please use 'airflow' user to run pip!
```

### Causa probable

- la imagen oficial de Airflow exige instalar paquetes como usuario `airflow`

### Solución aplicada

Se corrigió:

- [docker/airflow/Dockerfile](../docker/airflow/Dockerfile)

Instalando dependencias como usuario `airflow`.

## 4. `airflow-init` falla por cómo se lanzaba el comando

### Síntoma

Durante la inicialización aparecía algo como:

```text
airflow command error: argument GROUP_OR_COMMAND: invalid choice: '/bin/bash'
```

o bien:

```text
airflow command error: the following arguments are required: GROUP_OR_COMMAND
```

### Causa probable

- conflicto entre `ENTRYPOINT` de la imagen oficial y `command` en `docker-compose.yml`
- el script de inicialización no se estaba pasando correctamente al shell

### Solución aplicada

Se corrigió:

- [docker-compose.yml](../docker-compose.yml)

dejando el script completo dentro de `entrypoint` para `airflow-init`.

## 5. `superset-init` no crea bien el usuario admin

### Síntoma

Durante la inicialización aparecían errores como:

```text
/bin/sh: 2: --username: not found
```

o bien quedaba una petición interactiva:

```text
Username [admin]:
```

### Causa probable

- el comando `superset fab create-admin` estaba roto por saltos de línea mal interpretados

### Solución aplicada

Se corrigió:

- [docker-compose.yml](../docker-compose.yml)

dejando el comando de creación de admin en una única línea lógica dentro de `entrypoint`.

## 6. Iceberg contra MinIO falla por falta de región S3

### Síntoma

Al arrancar Bronze aparece:

```text
Unable to load region from any of the providers in the chain ...
```

### Causa probable

- Iceberg usa el SDK de AWS para hablar con MinIO
- aunque no se use AWS real, el cliente S3 necesita una región explícita

### Solución aplicada

Se fijó `us-east-1` en:

- [apps/spark/common.py](../apps/spark/common.py)
- [docker-compose.yml](../docker-compose.yml)
- [scripts/run_bronze.sh](../scripts/run_bronze.sh)
- [scripts/run_silver.sh](../scripts/run_silver.sh)
- [scripts/run_gold.sh](../scripts/run_gold.sh)

### Aclaración

Esto no implica usar AWS real ni requerir cuenta de Amazon.

## 7. Bronze parece arrancar pero vuelve al prompt

### Síntoma

`./scripts/run_bronze.sh` muestra logs de arranque y después vuelve al prompt, sin dejar una excepción clara.

### Causa probable

- comportamiento poco claro del proceso streaming al ejecutarse por `docker compose exec`
- falta de trazas explícitas si la query se paraba

### Solución aplicada

Se mejoró:

- [apps/spark/bronze_to_iceberg.py](../apps/spark/bronze_to_iceberg.py)
- [scripts/run_bronze.sh](../scripts/run_bronze.sh)

Cambios:

- nombre explícito de la query
- `trigger(processingTime="5 seconds")`
- mensaje de inicio con `query id`
- error explícito si la query se detiene
- `docker compose exec -T` para evitar interferencias de TTY

### Comprobación recomendada

Si ves:

```text
Bronze streaming query iniciada: id=...
```

la query ha arrancado correctamente.

## 8. `Spark UI` no carga en `http://localhost:4040`

### Síntoma

El navegador muestra que no se puede acceder a `http://localhost:4040`.

### Causa probable

- el job Spark todavía no ha arrancado
- el job Spark ya ha terminado
- el contenedor `spark` no estaba recreado con el puerto expuesto

### Solución

1. comprobar que el job está realmente en ejecución
2. si hace falta, recrear el contenedor:

```bash
docker compose up -d --build --force-recreate spark
```

3. volver a lanzar el job Spark

### Observación

La Spark UI solo está disponible mientras hay una aplicación Spark activa.

## 9. `trino` no está corriendo

### Síntoma

Al ejecutar:

```bash
docker compose exec trino trino
```

aparece:

```text
service "trino" is not running
```

### Causa probable

- el contenedor `fraud-trino` se ha caído tras arrancar
- `docker compose ps -a` mostrará `Exited (...)`
- puede faltar una propiedad obligatoria en el catálogo Iceberg JDBC

### Comprobación recomendada

```bash
docker compose ps -a
docker compose up -d trino
docker compose ps -a
docker compose logs --tail=100 trino
```

### Estado observado en la prueba

En la prueba real, `fraud-trino` apareció primero como:

```text
Exited (100)
```

y en los logs apareció:

```text
Invalid configuration property iceberg.jdbc-catalog.driver-class: must not be null
```

### Solución aplicada

Se añadió:

```properties
iceberg.jdbc-catalog.driver-class=org.postgresql.Driver
```

en:

- [iceberg.properties](../config/trino/catalog/iceberg.properties)

Después hay que volver a levantar Trino con:

```bash
docker compose up -d trino
```

## 10. `trino` arranca, pero luego se cae con `Exited (137)`

### Síntoma

`docker compose ps -a` muestra algo como:

```text
fraud-trino ... Exited (137)
```

### Causa probable

- finalización forzada del contenedor por falta de memoria
- configuración JVM demasiado agresiva para Docker Desktop

### Solución aplicada

Se ajustaron:

- [config/trino/jvm.config](../config/trino/jvm.config)
- [docker-compose.yml](../docker-compose.yml)

dejando una configuración más conservadora para la JVM de Trino.

### Comprobación recomendada

```bash
docker compose up -d --force-recreate trino
docker compose ps -a
docker compose logs --tail=100 trino
```

## 11. Neo4j aparece como `Exited (137)`

### Síntoma

`docker compose ps -a` muestra:

```text
fraud-neo4j ... Exited (137)
```

### Causa probable

- cierre forzado por memoria insuficiente
- competición de memoria con Trino, Spark y el resto de servicios

### Solución recomendada

1. intentar arrancarlo de nuevo con:

```bash
docker compose up -d neo4j
```

2. si vuelve a caer, revisar:

```bash
docker compose logs --tail=100 neo4j
```

3. si el patrón se repite, reducir memoria asignada a Neo4j o aumentar la memoria disponible en Docker Desktop

### Solución aplicada en este proyecto

Se ajustó:

- [docker-compose.yml](../docker-compose.yml)

Cambios aplicados:

- heap inicial y máximo reducido a `256m`
- page cache fijada en `128m`
- política `restart: unless-stopped` para que el servicio vuelva a levantarse si Docker lo reinicia

## 12. Servicios `*-init` en estado `Exited (0)`

### Síntoma

Servicios como `airflow-init`, `kafka-init`, `minio-init` o `superset-init` aparecen en `docker compose ps -a` como:

```text
Exited (0)
```

### Interpretación correcta

Eso es normal.

Son servicios de inicialización que:

- arrancan
- ejecutan una tarea puntual
- terminan correctamente

### Regla práctica

- `Exited (0)` en un servicio `*-init`: correcto
- `Exited` con codigo distinto de cero en un servicio principal: revisar logs

## 13. Gold falla con `PySparkTypeError: [NOT_ITERABLE] Column is not iterable`

### Síntoma

Al ejecutar `./scripts/run_gold.sh` aparece un error como:

```text
PySparkTypeError: [NOT_ITERABLE] Column is not iterable.
```

La traza apunta a:

- [gold_fraud_detection.py](../apps/spark/gold_fraud_detection.py)

### Causa probable

- se estaba usando `array_remove(..., lit(None))`
- en esta versión de PySpark esa combinación puede fallar al intentar tratar una `Column` como iterable

### Solución aplicada

Se corrigió:

- [gold_fraud_detection.py](../apps/spark/gold_fraud_detection.py)

Sustituyendo la eliminación de nulos con `array_remove` por un filtrado explícito:

- primero se construye el array bruto de razones
- después se aplica `filter(..., x -> x is not null)`

### Comprobación recomendada

Volver a ejecutar:

```bash
./scripts/run_gold.sh
```

Y validar luego en Trino:

```sql
SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;
```

## 14. Gold provoca un cierre de JVM con `SIGSEGV`

### Síntoma

Tras corregir el error anterior, `./scripts/run_gold.sh` puede fallar con una traza nativa como:

```text
# A fatal error has been detected by the Java Runtime Environment:
# SIGSEGV (0xb) ...
```

### Causa probable

- interacción inestable entre Spark 3.5, Java 21 en `aarch64` y la generación agresiva de código del plan
- escritura mediante un plan SQL demasiado grande para este entorno

### Solución aplicada

Se endureció:

- [gold_fraud_detection.py](../apps/spark/gold_fraud_detection.py)

Cambios aplicados:

- se desactivó `spark.sql.codegen.wholeStage`
- se desactivó `spark.sql.adaptive.enabled` para este job
- se sustituyó `CREATE OR REPLACE TABLE ... AS SELECT * FROM vista` por escritura directa con `DataFrame.writeTo(...).createOrReplace()`

### Comprobación recomendada

Volver a ejecutar:

```bash
./scripts/run_gold.sh
```

Y después validar en Trino:

```sql
SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;
```

## 15. Recomendación general de diagnóstico

Cuando un servicio o script falle, seguir este orden:

1. mirar si el contenedor está `Up` o `Exited` con `docker compose ps -a`
2. revisar logs del servicio con `docker compose logs --tail=100 <servicio>`
3. si el error es de inicialización, corregir configuración antes de reiniciar todo
4. si el error es de memoria, reducir recursos de JVM o aumentar memoria de Docker Desktop

## 16. Airflow muestra `Broken DAG` o desaparece el DAG tras un rato

### Síntoma

En la interfaz web puede aparecer:

- `Broken DAG`
- `DAG Import Errors`
- el DAG deja de verse en la lista aunque el archivo sigue existiendo

Y en los logs del webserver o scheduler aparecen mensajes como:

```text
Worker (...) was sent SIGKILL! Perhaps out of memory?
```

o bien:

```text
DAG ... is missing and will be deactivated.
```

### Causa probable

- Airflow estaba demasiado ajustado de memoria
- el webserver mataba workers de Gunicorn
- el scheduler podía matar procesos de parseo y deseríalizar mal el DAG

### Solución aplicada

Se ajustó:

- [docker-compose.yml](../docker-compose.yml)

Cambios aplicados:

- `AIRFLOW__WEBSERVER__WORKERS=1`
- `AIRFLOW__SCHEDULER__PARSING_PROCESSES=1`
- `AIRFLOW__CORE__PARALLELISM=4`
- `AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG=2`
- `restart: unless-stopped` en webserver y scheduler

### Recuperación recomendada

```bash
docker compose up -d --force-recreate airflow-webserver airflow-scheduler
```

Después, refrescar la web de Airflow.

## 17. El DAG de Airflow falla porque no puede resolver `trino`

### Síntoma

La task `compact_iceberg_table` falla con errores como:

```text
Failed to resolve 'trino'
```

o bien:

```text
TrinoConnectionError: failed to execute: HTTPConnectionPool(host='trino', port=8080) ...
```

### Causa probable

- dentro de los contenedores de Airflow, el nombre DNS `trino` no siempre estaba resolviendo correctamente en este entorno
- además, Trino podía reiniciarse por memoria y agravar el problema

### Solución aplicada

Se corrigió:

- [docker-compose.yml](../docker-compose.yml)
- [jvm.config](../config/trino/jvm.config)

Cambios aplicados:

- Airflow ahora conecta a Trino usando `host.docker.internal:8080`
- Trino tiene `restart: unless-stopped`
- se redujo aún más la memoria JVM de Trino

### Recuperación recomendada

```bash
docker compose up -d --force-recreate trino airflow-webserver airflow-scheduler
```

## 18. `compact_iceberg_table` falla, pero el grafo no necesita esa compactación para cargarse

### Síntoma

La primera task del DAG falla con errores como:

```text
TrinoConnectionError: failed to execute: ('Connection aborted.', RemoteDisconnected(...))
```

### Causa probable

- la sentencia `ALTER TABLE ... EXECUTE optimize(...)` de Trino es más pesada que la exportación del grafo
- en un entorno local con memoria ajustada, Trino puede cerrar la conexión durante la compactación

### Solución aplicada

Se corrigió:

- [lakehouse_tasks.py](../orchestration/lakehouse_tasks.py)

La compactación ahora se trata como paso opcional:

- si funciona, compacta
- si falla, deja una advertencia en el log y el pipeline continúa

### Motivo

Para la demo y la carga de Neo4j, la compactación no es necesaria. Lo importante es exportar `graph_payments` y cargar los CSV en Neo4j.

## 19. Falta de recursos en un Mac con 8 GB de RAM

### Síntoma

Cuando hay demasiados servicios levantados a la vez pueden aparecer varios síntomas mezclados:

- `Exited (137)` en Trino o Neo4j
- workers de Airflow muertos con `SIGKILL`
- respuestas lentas o reinicios en interfaces web
- fallos intermitentes en DAGs por servicios que dejan de responder

### Causa probable

- memoria insuficiente para mantener a la vez `spark`, `trino`, `neo4j`, `airflow`, `superset`, `kafka-ui` y el resto del stack en Docker Desktop

### Solución recomendada en la fase de grafo

Para ejecutar el DAG de Airflow y cargar Neo4j, deja solo:

- `postgres`
- `minio`
- `trino`
- `neo4j`
- `airflow-webserver`
- `airflow-scheduler`

Y apaga temporalmente servicios no necesarios:

```bash
docker compose stop spark generator kafka-ui superset
```

### Regla práctica

- si estás procesando Bronze, Silver o Gold: necesitas `spark`
- si estás consultando: necesitas `trino`
- si estás cargando el grafo: necesitas `trino + neo4j + airflow`
- si no estás usando una interfaz o un servicio en ese momento, conviene pararlo
