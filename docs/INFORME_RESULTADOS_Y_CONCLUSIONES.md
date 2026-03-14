# Informe de resultados y conclusiones

## 1. Objetivo del informe

Este documento sirve para cerrar la exposicion con un resumen analitico del comportamiento observado en el pipeline de fraude. Esta pensado para rellenarlo durante la prueba final del sistema o para usarlo como guion de cierre en la defensa.

## 2. Preguntas que debe responder el proyecto

El sistema debe permitir responder al menos a estas preguntas:

- cuantas transacciones se han procesado
- cuantas alertas de fraude se han generado
- que variables explican esas alertas
- que comercios, tarjetas o dispositivos concentran mas riesgo
- si existen relaciones entre entidades sospechosas que justifiquen investigacion adicional

## 3. Metricas a recoger en la demo o entrega final

Extrae estos datos desde Trino y Superset:

- numero de registros en Bronze
- numero de registros en Silver
- numero de alertas en Gold
- porcentaje de alertas sobre total procesado
- top 5 merchants por riesgo medio
- top 5 cards por riesgo medio
- numero de dispositivos compartidos por multiples tarjetas
- numero de tarjetas observadas en multiples paises

Consulta base:

```sql
SELECT count(*) AS bronze_rows
FROM iceberg.payments.bronze_payments;

SELECT count(*) AS silver_rows
FROM iceberg.payments.silver_payments;

SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;

SELECT round(100.0 * count(*) / nullif((SELECT count(*) FROM iceberg.payments.silver_payments), 0), 2) AS fraud_rate_pct
FROM iceberg.payments.fraud_alerts;

SELECT merchant_id, avg(risk_score) AS avg_risk_score, count(*) AS alerts
FROM iceberg.payments.fraud_alerts
GROUP BY 1
ORDER BY avg_risk_score DESC, alerts DESC
LIMIT 5;

SELECT card_id, avg(risk_score) AS avg_risk_score, count(*) AS alerts
FROM iceberg.payments.fraud_alerts
GROUP BY 1
ORDER BY avg_risk_score DESC, alerts DESC
LIMIT 5;
```

## 4. Plantilla de resultados

Rellena esta tabla con tus numeros reales:

| Indicador | Valor observado | Interpretacion |
|---|---:|---|
| Registros Bronze | ___ | Volumen bruto ingerido desde Kafka |
| Registros Silver | ___ | Volumen tras tipado y deduplicacion |
| Alertas Gold | ___ | Casos marcados por reglas |
| Tasa de alerta | ___ % | Presion estimada de fraude en el lote |
| Top merchant por riesgo | ___ | Comercio mas expuesto |
| Top card por riesgo | ___ | Tarjeta mas anomala |
| Dispositivos compartidos | ___ | Posibles puntos de fraude conectado |
| Tarjetas en multiples paises | ___ | Posible compromiso de credenciales |

## 5. Interpretacion esperada de Bronze, Silver y Gold

### Bronze

Conclusiones que debes transmitir:

- representa la traza operativa original
- es util para auditoria y replay
- no mezcla limpieza con ingesta

### Silver

Conclusiones que debes transmitir:

- mejora calidad del dato
- elimina ruido por duplicados
- incorpora contexto temporal que el evento crudo no tiene

### Gold

Conclusiones que debes transmitir:

- hace el dato accionable
- no solo detecta sospecha, sino que la explica
- prepara dos consumos distintos: analitico y relacional

## 6. Conclusiones tecnicas recomendadas

Estas conclusiones son apropiadas para la defensa del proyecto:

1. La arquitectura Lakehouse separa correctamente la ingesta, el enriquecimiento y la explotacion analitica.
2. Kafka y Spark permiten desacoplar la recepcion del evento de su procesamiento posterior.
3. Iceberg aporta versionado, gestion de tablas y una base mas robusta para consultas que un simple almacenamiento de ficheros.
4. Trino permite consultar el dato de forma unificada sin moverlo.
5. Superset cubre la capa de observabilidad operativa para negocio y riesgo.
6. Airflow encaja bien para tareas bajo demanda que no deben ejecutarse continuamente.
7. Neo4j aporta valor diferencial al revelar conexiones entre entidades que no se aprecian bien en SQL tabular.

## 7. Conclusiones funcionales recomendadas

Estas conclusiones conectan mejor con negocio:

1. El sistema detecta patrones de fraude frecuentes: alta velocidad, dispersion geografica, multiplicidad de comercios y dispositivos compartidos.
2. La explicabilidad de `reasons` permite justificar cada alerta.
3. El dashboard facilita monitorizacion rapida de volumen, alertas y focos de riesgo.
4. El modelo de grafo permite pasar de la alerta aislada a la investigacion de redes sospechosas.
5. La solucion es ampliable: se pueden anadir reglas, features y modelos de scoring sin romper la arquitectura base.

## 8. Limitaciones que conviene reconocer en la exposicion

Es mejor explicarlas de forma directa:

1. El score actual esta basado en reglas y pesos heurisiticos, no en un modelo supervisado entrenado.
2. Los datos son sinteticos, por lo que sirven para demostrar arquitectura y logica, no para validar precision real de fraude.
3. La calidad final depende de ejecutar y ajustar el entorno Docker en la maquina de demo.
4. La visualizacion en Superset se ha dejado guiada manualmente porque su configuracion final depende del entorno activo y de los objetos creados en la UI.

## 9. Mejoras futuras que elevan la propuesta

Si te preguntan como evolucionarlo:

1. Entrenar un modelo de machine learning sobre Silver y combinarlo con reglas.
2. Introducir listas negras o enriquecimiento externo por IP, BIN o geolocalizacion.
3. Automatizar snapshots y exportaciones periodicas del grafo.
4. Anadir tests de calidad de datos y validaciones automaticas.
5. Incorporar alertado operacional con correo, Slack o webhooks.

## 10. Mensaje final recomendado para el cierre

Puedes cerrar la exposicion con una idea como esta:

El proyecto demuestra una cadena completa de deteccion de fraude sobre arquitectura moderna de datos. Parte de eventos casi en tiempo real, los consolida en un Lakehouse, genera alertas interpretables, habilita analitica SQL y dashboards, y termina en un grafo de investigacion para descubrir relaciones complejas. No es solo una demo de herramientas conectadas, sino un flujo coherente de ingesta, procesamiento, explotacion y analisis forense.

## 11. Conclusiones finales desarrolladas

El proyecto ha servido para comprobar, de forma muy practica, que una arquitectura moderna de datos no consiste solo en conectar herramientas, sino en definir un flujo coherente de extremo a extremo. A lo largo del trabajo hemos construido una cadena completa que empieza en la generacion de eventos de pago, continua con su ingesta y transformacion en un Lakehouse, y termina en dos modos distintos de explotacion: el analitico, mediante SQL y dashboards, y el relacional, mediante un grafo de investigacion en Neo4j. Ese recorrido completo es, probablemente, el principal aprendizaje del proyecto.

Desde el punto de vista funcional, el sistema ha demostrado que es capaz de transformar eventos tecnicos en informacion util para la deteccion de fraude. En la ejecucion validada se procesaron `7443` registros en Bronze, `7299` en Silver y `7049` alertas en Gold. Mas alla del volumen concreto, lo importante es que cada capa ha cumplido una funcion distinta y bien separada. Bronze ha actuado como traza operativa y capa de persistencia cruda; Silver ha limpiado, tipado y enriquecido los datos con contexto temporal y agregados de comportamiento; y Gold ha convertido ese dato enriquecido en alertas interpretables, con un `risk_score` y un campo `reasons_text` que permiten entender por que una transaccion ha sido marcada como sospechosa. Esto da valor real a la solucion, porque no se limita a etiquetar casos, sino que ofrece explicabilidad, algo esencial en contextos de riesgo y auditoria.

Otro aprendizaje importante ha sido entender que SQL y grafo no compiten entre si, sino que resuelven preguntas distintas. Con Trino hemos podido validar rapidamente volumenes, tasas de alerta y entidades con mayor riesgo. Con Neo4j, en cambio, se ha hecho visible algo que en tablas resulta mucho mas costoso de interpretar: la existencia de dispositivos compartidos, tarjetas conectadas a multiples pagos sospechosos y comercios relacionados con actividad anomala. El proyecto confirma, por tanto, que una aproximacion hibrida tiene mucho sentido en fraude: el Lakehouse aporta consistencia, historico y capacidad de consulta; el grafo aporta contexto relacional e investigacion forense.

Tambien hemos aprendido bastante sobre la parte operativa y de infraestructura. Montar todo el sistema en Docker sobre un equipo ligero, en este caso un MacBook Air M1 con `8 GB` de RAM, nos ha obligado a enfrentarnos a problemas reales de integracion y recursos. Hemos tenido errores de resolucion de imagenes, cambios de tags no disponibles, conflictos de `entrypoint` y `command` en Airflow y Superset, problemas de region al usar MinIO a traves del cliente S3 compatible de Iceberg, caidas intermitentes de Trino y Neo4j por memoria, workers de Airflow terminados con `SIGKILL`, y algun fallo mas fino en Spark y PySpark durante Gold. Aunque estos problemas han ralentizado la puesta en marcha, tambien han aportado un aprendizaje muy valioso: en un proyecto de datos real, tan importante como escribir transformaciones es saber observar el sistema, leer logs, aislar servicios, reducir consumo y decidir que partes del pipeline son criticas y cuales pueden degradarse sin bloquear el objetivo principal.

Precisamente por eso, una conclusion relevante es que el proyecto no solo demuestra conocimientos de analitica de datos, sino tambien de ingenieria de datos. Ha sido necesario tomar decisiones pragmaticas para que la demo fuese estable: convertir la compactacion en un paso no bloqueante, reducir el numero de workers de Airflow, rebajar memoria de Trino y Neo4j, y trabajar por fases apagando contenedores no imprescindibles. Esa experiencia refuerza la idea de que la robustez operativa forma parte del valor de una solucion, y no es un detalle secundario.

Respecto a la utilidad del proyecto, la solucion construida puede servir como base de un sistema de deteccion e investigacion de fraude para pagos o transacciones financieras. En su estado actual ya permite simular eventos, procesarlos, generar alertas explicables, analizarlos por SQL y visualizarlos como red de relaciones. Eso la convierte en una plataforma muy buena para docencia, prototipado o validacion de arquitectura. No pretende ser un detector final listo para produccion, porque trabaja con datos sinteticos y reglas heuristicas, pero si demuestra con claridad como deberia organizarse una cadena real de ingesta, enriquecimiento, scoring y analisis posterior.

De cara al futuro, el proyecto tiene un recorrido claro. La primera mejora natural seria sustituir o complementar las reglas heuristicas por un modelo de machine learning entrenado sobre Silver, de forma que el `risk_score` no dependiera solo de umbrales manuales. Otra mejora importante seria incorporar enriquecimiento externo, por ejemplo con listas negras, informacion de BIN, reputacion de IPs o geolocalizacion mas precisa. Tambien seria muy interesante reforzar la calidad y gobernanza del dato con tests automaticos, controles de calidad, validaciones de esquema y alertas sobre drift o cambios en la distribucion de variables. En la parte de infraestructura, una evolucion razonable seria separar mejor los entornos de demo y mantenimiento, para que tareas pesadas como la compactacion no compartan recursos con la capa interactiva. Y, finalmente, en la parte de negocio, se podria mejorar la explotacion creando dashboards mas ricos, workflows de investigacion, y exportaciones periodicas del grafo para casos o snapshots temporales.

En definitiva, el proyecto ha permitido aprender arquitectura, procesamiento, consulta, visualizacion y operacion de una plataforma de datos orientada a fraude. Se ha comprobado que el enfoque Lakehouse encaja muy bien como columna vertebral del dato, que la orquestacion y la observabilidad son imprescindibles, y que el grafo aporta una capa diferencial de investigacion. A pesar de las limitaciones y de los problemas encontrados, el resultado final es consistente: se ha construido un sistema completo, explicable y ampliable, que demuestra de forma creible como se puede abordar la deteccion de fraude con tecnologias modernas de ingenieria de datos.
