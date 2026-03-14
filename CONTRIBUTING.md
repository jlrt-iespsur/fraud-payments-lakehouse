# Contributing

Gracias por tu interes en mejorar este proyecto.

## Flujo de trabajo recomendado

1. Crea una rama a partir de `main`.
2. Haz cambios pequenos y coherentes por tema.
3. Actualiza la documentacion si cambia el comportamiento funcional.
4. Verifica el flujo afectado antes de abrir la propuesta:
   - `./scripts/start_all.sh`
   - `./scripts/run_bronze.sh`
   - `./scripts/run_silver.sh`
   - `./scripts/run_gold.sh`
5. Describe en la propuesta:
   - problema que resuelve
   - impacto tecnico
   - pasos de validacion

## Normas practicas

- No subas secretos ni archivos `.env`.
- No subas datos de `runtime/`.
- Manten ASCII por defecto en scripts y configuracion.
- Evita cambios mezclados de estilo y logica en la misma propuesta.
- Si tocas Docker, Airflow, Trino o Spark, anade una nota de operacion en `README.md` o `docs/`.

## Calidad minima

- Los scripts deben seguir funcionando en macOS con Docker Desktop.
- Las credenciales de ejemplo deben permanecer en `.env.example`.
- Los logs y artefactos generados no deben entrar en Git.

