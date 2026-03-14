# Manual de uso del sistema

## 1. Finalidad del manual

Este manual explica, paso a paso, cómo:

- arrancar toda la plataforma
- generar datos sintéticos
- poblar Bronze, Silver y Gold
- consultar el Lakehouse
- visualizar resultados en Superset
- orquestar la exportación a Neo4j con Airflow
- ejecutar análisis de relaciones y extraer conclusiones

Esta guía está escrita para dos escenarios:

- uso normal del proyecto
- demostración o exposición en directo

## 2. Requisitos previos

Antes de empezar, verifica:

- Docker Desktop o Docker Engine instalado
- Docker Compose disponible
- conectividad a Internet en la primera ejecución, porque Spark descarga dependencias Maven con `--packages`
- puertos libres: `5432`, `7474`, `7687`, `8080`, `8081`, `8088`, `9000`, `9001`, `29092`

Comprobaciones mínimas:

```bash
docker --version
docker compose version
```

## 3. Estructura que debes conocer

Documentos principales:

- [README.md](../README.md)
- [DOCUMENTACION_FINAL.md](../docs/DOCUMENTACION_FINAL.md)
- [REFERENCIAS.md](../docs/REFERENCIAS.md)
- [INFORME_RESULTADOS_Y_CONCLUSIONES.md](../docs/INFORME_RESULTADOS_Y_CONCLUSIONES.md)

Scripts operativos:

- [start_all.sh](../scripts/start_all.sh)
- [restart_all.sh](../scripts/restart_all.sh)
- [clean_all.sh](../scripts/clean_all.sh)
- [run_bronze.sh](../scripts/run_bronze.sh)
- [run_generator.sh](../scripts/run_generator.sh)
- [run_silver.sh](../scripts/run_silver.sh)
- [run_gold.sh](../scripts/run_gold.sh)

## 4. Scripts del proyecto

### `start_all.sh`

Es el punto de entrada principal del proyecto.

Para qué sirve:

- preparar el entorno local
- construir imágenes si hace falta
- arrancar los servicios base
- ejecutar inicializaciones de Kafka, MinIO, Airflow y Superset

Cuándo usarlo:

- al empezar a trabajar
- después de clonar el repositorio
- cuando quieres dejar toda la plataforma lista para una demo o una validación completa

Qué no hace:

- no ejecuta Bronze, Silver ni Gold
- no genera eventos por sí solo

### `restart_all.sh`

Reinicia la plataforma sin borrar la persistencia local.

Para qué sirve:

- apagar y volver a levantar todo el stack
- recuperar un estado razonable cuando varios servicios han quedado inestables

Cuándo usarlo:

- si Airflow, Trino o Superset han quedado en un estado raro
- si quieres reiniciar todo sin perder datos del `runtime`

### `clean_all.sh`

Limpia el entorno local y deja el proyecto preparado para empezar desde cero.

Para qué sirve:

- borrar volúmenes y datos persistidos
- eliminar checkpoints y exportaciones antiguas
- resetear el entorno para una prueba limpia

Cuándo usarlo:

- si quieres una ejecución totalmente desde cero
- si sospechas que hay datos corruptos o residuos de ejecuciones anteriores
- antes de una entrega o demo final si necesitas reproducibilidad completa

Aviso:

- este script sí elimina persistencia local del proyecto
- después tendrás que volver a usar `./scripts/start_all.sh`

### `run_bronze.sh`

Lanza el job de Spark Streaming que consume Kafka y escribe Bronze en Iceberg.

Para qué sirve:

- mantener viva la ingesta desde Kafka
- poblar `iceberg.payments.bronze_payments`

Cuándo usarlo:

- siempre después de `./scripts/start_all.sh`
- antes de ejecutar el generador
- mientras quieras capturar eventos en tiempo casi real

Comportamiento esperado:

- se queda ejecutándose
- debe ir en una terminal aparte

### `run_generator.sh`

Ejecuta el generador de eventos sintéticos.

Para qué sirve:

- crear datos de prueba para el pipeline
- simular pagos normales, reintentos, fraude y duplicados

Cuándo usarlo:

- cuando Bronze ya está activo
- cuando necesitas alimentar Kafka con nuevos eventos

Comportamiento esperado:

- termina cuando alcanza el número de eventos indicado
- admite parámetros como `--events` y `--sleep-ms`

### `run_silver.sh`

Ejecuta el job batch que construye Silver.

Para qué sirve:

- limpiar y tipar Bronze
- deduplicar pagos
- calcular variables de comportamiento

Cuándo usarlo:

- después de haber generado suficientes eventos
- cuando Bronze ya haya escrito datos
- cuando quieras recalcular Silver con el estado actual de Bronze

Comportamiento esperado:

- es batch
- termina y devuelve el prompt

### `run_gold.sh`

Ejecuta el job batch que construye Gold.

Para qué sirve:

- generar `fraud_alerts`
- calcular `risk_score`
- preparar `graph_payments`

Cuándo usarlo:

- después de `./scripts/run_silver.sh`
- cuando quieras recalcular alertas y el dataset para Neo4j

Comportamiento esperado:

- es batch
- termina y devuelve el prompt

### Orden correcto de uso

El orden normal del proyecto es este:

1. `./scripts/start_all.sh`
2. `./scripts/run_bronze.sh`
3. `./scripts/run_generator.sh --events 5000 --sleep-ms 150`
4. `./scripts/run_silver.sh`
5. `./scripts/run_gold.sh`

El orden de mantenimiento sería este:

1. `./scripts/restart_all.sh` si solo quieres reiniciar
2. `./scripts/clean_all.sh` si quieres borrar el estado local y empezar desde cero

Regla práctica:

- `start_all.sh` prepara la infraestructura
- `run_bronze.sh` abre la ingesta
- `run_generator.sh` mete datos
- `run_silver.sh` enriquece
- `run_gold.sh` convierte el dato en alertas
- `restart_all.sh` reinicia
- `clean_all.sh` resetea
## 5. Primera puesta en marcha

### Paso 1. Preparar variables de entorno

```bash
cp .env.example .env
```

No es obligatorio cambiar nada para una demo local, pero puedes revisar:

- credenciales de PostgreSQL
- credenciales de MinIO
- credenciales de Superset
- credenciales de Airflow
- password de Neo4j

### Paso 2. Arrancar toda la infraestructura

```bash
./scripts/start_all.sh
```

Este script:

- crea los directorios de runtime
- construye las imágenes extendidas de Airflow, Superset, Spark y el generador
- levanta PostgreSQL, MinIO, Kafka, Spark, Neo4j y el contenedor del generador
- inicializa bucket en MinIO
- crea el topic `payments` en Kafka
- inicializa Airflow y Superset
- levanta Trino, Superset y Airflow

### Paso 3. Verificar que los servicios responden

Abre en navegador:

- MinIO: `http://localhost:9001`
- Kafka UI: `http://localhost:8082`
- Spark UI: `http://localhost:4040-4050`
- Trino: `http://localhost:8080`
- Superset: `http://localhost:8088`
- Airflow: `http://localhost:8081`
- Neo4j: `http://localhost:7474`

Credenciales por defecto:

- Superset: `admin / admin`
- Airflow: `admin / admin`
- Neo4j: `neo4j / neo4j_password`

Interfaces gráficas nuevas para la demo:

- Kafka UI sirve para ver visualmente los mensajes entrando al topic
- Spark UI sirve para ver visualmente cómo Spark consume y procesa micro-batches
- se expone el rango `4040-4050` para que puedas seguir varias ejecuciones Spark si Bronze, Silver y Gold se lanzan por separado

Imágenes de apoyo:

- Kafka UI: [captura de interfaz oficial](https://raw.githubusercontent.com/provectus/kafka-ui/master/documentation/images/Interface.gif)
- Spark Structured Streaming UI: [captura oficial](https://spark.apache.org/docs/3.5.6/img/webui-structured-streaming-detail.png)

## 6. Ejecución completa del pipeline

### Paso 4. Arrancar Bronze

En una terminal aparte:

```bash
./scripts/run_bronze.sh
```

Qué debes observar:

- Spark arranca un job streaming
- queda escuchando Kafka
- no termina por sí solo
- en `http://localhost:4040` aparece la Spark UI del driver mientras el job está en ejecución

Interpretación:

- Bronze es la capa cruda
- desde este punto cualquier evento que llegue a Kafka debe acabar en Iceberg

Nota técnica:

- MinIO usa una región S3-compatible fija, `us-east-1`, para que Iceberg y el cliente AWS de Spark puedan crear y leer tablas sin depender de autodetección de región
- esto no implica usar AWS real ni tener cuenta en Amazon; MinIO expone una API compatible con S3 y el SDK necesita una región aunque el endpoint sea local

Ruta visual en Spark UI:

1. abrir `http://localhost:4040`
2. entrar en la pestaña `Structured Streaming`
3. abrir el `run id` de la query

Qué mirar en Spark UI:

- `Input Rate`
- `Process Rate`
- `Input Rows`
- `Batch Duration`
- si aparecen excepciones en la parte superior de la query

Lectura recomendada:

- si `Process Rate` acompaña a `Input Rate`, Spark va absorbiendo el flujo
- si `Batch Duration` se dispara, el job se está retrasando
- si `Input Rows` crece tras lanzar el generador, el pipeline está consumiendo Kafka

### Paso 5. Generar datos sintéticos

En una segunda terminal:

```bash
./scripts/run_generator.sh --events 5000 --sleep-ms 150
```

Parámetros recomendados para distintas demos:

- demo rápida: `--events 1000 --sleep-ms 50`
- demo estable: `--events 5000 --sleep-ms 150`
- demo más rica para alertas: `--events 12000 --sleep-ms 40`

Qué genera el sistema:

- pagos normales
- pagos reintentados
- pagos sospechosos
- algunos duplicados intencionales

Comprobación visual recomendada:

- abre `http://localhost:8082`
- entra en el cluster `local`
- entra en `Topics`
- abre el topic `payments`
- pulsa la pestaña `Messages`

Qué debes fijarte:

- los eventos JSON van entrando en el topic
- el volumen crece a medida que corre el generador
- puedes enseñar campos como `payment_id`, `card_id`, `country`, `amount`, `status` y `scenario`

Lectura recomendada en Kafka UI:

- `Overview` sirve para confirmar particiones y actividad general del topic
- `Messages` es la vista principal para enseñar el contenido de los eventos
- si filtras o paginas mensajes, puedes enseñar rápidamente ejemplos de `normal`, `retry` y `suspicious`

### Paso 6. Construir Silver

Cuando ya se hayan generado suficientes eventos:

```bash
./scripts/run_silver.sh
```

Qué hace:

- lee Bronze
- tipa correctamente los campos
- elimina duplicados por `payment_id`
- calcula variables de comportamiento por ventanas temporales

Qué debes observar en la terminal:

- aparecen stages y tareas Spark de tipo batch
- el proceso debe terminar y devolverte el prompt, a diferencia de Bronze
- no debe aparecer ningún `Traceback` ni `Py4JJavaError`

Qué debes mirar en UIs o verificaciónes:

- si Bronze sigue ejecutándose, Silver suele abrir su Spark UI en `http://localhost:4041`
- si Bronze no está ejecutándose, la Spark UI de Silver suele quedar en `http://localhost:4040`
- en Spark UI interesa sobre todo la pestaña `Jobs` y la pestaña `SQL / DataFrame`
- en Trino conviene comprobar que ya existe `iceberg.payments.silver_payments`

Consulta recomendada tras Silver:

```sql
SELECT count(*) AS silver_rows
FROM iceberg.payments.silver_payments;

SELECT
  payment_id,
  card_id,
  tx_by_card_5m,
  distinct_merchants_10m,
  distinct_countries_1h,
  distinct_cards_per_device,
  declined_ratio_1h
FROM iceberg.payments.silver_payments
ORDER BY event_time DESC
LIMIT 20;
```

Interpretación recomendada:

- `silver_rows` debe ser menor o igual que Bronze por la deduplicación
- las columnas derivadas ya deben traer contexto temporal listo para Gold
- si ves valores altos en `tx_by_card_5m` o `distinct_merchants_10m`, ya hay señales de comportamiento anómalo

### Paso 7. Construir Gold

```bash
./scripts/run_gold.sh
```

Qué hace:

- lee Silver
- aplica reglas de riesgo
- crea `fraud_alerts`
- crea `graph_payments`

Qué debes observar:

- el proceso termina y devuelve el prompt
- si Bronze y Silver siguen activos, Gold suele aparecer en otra Spark UI libre, por ejemplo `http://localhost:4042`
- en Trino ya deberías poder consultar `fraud_alerts`

Consulta recomendada tras Gold:

```sql
SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;

SELECT payment_id, risk_score, reasons_text
FROM iceberg.payments.fraud_alerts
ORDER BY risk_score DESC
LIMIT 20;
```

## 7. Comprobación con Trino

### Paso 8. Entrar en Trino

```bash
docker compose exec trino trino
```

### Paso 9. Ejecutar consultas de validación

```sql
SHOW TABLES FROM iceberg.payments;

SELECT count(*) AS bronze_rows
FROM iceberg.payments.bronze_payments;

SELECT count(*) AS silver_rows
FROM iceberg.payments.silver_payments;

SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;

SELECT *
FROM iceberg.payments.fraud_alerts
ORDER BY risk_score DESC
LIMIT 20;
```

Qué debes explicar en una exposición:

- Bronze debe tener más o igual número de filas que Silver
- Silver puede tener menos por deduplicación
- Gold no contiene todas las transacciones, solo alertas
- `risk_score` y `reasons` justifican por qué una transacción se considera sospechosa

## 8. Visualización en Superset

### Paso 10. Configurar la conexión a Trino

En Superset:

1. Accede a `http://localhost:8088`
2. Ve a `Settings -> Data -> Database Connections`
3. Crea una nueva conexión con esta URI:

```text
trino://trino@trino:8080/iceberg/payments
```

### Paso 11. Registrar datasets

Registra como datasets:

- `iceberg.payments.silver_payments`
- `iceberg.payments.fraud_alerts`

### Paso 12. Crear las visualizaciones recomendadas

Las consultas base están en [dashboard_queries.sql](../superset/dashboard_queries.sql).

Visualizaciones recomendadas:

- KPI `Total de transacciones`
- KPI `Total de alertas de fraude`
- serie temporal `Alertas por hora`
- barra horizontal `Top merchants por riesgo medio`
- barra horizontal `Top cards por riesgo medio`

Nombre sugerido del dashboard:

- `Fraud Monitoring`

Narrativa para explicarlo:

- volumen total procesado
- porcentaje de transacciones sospechosas
- momentos de mayor actividad anómala
- entidades que concentran más riesgo

## 9. Orquestación con Airflow

### Paso 13. Ejecutar el DAG manual

En Airflow:

1. Accede a `http://localhost:8081`
2. Localiza el DAG `fraud_graph_pipeline`
3. Lanza `Trigger DAG`
4. Introduce parámetros

Ejemplo recomendado:

```json
{
  "source_table": "graph_payments",
  "start_ts": "",
  "end_ts": "",
  "graph_name": "fraud_snapshot_demo"
}
```

Qué hace el DAG:

1. compacta la tabla Iceberg
2. exporta el dataset de grafo a CSV
3. copia los CSV al directorio de importacion de Neo4j
4. carga nodos y relaciones en Neo4j

### Si tu equipo va justo de memoria

En un MacBook Air M1 con `8 GB` de RAM conviene apagar contenedores que no son necesarios en esta fase.

Para ejecutar el DAG y cargar Neo4j, lo mínimo recomendable es dejar activos:

- `postgres`
- `minio`
- `trino`
- `neo4j`
- `airflow-webserver`
- `airflow-scheduler`

Puedes liberar memoria apagando temporalmente:

```bash
docker compose stop spark generator kafka-ui superset
```

Si ya no estás generando ni recalculando Bronze, Silver o Gold, esos servicios no hacen falta para la carga del grafo.

Para comprobar el estado actual:

```bash
docker compose ps
```

## 10. Análisis en Neo4j

### Paso 14. Acceder a Neo4j Browser

Abre:

- `http://localhost:7474`

### Paso 15. Ejecutar consultas Cypher

Las consultas están en [investigation_queries.cypher](../neo4j/cypher/investigation_queries.cypher).

Consultas que conviene lanzar en una demo:

1. dispositivos compartidos por múltiples tarjetas
2. tarjetas usadas en múltiples países
3. comercios conectados a múltiples alertas
4. agrupaciones de comportamiento anómalo alrededor de dispositivos compartidos

Qué debes interpretar:

- un dispositivo compartido por muchas tarjetas puede indicar muleo, pruebas de tarjetas o uso fraudulento coordinado
- una tarjeta usada en varios países en poco tiempo es un indicador clásico de compromiso
- un comercio conectado a muchas alertas puede estar captando actividad de alto riesgo

## 11. Secuencia recomendada para una exposición en directo

La mejor secuencia para exponer sin perder tiempo es:

1. explicar la arquitectura con apoyo de [DOCUMENTACION_FINAL.md](../docs/DOCUMENTACION_FINAL.md)
2. arrancar servicios y mostrar que todos están operativos
3. lanzar Bronze
4. ejecutar el generador y comentar los tipos de eventos sintéticos
5. construir Silver y Gold
6. validar con Trino que existen tablas y alertas
7. mostrar dashboard en Superset
8. lanzar el DAG en Airflow
9. abrir Neo4j y ejecutar una consulta de relaciones
10. cerrar con conclusiones apoyándote en [INFORME_RESULTADOS_Y_CONCLUSIONES.md](../docs/INFORME_RESULTADOS_Y_CONCLUSIONES.md)

## 12. Guion corto para defender el proyecto

Puedes explicarlo asi:

1. Kafka recibe eventos de pago casi en tiempo real.
2. Spark Streaming persiste la capa Bronze sin alterar el dato original.
3. Spark batch construye Silver, limpia y enriquece el evento.
4. Gold transforma esas variables en alertas interpretables.
5. Trino y Superset convierten el Lakehouse en una capa analítica consultable.
6. Airflow orquesta procesos bajo demanda.
7. Neo4j permite detectar fraude conectado que una tabla no muestra bien.

## 13. Problemas frecuentes y respuesta rápida

### Caso 1. `start_all.sh` falla en la construcción de imágenes

Revisa:

- conexión de red
- espacio en disco
- versión de Docker

### Caso 2. Spark no puede descargar paquetes Maven

Síntoma:

- error al ejecutar `spark-submit --packages`

Accion:

- verificar salida a Internet
- relanzar el comando

### Caso 3. Trino no ve tablas

Revisa:

- que Bronze, Silver y Gold se hayan ejecutado
- que MinIO haya creado el bucket
- que PostgreSQL y Trino estén arriba

### Caso 4. El DAG termina bien pero Neo4j no muestra datos

Revisa:

- parametro `graph_name`
- presencia de CSVs en `runtime/neo4j/import/<graph_name>`
- logs del task `load_graph_to_neo4j`

## 14. Parada y limpieza

Parar servicios:

```bash
docker compose down
```

Reiniciar todo:

```bash
./scripts/restart_all.sh
```

Limpiar datos y volver a cero:

```bash
./scripts/clean_all.sh
```

## 14. Cierre del manual

Si sigues este orden, puedes enseñar el proyecto completo de extremo a extremo:

- ingesta
- persistencia
- enriquecimiento
- detección
- visualización
- orquestación
- investigación relacional

Ese recorrido es suficiente para defender tanto la parte técnica como la parte funcional del sistema.
