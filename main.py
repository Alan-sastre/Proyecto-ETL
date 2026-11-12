"""Orquestador del proyecto ETL de apuestas deportivas.

Ejecuta con un solo comando las fases Extract -> Transform -> Load ->
Visualizaciones, generando todos los entregables del proyecto.

Uso:
    python main.py
    python main.py --regenerar --semilla 42
    python main.py --sin-graficos --sin-sqlite
"""

from __future__ import annotations

import argparse
import logging
import time
from src.config import (
    FIGURES_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    REPORTS_DIR,
    configurar_logging,
)
from src.extract import extraer
from src.generate_sample_data import SEMILLA_POR_DEFECTO, generar_datos
from src.load import run_load
from src.transform import run_transform
from src.visualizations import generar_visualizaciones

logger = logging.getLogger("main")


def _existen_fuentes_crudas() -> bool:
    """Indica si ya hay archivos CSV o Excel en ``data/raw``."""
    if not RAW_DIR.exists():
        return False
    return any(
        ruta.suffix.lower() in {".csv", ".xlsx", ".xls"}
        and not ruta.name.startswith("~$")
        for ruta in RAW_DIR.iterdir()
        if ruta.is_file()
    )


def _construir_parser() -> argparse.ArgumentParser:
    """Define los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Pipeline ETL académico de datos simulados de apuestas deportivas."
    )
    parser.add_argument(
        "--regenerar",
        action="store_true",
        help="Vuelve a generar los datos simulados crudos antes del ETL.",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=SEMILLA_POR_DEFECTO,
        help=f"Semilla para los datos simulados (por defecto {SEMILLA_POR_DEFECTO}).",
    )
    parser.add_argument(
        "--sin-graficos",
        action="store_true",
        help="Omite la generación de figuras con Matplotlib.",
    )
    parser.add_argument(
        "--sin-sqlite",
        action="store_true",
        help="Omite la carga opcional a la base de datos SQLite.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ejecuta el pipeline completo y devuelve un código de salida."""
    args = _construir_parser().parse_args(argv)
    configurar_logging()
    inicio = time.perf_counter()

    logger.info("=" * 72)
    logger.info("PROYECTO ETL: ANÁLISIS DE DATOS DE APUESTAS DEPORTIVAS")
    logger.info("=" * 72)

    try:
        if args.regenerar or not _existen_fuentes_crudas():
            logger.info("Generando datos simulados (semilla=%s)...", args.semilla)
            generar_datos(semilla=args.semilla)
        else:
            logger.info("Se usarán las fuentes existentes en %s", RAW_DIR)

        logger.info("--- FASE 1: EXTRACT ---")
        df_crudo = extraer()
        if df_crudo.empty:
            logger.error("No se pudieron extraer datos. Revisa data/raw/.")
            return 1

        logger.info("--- FASE 2: TRANSFORM ---")
        df_limpio, stats = run_transform(df_crudo)

        logger.info("--- FASE 3: LOAD ---")
        rutas = run_load(df_limpio, usar_sqlite=not args.sin_sqlite)

        if not args.sin_graficos:
            logger.info("--- FASE 4: VISUALIZACIÓN ---")
            generar_visualizaciones(df_limpio)

        duracion = time.perf_counter() - inicio
        logger.info("=" * 72)
        logger.info("RESUMEN DEL PROCESO")
        logger.info("=" * 72)
        logger.info("Registros crudos extraídos:        %s", f"{stats.filas_iniciales:,}")
        logger.info("Registros limpios finales:         %s", f"{stats.filas_finales:,}")
        logger.info("Duplicados exactos eliminados:     %s", f"{stats.duplicados_exactos:,}")
        logger.info("Duplicados por id eliminados:      %s", f"{stats.duplicados_por_id:,}")
        logger.info("Filas sin id eliminadas:           %s", f"{stats.filas_sin_id:,}")
        logger.info("Fechas inválidas eliminadas:       %s", f"{stats.fechas_invalidas:,}")
        logger.info("Nombres de equipo corregidos:      %s", f"{stats.equipos_corregidos:,}")
        logger.info(
            "Cuotas inválidas corregidas:       %s",
            f"{sum(stats.cuotas_invalidas.values()):,}",
        )
        logger.info(
            "Cuotas atípicas tratadas:          %s",
            f"{sum(stats.cuotas_atipicas.values()):,}",
        )
        logger.info(
            "Cuotas nulas imputadas:            %s",
            f"{sum(stats.cuotas_imputadas.values()):,}",
        )
        logger.info("Resultados desconocidos:           %s", f"{stats.resultados_desconocidos:,}")
        tablas_estrella = [
            clave for clave in rutas if clave.startswith(("dim_", "fact_"))
        ]
        logger.info("Tablas del modelo estrella:        %s", len(tablas_estrella))
        logger.info("Dataset limpio:                    %s", PROCESSED_DIR)
        logger.info("Reporte de calidad:                %s", REPORTS_DIR)
        logger.info("Figuras:                           %s", FIGURES_DIR)
        logger.info("Duración total:                    %.1f segundos", duracion)
        logger.info("=" * 72)
        return 0

    except Exception as error:  # noqa: BLE001 - se registra y se devuelve error
        logger.exception("El pipeline falló: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
