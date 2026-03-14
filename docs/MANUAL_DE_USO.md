# Manual de uso del sistema

## 1. Finalidad del manual

Este manual explica, paso a paso, como:

- arrancar toda la plataforma
- generar datos sinteticos
- poblar Bronze, Silver y Gold
- consultar el Lakehouse
- visualizar resultados en Superset
- orquestar la exportacion a Neo4j con Airflow
- ejecutar analisis de relaciones y extraer conclusiones

Esta guia esta escrita para dos escenarios:

- uso normal del proyecto
- demostracion o exposicion en directo

## 2. Requisitos previos

Antes de empezar, verifica:

- Docker Desktop o Docker Engine instalado
- Docker Compose disponible
- conectividad a Internet en la primera ejecucion, porque Spark descarga dependencias Maven con `--packages`
- puertos libres: `5432`, `7474`, `7687`, `8080`, `8081`, `8088`, `9000`, `9001`, `29092`

Comprobaciones minimas:

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

## 4. Primera puesta en marcha

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
- construye las imagenes extendidas de Airflow, Superset, Spark y el generador
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

Interfaces graficas nuevas para la demo:

- Kafka UI sirve para ver visualmente los mensajes entrando al topic
- Spark UI sirve para ver visualmente como Spark consume y procesa micro-batches
- se expone el rango `4040-4050` para que puedas seguir varias ejecuciones Spark si Bronze, Silver y Gold se lanzan por separado

Imagenes de apoyo:

- Kafka UI: [captura de interfaz oficial](https://raw.githubusercontent.com/provectus/kafka-ui/master/documentation/images/Interface.gif)
- Spark Structured Streaming UI: [captura oficial](https://spark.apache.org/docs/3.5.6/img/webui-structured-streaming-detail.png)

## 5. Ejecucion completa del pipeline

### Paso 4. Arrancar Bronze

En una terminal aparte:

```bash
./scripts/run_bronze.sh
```

Que debes observar:

- Spark arranca un job streaming
- queda escuchando Kafka
- no termina por si solo
- en `http://localhost:4040` aparece la Spark UI del driver mientras el job esta en ejecucion

Interpretacion:

- Bronze es la capa cruda
- desde este punto cualquier evento que llegue a Kafka debe acabar en Iceberg

Nota tecnica:

- MinIO usa una region S3-compatible fija, `us-east-1`, para que Iceberg y el cliente AWS de Spark puedan crear y leer tablas sin depender de autodeteccion de region
- esto no implica usar AWS real ni tener cuenta en Amazon; MinIO expone una API compatible con S3 y el SDK necesita una region aunque el endpoint sea local

Ruta visual en Spark UI:

1. abrir `http://localhost:4040`
2. entrar en la pestana `Structured Streaming`
3. abrir el `run id` de la query

Que mirar en Spark UI:

- `Input Rate`
- `Process Rate`
- `Input Rows`
- `Batch Duration`
- si aparecen excepciones en la parte superior de la query

Lectura recomendada:

- si `Process Rate` acompana a `Input Rate`, Spark va absorbiendo el flujo
- si `Batch Duration` se dispara, el job se esta retrasando
- si `Input Rows` crece tras lanzar el generador, el pipeline esta consumiendo Kafka

### Paso 5. Generar datos sinteticos

En una segunda terminal:

```bash
./scripts/run_generator.sh --events 5000 --sleep-ms 150
```

Parametros recomendados para distintas demos:

- demo rapida: `--events 1000 --sleep-ms 50`
- demo estable: `--events 5000 --sleep-ms 150`
- demo mas rica para alertas: `--events 12000 --sleep-ms 40`

Que genera el sistema:

- pagos normales
- pagos reintentados
- pagos sospechosos
- algunos duplicados intencionales

Comprobacion visual recomendada:

- abre `http://localhost:8082`
- entra en el cluster `local`
- entra en `Topics`
- abre el topic `payments`
- pulsa la pestana `Messages`

Que debes fijarte:

- los eventos JSON van entrando en el topic
- el volumen crece a medida que corre el generador
- puedes ensenar campos como `payment_id`, `card_id`, `country`, `amount`, `status` y `scenario`

Lectura recomendada en Kafka UI:

- `Overview` sirve para confirmar particiones y actividad general del topic
- `Messages` es la vista principal para ensenar el contenido de los eventos
- si filtras o paginas mensajes, puedes ensenar rapidamente ejemplos de `normal`, `retry` y `suspicious`

### Paso 6. Construir Silver

Cuando ya se hayan generado suficientes eventos:

```bash
./scripts/run_silver.sh
```

Que hace:

- lee Bronze
- tipa correctamente los campos
- elimina duplicados por `payment_id`
- calcula variables de comportamiento por ventanas temporales

Que debes observar en la terminal:

- aparecen stages y tareas Spark de tipo batch
- el proceso debe terminar y devolverte el prompt, a diferencia de Bronze
- no debe aparecer ningun `Traceback` ni `Py4JJavaError`

Que debes mirar en UIs o verificaciones:

- si Bronze sigue ejecutandose, Silver suele abrir su Spark UI en `http://localhost:4041`
- si Bronze no esta ejecutandose, la Spark UI de Silver suele quedar en `http://localhost:4040`
- en Spark UI interesa sobre todo la pestana `Jobs` y la pestana `SQL / DataFrame`
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

Interpretacion recomendada:

- `silver_rows` debe ser menor o igual que Bronze por la deduplicacion
- las columnas derivadas ya deben traer contexto temporal listo para Gold
- si ves valores altos en `tx_by_card_5m` o `distinct_merchants_10m`, ya hay senales de comportamiento anomalo

### Paso 7. Construir Gold

```bash
./scripts/run_gold.sh
```

Que hace:

- lee Silver
- aplica reglas de riesgo
- crea `fraud_alerts`
- crea `graph_payments`

Que debes observar:

- el proceso termina y devuelve el prompt
- si Bronze y Silver siguen activos, Gold suele aparecer en otra Spark UI libre, por ejemplo `http://localhost:4042`
- en Trino ya deberias poder consultar `fraud_alerts`

Consulta recomendada tras Gold:

```sql
SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;

SELECT payment_id, risk_score, reasons_text
FROM iceberg.payments.fraud_alerts
ORDER BY risk_score DESC
LIMIT 20;
```

## 6. Comprobacion con Trino

### Paso 8. Entrar en Trino

```bash
docker compose exec trino trino
```

### Paso 9. Ejecutar consultas de validacion

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

Que debes explicar en una exposicion:

- Bronze debe tener mas o igual numero de filas que Silver
- Silver puede tener menos por deduplicacion
- Gold no contiene todas las transacciones, solo alertas
- `risk_score` y `reasons` justifican por que una transaccion se considera sospechosa

## 7. Visualizacion en Superset

### Paso 10. Configurar la conexion a Trino

En Superset:

1. Accede a `http://localhost:8088`
2. Ve a `Settings -> Data -> Database Connections`
3. Crea una nueva conexion con esta URI:

```text
trino://trino@trino:8080/iceberg/payments
```

### Paso 11. Registrar datasets

Registra como datasets:

- `iceberg.payments.silver_payments`
- `iceberg.payments.fraud_alerts`

### Paso 12. Crear las visualizaciones recomendadas

Las consultas base estan en [dashboard_queries.sql](../superset/dashboard_queries.sql).

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
- momentos de mayor actividad anomala
- entidades que concentran mas riesgo

## 8. Orquestacion con Airflow

### Paso 13. Ejecutar el DAG manual

En Airflow:

1. Accede a `http://localhost:8081`
2. Localiza el DAG `fraud_graph_pipeline`
3. Lanza `Trigger DAG`
4. Introduce parametros

Ejemplo recomendado:

```json
{
  "source_table": "graph_payments",
  "start_ts": "",
  "end_ts": "",
  "graph_name": "fraud_snapshot_demo"
}
```

Que hace el DAG:

1. compacta la tabla Iceberg
2. exporta el dataset de grafo a CSV
3. copia los CSV al directorio de importacion de Neo4j
4. carga nodos y relaciones en Neo4j

### Si tu equipo va justo de memoria

En un MacBook Air M1 con `8 GB` de RAM conviene apagar contenedores que no son necesarios en esta fase.

Para ejecutar el DAG y cargar Neo4j, lo minimo recomendable es dejar activos:

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

Si ya no estas generando ni recalculando Bronze, Silver o Gold, esos servicios no hacen falta para la carga del grafo.

Para comprobar el estado actual:

```bash
docker compose ps
```

## 9. Analisis en Neo4j

### Paso 14. Acceder a Neo4j Browser

Abre:

- `http://localhost:7474`

### Paso 15. Ejecutar consultas Cypher

Las consultas estan en [investigation_queries.cypher](../neo4j/cypher/investigation_queries.cypher).

Consultas que conviene lanzar en una demo:

1. dispositivos compartidos por multiples tarjetas
2. tarjetas usadas en multiples paises
3. comercios conectados a multiples alertas
4. agrupaciones de comportamiento anomalo alrededor de dispositivos compartidos

Que debes interpretar:

- un dispositivo compartido por muchas tarjetas puede indicar muleo, pruebas de tarjetas o uso fraudulento coordinado
- una tarjeta usada en varios paises en poco tiempo es un indicador clasico de compromiso
- un comercio conectado a muchas alertas puede estar captando actividad de alto riesgo

## 10. Secuencia recomendada para una exposicion en directo

La mejor secuencia para exponer sin perder tiempo es:

1. explicar la arquitectura con apoyo de [DOCUMENTACION_FINAL.md](../docs/DOCUMENTACION_FINAL.md)
2. arrancar servicios y mostrar que todos estan operativos
3. lanzar Bronze
4. ejecutar el generador y comentar los tipos de eventos sinteticos
5. construir Silver y Gold
6. validar con Trino que existen tablas y alertas
7. mostrar dashboard en Superset
8. lanzar el DAG en Airflow
9. abrir Neo4j y ejecutar una consulta de relaciones
10. cerrar con conclusiones apoyandote en [INFORME_RESULTADOS_Y_CONCLUSIONES.md](../docs/INFORME_RESULTADOS_Y_CONCLUSIONES.md)

## 11. Guion corto para defender el proyecto

Puedes explicarlo asi:

1. Kafka recibe eventos de pago casi en tiempo real.
2. Spark Streaming persiste la capa Bronze sin alterar el dato original.
3. Spark batch construye Silver, limpia y enriquece el evento.
4. Gold transforma esas variables en alertas interpretables.
5. Trino y Superset convierten el Lakehouse en una capa analitica consultable.
6. Airflow orquesta procesos bajo demanda.
7. Neo4j permite detectar fraude conectado que una tabla no muestra bien.

## 12. Problemas frecuentes y respuesta rapida

### Caso 1. `start_all.sh` falla en la construccion de imagenes

Revisa:

- conexion de red
- espacio en disco
- version de Docker

### Caso 2. Spark no puede descargar paquetes Maven

Sintoma:

- error al ejecutar `spark-submit --packages`

Accion:

- verificar salida a Internet
- relanzar el comando

### Caso 3. Trino no ve tablas

Revisa:

- que Bronze, Silver y Gold se hayan ejecutado
- que MinIO haya creado el bucket
- que PostgreSQL y Trino esten arriba

### Caso 4. El DAG termina bien pero Neo4j no muestra datos

Revisa:

- parametro `graph_name`
- presencia de CSVs en `runtime/neo4j/import/<graph_name>`
- logs del task `load_graph_to_neo4j`

## 13. Parada y limpieza

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

Si sigues este orden, puedes ensenar el proyecto completo de extremo a extremo:

- ingesta
- persistencia
- enriquecimiento
- deteccion
- visualizacion
- orquestacion
- investigacion relacional

Ese recorrido es suficiente para defender tanto la parte tecnica como la parte funcional del sistema.
