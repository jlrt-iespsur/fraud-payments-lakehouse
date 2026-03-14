# Security Policy

## Supported use

Este repositorio está pensado como proyecto académico y entorno local de demostración.
No está endurecido para producción.

## Scope

Antes de públicar o desplegar fuera de local:

- cambia todas las credenciales por defecto
- mueve secretos a un gestor seguro
- limita puertos expuestos
- revisa políticas de red, almacenamiento y acceso
- endurece Airflow, Superset, Trino, MinIO y Neo4j

## Reporting a vulnerability

Si detectas una vulnerabilidad relevante:

1. No la publiques en una issue abierta.
2. Comparte una descripción reproducible, impacto y versión afectada.
3. Propone una mitigación o workaround si es posible.

## Known demo defaults

El proyecto incluye credenciales de ejemplo en `.env.example` para facilitar la puesta en marcha local.
No deben reutilizarse en entornos reales.
