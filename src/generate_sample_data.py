"""Generador de datos simulados y deliberadamente sucios.

El objetivo es contar con un conjunto de datos académico, reproducible y con
problemas realistas de calidad (duplicados, nulos, formatos mezclados, cuotas
inválidas, nombres mal escritos y esquemas distintos entre fuentes).

Uso:
    python -m src.generate_sample_data
    python src/generate_sample_data.py --semilla 123
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ in (None, ""):  # Permite ejecutar el archivo directamente.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    ALIAS_EQUIPOS,
    DEPORTES,
    RAW_DIR,
    configurar_logging,
)

logger = logging.getLogger(__name__)

SEMILLA_POR_DEFECTO = 42
FECHA_INICIO = date(2021, 1, 1)
FECHA_FIN = date(2024, 12, 31)

# Cantidad de registros "limpios" por fuente (antes de inyectar duplicados).
CONFIG_DEPORTES: dict[str, dict[str, Any]] = {
    "Fútbol": {
        "registros": 1800,
        "prefijo": "FUT",
        "competiciones": [
            "La Liga",
            "Premier League",
            "Serie A",
            "Bundesliga",
            "Ligue 1",
            "UEFA Champions League",
        ],
        "tiene_empate": True,
    },
    "Baloncesto": {
        "registros": 900,
        "prefijo": "BAL",
        "competiciones": ["NBA", "Euroliga", "Liga ACB", "Copa del Rey"],
        "tiene_empate": False,
    },
    "Tenis": {
        "registros": 650,
        "prefijo": "TEN",
        "competiciones": [
            "Australian Open",
            "Roland Garros",
            "Wimbledon",
            "US Open",
            "ATP Masters 1000",
            "WTA 1000",
        ],
        "tiene_empate": False,
    },
}

FORMATOS_FECHA = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]
MESES_TEXTO_GEN = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Variantes "sucias" (abreviaturas) por equipo canónico.
VARIANTES_EQUIPO: dict[str, list[str]] = {}
for _clave, _canonico in ALIAS_EQUIPOS.items():
    VARIANTES_EQUIPO.setdefault(_canonico, []).append(_clave)

# Nombres de columna distintos por fuente, para forzar la unificación del ETL.
ESQUEMAS_FUENTE: dict[str, dict[str, str]] = {
    "eventos_futbol.csv": {col: col for col in [
        "id_evento", "deporte", "equipo_local", "equipo_visitante",
        "fecha_evento", "resultado", "competicion", "cuota_local",
        "cuota_empate", "cuota_visitante",
    ]},
    "eventos_baloncesto.csv": {
        "id_evento": "ID",
        "deporte": "Deporte",
        "equipo_local": "Equipo_Local",
        "equipo_visitante": "Equipo_Visitante",
        "fecha_evento": "Fecha",
        "resultado": "Marcador",
        "competicion": "Competicion",
        "cuota_local": "Cuota Local",
        "cuota_empate": "Cuota Empate",
        "cuota_visitante": "Cuota Visitante",
    },
    "eventos_tenis.xlsx": {
        "id_evento": "ID_Evento",
        "deporte": "Deporte",
        "equipo_local": "Jugador_Local",
        "equipo_visitante": "Jugador_Visitante",
        "fecha_evento": "Fecha",
        "resultado": "Resultado",
        "competicion": "Torneo",
        "cuota_local": "Cuota_Local",
        "cuota_visitante": "Cuota_Visitante",
    },
}


def _sin_tildes(texto: str) -> str:
    """Devuelve el texto sin tildes ni diacríticos."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _fecha_aleatoria(rng: random.Random) -> date:
    """Genera una fecha uniforme dentro del rango histórico simulado."""
    dias = (FECHA_FIN - FECHA_INICIO).days
    return FECHA_INICIO + timedelta(days=rng.randint(0, dias))


def _typo(nombre: str, rng: random.Random) -> str:
    """Introduce un error tipográfico intercambiando dos letras de una palabra."""
    palabras = [p for p in nombre.split() if len(p) > 4]
    if not palabras:
        return nombre
    palabra = rng.choice(palabras)
    indice = rng.randrange(1, len(palabra) - 1)
    letras = list(palabra)
    letras[indice], letras[indice + 1] = letras[indice + 1], letras[indice]
    return nombre.replace(palabra, "".join(letras), 1)


def _ensuciar_equipo(nombre: str, rng: random.Random) -> str | None:
    """Aplica una variante sucia a un nombre de equipo o jugador."""
    if rng.random() < 0.01:
        return None
    if rng.random() > 0.30:
        return nombre

    variantes = VARIANTES_EQUIPO.get(nombre, [])
    probabilidad = rng.random()
    if probabilidad < 0.18:
        return nombre.upper()
    if probabilidad < 0.32:
        return f"  {nombre.replace(' ', '  ', 1)} "
    if probabilidad < 0.48:
        return _sin_tildes(nombre)
    if probabilidad < 0.70 and variantes:
        return rng.choice(variantes)
    if probabilidad < 0.90:
        return _typo(nombre, rng)
    return nombre.lower()


def _ensuciar_fecha(valor: date, rng: random.Random, permitir_objeto: bool) -> Any:
    """Mezcla formatos de fecha e inyecta valores inválidos o nulos."""
    probabilidad = rng.random()
    if probabilidad < 0.015:
        return rng.choice(["N/A", "31/02/2024", "sin fecha", "--/--/----"])
    if probabilidad < 0.025:
        return None
    if permitir_objeto and probabilidad < 0.45:
        return valor
    formato = rng.choice(FORMATOS_FECHA + ["texto"])
    if formato == "texto":
        return f"{valor.day} de {MESES_TEXTO_GEN[valor.month - 1]} de {valor.year}"
    return valor.strftime(formato)


def _ensuciar_cuota(valor: float | None, rng: random.Random) -> Any:
    """Convierte cuotas a texto, inyecta nulos y valores fuera de rango."""
    if valor is None or pd.isna(valor):
        return None
    probabilidad = rng.random()
    if probabilidad < 0.020:
        return rng.choice(["N/A", "n/d", "-"])
    if probabilidad < 0.100:
        return f"{valor:.2f}".replace(".", ",")
    if probabilidad < 0.115:
        return round(-rng.uniform(1.0, 3.0), 2)
    if probabilidad < 0.130:
        return 0.0
    if probabilidad < 0.140:
        return round(rng.uniform(80.0, 250.0), 2)
    return valor


def _marcador(deporte: str, rng: random.Random, tiene_empate: bool) -> tuple[int, int]:
    """Genera un marcador coherente con el deporte."""
    if tiene_empate:
        local = rng.choices(range(6), weights=[16, 26, 24, 16, 10, 8])[0]
        visitante = rng.choices(range(6), weights=[22, 28, 23, 14, 8, 5])[0]
        return local, visitante
    if deporte == "Baloncesto":
        local = rng.randint(78, 128)
        visitante = rng.randint(78, 128)
        if local == visitante:
            local += 1
        return local, visitante
    # Tenis: el resultado representa sets ganados (2-0 o 2-1).
    perdedor = rng.choice([0, 1])
    return (2, perdedor) if rng.random() < 0.5 else (perdedor, 2)


def _cuotas(deporte: str, rng: random.Random) -> tuple[float, float | None, float]:
    """Genera cuotas plausibles (siempre mayores que 1.0)."""
    if deporte == "Fútbol":
        return (
            round(rng.uniform(1.40, 4.20), 2),
            round(rng.uniform(2.90, 4.30), 2),
            round(rng.uniform(1.50, 6.00), 2),
        )
    if deporte == "Baloncesto":
        return (
            round(rng.uniform(1.20, 7.50), 2),
            None,
            round(rng.uniform(1.20, 7.50), 2),
        )
    return (
        round(rng.uniform(1.10, 5.50), 2),
        None,
        round(rng.uniform(1.10, 5.50), 2),
    )


def _generar_registros(deporte: str, rng: random.Random) -> pd.DataFrame:
    """Construye los registros "limpios" de un deporte antes de ensuciarlos."""
    config = CONFIG_DEPORTES[deporte]
    equipos = DEPORTES[deporte]
    filas: list[dict[str, Any]] = []

    for indice in range(1, config["registros"] + 1):
        local, visitante = rng.sample(equipos, 2)
        marcador_local, marcador_visitante = _marcador(
            deporte, rng, config["tiene_empate"]
        )
        cuota_local, cuota_empate, cuota_visitante = _cuotas(deporte, rng)
        filas.append(
            {
                "id_evento": f"{config['prefijo']}-{indice:06d}",
                "deporte": deporte,
                "equipo_local": local,
                "equipo_visitante": visitante,
                "fecha_evento": _fecha_aleatoria(rng),
                "resultado": f"{marcador_local}-{marcador_visitante}",
                "competicion": rng.choice(config["competiciones"]),
                "cuota_local": cuota_local,
                "cuota_empate": cuota_empate,
                "cuota_visitante": cuota_visitante,
            }
        )

    return pd.DataFrame(filas)


def _ensuciar(df: pd.DataFrame, rng: random.Random, deporte: str) -> pd.DataFrame:
    """Inyecta nulos, formatos mezclados, typos y cuotas inválidas."""
    df = df.copy()

    df["equipo_local"] = df["equipo_local"].map(lambda x: _ensuciar_equipo(x, rng))
    df["equipo_visitante"] = df[
        "equipo_visitante"
    ].map(lambda x: _ensuciar_equipo(x, rng))

    permitir_objeto = deporte == "Tenis"
    df["fecha_evento"] = df["fecha_evento"].map(
        lambda x: _ensuciar_fecha(x, rng, permitir_objeto)
    )

    for columna in ("cuota_local", "cuota_empate", "cuota_visitante"):
        df[columna] = df[columna].map(lambda x: _ensuciar_cuota(x, rng))

    df["resultado"] = df["resultado"].map(
        lambda x: None if rng.random() < 0.020 else x
    )
    df["competicion"] = df["competicion"].map(
        lambda x: None if rng.random() < 0.015 else (
            f" {x} " if rng.random() < 0.02 else x
        )
    )

    return df


def _inyectar_duplicados(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """Agrega duplicados exactos y duplicados por ``id_evento`` con cambios."""
    n_exactos = max(1, int(len(df) * 0.015))
    duplicados_exactos = df.sample(n=n_exactos, random_state=rng.randint(0, 10**6))
    df = pd.concat([df, duplicados_exactos], ignore_index=True)

    n_por_id = max(1, int(len(df) * 0.008))
    indices = rng.sample(range(len(df)), n_por_id)
    copias = df.iloc[indices].copy()
    copias["cuota_local"] = 1.95
    copias["equipo_local"] = copias["equipo_local"].astype("string").fillna("Desconocido") + " "
    copias["resultado"] = "1-1"
    df = pd.concat([df, copias], ignore_index=True)

    return df.sample(frac=1.0, random_state=rng.randint(0, 10**6)).reset_index(drop=True)


def _renombrar_para_fuente(df: pd.DataFrame, archivo: str) -> pd.DataFrame:
    """Renombra las columnas con el esquema particular de cada fuente."""
    esquema = ESQUEMAS_FUENTE[archivo]
    salida = df[[col for col in esquema]].rename(columns=esquema)
    return salida


def generar_datos(
    raw_dir: Path = RAW_DIR,
    semilla: int = SEMILLA_POR_DEFECTO,
) -> dict[str, int]:
    """Genera las tres fuentes crudas y devuelve el conteo por archivo.

    Args:
        raw_dir: Carpeta donde se escribirán los archivos crudos.
        semilla: Semilla aleatoria para garantizar reproducibilidad.

    Returns:
        Diccionario ``{nombre_archivo: numero_de_registros}``.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(semilla)
    conteos: dict[str, int] = {}

    for deporte, config in CONFIG_DEPORTES.items():
        archivo = {
            "Fútbol": "eventos_futbol.csv",
            "Baloncesto": "eventos_baloncesto.csv",
            "Tenis": "eventos_tenis.xlsx",
        }[deporte]

        df = _generar_registros(deporte, rng)
        df = _ensuciar(df, rng, deporte)
        df = _inyectar_duplicados(df, rng)
        df = _renombrar_para_fuente(df, archivo)

        ruta = raw_dir / archivo
        if ruta.suffix == ".csv":
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
        else:
            df.to_excel(ruta, index=False, sheet_name="eventos", engine="openpyxl")

        conteos[archivo] = len(df)
        logger.info("Fuente generada: %s (%s registros)", ruta.name, len(df))

    logger.info(
        "Datos simulados creados con semilla=%s | total registros crudos=%s",
        semilla,
        sum(conteos.values()),
    )
    return conteos


def main() -> int:
    """Punto de entrada para ejecutar el generador por separado."""
    parser = argparse.ArgumentParser(description="Genera datos simulados sucios.")
    parser.add_argument(
        "--semilla", type=int, default=SEMILLA_POR_DEFECTO, help="Semilla aleatoria."
    )
    args = parser.parse_args()
    configurar_logging()
    generar_datos(semilla=args.semilla)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
