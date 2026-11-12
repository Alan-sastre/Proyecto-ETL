"""Fase Load: persistencia del dataset limpio y modelo estrella simple.

Genera los archivos que consume Power BI:

* ``data/processed/eventos_limpios.csv`` y ``.xlsx``
* ``dim_equipos.csv``, ``dim_deportes.csv``, ``dim_competiciones.csv``,
  ``dim_fecha.csv`` y ``fact_eventos.csv``
* Opcionalmente, una base SQLite ``data/processed/apuestas.db``.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    PROCESSED_DIR,
    configurar_logging,
)
from src.transform import MESES_ES, DIAS_SEMANA  # noqa: E402

logger = logging.getLogger(__name__)


def _categorias_a_texto(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas categóricas a texto para exportaciones estables."""
    df = df.copy()
    for columna in df.select_dtypes(include="category").columns:
        df[columna] = df[columna].astype(object)
    return df


def guardar_dataset(
    df: pd.DataFrame, processed_dir: Path = PROCESSED_DIR
) -> dict[str, Path]:
    """Guarda el dataset limpio en CSV (UTF-8) y Excel."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    ruta_csv = processed_dir / "eventos_limpios.csv"
    ruta_xlsx = processed_dir / "eventos_limpios.xlsx"

    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    df.to_excel(
        ruta_xlsx, index=False, sheet_name="eventos_limpios", engine="openpyxl"
    )
    logger.info("Dataset limpio guardado: %s y %s", ruta_csv.name, ruta_xlsx.name)
    return {"csv": ruta_csv, "xlsx": ruta_xlsx}


def construir_dim_deportes(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la dimensión de deportes con su conteo de eventos."""
    conteos = df["deporte"].astype(str).value_counts()
    deportes = sorted(conteos.index)
    return pd.DataFrame(
        {
            "id_deporte": [f"DEP-{indice:02d}" for indice in range(1, len(deportes) + 1)],
            "deporte": deportes,
            "n_eventos": [int(conteos[deporte]) for deporte in deportes],
        }
    )


def construir_dim_competiciones(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la dimensión de competiciones (competición + deporte)."""
    agrupado = (
        df.groupby(["competicion", "deporte"], observed=True)
        .size()
        .reset_index(name="n_eventos")
        .sort_values(["deporte", "competicion"], kind="stable")
        .reset_index(drop=True)
    )
    agrupado.insert(
        0,
        "id_competicion",
        [f"COM-{indice:03d}" for indice in range(1, len(agrupado) + 1)],
    )
    agrupado["competicion"] = agrupado["competicion"].astype(str)
    agrupado["deporte"] = agrupado["deporte"].astype(str)
    return agrupado


def construir_dim_equipos(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la dimensión de equipos/jugadores con estadísticas básicas."""
    base = df[["equipo_local", "equipo_visitante", "deporte", "resultado_normalizado"]]

    local = pd.DataFrame(
        {
            "equipo": base["equipo_local"],
            "deporte": base["deporte"],
            "victorias": (base["resultado_normalizado"] == "Local").astype(int),
            "empates": (base["resultado_normalizado"] == "Empate").astype(int),
            "derrotas": (base["resultado_normalizado"] == "Visitante").astype(int),
        }
    )
    visitante = pd.DataFrame(
        {
            "equipo": base["equipo_visitante"],
            "deporte": base["deporte"],
            "victorias": (base["resultado_normalizado"] == "Visitante").astype(int),
            "empates": (base["resultado_normalizado"] == "Empate").astype(int),
            "derrotas": (base["resultado_normalizado"] == "Local").astype(int),
        }
    )

    equipos = pd.concat([local, visitante], ignore_index=True)
    equipos["equipo"] = equipos["equipo"].astype(str)
    equipos = equipos[equipos["equipo"] != "Desconocido"]

    resumen = (
        equipos.groupby(["equipo", "deporte"], observed=True)
        .agg(
            partidos=("victorias", "size"),
            victorias=("victorias", "sum"),
            empates=("empates", "sum"),
            derrotas=("derrotas", "sum"),
        )
        .reset_index()
        .sort_values(["deporte", "equipo"], kind="stable")
        .reset_index(drop=True)
    )
    resumen["tasa_victoria"] = (resumen["victorias"] / resumen["partidos"]).round(4)
    resumen.insert(
        0,
        "id_equipo",
        [f"EQP-{indice:04d}" for indice in range(1, len(resumen) + 1)],
    )
    resumen["deporte"] = resumen["deporte"].astype(str)
    return resumen[
        [
            "id_equipo", "equipo", "deporte", "partidos", "victorias",
            "empates", "derrotas", "tasa_victoria",
        ]
    ]


def construir_dim_fecha(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la dimensión de fechas a partir de los eventos."""
    fechas = pd.DataFrame(
        {"fecha": pd.to_datetime(sorted(df["fecha_evento"].dropna().unique()))}
    )
    if fechas.empty:
        return fechas

    fechas["id_fecha"] = fechas["fecha"].dt.strftime("%Y-%m-%d")
    fechas["año"] = fechas["fecha"].dt.year
    fechas["trimestre"] = "T" + fechas["fecha"].dt.quarter.astype(str)
    fechas["mes"] = fechas["fecha"].dt.month
    fechas["nombre_mes"] = fechas["mes"].map(MESES_ES)
    fechas["semana_iso"] = fechas["fecha"].dt.isocalendar().week.astype(int)
    fechas["dia"] = fechas["fecha"].dt.day
    fechas["dia_semana"] = fechas["fecha"].dt.dayofweek.map(DIAS_SEMANA)
    fechas["es_fin_semana"] = fechas["fecha"].dt.dayofweek.isin([5, 6])
    return fechas[
        [
            "id_fecha", "fecha", "año", "trimestre", "mes", "nombre_mes",
            "semana_iso", "dia", "dia_semana", "es_fin_semana",
        ]
    ]


def construir_fact_eventos(
    df: pd.DataFrame,
    dim_deportes: pd.DataFrame,
    dim_competiciones: pd.DataFrame,
    dim_equipos: pd.DataFrame,
) -> pd.DataFrame:
    """Construye la tabla de hechos con claves foráneas del modelo estrella."""
    hechos = df.copy()

    mapa_deporte = dict(zip(dim_deportes["deporte"], dim_deportes["id_deporte"]))
    mapa_competicion = {
        (fila.competicion, fila.deporte): fila.id_competicion
        for fila in dim_competiciones.itertuples(index=False)
    }
    mapa_equipo = {
        (fila.equipo, fila.deporte): fila.id_equipo
        for fila in dim_equipos.itertuples(index=False)
    }

    hechos["id_fecha"] = hechos["fecha_evento"].dt.strftime("%Y-%m-%d")
    hechos["id_deporte"] = hechos["deporte"].astype(str).map(mapa_deporte)
    hechos["id_competicion"] = [
        mapa_competicion.get((str(competicion), str(deporte)))
        for competicion, deporte in zip(hechos["competicion"], hechos["deporte"])
    ]
    hechos["id_equipo_local"] = [
        mapa_equipo.get((str(equipo), str(deporte)))
        for equipo, deporte in zip(hechos["equipo_local"], hechos["deporte"])
    ]
    hechos["id_equipo_visitante"] = [
        mapa_equipo.get((str(equipo), str(deporte)))
        for equipo, deporte in zip(hechos["equipo_visitante"], hechos["deporte"])
    ]

    columnas = [
        "id_evento", "id_fecha", "fecha_evento", "id_deporte", "id_competicion",
        "id_equipo_local", "id_equipo_visitante", "marcador_local",
        "marcador_visitante", "goles_local", "goles_visitante", "puntos_local",
        "puntos_visitante", "diferencia_marcador", "resultado_normalizado",
        "cuota_local", "cuota_empate", "cuota_visitante", "cuota_favorita",
        "favorito", "prob_implicita_local", "prob_implicita_empate",
        "prob_implicita_visitante", "margen_mercado", "fuente_archivo",
    ]
    return hechos[columnas].copy()


def construir_modelo_estrella(
    df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Construye las cuatro dimensiones y la tabla de hechos."""
    dim_deportes = construir_dim_deportes(df)
    dim_competiciones = construir_dim_competiciones(df)
    dim_equipos = construir_dim_equipos(df)
    dim_fecha = construir_dim_fecha(df)
    fact_eventos = construir_fact_eventos(
        df, dim_deportes, dim_competiciones, dim_equipos
    )
    return {
        "dim_deportes": dim_deportes,
        "dim_competiciones": dim_competiciones,
        "dim_equipos": dim_equipos,
        "dim_fecha": dim_fecha,
        "fact_eventos": fact_eventos,
    }


def guardar_modelo_estrella(
    tablas: dict[str, pd.DataFrame], processed_dir: Path = PROCESSED_DIR
) -> dict[str, Path]:
    """Guarda cada tabla del modelo estrella en CSV UTF-8."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}
    for nombre, tabla in tablas.items():
        ruta = processed_dir / f"{nombre}.csv"
        tabla = _categorias_a_texto(tabla)
        tabla.to_csv(ruta, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
        rutas[nombre] = ruta
        logger.info("Tabla del modelo estrella guardada: %s (%s filas)", ruta.name, len(tabla))
    return rutas


def cargar_sqlite(
    tablas: dict[str, pd.DataFrame],
    db_path: Path = PROCESSED_DIR / "apuestas.db",
) -> Path:
    """Carga las tablas en una base SQLite local (reemplazándolas si existen)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conexion:
        for nombre, tabla in tablas.items():
            tabla = _categorias_a_texto(tabla)
            tabla.to_sql(nombre, conexion, if_exists="replace", index=False)
            logger.info("Tabla SQLite cargada: %s (%s filas)", nombre, len(tabla))
    logger.info("Base SQLite disponible en %s", db_path)
    return db_path


def run_load(
    df: pd.DataFrame,
    processed_dir: Path = PROCESSED_DIR,
    usar_sqlite: bool = True,
) -> dict[str, Path]:
    """Ejecuta la fase Load completa y devuelve las rutas generadas."""
    if df.empty:
        logger.error("El dataset está vacío; no se genera ningún archivo.")
        return {}

    rutas = guardar_dataset(df, processed_dir)
    tablas = construir_modelo_estrella(df)
    rutas.update(guardar_modelo_estrella(tablas, processed_dir))

    if usar_sqlite:
        rutas["sqlite"] = cargar_sqlite(tablas, processed_dir / "apuestas.db")

    logger.info(
        "Carga finalizada: %s filas y %s tablas del modelo estrella",
        len(df),
        len(tablas),
    )
    return rutas


def main() -> int:
    """Ejecuta Extract + Transform + Load de forma independiente."""
    from src.extract import extraer
    from src.transform import run_transform

    configurar_logging()
    df_crudo = extraer()
    if df_crudo.empty:
        logger.error("No hay datos para cargar.")
        return 1
    df_limpio, _ = run_transform(df_crudo)
    run_load(df_limpio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
