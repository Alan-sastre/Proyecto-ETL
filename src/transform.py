"""Fase Transform: limpieza, normalización y enriquecimiento del dataset.

Cada paso está implementado como una función independiente, registra con
logging cuántos registros afecta y puede probarse de forma aislada con pytest.
"""

from __future__ import annotations

import difflib
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    ALIAS_EQUIPOS,
    DEPORTES,
    DEPORTES_POR_CLAVE,
    REPORTS_DIR,
    configurar_logging,
    normalizar_clave,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de negocio
# ---------------------------------------------------------------------------
LIMITE_CUOTA: float = 50.0
CUTOFF_SIMILITUD: float = 0.80

MESES_ES: dict[int, str] = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

DIAS_SEMANA: dict[int, str] = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

MESES_TEXTO: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

COLUMNAS_FINALES: list[str] = [
    "id_evento", "deporte", "equipo_local", "equipo_visitante", "fecha_evento",
    "año", "mes", "nombre_mes", "dia", "dia_semana", "competicion", "resultado",
    "marcador_local", "marcador_visitante", "goles_local", "goles_visitante",
    "puntos_local", "puntos_visitante", "diferencia_marcador",
    "resultado_normalizado", "cuota_local", "cuota_empate", "cuota_visitante",
    "cuota_favorita", "favorito", "prob_implicita_local",
    "prob_implicita_empate", "prob_implicita_visitante", "margen_mercado",
    "fuente_archivo",
]

ESTRATEGIA_NULOS: list[tuple[str, str, str]] = [
    ("id_evento", "Eliminar fila", "Sin identificador no es posible deduplicar ni trazar el evento."),
    ("fecha_evento", "Eliminar fila", "La fecha es imprescindible para el modelo temporal; imputarla introduciría sesgo."),
    ("deporte", "Imputar 'Desconocido'", "Se conserva el registro y se hace explícita la ausencia de dato."),
    ("equipo_local", "Imputar 'Desconocido'", "Se conserva el evento; el equipo no participa en los rankings."),
    ("equipo_visitante", "Imputar 'Desconocido'", "Se conserva el evento; el equipo no participa en los rankings."),
    ("competicion", "Imputar 'Desconocida'", "Categoría explícita para no perder el evento."),
    ("resultado", "Imputar 'Desconocido'", "El marcador derivado queda nulo y el resultado se marca como desconocido."),
    ("cuota_local", "Imputar mediana por deporte", "La mediana es robusta a valores extremos y respeta el deporte."),
    ("cuota_empate", "Nulo estructural / mediana en deportes con empate", "Baloncesto y tenis no admiten empate: no se inventa una cuota."),
    ("cuota_visitante", "Imputar mediana por deporte", "La mediana es robusta a valores extremos y respeta el deporte."),
    ("fuente_archivo", "Imputar 'desconocida'", "Columna de trazabilidad, nunca debe quedar vacía."),
]


@dataclass
class TransformStats:
    """Acumula métricas del proceso de transformación para el reporte."""

    filas_iniciales: int = 0
    filas_finales: int = 0
    duplicados_exactos: int = 0
    duplicados_por_id: int = 0
    filas_sin_id: int = 0
    filas_sin_fecha: int = 0
    fechas_invalidas: int = 0
    equipos_corregidos: int = 0
    resultados_desconocidos: int = 0
    nulos_antes: dict[str, int] = field(default_factory=dict)
    nulos_despues: dict[str, int] = field(default_factory=dict)
    nulos_imputados: dict[str, int] = field(default_factory=dict)
    cuotas_invalidas: dict[str, int] = field(default_factory=dict)
    cuotas_atipicas: dict[str, int] = field(default_factory=dict)
    cuotas_imputadas: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _conteo_nulos(df: pd.DataFrame) -> dict[str, int]:
    """Cuenta nulos por columna y los devuelve como diccionario."""
    return {columna: int(valor) for columna, valor in df.isna().sum().items()}


def _limpiar_espacios(valor: Any) -> str:
    """Colapsa espacios repetidos y recorta extremos de un texto."""
    if valor is None:
        return "Desconocido"
    try:
        if pd.isna(valor):
            return "Desconocido"
    except (TypeError, ValueError):
        pass
    limpio = re.sub(r"\s+", " ", str(valor)).strip()
    return limpio or "Desconocido"


def _equipo_canonico(nombre: Any, deporte: Any) -> str:
    """Devuelve el nombre canónico de un equipo o jugador.

    Estrategia: limpieza de espacios -> diccionario de alias -> coincidencia
    exacta normalizada -> similitud con ``difflib``. Si no hay coincidencia
    fiable se conserva el nombre limpio.
    """
    limpio = _limpiar_espacios(nombre)
    clave = normalizar_clave(limpio)
    if not clave or clave in {"desconocido", "desconocida", "sin_equipo"}:
        return "Desconocido"
    if clave in ALIAS_EQUIPOS:
        return ALIAS_EQUIPOS[clave]

    candidatos = DEPORTES_POR_CLAVE.get(normalizar_clave(deporte))
    if not candidatos:
        candidatos = [equipo for equipos in DEPORTES.values() for equipo in equipos]

    exactos = {normalizar_clave(equipo): equipo for equipo in candidatos}
    if clave in exactos:
        return exactos[clave]

    coincidencias = difflib.get_close_matches(
        limpio, candidatos, n=1, cutoff=CUTOFF_SIMILITUD
    )
    return coincidencias[0] if coincidencias else limpio


def _cuota_a_numero(valor: Any) -> float:
    """Convierte una cuota almacenada como texto a ``float``.

    Soporta coma decimal (``"1,85"``), separadores de miles y valores como
    ``"N/A"`` (devuelve ``NaN``).
    """
    if valor is None:
        return float("nan")
    try:
        if pd.isna(valor):
            return float("nan")
    except (TypeError, ValueError):
        pass
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip().replace("€", "").replace(" ", "")
    if not texto or texto.lower() in {"n/a", "n/d", "na", "nan", "none", "-"}:
        return float("nan")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return float("nan")


def _parsear_marcador(resultado: Any) -> tuple[int | None, int | None]:
    """Extrae los dos marcadores de un texto como ``"2-1"`` o ``"98:91"``."""
    if resultado is None:
        return None, None
    try:
        if pd.isna(resultado):
            return None, None
    except (TypeError, ValueError):
        pass
    coincidencia = re.search(r"(\d+)\s*[-:xX]\s*(\d+)", str(resultado))
    if not coincidencia:
        return None, None
    return int(coincidencia.group(1)), int(coincidencia.group(2))


def parsear_fecha(valor: Any) -> pd.Timestamp:
    """Convierte fechas en múltiples formatos a ``Timestamp`` (o ``NaT``).

    Reconoce ``DD/MM/YYYY``, ``YYYY-MM-DD``, ``DD-MM-YYYY``, ``YYYY/MM/DD``,
    ``YYYYMMDD`` y expresiones como ``"5 de marzo de 2024"``. Los valores
    inválidos, vacíos o fuera de rango devuelven ``pd.NaT``.
    """
    if valor is None:
        return pd.NaT
    if isinstance(valor, pd.Timestamp):
        fecha = valor
    elif isinstance(valor, (datetime, date)):
        fecha = pd.Timestamp(valor)
    else:
        texto = re.sub(r"\s+", " ", str(valor).strip())
        if not texto or normalizar_clave(texto) in {
            "n_a", "na", "nan", "none", "sin_fecha", "s_f", "fecha_invalida"
        }:
            return pd.NaT

        coincidencia = re.match(
            r"^(\d{1,2})\s+de\s+([a-záéíóúüñ]+)\s+de\s+(\d{4})$", texto, re.IGNORECASE
        )
        if coincidencia:
            dia, mes_texto, anio = coincidencia.groups()
            mes = MESES_TEXTO.get(normalizar_clave(mes_texto))
            if mes is None:
                return pd.NaT
            fecha = pd.to_datetime(
                f"{anio}-{mes:02d}-{int(dia):02d}", errors="coerce"
            )
        elif re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T].*)?$", texto):
            fecha = pd.to_datetime(texto, errors="coerce", yearfirst=True)
        elif re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$", texto):
            fecha = pd.to_datetime(texto, errors="coerce", dayfirst=True)
        elif re.match(r"^\d{8}$", texto):
            fecha = pd.to_datetime(texto, format="%Y%m%d", errors="coerce")
        else:
            fecha = pd.to_datetime(texto, errors="coerce", dayfirst=True)

    if pd.isna(fecha) or not 1990 <= fecha.year <= 2100:
        return pd.NaT
    return fecha.normalize()


# ---------------------------------------------------------------------------
# Pasos del ETL
# ---------------------------------------------------------------------------
def eliminar_duplicados(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Elimina duplicados exactos y duplicados por ``id_evento``.

    Para los duplicados por identificador se conserva la fila más completa
    (mayor número de valores no nulos); en caso de empate se mantiene la
    primera aparición en el archivo.
    """
    stats = stats or TransformStats()
    df = df.copy()

    n_inicial = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    stats.duplicados_exactos = n_inicial - len(df)
    df["_orden_original"] = range(len(df))

    con_id = df[df["id_evento"].notna()].copy()
    sin_id = df[df["id_evento"].isna()].copy()

    con_id["_completitud"] = con_id.notna().sum(axis=1)
    n_con_id = len(con_id)
    con_id = (
        con_id.sort_values(
            ["_completitud", "_orden_original"], ascending=[False, True], kind="stable"
        )
        .drop_duplicates(subset=["id_evento"], keep="first")
        .drop(columns=["_completitud"])
    )
    stats.duplicados_por_id = n_con_id - len(con_id)

    df = (
        pd.concat([con_id, sin_id])
        .sort_values("_orden_original")
        .drop(columns=["_orden_original"])
        .reset_index(drop=True)
    )
    logger.info(
        "Duplicados eliminados: %s exactos y %s por id_evento (quedan %s filas)",
        stats.duplicados_exactos,
        stats.duplicados_por_id,
        len(df),
    )
    return df


def tratar_nulos(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Aplica la estrategia de nulos documentada en ``ESTRATEGIA_NULOS``.

    Las cuotas se imputan más adelante, cuando ya se validaron sus rangos.
    """
    stats = stats or TransformStats()
    df = df.copy()

    columnas_texto = [
        "deporte", "equipo_local", "equipo_visitante", "competicion",
        "resultado", "fuente_archivo",
    ]
    for columna in columnas_texto:
        df[columna] = df[columna].map(
            lambda valor: pd.NA
            if isinstance(valor, str) and not valor.strip()
            else valor
        )

    n_inicial = len(df)
    df = df[df["id_evento"].notna()]
    df = df[df["id_evento"].astype("string").str.strip().str.len() > 0]
    stats.filas_sin_id = n_inicial - len(df)

    imputaciones = {
        "deporte": "Desconocido",
        "equipo_local": "Desconocido",
        "equipo_visitante": "Desconocido",
        "competicion": "Desconocida",
        "resultado": "Desconocido",
        "fuente_archivo": "desconocida",
    }
    for columna, valor in imputaciones.items():
        nulos = int(df[columna].isna().sum())
        stats.nulos_imputados[columna] = nulos
        df[columna] = df[columna].fillna(valor)

    logger.info(
        "Nulos tratados: %s filas sin id eliminadas; imputaciones=%s",
        stats.filas_sin_id,
        {k: v for k, v in stats.nulos_imputados.items() if v},
    )
    return df.reset_index(drop=True)


def estandarizar_fechas(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Convierte ``fecha_evento`` a ISO (``YYYY-MM-DD``) y elimina inválidas."""
    stats = stats or TransformStats()
    df = df.copy()

    df["fecha_evento"] = pd.to_datetime(
        df["fecha_evento"].map(parsear_fecha), errors="coerce"
    )
    stats.fechas_invalidas = int(df["fecha_evento"].isna().sum())
    stats.filas_sin_fecha = stats.fechas_invalidas

    df = df[df["fecha_evento"].notna()].copy()
    logger.info(
        "Fechas estandarizadas: %s registros con fecha inválida o nula eliminados",
        stats.filas_sin_fecha,
    )
    return df.reset_index(drop=True)


def corregir_nombres_equipos(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Normaliza nombres de equipos y corrige typos con alias y ``difflib``."""
    stats = stats or TransformStats()
    df = df.copy()
    corregidos = 0

    for columna in ("equipo_local", "equipo_visitante"):
        antes = df[columna].map(_limpiar_espacios)
        despues = pd.Series(
            [
                _equipo_canonico(nombre, deporte)
                for nombre, deporte in zip(df[columna], df["deporte"])
            ],
            index=df.index,
            dtype="object",
        )
        corregidos += int((antes != despues).sum())
        df[columna] = despues

    stats.equipos_corregidos = corregidos
    logger.info("Nombres de equipos/jugadores corregidos: %s", corregidos)
    return df


def validar_cuotas(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Convierte cuotas a numérico, valida ``> 1.0`` y trata valores atípicos.

    Las cuotas inválidas (texto, negativas, cero o ``<= 1.0``) y las
    atípicas (``> 50``) se imputan con la mediana del deporte. La cuota de
    empate solo se imputa en deportes que realmente admiten empate.
    """
    stats = stats or TransformStats()
    df = df.copy()
    columnas = ("cuota_local", "cuota_empate", "cuota_visitante")

    for columna in columnas:
        serie = df[columna].map(_cuota_a_numero).astype(float)
        stats.cuotas_invalidas[columna] = int(
            (serie.notna() & (serie <= 1.0)).sum()
        )
        stats.cuotas_atipicas[columna] = int((serie > LIMITE_CUOTA).sum())

        serie = serie.mask(serie <= 1.0)
        serie = serie.mask(serie > LIMITE_CUOTA)

        if columna == "cuota_empate":
            deportes_con_empate = set(df.loc[serie.notna(), "deporte"])
            # El fútbol admite empate por definición, aunque falten observaciones.
            deportes_con_empate |= {
                deporte for deporte in df["deporte"].unique()
                if normalizar_clave(deporte) == "futbol"
            }
            aplica = df["deporte"].isin(deportes_con_empate)
        else:
            aplica = pd.Series(True, index=df.index)

        stats.cuotas_imputadas[columna] = int(serie[aplica].isna().sum())
        medianas = serie.groupby(df["deporte"]).transform("median")
        serie = serie.fillna(medianas).fillna(serie.median())
        df[columna] = serie.where(aplica).round(2)

    logger.info(
        "Cuotas validadas: inválidas=%s | atípicas=%s | imputadas=%s",
        stats.cuotas_invalidas,
        stats.cuotas_atipicas,
        stats.cuotas_imputadas,
    )
    return df


def crear_columnas_derivadas(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Crea variables temporales, de marcador, resultado y de cuotas."""
    stats = stats or TransformStats()
    df = df.copy()

    df["año"] = df["fecha_evento"].dt.year.astype("Int64")
    df["mes"] = df["fecha_evento"].dt.month.astype("Int64")
    df["nombre_mes"] = df["mes"].map(MESES_ES)
    df["dia"] = df["fecha_evento"].dt.day.astype("Int64")
    df["dia_semana"] = df["fecha_evento"].dt.dayofweek.map(DIAS_SEMANA)

    marcadores = df["resultado"].map(_parsear_marcador)
    df["marcador_local"] = pd.to_numeric(
        marcadores.map(lambda par: par[0]), errors="coerce"
    ).astype("Int64")
    df["marcador_visitante"] = pd.to_numeric(
        marcadores.map(lambda par: par[1]), errors="coerce"
    ).astype("Int64")

    deporte_clave = df["deporte"].map(normalizar_clave)
    df["goles_local"] = df["marcador_local"].where(deporte_clave == "futbol")
    df["goles_visitante"] = df["marcador_visitante"].where(deporte_clave == "futbol")
    df["puntos_local"] = df["marcador_local"].where(
        deporte_clave.isin(["baloncesto", "tenis"])
    )
    df["puntos_visitante"] = df["marcador_visitante"].where(
        deporte_clave.isin(["baloncesto", "tenis"])
    )

    df["diferencia_marcador"] = (
        df["marcador_local"] - df["marcador_visitante"]
    ).astype("Int64")

    def _normalizar_resultado(local: Any, visitante: Any) -> str:
        if pd.isna(local) or pd.isna(visitante):
            return "Desconocido"
        if local > visitante:
            return "Local"
        if local < visitante:
            return "Visitante"
        return "Empate"

    df["resultado_normalizado"] = [
        _normalizar_resultado(local, visitante)
        for local, visitante in zip(df["marcador_local"], df["marcador_visitante"])
    ]
    stats.resultados_desconocidos = int(
        (df["resultado_normalizado"] == "Desconocido").sum()
    )

    cuotas = df[["cuota_local", "cuota_empate", "cuota_visitante"]]
    etiquetas = {
        "cuota_local": "Local",
        "cuota_empate": "Empate",
        "cuota_visitante": "Visitante",
    }
    df["favorito"] = cuotas.idxmin(axis=1, skipna=True).map(etiquetas)
    df["cuota_favorita"] = cuotas.min(axis=1, skipna=True).round(2)

    df["prob_implicita_local"] = (1.0 / df["cuota_local"]).round(4)
    df["prob_implicita_empate"] = (1.0 / df["cuota_empate"]).round(4)
    df["prob_implicita_visitante"] = (1.0 / df["cuota_visitante"]).round(4)
    df["margen_mercado"] = (
        df[
            [
                "prob_implicita_local",
                "prob_implicita_empate",
                "prob_implicita_visitante",
            ]
        ]
        .sum(axis=1, skipna=True)
        .sub(1.0)
        .round(4)
    )

    logger.info(
        "Columnas derivadas creadas: temporales, marcadores, resultado, favorito "
        "y probabilidades implícitas (resultados desconocidos=%s)",
        stats.resultados_desconocidos,
    )
    return df


def convertir_tipos(
    df: pd.DataFrame, stats: TransformStats | None = None
) -> pd.DataFrame:
    """Ajusta tipos: texto, numéricos, enteros nullable y categóricos."""
    df = df.copy()
    df["id_evento"] = df["id_evento"].astype("string").str.strip()

    for columna in ("cuota_local", "cuota_empate", "cuota_visitante", "cuota_favorita"):
        df[columna] = pd.to_numeric(df[columna], errors="coerce").astype(float)

    for columna in (
        "año", "mes", "dia", "marcador_local", "marcador_visitante",
        "goles_local", "goles_visitante", "puntos_local", "puntos_visitante",
        "diferencia_marcador",
    ):
        df[columna] = pd.to_numeric(df[columna], errors="coerce").astype("Int64")

    for columna in (
        "deporte", "competicion", "resultado_normalizado", "favorito",
        "dia_semana", "nombre_mes", "fuente_archivo",
    ):
        df[columna] = df[columna].astype("category")

    logger.info("Tipos de datos convertidos correctamente.")
    return df


def organizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena las columnas según el esquema final y descarta columnas auxiliares."""
    faltantes = [columna for columna in COLUMNAS_FINALES if columna not in df.columns]
    if faltantes:
        logger.warning("Columnas finales ausentes: %s", ", ".join(faltantes))
    return df.reindex(columns=COLUMNAS_FINALES)


def generar_reporte_calidad(
    df_crudo: pd.DataFrame,
    df_limpio: pd.DataFrame,
    stats: TransformStats,
    reports_dir: Path = REPORTS_DIR,
) -> tuple[Path, Path]:
    """Genera el reporte de calidad antes/después en Markdown y CSV.

    Returns:
        Tupla ``(ruta_markdown, ruta_csv)``.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    ruta_md = reports_dir / "reporte_calidad.md"
    ruta_csv = reports_dir / "reporte_calidad.csv"

    filas_antes = stats.filas_iniciales
    filas_despues = stats.filas_finales
    columnas = sorted(set(df_crudo.columns) | set(df_limpio.columns))
    filas_csv: list[dict[str, Any]] = []

    def agregar(
        seccion: str,
        metrica: str,
        antes: Any,
        despues: Any,
        detalle: str = "",
    ) -> None:
        filas_csv.append(
            {
                "seccion": seccion,
                "metrica": metrica,
                "valor_antes": antes,
                "valor_despues": despues,
                "detalle": detalle,
            }
        )

    agregar("resumen", "filas_totales", filas_antes, filas_despues,
            f"Se conserva el {filas_despues / filas_antes:.1%} de los registros")
    agregar("resumen", "columnas_totales", len(df_crudo.columns), len(df_limpio.columns))
    agregar("duplicados", "duplicados_exactos_eliminados", stats.duplicados_exactos, 0)
    agregar("duplicados", "duplicados_por_id_eliminados", stats.duplicados_por_id, 0)
    agregar("nulos", "filas_sin_id_eliminadas", stats.filas_sin_id, 0)
    agregar("fechas", "fechas_invalidas_eliminadas", stats.fechas_invalidas, 0)
    agregar("equipos", "nombres_corregidos", stats.equipos_corregidos, 0)
    agregar("resultados", "resultados_desconocidos", stats.resultados_desconocidos,
            int((df_limpio["resultado_normalizado"] == "Desconocido").sum()))

    for columna in ("cuota_local", "cuota_empate", "cuota_visitante"):
        agregar(
            "cuotas", f"{columna}_invalidas_corregidas",
            stats.cuotas_invalidas.get(columna, 0), 0,
        )
        agregar(
            "cuotas", f"{columna}_atipicas_tratadas",
            stats.cuotas_atipicas.get(columna, 0), 0,
        )
        agregar(
            "cuotas", f"{columna}_nulos_imputados",
            stats.cuotas_imputadas.get(columna, 0), 0,
        )

    nulos_antes = stats.nulos_antes or _conteo_nulos(df_crudo)
    nulos_despues = stats.nulos_despues or _conteo_nulos(df_limpio)
    for columna in columnas:
        agregar(
            "nulos_por_columna",
            columna,
            nulos_antes.get(columna, 0),
            nulos_despues.get(columna, 0),
            "Nulo estructural" if columna == "cuota_empate" else "",
        )

    pd.DataFrame(filas_csv).to_csv(ruta_csv, index=False, encoding="utf-8-sig")

    lineas: list[str] = [
        "# Reporte de calidad de datos",
        "",
        "**Proyecto:** ETL de análisis de datos de apuestas deportivas  ",
        "**Fuente:** datos históricos simulados (semilla fija, sin apuestas reales)  ",
        f"**Fecha de generación:** {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## 1. Resumen general",
        "",
        "| Métrica | Antes | Después |",
        "|---|---:|---:|",
        f"| Filas | {filas_antes:,} | {filas_despues:,} |",
        f"| Columnas | {len(df_crudo.columns)} | {len(df_limpio.columns)} |",
        f"| Duplicados exactos | {stats.duplicados_exactos:,} | 0 |",
        f"| Duplicados por `id_evento` | {stats.duplicados_por_id:,} | 0 |",
        f"| Filas sin identificador | {stats.filas_sin_id:,} | 0 |",
        f"| Fechas inválidas o nulas | {stats.fechas_invalidas:,} | 0 |",
        f"| Nombres de equipo corregidos | {stats.equipos_corregidos:,} | 0 |",
        f"| Resultados desconocidos | — | {stats.resultados_desconocidos:,} |",
        "",
        "## 2. Nulos por columna",
        "",
        "| Columna | Nulos antes | % antes | Nulos después | % después |",
        "|---|---:|---:|---:|---:|",
    ]

    for columna in columnas:
        antes = nulos_antes.get(columna, 0)
        despues = nulos_despues.get(columna, 0)
        porcentaje_antes = antes / filas_antes if filas_antes else 0.0
        porcentaje_despues = despues / filas_despues if filas_despues else 0.0
        lineas.append(
            f"| `{columna}` | {antes:,} | {porcentaje_antes:.1%} | "
            f"{despues:,} | {porcentaje_despues:.1%} |"
        )

    lineas += [
        "",
        "> Los nulos restantes en `cuota_empate` son **estructurales**: baloncesto y",
        "> tenis no admiten empate, por lo que no se inventa una cuota.",
        "> Del mismo modo, `goles_*` solo aplica a fútbol y `puntos_*` a baloncesto",
        "> y tenis; sus nulos cruzados son estructurales y no un problema de calidad.",
        "",
        "## 3. Estrategia de tratamiento de nulos",
        "",
        "| Columna | Estrategia | Justificación |",
        "|---|---|---|",
    ]
    for columna, estrategia, justificacion in ESTRATEGIA_NULOS:
        lineas.append(f"| `{columna}` | {estrategia} | {justificacion} |")

    lineas += [
        "",
        "## 4. Correcciones y validaciones aplicadas",
        "",
        "### Duplicados",
        f"- Duplicados exactos eliminados: **{stats.duplicados_exactos:,}**.",
        "- Duplicados por `id_evento` eliminados: "
        f"**{stats.duplicados_por_id:,}** (se conservó la fila más completa).",
        "",
        "### Fechas",
        "- Formatos normalizados a ISO `YYYY-MM-DD`: DD/MM/YYYY, YYYY-MM-DD, "
        "DD-MM-YYYY, YYYY/MM/DD y texto en español.",
        f"- Registros eliminados por fecha inválida o nula: **{stats.fechas_invalidas:,}**.",
        "",
        "### Nombres de equipos",
        "- Limpieza de mayúsculas, espacios extra y tildes; alias de abreviaturas y "
        "corrección de typos por similitud (`difflib`, umbral 0.80).",
        f"- Nombres corregidos: **{stats.equipos_corregidos:,}**.",
        "",
        "### Cuotas",
        "| Cuota | Inválidas (<= 1.0) | Atípicas (> 50) | Nulos imputados |",
        "|---|---:|---:|---:|",
    ]
    for columna in ("cuota_local", "cuota_empate", "cuota_visitante"):
        lineas.append(
            f"| `{columna}` | {stats.cuotas_invalidas.get(columna, 0):,} | "
            f"{stats.cuotas_atipicas.get(columna, 0):,} | "
            f"{stats.cuotas_imputadas.get(columna, 0):,} |"
        )

    lineas += [
        "",
        "## 5. Resultado final",
        "",
        f"- Dataset limpio: **{filas_despues:,} eventos** con "
        f"**{len(df_limpio.columns)} columnas**.",
        f"- Duplicados por `id_evento`: **{int(df_limpio['id_evento'].duplicated().sum())}**.",
        f"- Fechas nulas: **{int(df_limpio['fecha_evento'].isna().sum())}**.",
        "- Estado: **apto para análisis estadístico y visualización en Power BI**.",
        "",
        "## 6. Observaciones",
        "",
        "- Las cuotas se imputaron con la mediana del deporte para no alterar la "
        "distribución con valores extremos.",
        "- Los eventos sin fecha o sin identificador se eliminaron porque no son "
        "trazables ni ubicables en el tiempo.",
        "- La columna `fuente_archivo` permite auditar el origen de cada registro.",
        "- Este proyecto es académico: los datos son simulados y no se promueven "
        "apuestas reales.",
        "",
    ]

    ruta_md.write_text("\n".join(lineas), encoding="utf-8")
    logger.info("Reporte de calidad generado: %s y %s", ruta_md.name, ruta_csv.name)
    return ruta_md, ruta_csv


def run_transform(
    df_crudo: pd.DataFrame,
    reports_dir: Path = REPORTS_DIR,
) -> tuple[pd.DataFrame, TransformStats]:
    """Ejecuta la fase Transform completa y devuelve el dataset y las métricas."""
    if df_crudo.empty:
        logger.error("El DataFrame de entrada está vacío; no hay nada que transformar.")
        return df_crudo.copy(), TransformStats()

    stats = TransformStats(
        filas_iniciales=len(df_crudo),
        nulos_antes=_conteo_nulos(df_crudo),
    )

    df = eliminar_duplicados(df_crudo, stats)
    df = tratar_nulos(df, stats)
    df = estandarizar_fechas(df, stats)
    df = corregir_nombres_equipos(df, stats)
    df = validar_cuotas(df, stats)
    df = crear_columnas_derivadas(df, stats)
    df = convertir_tipos(df, stats)
    df = organizar_columnas(df)

    stats.filas_finales = len(df)
    stats.nulos_despues = _conteo_nulos(df)
    generar_reporte_calidad(df_crudo, df, stats, reports_dir)

    logger.info(
        "Transformación finalizada: %s filas de entrada -> %s filas limpias",
        stats.filas_iniciales,
        stats.filas_finales,
    )
    return df, stats


def main() -> int:
    """Ejecuta Extract + Transform de forma independiente."""
    from src.extract import extraer

    configurar_logging()
    df_crudo = extraer()
    if df_crudo.empty:
        logger.error("No hay datos crudos para transformar.")
        return 1
    df_limpio, _ = run_transform(df_crudo)
    logger.info("Vista previa del dataset limpio:\n%s", df_limpio.head(5).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
