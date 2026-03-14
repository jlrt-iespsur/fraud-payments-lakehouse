# Informe de resultados y conclusiones

## 1. Objetivo del informe

Este documento sirve para cerrar la exposición con un resumen analítico del comportamiento observado en el pipeline de fraude. Está pensado para completarlo durante la prueba final del sistema o para usarlo como guion de cierre en la defensa.

## 2. Preguntas que debe responder el proyecto

El sistema debe permitir responder al menos a estas preguntas:

- cuántas transacciones se han procesado
- cuántas alertas de fraude se han generado
- qué variables explican esas alertas
- qué comercios, tarjetas o dispositivos concentran más riesgo
- si existen relaciones entre entidades sospechosas que justifiquen investigación adicional

## 3. Métricas a recoger en la demo o entrega final

Extrae estos datos desde Trino y Superset:

- número de registros en Bronze
- número de registros en Silver
- número de alertas en Gold
- porcentaje de alertas sobre total procesado
- top 5 merchants por riesgo medio
- top 5 cards por riesgo medio
- número de dispositivos compartidos por múltiples tarjetas
- número de tarjetas observadas en múltiples países

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

Rellena esta tabla con tus números reales:

| Indicador | Valor observado | Interpretación |
|---|---:|---|
| Registros Bronze | ___ | Volumen bruto ingerido desde Kafka |
| Registros Silver | ___ | Volumen tras tipado y deduplicación |
| Alertas Gold | ___ | Casos marcados por reglas |
| Tasa de alerta | ___ % | Presión estimada de fraude en el lote |
| Top merchant por riesgo | ___ | Comercio más expuesto |
| Top card por riesgo | ___ | Tarjeta más anómala |
| Dispositivos compartidos | ___ | Posibles puntos de fraude conectado |
| Tarjetas en múltiples países | ___ | Posible compromiso de credenciales |

## 5. Interpretación esperada de Bronze, Silver y Gold

### Bronze

Conclusiones que debes transmitir:

- representa la traza operativa original
- es útil para auditoría y replay
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
- prepara dos consumos distintos: analítico y relacional

## 6. Conclusiones técnicas recomendadas

Estas conclusiones son apropiadas para la defensa del proyecto:

1. La arquitectura Lakehouse separa correctamente la ingesta, el enriquecimiento y la explotación analítica.
2. Kafka y Spark permiten desacoplar la recepción del evento de su procesamiento posterior.
3. Iceberg aporta versionado, gestion de tablas y una base más robusta para consultas que un simple almacenamiento de ficheros.
4. Trino permite consultar el dato de forma unificada sin moverlo.
5. Superset cubre la capa de observabilidad operativa para negocio y riesgo.
6. Airflow encaja bien para tareas bajo demanda que no deben ejecutarse continuamente.
7. Neo4j aporta valor diferencial al revelar conexiones entre entidades que no se aprecian bien en SQL tabular.

## 7. Conclusiones funcionales recomendadas

Estas conclusiones conectan mejor con negocio:

1. El sistema detecta patrones de fraude frecuentes: alta velocidad, dispersión geográfica, multiplicidad de comercios y dispositivos compartidos.
2. La explicabilidad de `reasons` permite justificar cada alerta.
3. El dashboard facilita monitorización rápida de volumen, alertas y focos de riesgo.
4. El modelo de grafo permite pasar de la alerta aislada a la investigación de redes sospechosas.
5. La solución es ampliable: se pueden añadir reglas, features y modelos de scoring sin romper la arquitectura base.

## 8. Limitaciones que conviene reconocer en la exposición

Es mejor explicarlas de forma directa:

1. El score actual está basado en reglas y pesos heurísticos, no en un modelo supervisado entrenado.
2. Los datos son sintéticos, por lo que sirven para demostrar arquitectura y lógica, no para validar precisión real de fraude.
3. La calidad final depende de ejecutar y ajustar el entorno Docker en la máquina de demo.
4. La visualización en Superset se ha dejado guiada manualmente porque su configuración final depende del entorno activo y de los objetos creados en la UI.

## 9. Mejoras futuras que elevan la propuesta

Si te preguntan cómo evolucionarlo:

1. Entrenar un modelo de machine learning sobre Silver y combinarlo con reglas.
2. Introducir listas negras o enriquecimiento externo por IP, BIN o geolocalización.
3. Automatizar snapshots y exportaciones periódicas del grafo.
4. Añadir tests de calidad de datos y validaciones automáticas.
5. Incorporar alertado operacional con correo, Slack o webhooks.

## 10. Mensaje final recomendado para el cierre

Puedes cerrar la exposición con una idea como está:

El proyecto demuestra una cadena completa de detección de fraude sobre arquitectura moderna de datos. Parte de eventos casi en tiempo real, los consolida en un Lakehouse, genera alertas interpretables, habilita analítica SQL y dashboards, y termina en un grafo de investigación para descubrir relaciones complejas. No es solo una demo de herramientas conectadas, sino un flujo coherente de ingesta, procesamiento, explotación y análisis forense.

## 11. Conclusiones finales desarrolladas

El proyecto ha servido para comprobar, de forma muy práctica, que una arquitectura moderna de datos no consiste solo en conectar herramientas, sino en definir un flujo coherente de extremo a extremo. A lo largo del trabajo hemos construido una cadena completa que empieza en la generación de eventos de pago, continúa con su ingesta y transformación en un Lakehouse, y termina en dos modos distintos de explotación: el analítico, mediante SQL y dashboards, y el relacional, mediante un grafo de investigación en Neo4j. Ese recorrido completo es, probablemente, el principal aprendizaje del proyecto.

Desde el punto de vista funcional, el sistema ha demostrado que es capaz de transformar eventos técnicos en información útil para la detección de fraude. En la ejecución validada se procesaron `7443` registros en Bronze, `7299` en Silver y `7049` alertas en Gold. Más allá del volumen concreto, lo importante es que cada capa ha cumplido una función distinta y bien separada. Bronze ha actuado como traza operativa y capa de persistencia cruda; Silver ha limpiado, tipado y enriquecido los datos con contexto temporal y agregados de comportamiento; y Gold ha convertido ese dato enriquecido en alertas interpretables, con un `risk_score` y un campo `reasons_text` que permiten entender por qué una transacción ha sido marcada como sospechosa. Esto da valor real a la solución, porque no se limita a etiquetar casos, sino que ofrece explicabilidad, algo esencial en contextos de riesgo y auditoría.

Otro aprendizaje importante ha sido entender que SQL y grafo no compiten entre sí, sino que resuelven preguntas distintas. Con Trino hemos podido validar rápidamente volúmenes, tasas de alerta y entidades con mayor riesgo. Con Neo4j, en cambio, se ha hecho visible algo que en tablas resulta mucho más costoso de interpretar: la existencia de dispositivos compartidos, tarjetas conectadas a múltiples pagos sospechosos y comercios relacionados con actividad anómala. El proyecto confirma, por tanto, que una aproximación híbrida tiene mucho sentido en fraude: el Lakehouse aporta consistencia, histórico y capacidad de consulta; el grafo aporta contexto relacional e investigación forense.

También hemos aprendido bastante sobre la parte operativa y de infraestructura. Montar todo el sistema en Docker sobre un equipo ligero, en este caso un MacBook Air M1 con `8 GB` de RAM, nos ha obligado a enfrentarnos a problemas reales de integración y recursos. Hemos tenido errores de resolución de imágenes, cambios de tags no disponibles, conflictos de `entrypoint` y `command` en Airflow y Superset, problemas de región al usar MinIO a través del cliente S3 compatible de Iceberg, caídas intermitentes de Trino y Neo4j por memoria, workers de Airflow terminados con `SIGKILL` y algún fallo más fino en Spark y PySpark durante Gold. Aunque estos problemas han ralentizado la puesta en marcha, también han aportado un aprendizaje muy valioso: en un proyecto de datos real, tan importante como escribir transformaciones es saber observar el sistema, leer logs, aislar servicios, reducir consumo y decidir qué partes del pipeline son críticas y cuáles pueden degradarse sin bloquear el objetivo principal.

Precisamente por eso, una conclusión relevante es que el proyecto no solo demuestra conocimientos de analítica de datos, sino también de ingeniería de datos. Ha sido necesario tomar decisiones pragmáticas para que la demo fuese estable: convertir la compactación en un paso no bloqueante, reducir el número de workers de Airflow, rebajar memoria de Trino y Neo4j, y trabajar por fases apagando contenedores no imprescindibles. Esa experiencia refuerza la idea de que la robustez operativa forma parte del valor de una solución, y no es un detalle secundario.

Respecto a la utilidad del proyecto, la solución construida puede servir como base de un sistema de detección e investigación de fraude para pagos o transacciones financieras. En su estado actual ya permite simular eventos, procesarlos, generar alertas explicables, analizarlos por SQL y visualizarlos como red de relaciones. Eso la convierte en una plataforma muy buena para docencia, prototipado o validación de arquitectura. No pretende ser un detector final listo para producción, porque trabaja con datos sintéticos y reglas heurísticas, pero sí demuestra con claridad cómo debería organizarse una cadena real de ingesta, enriquecimiento, scoring y análisis posterior.

De cara al futuro, el proyecto tiene un recorrido claro. La primera mejora natural sería sustituir o complementar las reglas heurísticas por un modelo de machine learning entrenado sobre Silver, de forma que el `risk_score` no dependiera solo de umbrales manuales. Otra mejora importante sería incorporar enriquecimiento externo, por ejemplo con listas negras, información de BIN, reputación de IPs o geolocalización más precisa. También sería muy interesante reforzar la calidad y gobernanza del dato con tests automáticos, controles de calidad, validaciones de esquema y alertas sobre drift o cambios en la distribución de variables. En la parte de infraestructura, una evolución razonable sería separar mejor los entornos de demo y mantenimiento, para que tareas pesadas como la compactación no compartan recursos con la capa interactiva. Y, finalmente, en la parte de negocio, se podría mejorar la explotación creando dashboards más ricos, workflows de investigación y exportaciones periódicas del grafo para casos o snapshots temporales.

En definitiva, el proyecto ha permitido aprender arquitectura, procesamiento, consulta, visualización y operación de una plataforma de datos orientada a fraude. Se ha comprobado que el enfoque Lakehouse encaja muy bien como columna vertebral del dato, que la orquestación y la observabilidad son imprescindibles, y que el grafo aporta una capa diferencial de investigación. A pesar de las limitaciones y de los problemas encontrados, el resultado final es consistente: se ha construido un sistema completo, explicable y ampliable, que demuestra de forma creíble cómo se puede abordar la detección de fraude con tecnologías modernas de ingeniería de datos.
