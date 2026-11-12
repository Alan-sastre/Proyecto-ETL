"""Fase Extract: lectura y unificación de las fuentes crudas.

Descubre automáticamente archivos CSV y Excel en ``data/raw/``, los lee con
tolerancia a codificaciones y separadores, unifica los nombres de columnas y
agrega la columna de trazabilidad ``fuente_archivo``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    ALIAS_COLUMNAS,
    COLUMNAS_ESTANDAR,
    RAW_DIR,
    configurar_logging,
    normalizar_clave,
)

logger = logging.getLogger(__name__)

EXTENSIONES_VALIDAS = (".csv", ".xlsx", ".xls")
CODIFICACIONES = ("utf-8-sig", "utf-8", "latin-1")
SEPARADORES = (None, ";", "\t", ",")


def descubrir_archivos(raw_dir: Path = RAW_DIR) -> list[Path]:
    """Lista los archivos de datos disponibles, ignorando temporales de Excel."""
    if not raw_dir.exists():
        logger.error("La carpeta de datos crudos no existe: %s", raw_dir)
        return []

    archivos = [
        ruta
        for ruta in sorted(raw_dir.iterdir())
        if ruta.is_file()
        and ruta.suffix.lower() in EXTENSIONES_VALIDAS
        and not ruta.name.startswith("~$")
    ]
    if not archivos:
        logger.warning("No se encontraron archivos CSV o Excel en %s", raw_dir)
    return archivos


def _leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee un CSV probando codificaciones y separadores habituales."""
    ultimo_error: Exception | None = None
    for codificacion in CODIFICACIONES:
        for separador in SEPARADORES:
            try:
                if separador is None:
                    df = pd.read_csv(
                        ruta,
                        encoding=codificacion,
                        sep=None,
                        engine="python",
                    )
                else:
                    df = pd.read_csv(
                        ruta, encoding=codificacion, sep=separador, engine="python"
                    )
                if df.shape[1] > 1 or len(df) == 0:
                    return df
            except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
                ultimo_error = error
    if ultimo_error is not None:
        raise ultimo_error
    raise pd.errors.EmptyDataError(f"No se pudo interpretar el archivo {ruta.name}")


def leer_archivo(ruta: Path) -> pd.DataFrame:
    """Lee un archivo CSV o Excel y devuelve un DataFrame.

    Los errores se registran con un mensaje claro y se devuelve un DataFrame
    vacío, de modo que una fuente corrupta no detenga todo el pipeline.
    """
    try:
        if ruta.suffix.lower() == ".csv":
            df = _leer_csv(ruta)
        else:
            df = pd.read_excel(ruta, engine="openpyxl")
        logger.info("Leídos %s registros desde %s", len(df), ruta.name)
        return df
    except Exception as error:  # noqa: BLE001 - se informa y se continúa
        logger.error("No se pudo leer %s: %s", ruta.name, error)
        return pd.DataFrame()


def unificar_columnas(df: pd.DataFrame, nombre_archivo: str = "") -> pd.DataFrame:
    """Renombra columnas al esquema estándar y completa las columnas faltantes.

    Args:
        df: Datos crudos de una fuente.
        nombre_archivo: Nombre del archivo, solo para mensajes de log.

    Returns:
        DataFrame con exactamente las columnas de ``COLUMNAS_ESTANDAR``.
    """
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_ESTANDAR)

    renombres: dict[str, str] = {}
    usadas: set[str] = set()
    extras: list[str] = []

    for columna in df.columns:
        canonica = ALIAS_COLUMNAS.get(normalizar_clave(columna))
        if canonica and canonica not in usadas:
            renombres[columna] = canonica
            usadas.add(canonica)
        else:
            extras.append(str(columna))

    if extras:
        logger.warning(
            "%s: columnas no reconocidas (se omiten): %s",
            nombre_archivo or "fuente",
            ", ".join(extras),
        )

    df = df.rename(columns=renombres)
    df = df.loc[:, ~df.columns.duplicated()]

    faltantes = [col for col in COLUMNAS_ESTANDAR if col not in df.columns]
    for columna in faltantes:
        df[columna] = pd.NA
    if faltantes:
        logger.warning(
            "%s: columnas ausentes completadas con nulos: %s",
            nombre_archivo or "fuente",
            ", ".join(faltantes),
        )

    return df[COLUMNAS_ESTANDAR].copy()


def extraer(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Extrae y concatena todas las fuentes disponibles.

    Returns:
        DataFrame unificado con la columna adicional ``fuente_archivo``.
        Si no hay datos, devuelve un DataFrame vacío con el esquema esperado.
    """
    archivos = descubrir_archivos(raw_dir)
    if not archivos:
        return pd.DataFrame(columns=COLUMNAS_ESTANDAR + ["fuente_archivo"])

    partes: list[pd.DataFrame] = []
    for ruta in archivos:
        df = leer_archivo(ruta)
        if df.empty:
            logger.warning("Se omite la fuente vacía o ilegible: %s", ruta.name)
            continue
        df = unificar_columnas(df, ruta.name)
        df["fuente_archivo"] = ruta.name
        partes.append(df)
        logger.info(
            "Fuente %s aportada al dataset: %s registros", ruta.name, len(df)
        )

    if not partes:
        logger.error("Ninguna fuente pudo procesarse correctamente.")
        return pd.DataFrame(columns=COLUMNAS_ESTANDAR + ["fuente_archivo"])

    datos = pd.concat(partes, ignore_index=True)
    logger.info(
        "Extracción finalizada: %s registros desde %s fuentes",
        len(datos),
        len(partes),
    )
    return datos


def main() -> int:
    """Ejecuta la extracción de forma independiente y muestra un resumen."""
    configurar_logging()
    datos = extraer()
    if datos.empty:
        logger.error("No hay datos para procesar.")
        return 1
    logger.info("Vista previa:\n%s", datos.head(5).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
