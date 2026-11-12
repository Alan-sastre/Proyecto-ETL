"""Fixtures compartidas por las pruebas del proyecto ETL."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Permite importar ``src`` al ejecutar pytest desde la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COLUMNAS_CRUDAS = [
    "id_evento",
    "deporte",
    "equipo_local",
    "equipo_visitante",
    "fecha_evento",
    "resultado",
    "competicion",
    "cuota_local",
    "cuota_empate",
    "cuota_visitante",
    "fuente_archivo",
]


@pytest.fixture
def df_crudo() -> pd.DataFrame:
    """Dataset pequeño y sucio que cubre todos los problemas del ETL."""
    registros = [
        {
            "id_evento": "FUT-001",
            "deporte": "Fútbol",
            "equipo_local": "  real madird ",
            "equipo_visitante": "BARCELONA",
            "fecha_evento": "01/02/2023",
            "resultado": "2-1",
            "competicion": "La Liga",
            "cuota_local": "1,85",
            "cuota_empate": "3,40",
            "cuota_visitante": "4,20",
            "fuente_archivo": "futbol.csv",
        },
        # Duplicado exacto del anterior.
        {
            "id_evento": "FUT-001",
            "deporte": "Fútbol",
            "equipo_local": "  real madird ",
            "equipo_visitante": "BARCELONA",
            "fecha_evento": "01/02/2023",
            "resultado": "2-1",
            "competicion": "La Liga",
            "cuota_local": "1,85",
            "cuota_empate": "3,40",
            "cuota_visitante": "4,20",
            "fuente_archivo": "futbol.csv",
        },
        # Duplicado por id con otros valores.
        {
            "id_evento": "FUT-001",
            "deporte": "Fútbol",
            "equipo_local": "Real Madrid",
            "equipo_visitante": "Barcelona",
            "fecha_evento": "2023-02-01",
            "resultado": "2-1",
            "competicion": "La Liga",
            "cuota_local": 1.90,
            "cuota_empate": 3.30,
            "cuota_visitante": 4.00,
            "fuente_archivo": "futbol.csv",
        },
        # Fecha inválida: debe eliminarse.
        {
            "id_evento": "FUT-002",
            "deporte": "Fútbol",
            "equipo_local": "Atletico",
            "equipo_visitante": "Sevilla",
            "fecha_evento": "31/02/2023",
            "resultado": "0-0",
            "competicion": None,
            "cuota_local": -1.5,
            "cuota_empate": 0,
            "cuota_visitante": "N/A",
            "fuente_archivo": "futbol.csv",
        },
        {
            "id_evento": "BAL-001",
            "deporte": "Baloncesto",
            "equipo_local": "Lakers",
            "equipo_visitante": "Celtics",
            "fecha_evento": "2023/03/10",
            "resultado": "98-91",
            "competicion": "NBA",
            "cuota_local": "1,50",
            "cuota_empate": None,
            "cuota_visitante": "2,60",
            "fuente_archivo": "baloncesto.csv",
        },
        {
            "id_evento": "BAL-002",
            "deporte": "Baloncesto",
            "equipo_local": None,
            "equipo_visitante": "Warriors",
            "fecha_evento": "10-03-2023",
            "resultado": "100-95",
            "competicion": "NBA",
            "cuota_local": 200,
            "cuota_empate": None,
            "cuota_visitante": 1.20,
            "fuente_archivo": "baloncesto.csv",
        },
        {
            "id_evento": "TEN-001",
            "deporte": "Tenis",
            "equipo_local": "alcaraz",
            "equipo_visitante": "nadal",
            "fecha_evento": "5 de marzo de 2024",
            "resultado": "2-0",
            "competicion": "Wimbledon",
            "cuota_local": 1.50,
            "cuota_empate": None,
            "cuota_visitante": 2.80,
            "fuente_archivo": "tenis.xlsx",
        },
        {
            "id_evento": "TEN-002",
            "deporte": "Tenis",
            "equipo_local": "Djokovic",
            "equipo_visitante": "Sinner",
            "fecha_evento": "2024-03-05",
            "resultado": "2-1",
            "competicion": None,
            "cuota_local": "N/A",
            "cuota_empate": None,
            "cuota_visitante": "N/A",
            "fuente_archivo": "tenis.xlsx",
        },
        # Sin identificador: debe eliminarse en el tratamiento de nulos.
        {
            "id_evento": None,
            "deporte": "Fútbol",
            "equipo_local": "Getafe",
            "equipo_visitante": "Osasuna",
            "fecha_evento": "2023-04-15",
            "resultado": "1-1",
            "competicion": "La Liga",
            "cuota_local": 3.10,
            "cuota_empate": 3.00,
            "cuota_visitante": 2.90,
            "fuente_archivo": "futbol.csv",
        },
    ]
    return pd.DataFrame(registros, columns=COLUMNAS_CRUDAS)
