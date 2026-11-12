"""Pruebas unitarias de las funciones de transformación."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.transform import (
    COLUMNAS_FINALES,
    TransformStats,
    corregir_nombres_equipos,
    crear_columnas_derivadas,
    eliminar_duplicados,
    estandarizar_fechas,
    organizar_columnas,
    parsear_fecha,
    run_transform,
    tratar_nulos,
    validar_cuotas,
)


# ---------------------------------------------------------------------------
# Duplicados
# ---------------------------------------------------------------------------
def test_elimina_duplicados_exactos_y_por_id(df_crudo: pd.DataFrame) -> None:
    """El dataset de prueba pierde 1 duplicado exacto y 1 duplicado por id."""
    stats = TransformStats()
    limpio = eliminar_duplicados(df_crudo, stats)

    assert len(limpio) == 7
    assert stats.duplicados_exactos == 1
    assert stats.duplicados_por_id == 1
    assert limpio["id_evento"].duplicated().sum() == 0


def test_conserva_la_fila_mas_completa_por_id() -> None:
    """Ante un id repetido se conserva la fila con más valores no nulos."""
    df = pd.DataFrame(
        {
            "id_evento": ["A", "A"],
            "equipo_local": ["X", "X"],
            "equipo_visitante": ["Y", "Y"],
            "competicion": [None, "Liga"],
            "cuota_local": [1.5, 1.6],
        }
    )
    limpio = eliminar_duplicados(df)

    assert len(limpio) == 1
    assert limpio.iloc[0]["competicion"] == "Liga"


# ---------------------------------------------------------------------------
# Nulos
# ---------------------------------------------------------------------------
def test_tratar_nulos_elimina_sin_id_y_rellena_categorias(
    df_crudo: pd.DataFrame,
) -> None:
    """Las filas sin id se eliminan y las categorías nulas se marcan."""
    stats = TransformStats()
    resultado = tratar_nulos(df_crudo, stats)

    assert stats.filas_sin_id == 1
    assert len(resultado) == 8
    assert resultado["id_evento"].isna().sum() == 0
    assert (resultado["competicion"] == "Desconocida").any()
    assert (resultado["equipo_local"] == "Desconocido").any()


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        ("01/02/2023", "2023-02-01"),
        ("2023-02-01", "2023-02-01"),
        ("01-02-2023", "2023-02-01"),
        ("2023/02/01", "2023-02-01"),
        ("5 de marzo de 2024", "2024-03-05"),
        (date(2022, 12, 31), "2022-12-31"),
    ],
)
def test_parsear_fecha_formatos(entrada: object, esperada: str) -> None:
    """Todos los formatos documentados se convierten a ISO."""
    assert parsear_fecha(entrada) == pd.Timestamp(esperada)


@pytest.mark.parametrize(
    "entrada", ["31/02/2024", "sin fecha", "N/A", None, "--/--/----", "1800-01-01"]
)
def test_parsear_fecha_invalida_devuelve_nat(entrada: object) -> None:
    """Fechas imposibles, vacías o fuera de rango se consideran inválidas."""
    assert pd.isna(parsear_fecha(entrada))


def test_estandarizar_fechas_elimina_invalidas(df_crudo: pd.DataFrame) -> None:
    """Se elimina la fila con fecha imposible y se normaliza el resto."""
    stats = TransformStats()
    resultado = estandarizar_fechas(df_crudo, stats)

    assert stats.fechas_invalidas == 1
    assert len(resultado) == 8
    assert resultado["fecha_evento"].isna().sum() == 0
    assert resultado["fecha_evento"].dt.year.between(1990, 2100).all()


# ---------------------------------------------------------------------------
# Equipos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("entrada", "deporte", "esperado"),
    [
        ("  real madird ", "Fútbol", "Real Madrid"),
        ("BARCELONA", "Fútbol", "Barcelona"),
        ("Atletico", "Fútbol", "Atlético de Madrid"),
        ("L.A. Lakers", "Baloncesto", "Lakers"),
        ("alcaraz", "Tenis", "Carlos Alcaraz"),
        ("Manchester Cty", "Fútbol", "Manchester City"),
        ("Desconocido", "Fútbol", "Desconocido"),
    ],
)
def test_corregir_nombres_equipos(
    entrada: str, deporte: str, esperado: str
) -> None:
    """Mayúsculas, espacios, tildes, alias y typos se normalizan."""
    df = pd.DataFrame(
        {
            "equipo_local": [entrada],
            "equipo_visitante": ["Sevilla"],
            "deporte": [deporte],
        }
    )
    resultado = corregir_nombres_equipos(df)
    assert resultado.iloc[0]["equipo_local"] == esperado


# ---------------------------------------------------------------------------
# Cuotas
# ---------------------------------------------------------------------------
def test_validar_cuotas_corrige_invalidas_y_atipicas() -> None:
    """Cuotas <= 1.0 y > 50 se sustituyen por la mediana del deporte."""
    df = pd.DataFrame(
        {
            "id_evento": ["1", "2", "3", "4", "5"],
            "deporte": ["Fútbol", "Fútbol", "Fútbol", "Baloncesto", "Baloncesto"],
            "cuota_local": [1.8, -2.0, 0.0, 200.0, "1,95"],
            "cuota_empate": [3.2, 3.3, 3.4, None, None],
            "cuota_visitante": [4.1, 4.2, 4.3, 1.5, 2.0],
        }
    )
    stats = TransformStats()
    resultado = validar_cuotas(df, stats)

    assert resultado["cuota_local"].between(1.01, 50.0).all()
    assert stats.cuotas_invalidas["cuota_local"] == 2
    assert stats.cuotas_atipicas["cuota_local"] == 1
    assert resultado.loc[4, "cuota_local"] == pytest.approx(1.95)


def test_validar_cuotas_no_inventa_empate_en_baloncesto() -> None:
    """La cuota de empate queda nula en deportes sin empate."""
    df = pd.DataFrame(
        {
            "deporte": ["Fútbol", "Fútbol", "Baloncesto"],
            "cuota_local": [2.0, 2.2, 2.0],
            "cuota_empate": [None, 3.5, None],
            "cuota_visitante": [3.0, 3.2, 3.0],
        }
    )
    resultado = validar_cuotas(df)

    assert pd.notna(resultado.loc[0, "cuota_empate"])
    assert pd.isna(resultado.loc[2, "cuota_empate"])


# ---------------------------------------------------------------------------
# Columnas derivadas y tipos
# ---------------------------------------------------------------------------
def test_crear_columnas_derivadas() -> None:
    """Se generan variables temporales, de marcador y de cuotas."""
    df = pd.DataFrame(
        {
            "id_evento": ["A", "B"],
            "deporte": ["Fútbol", "Baloncesto"],
            "fecha_evento": pd.to_datetime(["2023-02-01", "2024-03-05"]),
            "resultado": ["2-1", "98-91"],
            "cuota_local": [2.0, 1.5],
            "cuota_empate": [4.0, None],
            "cuota_visitante": [4.0, 2.5],
        }
    )
    stats = TransformStats()
    resultado = crear_columnas_derivadas(df, stats)

    assert resultado.loc[0, "año"] == 2023
    assert resultado.loc[0, "mes"] == 2
    assert resultado.loc[0, "dia_semana"] == "Miércoles"
    assert resultado.loc[0, "marcador_local"] == 2
    assert resultado.loc[0, "resultado_normalizado"] == "Local"
    assert resultado.loc[1, "resultado_normalizado"] == "Local"
    assert resultado.loc[0, "favorito"] == "Local"
    assert resultado.loc[0, "cuota_favorita"] == pytest.approx(2.0)
    assert resultado.loc[0, "prob_implicita_local"] == pytest.approx(0.5)
    assert resultado.loc[0, "margen_mercado"] == pytest.approx(0.0)
    assert resultado.loc[0, "goles_local"] == 2
    assert pd.isna(resultado.loc[1, "goles_local"])
    assert resultado.loc[1, "puntos_local"] == 98


def test_convertir_tipos_y_organizar_columnas(
    df_crudo: pd.DataFrame, tmp_path
) -> None:
    """El esquema final tiene el orden y los tipos esperados."""
    limpio, _ = run_transform(df_crudo, reports_dir=tmp_path)

    assert list(limpio.columns) == COLUMNAS_FINALES
    assert str(limpio["id_evento"].dtype) == "string"
    assert limpio["cuota_local"].dtype == float
    assert str(limpio["marcador_local"].dtype) == "Int64"
    assert str(limpio["deporte"].dtype) == "category"


def test_run_transform_completo(df_crudo: pd.DataFrame, tmp_path) -> None:
    """El pipeline completo deja 5 filas limpias y sin problemas básicos."""
    limpio, stats = run_transform(df_crudo, reports_dir=tmp_path)

    assert len(limpio) == 5
    assert stats.filas_iniciales == 9
    assert stats.filas_finales == 5
    assert limpio["id_evento"].duplicated().sum() == 0
    assert limpio["fecha_evento"].isna().sum() == 0
    assert set(limpio["resultado_normalizado"]).issubset(
        {"Local", "Empate", "Visitante", "Desconocido"}
    )
    for columna in ("cuota_local", "cuota_visitante"):
        valores = limpio[columna].dropna()
        assert valores.gt(1.0).all()
        assert valores.le(50.0).all()
    assert (tmp_path / "reporte_calidad.md").exists()
    assert (tmp_path / "reporte_calidad.csv").exists()
    contenido = (tmp_path / "reporte_calidad.md").read_text(encoding="utf-8")
    assert "Reporte de calidad de datos" in contenido


def test_organizar_columnas_completa_faltantes() -> None:
    """``organizar_columnas`` rellena con nulos las columnas ausentes."""
    df = pd.DataFrame({"id_evento": ["A"]})
    resultado = organizar_columnas(df)

    assert list(resultado.columns) == COLUMNAS_FINALES
    assert resultado["deporte"].isna().all()
