"""Pruebas unitarias de la fase Extract."""

from __future__ import annotations

import pandas as pd

from src.config import COLUMNAS_ESTANDAR
from src.extract import extraer, leer_archivo, unificar_columnas


def test_extraer_csv_y_excel_con_esquemas_distintos(tmp_path) -> None:
    """Extrae y unifica dos fuentes con nombres de columna diferentes."""
    futbol = pd.DataFrame(
        {
            "ID": ["F1"],
            "Deporte": ["Fútbol"],
            "Equipo_Local": ["Real Madrid"],
            "Equipo_Visitante": ["Barcelona"],
            "Fecha": ["2023-02-01"],
            "Marcador": ["2-1"],
            "Competicion": ["La Liga"],
            "Cuota Local": ["1,85"],
            "Cuota Empate": ["3,40"],
            "Cuota Visitante": ["4,20"],
        }
    )
    futbol.to_csv(tmp_path / "futbol.csv", index=False, encoding="utf-8-sig")

    tenis = pd.DataFrame(
        {
            "ID_Evento": ["T1"],
            "Deporte": ["Tenis"],
            "Jugador_Local": ["Carlos Alcaraz"],
            "Jugador_Visitante": ["Rafael Nadal"],
            "Fecha": ["2023/03/10"],
            "Resultado": ["2-0"],
            "Torneo": ["Wimbledon"],
            "Cuota_Local": [1.5],
            "Cuota_Visitante": [2.8],
        }
    )
    tenis.to_excel(tmp_path / "tenis.xlsx", index=False, engine="openpyxl")

    datos = extraer(raw_dir=tmp_path)

    assert len(datos) == 2
    assert list(datos.columns) == COLUMNAS_ESTANDAR + ["fuente_archivo"]
    assert set(datos["fuente_archivo"]) == {"futbol.csv", "tenis.xlsx"}
    assert datos["cuota_empate"].isna().sum() == 1


def test_unificar_columnas_completa_columnas_ausentes() -> None:
    """Las columnas que no existen en la fuente se agregan como nulas."""
    df = pd.DataFrame({"ID": ["A"], "Deporte": ["Fútbol"]})
    unificado = unificar_columnas(df, "prueba.csv")

    assert list(unificado.columns) == COLUMNAS_ESTANDAR
    assert unificado["cuota_local"].isna().all()


def test_leer_archivo_corrupto_devuelve_vacio(tmp_path) -> None:
    """Un Excel corrupto no detiene el pipeline: se informa y se omite."""
    ruta = tmp_path / "roto.xlsx"
    ruta.write_bytes(b"esto no es un archivo de Excel")

    resultado = leer_archivo(ruta)

    assert resultado.empty


def test_extraer_sin_archivos_devuelve_esquema_vacio(tmp_path) -> None:
    """Sin fuentes disponibles se devuelve un DataFrame vacío con esquema."""
    datos = extraer(raw_dir=tmp_path)

    assert datos.empty
    assert list(datos.columns) == COLUMNAS_ESTANDAR + ["fuente_archivo"]
