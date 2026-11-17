"""Pruebas del generador del proyecto de Power BI (``powerbi/build_pbip.py``)."""

from __future__ import annotations

import json

import powerbi.build_pbip as pbip


def _tablas() -> dict[str, dict]:
    """Devuelve las tablas del modelo indexadas por nombre."""
    modelo = pbip.construir_modelo()
    return {tabla["name"]: tabla for tabla in modelo["model"]["tables"]}


def test_modelo_contiene_esquema_estrella_y_medidas() -> None:
    """El modelo incluye las cinco tablas de datos, la de medidas y el total."""
    tablas = _tablas()

    assert set(tablas) == {
        "fact_eventos",
        "dim_fecha",
        "dim_deportes",
        "dim_competiciones",
        "dim_equipos",
        "_Medidas",
    }
    assert len(tablas["_Medidas"]["measures"]) == 33
    assert len(tablas["fact_eventos"]["columns"]) == 25


def test_relaciones_una_inactiva_para_el_visitante() -> None:
    """Hay cinco relaciones y solo la del equipo visitante está inactiva."""
    modelo = pbip.construir_modelo()
    relaciones = modelo["model"]["relationships"]

    assert len(relaciones) == 5
    inactivas = [relacion for relacion in relaciones if relacion.get("isActive") is False]
    assert len(inactivas) == 1
    assert inactivas[0]["fromColumn"] == "id_equipo_visitante"
    assert inactivas[0]["toTable"] == "dim_equipos"


def test_columnas_tecnicas_ocultas_y_formato_de_fecha() -> None:
    """Los identificadores se ocultan y las fechas usan formato español."""
    tablas = _tablas()
    columnas = {columna["name"]: columna for columna in tablas["fact_eventos"]["columns"]}

    assert columnas["id_evento"]["isHidden"] is True
    assert columnas["fecha_evento"]["formatString"] == "dd/MM/yyyy"
    assert columnas["cuota_local"]["dataType"] == "double"


def test_modelo_incrusta_los_datos_sin_rutas_externas() -> None:
    """Por defecto el modelo contiene tablas M con los datos y ninguna ruta."""
    modelo = pbip.construir_modelo()
    consulta = "\n".join(modelo["model"]["tables"][0]["partitions"][0]["source"]["expression"])

    assert "expressions" not in modelo["model"]
    assert "File.Contents" not in consulta
    assert "RutaDatos" not in consulta
    assert "#table(" in consulta and "type table [" in consulta
    assert "#date(" in consulta
    assert consulta.rstrip().endswith("Origen")
    # 3.278 eventos del CSV + una línea por cabecera de tabla
    assert consulta.count("\n            { ") >= 3278


def test_modo_csv_usa_el_parametro_de_ruta_sin_barra_final() -> None:
    """El modo opcional --usar-csv conecta el modelo con la carpeta indicada."""
    modelo = pbip.construir_modelo(usar_csv=True, ruta_datos=pbip.PROCESADOS)
    parametro = modelo["model"]["expressions"][0]
    consulta = "\n".join(modelo["model"]["tables"][0]["partitions"][0]["source"]["expression"])

    assert parametro["name"] == "RutaDatos"
    assert parametro["expression"].startswith('"') and "IsParameterQuery=true" in parametro["expression"]
    # La ruta no debe terminar en barra: se añade junto al nombre del archivo.
    ruta = parametro["expression"].split('"')[1]
    assert not ruta.endswith("\\")
    assert 'File.Contents(RutaDatos & "\\fact_eventos.csv")' in consulta
    assert consulta.rstrip().endswith("Tipado")


def test_paginas_y_visuales_unicos() -> None:
    """Las tres páginas existen y ningún visual repite nombre."""
    nombres_paginas = [pagina["nombre"] for pagina in pbip.PAGINAS]
    assert nombres_paginas == ["pResumen", "pCuotas", "pEquipos"]

    nombres_visuales = [
        visual["nombre"] for pagina in pbip.PAGINAS for visual in pagina["visuals"]
    ]
    assert len(nombres_visuales) == 24
    assert len(set(nombres_visuales)) == len(nombres_visuales)


def test_excel_para_power_bi_tiene_una_hoja_por_tabla() -> None:
    """El libro listo para subir incluye las cinco tablas y sus cabeceras."""
    from openpyxl import load_workbook

    pbip.generar(excel=True)
    libro = load_workbook(pbip.EXCEL, read_only=True)

    assert libro.sheetnames == [
        "fact_eventos",
        "dim_fecha",
        "dim_deportes",
        "dim_competiciones",
        "dim_equipos",
    ]
    assert libro["fact_eventos"].max_row == 3279
    assert libro["fact_eventos"].max_column == 25
    libro.close()


def test_proyecto_generado_es_coherente() -> None:
    """El proyecto escrito en disco referencia solo campos existentes."""
    pbip.generar()

    assert pbip.verificar() == []
    assert pbip.EXCEL.exists()

    entrada = pbip.DESTINO / f"{pbip.NOMBRE}.pbip"
    datos = json.loads(entrada.read_text(encoding="utf-8"))
    assert datos["artifacts"][0]["report"]["path"] == f"{pbip.NOMBRE}.Report"

    modelo = pbip.DESTINO / f"{pbip.NOMBRE}.SemanticModel" / "model.bim"
    assert json.loads(modelo.read_text(encoding="utf-8"))["compatibilityLevel"] >= 1550

    informe = pbip.DESTINO / f"{pbip.NOMBRE}.Report" / "definition.pbir"
    referencia = json.loads(informe.read_text(encoding="utf-8"))["datasetReference"]
    assert referencia["byPath"]["path"] == f"../{pbip.NOMBRE}.SemanticModel"
