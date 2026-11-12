"""Pruebas del modelo estrella y de la carga de datos."""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.load import (
    cargar_sqlite,
    construir_modelo_estrella,
    guardar_modelo_estrella,
)
from src.transform import run_transform


def _modelo(df_crudo: pd.DataFrame, tmp_path) -> dict[str, pd.DataFrame]:
    limpio, _ = run_transform(df_crudo, reports_dir=tmp_path / "reports")
    return construir_modelo_estrella(limpio)


def test_modelo_estrella_tiene_claves_y_granularidad(
    df_crudo: pd.DataFrame, tmp_path
) -> None:
    """Las dimensiones son únicas y la tabla de hechos conserva el grano."""
    tablas = _modelo(df_crudo, tmp_path)

    assert set(tablas) == {
        "dim_equipos",
        "dim_deportes",
        "dim_competiciones",
        "dim_fecha",
        "fact_eventos",
    }
    assert len(tablas["fact_eventos"]) == 5
    assert tablas["fact_eventos"]["id_evento"].is_unique
    assert tablas["dim_equipos"]["id_equipo"].is_unique
    assert tablas["dim_deportes"]["id_deporte"].is_unique
    assert tablas["dim_competiciones"]["id_competicion"].is_unique
    assert tablas["dim_fecha"]["id_fecha"].is_unique
    assert tablas["dim_fecha"]["fecha"].is_unique

    hecho = tablas["fact_eventos"]
    assert hecho["id_deporte"].notna().all()
    assert hecho["id_competicion"].notna().all()
    assert hecho["id_fecha"].notna().all()
    equipos_validos = set(tablas["dim_equipos"]["id_equipo"])
    for columna in ("id_equipo_local", "id_equipo_visitante"):
        assert set(hecho[columna].dropna()).issubset(equipos_validos)


def test_guardar_tablas_y_cargar_sqlite(
    df_crudo: pd.DataFrame, tmp_path
) -> None:
    """Las tablas se guardan en CSV y se cargan en SQLite."""
    tablas = _modelo(df_crudo, tmp_path)
    procesados = tmp_path / "processed"

    rutas = guardar_modelo_estrella(tablas, procesados)
    assert set(rutas) == set(tablas)
    assert all(ruta.exists() for ruta in rutas.values())

    ruta_db = cargar_sqlite(tablas, tmp_path / "apuestas.db")
    assert ruta_db.exists()

    with sqlite3.connect(ruta_db) as conexion:
        total = conexion.execute("SELECT COUNT(*) FROM fact_eventos").fetchone()[0]
    assert total == len(tablas["fact_eventos"])
