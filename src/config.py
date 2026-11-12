"""Configuración central del proyecto ETL de apuestas deportivas.

Aquí se definen las rutas del proyecto, los nombres estándar de las columnas,
los alias de columnas y equipos, y utilidades de logging. Todo el proyecto
trabaja con rutas relativas construidas a partir de la ubicación de este archivo.
"""

from __future__ import annotations

import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Rutas del proyecto (siempre relativas a la raíz del repositorio)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
FIGURES_DIR: Path = REPORTS_DIR / "figures"
LOGS_DIR: Path = REPORTS_DIR / "logs"

# ---------------------------------------------------------------------------
# Esquema estándar (nombres canónicos usados por todo el pipeline)
# ---------------------------------------------------------------------------
COLUMNAS_ESTANDAR: list[str] = [
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
]

# Alias aceptados al leer las fuentes. Las claves están normalizadas con
# ``normalizar_clave`` (minúsculas, sin tildes, separadores convertidos en "_").
ALIAS_COLUMNAS: dict[str, str] = {
    # Identificador
    "id_evento": "id_evento",
    "id": "id_evento",
    "evento_id": "id_evento",
    "id_partido": "id_evento",
    "id_encuentro": "id_evento",
    "codigo_evento": "id_evento",
    "event_id": "id_evento",
    # Deporte
    "deporte": "deporte",
    "sport": "deporte",
    "disciplina": "deporte",
    # Equipos / jugadores
    "equipo_local": "equipo_local",
    "local": "equipo_local",
    "equipo_casa": "equipo_local",
    "home_team": "equipo_local",
    "jugador_local": "equipo_local",
    "equipo1": "equipo_local",
    "equipo_visitante": "equipo_visitante",
    "visitante": "equipo_visitante",
    "equipo_fuera": "equipo_visitante",
    "away_team": "equipo_visitante",
    "jugador_visitante": "equipo_visitante",
    "equipo2": "equipo_visitante",
    # Fecha
    "fecha_evento": "fecha_evento",
    "fecha": "fecha_evento",
    "fecha_partido": "fecha_evento",
    "date": "fecha_evento",
    "event_date": "fecha_evento",
    # Resultado
    "resultado": "resultado",
    "marcador": "resultado",
    "score": "resultado",
    "resultado_final": "resultado",
    # Competición
    "competicion": "competicion",
    "liga": "competicion",
    "league": "competicion",
    "torneo": "competicion",
    "tournament": "competicion",
    "competition": "competicion",
    # Cuotas
    "cuota_local": "cuota_local",
    "odd_local": "cuota_local",
    "home_odds": "cuota_local",
    "odds_home": "cuota_local",
    "cuota1": "cuota_local",
    "cuota_1": "cuota_local",
    "cuota_empate": "cuota_empate",
    "empate": "cuota_empate",
    "odd_empate": "cuota_empate",
    "draw_odds": "cuota_empate",
    "cuota_x": "cuota_empate",
    "cuota_visitante": "cuota_visitante",
    "odd_visitante": "cuota_visitante",
    "away_odds": "cuota_visitante",
    "odds_away": "cuota_visitante",
    "cuota2": "cuota_visitante",
    "cuota_2": "cuota_visitante",
}

# ---------------------------------------------------------------------------
# Equipos / jugadores canónicos por deporte
# ---------------------------------------------------------------------------
DEPORTES: dict[str, list[str]] = {
    "Fútbol": [
        "Real Madrid",
        "Barcelona",
        "Atlético de Madrid",
        "Sevilla",
        "Valencia",
        "Villarreal",
        "Real Sociedad",
        "Athletic Club",
        "Betis",
        "Celta de Vigo",
        "Osasuna",
        "Getafe",
        "Mallorca",
        "Rayo Vallecano",
        "Alavés",
        "Espanyol",
        "Elche",
        "Cádiz",
        "Levante",
        "Granada",
        "Manchester City",
        "Manchester United",
        "Liverpool",
        "Arsenal",
        "Chelsea",
        "Tottenham",
        "Bayern Múnich",
        "Borussia Dortmund",
        "Juventus",
        "Inter de Milán",
        "Milan",
        "PSG",
    ],
    "Baloncesto": [
        "Lakers",
        "Celtics",
        "Warriors",
        "Bulls",
        "Heat",
        "Knicks",
        "Bucks",
        "Suns",
        "Mavericks",
        "Nuggets",
        "Real Madrid",
        "Barcelona",
        "Baskonia",
        "Valencia Basket",
        "Unicaja",
        "Gran Canaria",
        "Tenerife",
        "Joventut",
        "Bilbao Basket",
        "Zaragoza",
    ],
    "Tenis": [
        "Carlos Alcaraz",
        "Novak Djokovic",
        "Rafael Nadal",
        "Daniil Medvedev",
        "Jannik Sinner",
        "Alexander Zverev",
        "Stefanos Tsitsipas",
        "Andrey Rublev",
        "Casper Ruud",
        "Taylor Fritz",
        "Iga Swiatek",
        "Aryna Sabalenka",
        "Elena Rybakina",
        "Coco Gauff",
        "Ons Jabeur",
        "Jessica Pegula",
        "Maria Sakkari",
        "Caroline Garcia",
        "Holger Rune",
        "Hubert Hurkacz",
        "Frances Tiafoe",
        "Tommy Paul",
        "Alex de Minaur",
        "Grigor Dimitrov",
    ],
}

# Alias de equipos: clave normalizada -> nombre canónico.
# No se incluyen alias ambiguos entre deportes (por ejemplo "valencia").
ALIAS_EQUIPOS: dict[str, str] = {
    # Fútbol
    "r_madrid": "Real Madrid",
    "real_madird": "Real Madrid",
    "real_madrid_cf": "Real Madrid",
    "madrid": "Real Madrid",
    "barca": "Barcelona",
    "fc_barcelona": "Barcelona",
    "barcellona": "Barcelona",
    "atletico": "Atlético de Madrid",
    "atleti": "Atlético de Madrid",
    "atletico_madrid": "Atlético de Madrid",
    "athletic": "Athletic Club",
    "athletic_bilbao": "Athletic Club",
    "real_betis": "Betis",
    "celta": "Celta de Vigo",
    "la_real": "Real Sociedad",
    "sevilla_fc": "Sevilla",
    "valencia_cf": "Valencia",
    "villarreal_cf": "Villarreal",
    "man_city": "Manchester City",
    "mancity": "Manchester City",
    "man_united": "Manchester United",
    "manchester_utd": "Manchester United",
    "spurs": "Tottenham",
    "bayern": "Bayern Múnich",
    "bayern_munich": "Bayern Múnich",
    "dortmund": "Borussia Dortmund",
    "bvb": "Borussia Dortmund",
    "juve": "Juventus",
    "inter": "Inter de Milán",
    "internazionale": "Inter de Milán",
    "ac_milan": "Milan",
    "paris_saint_germain": "PSG",
    # Baloncesto
    "la_lakers": "Lakers",
    "l_a_lakers": "Lakers",
    "los_angeles_lakers": "Lakers",
    "gsw": "Warriors",
    "golden_state": "Warriors",
    "golden_state_warriors": "Warriors",
    "ny_knicks": "Knicks",
    "new_york_knicks": "Knicks",
    "miami_heat": "Heat",
    "boston_celtics": "Celtics",
    "chicago_bulls": "Bulls",
    "phoenix_suns": "Suns",
    "dallas_mavericks": "Mavericks",
    "mavs": "Mavericks",
    "denver_nuggets": "Nuggets",
    "milwaukee_bucks": "Bucks",
    "real_madrid_baloncesto": "Real Madrid",
    "barca_basket": "Barcelona",
    "baskonia_vitoria": "Baskonia",
    "valencia_basket": "Valencia Basket",
    "valencia_bc": "Valencia Basket",
    "unicaja_malaga": "Unicaja",
    "dreamland_gran_canaria": "Gran Canaria",
    "lenovo_tenerife": "Tenerife",
    "iberostar_tenerife": "Tenerife",
    "penya": "Joventut",
    "joventut_badalona": "Joventut",
    "bilbao": "Bilbao Basket",
    "casademont_zaragoza": "Zaragoza",
    # Tenis
    "alcaraz": "Carlos Alcaraz",
    "djokovic": "Novak Djokovic",
    "nadal": "Rafael Nadal",
    "medvedev": "Daniil Medvedev",
    "sinner": "Jannik Sinner",
    "zverev": "Alexander Zverev",
    "tsitsipas": "Stefanos Tsitsipas",
    "rublev": "Andrey Rublev",
    "ruud": "Casper Ruud",
    "fritz": "Taylor Fritz",
    "swiatek": "Iga Swiatek",
    "sabalenka": "Aryna Sabalenka",
    "rybakina": "Elena Rybakina",
    "gauff": "Coco Gauff",
    "jabeur": "Ons Jabeur",
    "pegula": "Jessica Pegula",
    "sakkari": "Maria Sakkari",
    "garcia": "Caroline Garcia",
    "rune": "Holger Rune",
    "hurkacz": "Hubert Hurkacz",
    "tiafoe": "Frances Tiafoe",
    "paul": "Tommy Paul",
    "de_minaur": "Alex de Minaur",
    "dimitrov": "Grigor Dimitrov",
}


def normalizar_clave(texto: Any) -> str:
    """Normaliza un texto para usarlo como clave de comparación.

    Convierte a minúsculas, elimina tildes/diacríticos y reemplaza cualquier
    secuencia de caracteres no alfanuméricos por un guion bajo.

    Args:
        texto: Valor de entrada (columna, equipo o categoría).

    Returns:
        Cadena normalizada, por ejemplo ``"Atlético de Madrid"`` ->
        ``"atletico_de_madrid"``.
    """
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower().strip())
    return limpio.strip("_")


# Recalcular el índice de equipos ahora que ``normalizar_clave`` ya existe.
DEPORTES_POR_CLAVE = {
    normalizar_clave(deporte): equipos for deporte, equipos in DEPORTES.items()
}

DEPORTE_POR_CLAVE: dict[str, str] = {
    normalizar_clave(deporte): deporte for deporte in DEPORTES
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_FORMATO_LOG = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Configura logging a consola y a ``reports/logs/pipeline.log``.

    Es idempotente: si ya existe un handler de este proyecto no se duplica,
    lo que evita mensajes repetidos cuando se ejecuta main.py o pytest.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            try:
                flujo.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass
    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(nivel)
    if getattr(logger_raiz, "_etl_configurado", False):
        return

    consola = logging.StreamHandler()
    consola.setFormatter(logging.Formatter(_FORMATO_LOG))

    archivo = logging.FileHandler(LOGS_DIR / "pipeline.log", encoding="utf-8")
    archivo.setFormatter(logging.Formatter(_FORMATO_LOG))

    logger_raiz.addHandler(consola)
    logger_raiz.addHandler(archivo)
    logger_raiz._etl_configurado = True  # type: ignore[attr-defined]
