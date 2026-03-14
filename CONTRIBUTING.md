# Contributing

Gracias por tu interés en mejorar este proyecto.

## Flujo de trabajo recomendado

1. Crea una rama a partir de `main`.
2. Haz cambios pequeños y coherentes por tema.
3. Actualiza la documentación si cambia el comportamiento funcional.
4. Verifica el flujo afectado antes de abrir la propuesta:
   - `./scripts/start_all.sh`
   - `./scripts/run_bronze.sh`
   - `./scripts/run_silver.sh`
   - `./scripts/run_gold.sh`
5. Describe en la propuesta:
   - problema que resuelve
   - impacto técnico
   - pasos de validación

## Normas prácticas

- No subas secretos ni archivos `.env`.
- No subas datos de `runtime/`.
- Manten ASCII por defecto en scripts y configuración.
- Evita cambios mezclados de estilo y lógica en la misma propuesta.
- Si tocas Docker, Airflow, Trino o Spark, añade una nota de operación en `README.md` o `docs/`.

## Calidad mínima

- Los scripts deben seguir funcionando en macOS con Docker Desktop.
- Las credenciales de ejemplo deben permanecer en `.env.example`.
- Los logs y artefactos generados no deben entrar en Git.
