"""Fase Visualización: gráficos estadísticos con Matplotlib.

Genera PNG en ``reports/figures/`` con títulos, ejes y leyendas en español,
listos para incorporar al informe académico o como referencia del dashboard.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Backend sin interfaz gráfica (servidores y CI).

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import FIGURES_DIR, configurar_logging  # noqa: E402

logger = logging.getLogger(__name__)

PALETA = ["#1F4E79", "#2E75B6", "#9DC3E6", "#C55A11", "#548235", "#7030A0", "#BF9000"]
COLORES_RESULTADO = {"Local": "#2E75B6", "Empate": "#A6A6A6", "Visitante": "#C55A11"}
COLOR_FONDO = "#FFFFFF"

plt.rcParams.update(
    {
        "figure.facecolor": COLOR_FONDO,
        "axes.facecolor": COLOR_FONDO,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.alpha": 0.25,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
    }
)


def _numero(valor: float, decimales: int = 0) -> str:
    """Formatea números con separador de miles y coma decimal en español."""
    formato = f"{{:,.{decimales}f}}"
    return formato.format(valor).replace(",", "X").replace(".", ",").replace("X", ".")


def _guardar(fig: plt.Figure, ruta: Path) -> Path:
    """Guarda una figura con resolución adecuada para informes."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150, bbox_inches="tight", facecolor=COLOR_FONDO)
    plt.close(fig)
    logger.info("Figura generada: %s", ruta.name)
    return ruta


def _figura_total_eventos(df: pd.DataFrame, figuras: Path) -> Path:
    """Tarjeta con el total de eventos y un resumen del alcance del dataset."""
    deportes = df["deporte"].nunique()
    competiciones = df["competicion"].nunique()
    fecha_min = df["fecha_evento"].min()
    fecha_max = df["fecha_evento"].max()
    periodo = (
        f"{fecha_min:%d/%m/%Y} — {fecha_max:%d/%m/%Y}"
        if pd.notna(fecha_min) and pd.notna(fecha_max)
        else "sin fechas válidas"
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis("off")
    ax.text(
        0.5, 0.68, _numero(len(df)), ha="center", va="center",
        fontsize=72, fontweight="bold", color=PALETA[0],
    )
    ax.text(
        0.5, 0.46, "Eventos deportivos registrados", ha="center",
        fontsize=20, color="#333333",
    )
    ax.text(
        0.5, 0.26,
        f"{deportes} deportes  •  {competiciones} competiciones  •  {periodo}",
        ha="center", fontsize=12, color="#666666",
    )
    ax.text(
        0.5, 0.10, "Datos históricos simulados con fines académicos",
        ha="center", fontsize=10, color="#999999", style="italic",
    )
    ax.set_title("Cantidad total de eventos", pad=18)
    return _guardar(fig, figuras / "01_total_eventos.png")


def _figura_eventos_por_deporte(df: pd.DataFrame, figuras: Path) -> Path:
    """Gráfico de barras con la distribución de eventos por deporte."""
    conteos = df["deporte"].astype(str).value_counts().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    barras = ax.bar(
        conteos.index, conteos.values,
        color=PALETA[: len(conteos)], edgecolor="white", linewidth=0.8,
    )
    total = int(conteos.sum())
    for barra, valor in zip(barras, conteos.values):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + total * 0.012,
            f"{_numero(valor)} ({valor / total:.1%})",
            ha="center", va="bottom", fontsize=10, fontweight="bold",
        )
    ax.set_title("Distribución de eventos por deporte")
    ax.set_xlabel("Deporte")
    ax.set_ylabel("Cantidad de eventos")
    ax.set_ylim(0, conteos.max() * 1.18)
    ax.grid(axis="x", visible=False)
    return _guardar(fig, figuras / "02_eventos_por_deporte.png")


def _estadisticas_equipos(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula partidos, victorias, empates y derrotas por equipo."""
    local = pd.DataFrame(
        {
            "equipo": df["equipo_local"].astype(str),
            "victorias": (df["resultado_normalizado"] == "Local").astype(int),
            "empates": (df["resultado_normalizado"] == "Empate").astype(int),
            "derrotas": (df["resultado_normalizado"] == "Visitante").astype(int),
        }
    )
    visitante = pd.DataFrame(
        {
            "equipo": df["equipo_visitante"].astype(str),
            "victorias": (df["resultado_normalizado"] == "Visitante").astype(int),
            "empates": (df["resultado_normalizado"] == "Empate").astype(int),
            "derrotas": (df["resultado_normalizado"] == "Local").astype(int),
        }
    )
    equipos = pd.concat([local, visitante], ignore_index=True)
    equipos = equipos[equipos["equipo"] != "Desconocido"]
    return (
        equipos.groupby("equipo", observed=True)
        .agg(
            partidos=("victorias", "size"),
            victorias=("victorias", "sum"),
            empates=("empates", "sum"),
            derrotas=("derrotas", "sum"),
        )
        .reset_index()
        .sort_values(["partidos", "victorias"], ascending=False)
    )


def _figura_resultados_equipos(df: pd.DataFrame, figuras: Path) -> Path:
    """Top 10 de equipos con más partidos y su historial de resultados."""
    estadisticas = _estadisticas_equipos(df).head(10).sort_values("partidos")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(
        estadisticas["equipo"], estadisticas["victorias"],
        color="#2E75B6", label="Victorias",
    )
    ax.barh(
        estadisticas["equipo"], estadisticas["empates"],
        left=estadisticas["victorias"], color="#A6A6A6", label="Empates",
    )
    ax.barh(
        estadisticas["equipo"], estadisticas["derrotas"],
        left=estadisticas["victorias"] + estadisticas["empates"],
        color="#C55A11", label="Derrotas",
    )
    for indice, fila in enumerate(estadisticas.itertuples(index=False)):
        ax.text(
            fila.partidos + 1.5, indice, _numero(fila.partidos),
            va="center", fontsize=9, color="#444444",
        )
    ax.set_title("Resultados históricos por equipo (top 10 por partidos)")
    ax.set_xlabel("Cantidad de partidos")
    ax.set_ylabel("")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="y", visible=False)
    return _guardar(fig, figuras / "03_resultados_por_equipo.png")


def _figura_local_vs_visitante(df: pd.DataFrame, figuras: Path) -> Path:
    """Compara promedios de marcador y porcentaje de resultados por deporte."""
    fig, ejes = plt.subplots(2, 2, figsize=(13, 10))
    promedios = (
        df.groupby("deporte", observed=True)[["marcador_local", "marcador_visitante"]]
        .mean()
        .dropna(how="all")
    )
    promedios = promedios.reindex(
        df["deporte"].astype(str).value_counts().index.intersection(promedios.index)
    )

    etiquetas_unidad = {
        "Fútbol": "Goles promedio",
        "Baloncesto": "Puntos promedio",
        "Tenis": "Sets promedio",
    }
    paneles = [ejes[0, 0], ejes[0, 1], ejes[1, 0]]
    for ax, deporte in zip(paneles, promedios.index[:3]):
        fila = promedios.loc[deporte]
        valores = [fila["marcador_local"], fila["marcador_visitante"]]
        barras = ax.bar(
            ["Local", "Visitante"], valores,
            color=["#2E75B6", "#C55A11"], width=0.55,
        )
        for barra, valor in zip(barras, valores):
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height() + max(valores) * 0.04,
                f"{valor:.2f}", ha="center", fontsize=11, fontweight="bold",
            )
        ax.set_title(f"{deporte}: marcador promedio")
        ax.set_ylabel(etiquetas_unidad.get(deporte, "Marcador promedio"))
        ax.set_ylim(0, max(valores) * 1.25)
        ax.grid(axis="x", visible=False)

    for ax in paneles[len(promedios.index[:3]):]:
        ax.axis("off")

    porcentajes = (
        pd.crosstab(df["deporte"].astype(str), df["resultado_normalizado"])
        .reindex(columns=["Local", "Empate", "Visitante"], fill_value=0)
    )
    porcentajes = porcentajes.div(porcentajes.sum(axis=1), axis=0) * 100
    base = pd.Series(0.0, index=porcentajes.index)
    ax_resultados = ejes[1, 1]
    for resultado in ["Local", "Empate", "Visitante"]:
        ax_resultados.bar(
            porcentajes.index, porcentajes[resultado], bottom=base,
            color=COLORES_RESULTADO[resultado], label=resultado,
        )
        base = base + porcentajes[resultado]
    for pos, total in enumerate(porcentajes.sum(axis=1)):
        ax_resultados.text(pos, total + 1.5, f"{total:.0f}%", ha="center", fontsize=9)
    ax_resultados.set_title("Porcentaje de resultados por deporte")
    ax_resultados.set_ylabel("Porcentaje de eventos (%)")
    ax_resultados.set_ylim(0, 112)
    ax_resultados.legend(frameon=False, ncol=3, loc="upper center")
    ax_resultados.grid(axis="x", visible=False)

    fig.suptitle("Comparación estadística de los encuentros", fontweight="bold", y=1.01)
    return _guardar(fig, figuras / "04_local_vs_visitante.png")


def _figura_eventos_por_competicion(df: pd.DataFrame, figuras: Path) -> Path:
    """Barras horizontales con las competiciones con más eventos."""
    conteos = df["competicion"].astype(str).value_counts().head(12).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    barras = ax.barh(
        conteos.index, conteos.values,
        color=PALETA[1], edgecolor="white", linewidth=0.6,
    )
    for barra, valor in zip(barras, conteos.values):
        ax.text(
            barra.get_width() + conteos.max() * 0.012,
            barra.get_y() + barra.get_height() / 2,
            _numero(valor), va="center", fontsize=9,
        )
    ax.set_title("Distribución de registros por competición")
    ax.set_xlabel("Cantidad de eventos")
    ax.set_ylabel("")
    ax.set_xlim(0, conteos.max() * 1.12)
    ax.grid(axis="y", visible=False)
    return _guardar(fig, figuras / "05_eventos_por_competicion.png")


def _figura_analisis_cuotas(df: pd.DataFrame, figuras: Path) -> Path:
    """Histograma, boxplot y estadísticos descriptivos de las cuotas."""
    columnas = {
        "cuota_local": "Local",
        "cuota_empate": "Empate",
        "cuota_visitante": "Visitante",
    }
    fig, ejes = plt.subplots(1, 3, figsize=(18, 5.8))

    cuota_local = df["cuota_local"].dropna()
    ejes[0].hist(
        cuota_local, bins=30, color=PALETA[1], edgecolor="white", alpha=0.9
    )
    ejes[0].axvline(
        cuota_local.mean(), color="#C55A11", linestyle="--", linewidth=2,
        label=f"Media: {cuota_local.mean():.2f}",
    )
    ejes[0].axvline(
        cuota_local.median(), color="#548235", linestyle=":", linewidth=2,
        label=f"Mediana: {cuota_local.median():.2f}",
    )
    ejes[0].set_title("Distribución de la cuota local")
    ejes[0].set_xlabel("Cuota")
    ejes[0].set_ylabel("Frecuencia")
    ejes[0].legend(frameon=False)

    datos = [df[columna].dropna() for columna in columnas]
    ejes[1].boxplot(
        datos, tick_labels=list(columnas.values()), patch_artist=True,
        boxprops={"facecolor": PALETA[2], "edgecolor": PALETA[0]},
        medianprops={"color": "#C55A11", "linewidth": 2},
        whiskerprops={"color": PALETA[0]},
        capprops={"color": PALETA[0]},
    )
    ejes[1].set_title("Boxplot de cuotas por tipo")
    ejes[1].set_ylabel("Cuota")
    ejes[1].grid(axis="x", visible=False)

    estadisticas: list[list[str]] = []
    for columna, etiqueta in columnas.items():
        serie = df[columna].dropna()
        if serie.empty:
            continue
        estadisticas.append(
            [
                etiqueta,
                f"{serie.mean():.2f}",
                f"{serie.median():.2f}",
                f"{serie.std():.2f}",
                f"{serie.min():.2f}",
                f"{serie.max():.2f}",
            ]
        )
    ejes[2].axis("off")
    tabla = ejes[2].table(
        cellText=estadisticas,
        colLabels=["Cuota", "Media", "Mediana", "Desv. típ.", "Mín.", "Máx."],
        loc="center",
        cellLoc="center",
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1.0, 1.7)
    for (fila, _columna), celda in tabla.get_celld().items():
        if fila == 0:
            celda.set_facecolor(PALETA[0])
            celda.set_text_props(color="white", fontweight="bold")
        else:
            celda.set_facecolor("#F2F2F2" if fila % 2 == 0 else "white")
    ejes[2].set_title("Estadísticos descriptivos de cuotas", pad=20)

    fig.suptitle("Análisis descriptivo de las cuotas", fontweight="bold", y=1.02)
    return _guardar(fig, figuras / "06_analisis_cuotas.png")


def _figura_tendencia_temporal(df: pd.DataFrame, figuras: Path) -> Path:
    """Evolución mensual del número de eventos registrados."""
    serie = (
        df.set_index("fecha_evento")
        .sort_index()
        .resample("MS")
        .size()
    )
    serie = serie[serie > 0]
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(
        range(len(serie)), serie.values, marker="o", markersize=4,
        color=PALETA[0], linewidth=2,
    )
    ax.fill_between(range(len(serie)), serie.values, color=PALETA[2], alpha=0.35)
    paso = max(1, len(serie) // 10)
    ax.set_xticks(list(range(0, len(serie), paso)))
    ax.set_xticklabels(
        [fecha.strftime("%m/%Y") for fecha in serie.index[::paso]],
        rotation=45, ha="right",
    )
    ax.set_title("Evolución mensual de los eventos registrados")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Cantidad de eventos")
    ax.grid(axis="x", visible=False)
    return _guardar(fig, figuras / "07_tendencia_mensual.png")


def generar_visualizaciones(
    df: pd.DataFrame, figures_dir: Path = FIGURES_DIR
) -> list[Path]:
    """Genera todas las figuras del proyecto y devuelve sus rutas."""
    if df.empty:
        logger.warning("Dataset vacío: no se generan visualizaciones.")
        return []

    figures_dir.mkdir(parents=True, exist_ok=True)
    generadores = [
        _figura_total_eventos,
        _figura_eventos_por_deporte,
        _figura_resultados_equipos,
        _figura_local_vs_visitante,
        _figura_eventos_por_competicion,
        _figura_analisis_cuotas,
        _figura_tendencia_temporal,
    ]

    rutas: list[Path] = []
    for generador in generadores:
        try:
            rutas.append(generador(df, figures_dir))
        except Exception as error:  # noqa: BLE001 - una figura no debe romper el ETL
            logger.exception("No se pudo generar %s: %s", generador.__name__, error)

    logger.info("Visualizaciones generadas: %s archivos en %s", len(rutas), figures_dir)
    return rutas


def main() -> int:
    """Genera las figuras a partir del dataset limpio ya procesado."""
    from src.config import PROCESSED_DIR

    configurar_logging()
    ruta = PROCESSED_DIR / "eventos_limpios.csv"
    if not ruta.exists():
        logger.error("No existe %s. Ejecuta main.py primero.", ruta)
        return 1
    df = pd.read_csv(ruta, encoding="utf-8-sig", parse_dates=["fecha_evento"])
    generar_visualizaciones(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
