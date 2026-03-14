# Security Policy

## Supported use

Este repositorio esta pensado como proyecto academico y entorno local de demostracion.
No esta endurecido para produccion.

## Scope

Antes de publicar o desplegar fuera de local:

- cambia todas las credenciales por defecto
- mueve secretos a un gestor seguro
- limita puertos expuestos
- revisa politicas de red, almacenamiento y acceso
- endurece Airflow, Superset, Trino, MinIO y Neo4j

## Reporting a vulnerability

Si detectas una vulnerabilidad relevante:

1. No la publiques en una issue abierta.
2. Comparte una descripcion reproducible, impacto y version afectada.
3. Propone una mitigacion o workaround si es posible.

## Known demo defaults

El proyecto incluye credenciales de ejemplo en `.env.example` para facilitar la puesta en marcha local.
No deben reutilizarse en entornos reales.

