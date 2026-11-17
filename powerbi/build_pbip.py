"""Genera un proyecto Power BI (.pbip) listo para abrir y publicar.

El script construye, a partir de los CSV de ``data/processed``:

* el modelo semantico en formato TMSL (``model.bim``) con tipos, medidas DAX
  y relaciones del esquema estrella;
* el informe en formato PBIR (``definition``) con tres paginas y sus visuales;
* los archivos de plataforma (``.platform``, ``definition.pbip*``);
* un libro ``powerbi/datos_powerbi.xlsx`` con las cinco tablas para subirlo
  directamente al servicio de Power BI.

Por defecto los datos se **incrustan** en el modelo, de modo que el ``.pbip``
no depende de ninguna ruta absoluta y funciona en cualquier equipo. Con
``--usar-csv`` (o ``--ruta-datos``) se genera el modelo conectado a los CSV,
pensado para el flujo ETL local.

Con ``--validar`` se comprueba cada archivo JSON contra los esquemas publicos
de Microsoft (requiere el paquete ``jsonschema`` y conexion a Internet).

Uso::

    python powerbi/build_pbip.py
    python powerbi/build_pbip.py --usar-csv
    python powerbi/build_pbip.py --ruta-datos "C:\\datos\\processed"
    python powerbi/build_pbip.py --validar
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

# ``PROYECTO_ETL_ROOT`` permite que el ejecutable empaquetado genere los
# archivos junto al .exe y no en la carpeta temporal de PyInstaller.
RAIZ = Path(
    os.environ.get("PROYECTO_ETL_ROOT", Path(__file__).resolve().parents[1])
).expanduser().resolve()
PROCESADOS = RAIZ / "data" / "processed"
DESTINO = RAIZ / "powerbi" / "PBIP"
EXCEL = RAIZ / "powerbi" / "datos_powerbi.xlsx"
NOMBRE = "Dashboard_Apuestas"

ESPACIO = uuid.UUID("8f1a4c62-3d77-4b1e-9c0a-5e6d7f8a9b10")

ESQUEMA_PBIP = "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json"
ESQUEMA_PLATAFORMA = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json"
ESQUEMA_PBIR = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"
ESQUEMA_PBISM = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json"
ESQUEMA_VERSION = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"
ESQUEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json"
ESQUEMA_PAGINAS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
ESQUEMA_PAGINA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json"
ESQUEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"

TEXTO_LEEME = """DASHBOARD DE APUESTAS - PROYECTO ETL
====================================

1. Instala Power BI Desktop (gratis): https://powerbi.microsoft.com/desktop/
2. Abre el archivo "Dashboard_Apuestas.pbip" (doble clic o Archivo > Abrir).
3. Pulsa Inicio > Actualizar. Los datos ya van incluidos en el modelo: no
   necesitas los CSV ni cambiar ninguna ruta.
4. Encontrarás tres páginas: Resumen general, Cuotas y mercado y Detalle por
   equipo, con 24 visuales y 33 medidas ya creadas.
5. Para publicarlo en el servicio de Power BI: Archivo > Guardar como >
   Power BI (.pbix) y después Publicar. El servicio NO acepta archivos .pbip.

El libro "powerbi/datos_powerbi.xlsx" contiene las cinco tablas y sirve para
crear un conjunto de datos directamente en el servicio de Power BI.

Guía paso a paso: ../SUBIR_A_POWER_BI.md
Guía de apertura: ../ABRIR_EN_POWER_BI.md
"""

LOG = logging.getLogger("build_pbip")

# ---------------------------------------------------------------------------
# Modelo semantico
# ---------------------------------------------------------------------------

TIPOS_M = {
    "string": "type text",
    "int64": "Int64.Type",
    "double": "type number",
    "date": "type date",
    "boolean": "type logical",
}

# tipos usados dentro de "type table [...]" para los datos incrustados
TIPOS_M_TABLA = {
    "string": "text",
    "int64": "Int64.Type",
    "double": "number",
    "date": "date",
    "boolean": "logical",
}

TIPOS_TMSL = {
    "string": "string",
    "int64": "int64",
    "double": "double",
    "date": "dateTime",
    "boolean": "boolean",
}

# (columna, tipo, formato, oculta)
COLUMNAS: dict[str, list[tuple[str, str, str | None, bool]]] = {
    "fact_eventos": [
        ("id_evento", "string", None, True),
        ("id_fecha", "string", None, True),
        ("fecha_evento", "date", "dd/MM/yyyy", False),
        ("id_deporte", "string", None, True),
        ("id_competicion", "string", None, True),
        ("id_equipo_local", "string", None, True),
        ("id_equipo_visitante", "string", None, True),
        ("marcador_local", "int64", "0", False),
        ("marcador_visitante", "int64", "0", False),
        ("goles_local", "double", "0.00", False),
        ("goles_visitante", "double", "0.00", False),
        ("puntos_local", "int64", "0", False),
        ("puntos_visitante", "int64", "0", False),
        ("diferencia_marcador", "int64", "+0;-0;0", False),
        ("resultado_normalizado", "string", None, False),
        ("cuota_local", "double", "0.00", False),
        ("cuota_empate", "double", "0.00", False),
        ("cuota_visitante", "double", "0.00", False),
        ("cuota_favorita", "double", "0.00", False),
        ("favorito", "string", None, False),
        ("prob_implicita_local", "double", "0.0%", False),
        ("prob_implicita_empate", "double", "0.0%", False),
        ("prob_implicita_visitante", "double", "0.0%", False),
        ("margen_mercado", "double", "0.0%", False),
        ("fuente_archivo", "string", None, True),
    ],
    "dim_fecha": [
        ("id_fecha", "string", None, True),
        ("fecha", "date", "dd/MM/yyyy", False),
        ("año", "int64", "0", False),
        ("trimestre", "string", None, False),
        ("mes", "int64", "0", False),
        ("nombre_mes", "string", None, False),
        ("semana_iso", "int64", "0", False),
        ("dia", "int64", "0", False),
        ("dia_semana", "string", None, False),
        ("es_fin_semana", "boolean", None, False),
    ],
    "dim_deportes": [
        ("id_deporte", "string", None, True),
        ("deporte", "string", None, False),
        ("n_eventos", "int64", "#,##0", False),
    ],
    "dim_competiciones": [
        ("id_competicion", "string", None, True),
        ("competicion", "string", None, False),
        ("deporte", "string", None, False),
        ("n_eventos", "int64", "#,##0", False),
    ],
    "dim_equipos": [
        ("id_equipo", "string", None, True),
        ("equipo", "string", None, False),
        ("deporte", "string", None, False),
        ("partidos", "int64", "#,##0", False),
        ("victorias", "int64", "#,##0", False),
        ("empates", "int64", "#,##0", False),
        ("derrotas", "int64", "#,##0", False),
        ("tasa_victoria", "double", "0.0%", False),
    ],
}

# columnas que se ordenan por otra columna
ORDEN_POR = {"dim_fecha": {"nombre_mes": "mes"}}

# tabla solo para agrupar medidas
TABLA_MEDIDAS = "_Medidas"

MEDIDAS: list[dict[str, str]] = [
    {
        "nombre": "Total Eventos",
        "dax": "COUNTROWS ( fact_eventos )",
        "formato": "#,##0",
    },
    {
        "nombre": "Eventos con Resultado",
        "dax": 'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] <> "Desconocido" )',
        "formato": "#,##0",
    },
    {
        "nombre": "% del Total",
        "dax": "DIVIDE ( [Total Eventos], CALCULATE ( [Total Eventos], ALLSELECTED ( fact_eventos ) ) )",
        "formato": "0.0%",
    },
    {
        "nombre": "Equipos Distintos",
        "dax": "COUNTROWS ( dim_equipos )",
        "formato": "#,##0",
    },
    {
        "nombre": "Competiciones Distintas",
        "dax": "COUNTROWS ( dim_competiciones )",
        "formato": "#,##0",
    },
    {
        "nombre": "Deportes Distintos",
        "dax": "COUNTROWS ( dim_deportes )",
        "formato": "#,##0",
    },
    {
        "nombre": "Victorias Local",
        "dax": 'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] = "Local" )',
        "formato": "#,##0",
    },
    {
        "nombre": "Victorias Visitante",
        "dax": 'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] = "Visitante" )',
        "formato": "#,##0",
    },
    {
        "nombre": "Empates",
        "dax": 'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] = "Empate" )',
        "formato": "#,##0",
    },
    {
        "nombre": "Resultados Desconocidos",
        "dax": 'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] = "Desconocido" )',
        "formato": "#,##0",
    },
    {
        "nombre": "% Victorias Local",
        "dax": "DIVIDE ( [Victorias Local], [Eventos con Resultado] )",
        "formato": "0.0%",
    },
    {
        "nombre": "% Victorias Visitante",
        "dax": "DIVIDE ( [Victorias Visitante], [Eventos con Resultado] )",
        "formato": "0.0%",
    },
    {
        "nombre": "% Empates",
        "dax": "DIVIDE ( [Empates], [Eventos con Resultado] )",
        "formato": "0.0%",
    },
    {
        "nombre": "Promedio Cuota Local",
        "dax": "AVERAGE ( fact_eventos[cuota_local] )",
        "formato": "0.00",
    },
    {
        "nombre": "Promedio Cuota Visitante",
        "dax": "AVERAGE ( fact_eventos[cuota_visitante] )",
        "formato": "0.00",
    },
    {
        "nombre": "Promedio Cuota Empate",
        "dax": "AVERAGE ( fact_eventos[cuota_empate] )",
        "formato": "0.00",
    },
    {
        "nombre": "Promedio Cuota Favorita",
        "dax": "AVERAGE ( fact_eventos[cuota_favorita] )",
        "formato": "0.00",
    },
    {
        "nombre": "Cuota Mínima",
        "dax": "MIN ( fact_eventos[cuota_local] )",
        "formato": "0.00",
    },
    {
        "nombre": "Cuota Máxima",
        "dax": "MAX ( fact_eventos[cuota_local] )",
        "formato": "0.00",
    },
    {
        "nombre": "Margen Medio del Mercado",
        "dax": "AVERAGE ( fact_eventos[margen_mercado] )",
        "formato": "0.0%",
    },
    {
        "nombre": "% Favorito Local",
        "dax": 'DIVIDE ( CALCULATE ( [Total Eventos], fact_eventos[favorito] = "Local" ), [Total Eventos] )',
        "formato": "0.0%",
    },
    {
        "nombre": "% Favorito Visitante",
        "dax": 'DIVIDE ( CALCULATE ( [Total Eventos], fact_eventos[favorito] = "Visitante" ), [Total Eventos] )',
        "formato": "0.0%",
    },
    {
        "nombre": "Promedio Goles Local",
        "dax": "AVERAGE ( fact_eventos[goles_local] )",
        "formato": "0.00",
    },
    {
        "nombre": "Promedio Goles Visitante",
        "dax": "AVERAGE ( fact_eventos[goles_visitante] )",
        "formato": "0.00",
    },
    {
        "nombre": "Promedio Puntos Local",
        "dax": "AVERAGE ( fact_eventos[puntos_local] )",
        "formato": "0.0",
    },
    {
        "nombre": "Promedio Puntos Visitante",
        "dax": "AVERAGE ( fact_eventos[puntos_visitante] )",
        "formato": "0.0",
    },
    {
        "nombre": "Partidos como Visitante",
        "dax": (
            "CALCULATE (\n"
            "    [Total Eventos],\n"
            "    USERELATIONSHIP ( fact_eventos[id_equipo_visitante], dim_equipos[id_equipo] )\n"
            ")"
        ),
        "formato": "#,##0",
    },
    {
        "nombre": "Partidos Totales Equipo",
        "dax": "[Total Eventos] + [Partidos como Visitante]",
        "formato": "#,##0",
    },
    {
        "nombre": "Victorias Equipo",
        "dax": (
            'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] = "Local" )\n'
            '+ CALCULATE (\n'
            '    [Total Eventos],\n'
            '    fact_eventos[resultado_normalizado] = "Visitante",\n'
            "    USERELATIONSHIP ( fact_eventos[id_equipo_visitante], dim_equipos[id_equipo] )\n"
            ")"
        ),
        "formato": "#,##0",
    },
    {
        "nombre": "Empates Equipo",
        "dax": (
            'CALCULATE ( [Total Eventos], fact_eventos[resultado_normalizado] = "Empate" )\n'
            '+ CALCULATE (\n'
            '    [Total Eventos],\n'
            '    fact_eventos[resultado_normalizado] = "Empate",\n'
            "    USERELATIONSHIP ( fact_eventos[id_equipo_visitante], dim_equipos[id_equipo] )\n"
            ")"
        ),
        "formato": "#,##0",
    },
    {
        "nombre": "Derrotas Equipo",
        "dax": "[Partidos Totales Equipo] - [Victorias Equipo] - [Empates Equipo]",
        "formato": "#,##0",
    },
    {
        "nombre": "% Victorias Equipo",
        "dax": "DIVIDE ( [Victorias Equipo], [Partidos Totales Equipo] )",
        "formato": "0.0%",
    },
    {
        "nombre": "Ranking Equipos",
        "dax": (
            "RANKX (\n"
            "    ALLSELECTED ( dim_equipos[id_equipo] ),\n"
            "    [Partidos Totales Equipo],\n"
            "    ,\n"
            "    DESC,\n"
            "    DENSE\n"
            ")"
        ),
        "formato": "#,##0",
    },
]

RELACIONES = [
    ("fact_eventos", "id_fecha", "dim_fecha", "id_fecha", True),
    ("fact_eventos", "id_deporte", "dim_deportes", "id_deporte", True),
    ("fact_eventos", "id_competicion", "dim_competiciones", "id_competicion", True),
    ("fact_eventos", "id_equipo_local", "dim_equipos", "id_equipo", True),
    ("fact_eventos", "id_equipo_visitante", "dim_equipos", "id_equipo", False),
]


def guid(clave: str) -> str:
    """Devuelve un GUID estable a partir de una clave de texto."""
    return str(uuid.uuid5(ESPACIO, clave))


def _expresion_m(tabla: str, columnas: list[tuple[str, str, str | None, bool]]) -> list[str]:
    """Construye la consulta M que lee un CSV y le aplica los tipos del modelo."""
    tipos = ", ".join(
        '{"%s", %s}' % (nombre, TIPOS_M[tipo]) for nombre, tipo, _, _ in columnas
    )
    return [
        "let",
        "    Origen = Csv.Document(",
        '        File.Contents(RutaDatos & "\\%s.csv"),' % tabla,
        '        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]',
        "    ),",
        "    Encabezado = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),",
        "    Primera = Table.ColumnNames(Encabezado){0},",
        "    SinBom = if Text.StartsWith(Primera, \"#(feff)\") then",
        '        Table.RenameColumns(Encabezado, {{Primera, Text.TrimStart(Primera, "#(feff)")}})',
        "    else",
        "        Encabezado,",
        '    Saneado = Table.ReplaceValue(SinBom, "", null, Replacer.ReplaceValue, Table.ColumnNames(SinBom)),',
        "    Tipado = Table.TransformColumnTypes(",
        "        Saneado,",
        "        {%s}," % tipos,
        '        "en-US"',
        "    )",
        "in",
        "    Tipado",
    ]


def _m_texto(valor: str) -> str:
    """Devuelve un literal de texto M correctamente escapado."""
    escapado = (
        valor.replace('"', '""')
        .replace("\r", "#(cr)")
        .replace("\n", "#(lf)")
        .replace("\t", "#(tab)")
    )
    return f'"{escapado}"'


def _m_valor(valor: str, tipo: str) -> str:
    """Convierte un valor del CSV en un literal M del tipo indicado."""
    limpio = (valor or "").strip()
    if limpio == "" or limpio.lower() in {"nan", "none", "null"}:
        return "null"
    if tipo == "string":
        return _m_texto(valor)
    if tipo == "int64":
        return str(int(float(limpio)))
    if tipo == "double":
        return repr(float(limpio))
    if tipo == "boolean":
        return "true" if limpio.lower() in {"true", "1", "si", "sí"} else "false"
    if tipo == "date":
        fecha = date.fromisoformat(limpio[:10])
        return f"#date({fecha.year}, {fecha.month}, {fecha.day})"
    raise ValueError(f"tipo M desconocido: {tipo}")


def _expresion_embebida(tabla: str, columnas: list[tuple[str, str, str | None, bool]]) -> list[str]:
    """Construye una tabla M literal con todos los datos del CSV.

    Al no usar ``File.Contents`` el modelo queda autocontenido: el proyecto
    funciona aunque se mueva de carpeta o se abra en otro equipo.
    """
    ruta = PROCESADOS / f"{tabla}.csv"
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))

    lineas = ["let", "    Origen = #table(", "        type table ["]
    for indice, (nombre, tipo, _, _) in enumerate(columnas):
        coma = "," if indice < len(columnas) - 1 else ""
        lineas.append(f'            #"{nombre}" = {TIPOS_M_TABLA[tipo]}{coma}')
    lineas += ["        ],", "        {"]
    for fila in filas:
        valores = ", ".join(_m_valor(fila.get(nombre, ""), tipo) for nombre, tipo, _, _ in columnas)
        lineas.append(f"            {{ {valores} }},")
    lineas += ["        }", "    )", "in", "    Origen"]
    return lineas


def construir_modelo(
    usar_csv: bool = False, ruta_datos: str | Path | None = None
) -> dict[str, Any]:
    """Devuelve el diccionario TMSL completo del modelo semantico.

    Por defecto incrusta los datos de los CSV. Con ``usar_csv=True`` genera
    consultas M que leen los CSV de ``ruta_datos`` (o de ``data/processed``).
    """
    carpeta = (
        Path(ruta_datos).expanduser().resolve() if ruta_datos else PROCESADOS
    )
    ruta = str(carpeta)
    tablas: list[dict[str, Any]] = []

    for tabla, columnas in COLUMNAS.items():
        if usar_csv and not (carpeta / f"{tabla}.csv").exists():
            raise FileNotFoundError(f"No se encuentra {carpeta / f'{tabla}.csv'}")
        columnas_tmsl = []
        for nombre, tipo, formato, oculta in columnas:
            columna: dict[str, Any] = {
                "name": nombre,
                "dataType": TIPOS_TMSL[tipo],
                "sourceColumn": nombre,
                "lineageTag": guid(f"{tabla}.{nombre}"),
                "summarizeBy": "none",
            }
            if formato:
                columna["formatString"] = formato
            if oculta:
                columna["isHidden"] = True
            orden = ORDEN_POR.get(tabla, {}).get(nombre)
            if orden:
                columna["sortByColumn"] = orden
            columnas_tmsl.append(columna)

        expresion = (
            _expresion_m(tabla, columnas)
            if usar_csv
            else _expresion_embebida(tabla, columnas)
        )
        tablas.append(
            {
                "name": tabla,
                "lineageTag": guid(tabla),
                "columns": columnas_tmsl,
                "partitions": [
                    {
                        "name": tabla,
                        "mode": "import",
                        "source": {"type": "m", "expression": expresion},
                    }
                ],
            }
        )

    tablas.append(
        {
            "name": TABLA_MEDIDAS,
            "lineageTag": guid(TABLA_MEDIDAS),
            "columns": [
                {
                    "name": "Medida",
                    "dataType": "string",
                    "sourceColumn": "Medida",
                    "lineageTag": guid("_Medidas.Medida"),
                    "isHidden": True,
                    "summarizeBy": "none",
                }
            ],
            "partitions": [
                {
                    "name": TABLA_MEDIDAS,
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": ['let Origen = #table({"Medida"}, {}) in Origen'],
                    },
                }
            ],
            "measures": [
                {
                    "name": medida["nombre"],
                    "expression": medida["dax"].split("\n"),
                    "formatString": medida["formato"],
                    "lineageTag": guid(f"medida.{medida['nombre']}"),
                }
                for medida in MEDIDAS
            ],
        }
    )

    relaciones = []
    for desde_tabla, desde_col, hacia_tabla, hacia_col, activa in RELACIONES:
        relacion: dict[str, Any] = {
            "name": guid(f"rel.{desde_tabla}.{desde_col}"),
            "fromTable": desde_tabla,
            "fromColumn": desde_col,
            "toTable": hacia_tabla,
            "toColumn": hacia_col,
            "crossFilteringBehavior": "oneDirection",
        }
        if not activa:
            relacion["isActive"] = False
        relaciones.append(relacion)

    modelo: dict[str, Any] = {
        "culture": "es-ES",
        "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "tables": tablas,
        "relationships": relaciones,
        "annotations": [
            {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            {"name": "PBIDesktopVersion", "value": "2.140.1.0"},
        ],
    }
    if usar_csv:
        modelo["expressions"] = [
            {
                "name": "RutaDatos",
                "kind": "m",
                "expression": '"%s" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
                % ruta,
                "annotations": [
                    {"name": "PBI_NavigationStepName", "value": "Navigation"},
                    {"name": "PBI_ResultType", "value": "Text"},
                ],
            }
        ]

    return {
        "name": NOMBRE,
        "compatibilityLevel": 1550,
        "model": modelo,
    }


# ---------------------------------------------------------------------------
# Informe (PBIR)
# ---------------------------------------------------------------------------

# (tabla, columna/medida, "col" | "med")
Campo = tuple[str, str, str]


def campo_columna(tabla: str, columna: str) -> dict[str, Any]:
    """Expresion semantica para una columna."""
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": columna}}


def campo_medida(medida: str) -> dict[str, Any]:
    """Expresion semantica para una medida de la tabla `_Medidas`."""
    return {"Measure": {"Expression": {"SourceRef": {"Entity": TABLA_MEDIDAS}}, "Property": medida}}


def _literal(valor: str) -> dict[str, Any]:
    """Envuelve un valor en el formato de expresion de formato de Power BI."""
    return {"expr": {"Literal": {"Value": valor}}}


def _titulo(texto: str) -> dict[str, Any]:
    """Devuelve el objeto de formato del titulo del visual."""
    return {
        "title": [
            {
                "properties": {
                    "show": _literal("true"),
                    "text": _literal("'%s'" % texto.replace("'", "''")),
                    "fontSize": _literal("12D"),
                    "bold": _literal("true"),
                    "alignment": _literal("'left'"),
                }
            }
        ]
    }


def construir_visual(
    nombre: str,
    tipo: str,
    posicion: tuple[int, int, int, int],
    roles: dict[str, list[Campo]],
    ordenar_por: Campo | None = None,
    titulo: str | None = None,
) -> dict[str, Any]:
    """Devuelve el JSON de un visual (visual.json)."""
    x, y, ancho, alto = posicion
    query_state: dict[str, Any] = {}
    for rol, campos in roles.items():
        proyecciones = []
        for tabla, propiedad, clase in campos:
            campo = campo_columna(tabla, propiedad) if clase == "col" else campo_medida(propiedad)
            proyecciones.append(
                {"field": campo, "queryRef": "%s.%s" % (tabla, propiedad)}
            )
        query_state[rol] = {"projections": proyecciones}

    query: dict[str, Any] = {"queryState": query_state}
    if ordenar_por is not None:
        tabla, propiedad, clase = ordenar_por
        campo = campo_columna(tabla, propiedad) if clase == "col" else campo_medida(propiedad)
        query["sortDefinition"] = {
            "sort": [{"field": campo, "direction": "Descending"}],
            "isDefaultSort": False,
        }

    visual: dict[str, Any] = {
        "visualType": tipo,
        "query": query,
        "drillFilterOtherVisuals": True,
    }
    if titulo:
        visual["visualContainerObjects"] = _titulo(titulo)

    return {
        "$schema": ESQUEMA_VISUAL,
        "name": nombre,
        "position": {
            "x": x,
            "y": y,
            "z": 0,
            "width": ancho,
            "height": alto,
            "tabOrder": 0,
        },
        "visual": visual,
    }


PAGINAS: list[dict[str, Any]] = [
    {
        "nombre": "pResumen",
        "titulo": "Resumen general",
        "visuals": [
            {
                "nombre": "vSlicerDeporte",
                "tipo": "slicer",
                "pos": (20, 20, 260, 150),
                "titulo": "Filtrar por deporte",
                "roles": {"Values": [("dim_deportes", "deporte", "col")]},
            },
            {
                "nombre": "vCardTotal",
                "tipo": "card",
                "pos": (300, 20, 220, 150),
                "titulo": "Total de eventos",
                "roles": {"Values": [(TABLA_MEDIDAS, "Total Eventos", "med")]},
            },
            {
                "nombre": "vCardEquipos",
                "tipo": "card",
                "pos": (540, 20, 220, 150),
                "titulo": "Equipos distintos",
                "roles": {"Values": [(TABLA_MEDIDAS, "Equipos Distintos", "med")]},
            },
            {
                "nombre": "vCardCompeticiones",
                "tipo": "card",
                "pos": (780, 20, 220, 150),
                "titulo": "Competiciones",
                "roles": {"Values": [(TABLA_MEDIDAS, "Competiciones Distintas", "med")]},
            },
            {
                "nombre": "vCardMargen",
                "tipo": "card",
                "pos": (1020, 20, 240, 150),
                "titulo": "Margen medio del mercado",
                "roles": {"Values": [(TABLA_MEDIDAS, "Margen Medio del Mercado", "med")]},
            },
            {
                "nombre": "vEventosPorDeporte",
                "tipo": "clusteredColumnChart",
                "pos": (20, 190, 600, 300),
                "titulo": "Eventos por deporte",
                "roles": {
                    "Category": [("dim_deportes", "deporte", "col")],
                    "Y": [(TABLA_MEDIDAS, "Total Eventos", "med")],
                },
                "orden": ("dim_deportes", "deporte", "col"),
            },
            {
                "nombre": "vResultados",
                "tipo": "donutChart",
                "pos": (640, 190, 300, 300),
                "titulo": "Distribución de resultados",
                "roles": {
                    "Category": [("fact_eventos", "resultado_normalizado", "col")],
                    "Y": [(TABLA_MEDIDAS, "Total Eventos", "med")],
                },
            },
            {
                "nombre": "vTendencia",
                "tipo": "lineChart",
                "pos": (960, 190, 300, 300),
                "titulo": "Eventos por mes",
                "roles": {
                    "Category": [
                        ("dim_fecha", "año", "col"),
                        ("dim_fecha", "mes", "col"),
                    ],
                    "Y": [(TABLA_MEDIDAS, "Total Eventos", "med")],
                },
            },
            {
                "nombre": "vPorCompeticion",
                "tipo": "clusteredBarChart",
                "pos": (20, 510, 620, 190),
                "titulo": "Eventos por competición",
                "roles": {
                    "Category": [("dim_competiciones", "competicion", "col")],
                    "Y": [(TABLA_MEDIDAS, "Total Eventos", "med")],
                },
                "orden": (TABLA_MEDIDAS, "Total Eventos", "med"),
            },
            {
                "nombre": "vTablaEquipos",
                "tipo": "tableEx",
                "pos": (660, 510, 600, 190),
                "titulo": "Equipos con más partidos",
                "roles": {
                    "Values": [
                        ("dim_equipos", "equipo", "col"),
                        ("dim_equipos", "deporte", "col"),
                        ("_Medidas", "Partidos Totales Equipo", "med"),
                        ("_Medidas", "% Victorias Equipo", "med"),
                    ]
                },
            },
        ],
    },
    {
        "nombre": "pCuotas",
        "titulo": "Cuotas y mercado",
        "visuals": [
            {
                "nombre": "vCuotasMes",
                "tipo": "lineChart",
                "pos": (20, 20, 620, 330),
                "titulo": "Evolución de cuotas medias por mes",
                "roles": {
                    "Category": [("dim_fecha", "mes", "col")],
                    "Y": [
                        (TABLA_MEDIDAS, "Promedio Cuota Local", "med"),
                        (TABLA_MEDIDAS, "Promedio Cuota Visitante", "med"),
                        (TABLA_MEDIDAS, "Promedio Cuota Empate", "med"),
                    ],
                },
            },
            {
                "nombre": "vMargenDeporte",
                "tipo": "clusteredColumnChart",
                "pos": (660, 20, 600, 330),
                "titulo": "Margen del mercado por deporte",
                "roles": {
                    "Category": [("dim_deportes", "deporte", "col")],
                    "Y": [(TABLA_MEDIDAS, "Margen Medio del Mercado", "med")],
                },
            },
            {
                "nombre": "vFavorito",
                "tipo": "clusteredColumnChart",
                "pos": (20, 370, 620, 330),
                "titulo": "Favorito del mercado por competición",
                "roles": {
                    "Category": [("dim_competiciones", "competicion", "col")],
                    "Y": [
                        (TABLA_MEDIDAS, "% Favorito Local", "med"),
                        (TABLA_MEDIDAS, "% Favorito Visitante", "med"),
                    ],
                },
            },
            {
                "nombre": "vCardCuotaFavorita",
                "tipo": "card",
                "pos": (660, 370, 280, 150),
                "titulo": "Cuota media del favorito",
                "roles": {"Values": [(TABLA_MEDIDAS, "Promedio Cuota Favorita", "med")]},
            },
            {
                "nombre": "vCardCuotaMin",
                "tipo": "card",
                "pos": (660, 540, 140, 160),
                "titulo": "Cuota mínima",
                "roles": {"Values": [(TABLA_MEDIDAS, "Cuota Mínima", "med")]},
            },
            {
                "nombre": "vCardCuotaMax",
                "tipo": "card",
                "pos": (820, 540, 140, 160),
                "titulo": "Cuota máxima",
                "roles": {"Values": [(TABLA_MEDIDAS, "Cuota Máxima", "med")]},
            },
            {
                "nombre": "vCardProbLocal",
                "tipo": "card",
                "pos": (980, 540, 140, 160),
                "titulo": "% Favorito local",
                "roles": {"Values": [(TABLA_MEDIDAS, "% Favorito Local", "med")]},
            },
            {
                "nombre": "vCardProbVis",
                "tipo": "card",
                "pos": (1140, 540, 120, 160),
                "titulo": "% Favorito visitante",
                "roles": {"Values": [(TABLA_MEDIDAS, "% Favorito Visitante", "med")]},
            },
        ],
    },
    {
        "nombre": "pEquipos",
        "titulo": "Detalle por equipo",
        "visuals": [
            {
                "nombre": "vTablaDetalle",
                "tipo": "tableEx",
                "pos": (20, 20, 1240, 380),
                "titulo": "Estadísticas históricas por equipo",
                "roles": {
                    "Values": [
                        ("dim_equipos", "equipo", "col"),
                        ("dim_equipos", "deporte", "col"),
                        ("_Medidas", "Partidos Totales Equipo", "med"),
                        ("_Medidas", "Victorias Equipo", "med"),
                        ("_Medidas", "Empates Equipo", "med"),
                        ("_Medidas", "Derrotas Equipo", "med"),
                        ("_Medidas", "% Victorias Equipo", "med"),
                        ("_Medidas", "Ranking Equipos", "med"),
                    ]
                },
            },
            {
                "nombre": "vCardVictoriasLocal",
                "tipo": "card",
                "pos": (20, 430, 300, 130),
                "titulo": "Victorias del local",
                "roles": {"Values": [(TABLA_MEDIDAS, "Victorias Local", "med")]},
            },
            {
                "nombre": "vCardEmpates",
                "tipo": "card",
                "pos": (340, 430, 300, 130),
                "titulo": "Empates",
                "roles": {"Values": [(TABLA_MEDIDAS, "Empates", "med")]},
            },
            {
                "nombre": "vCardVictoriasVis",
                "tipo": "card",
                "pos": (660, 430, 300, 130),
                "titulo": "Victorias del visitante",
                "roles": {"Values": [(TABLA_MEDIDAS, "Victorias Visitante", "med")]},
            },
            {
                "nombre": "vCardDesconocidos",
                "tipo": "card",
                "pos": (980, 430, 280, 130),
                "titulo": "Eventos sin resultado",
                "roles": {"Values": [(TABLA_MEDIDAS, "Resultados Desconocidos", "med")]},
            },
            {
                "nombre": "vLocalVisitante",
                "tipo": "clusteredColumnChart",
                "pos": (20, 580, 1240, 120),
                "titulo": "Resultado de los eventos",
                "roles": {
                    "Category": [("fact_eventos", "resultado_normalizado", "col")],
                    "Y": [(TABLA_MEDIDAS, "Total Eventos", "med")],
                },
            },
        ],
    },
]


def construir_informe() -> dict[str, Any]:
    """Devuelve la estructura del informe (paginas y visuales)."""
    paginas = []
    for pagina in PAGINAS:
        visuales = []
        for visual in pagina["visuals"]:
            visuales.append(
                (
                    visual["nombre"],
                    construir_visual(
                        visual["nombre"],
                        visual["tipo"],
                        visual["pos"],
                        visual["roles"],
                        visual.get("orden"),
                        visual.get("titulo"),
                    ),
                )
            )
        paginas.append((pagina, visuales))
    return {"paginas": paginas}


# ---------------------------------------------------------------------------
# Escritura y validacion
# ---------------------------------------------------------------------------

def escribir_json(ruta: Path, datos: Any) -> None:
    """Escribe un archivo JSON con formato legible y saltos de linea LF."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(datos, indent=2, ensure_ascii=False) + "\n"
    ruta.write_text(texto, encoding="utf-8", newline="\n")
    LOG.info("Escrito %s", ruta.relative_to(RAIZ))


def _valor_excel(valor: str, tipo: str) -> Any:
    """Convierte un valor del CSV al tipo nativo que entiende Excel."""
    limpio = (valor or "").strip()
    if limpio == "" or limpio.lower() in {"nan", "none", "null"}:
        return None
    if tipo == "string":
        return valor
    if tipo == "int64":
        return int(float(limpio))
    if tipo == "double":
        return float(limpio)
    if tipo == "boolean":
        return limpio.lower() in {"true", "1", "si", "sí"}
    if tipo == "date":
        return date.fromisoformat(limpio[:10])
    raise ValueError(f"tipo desconocido: {tipo}")


def exportar_excel(destino: Path | None = None) -> Path:
    """Escribe un libro con una hoja por tabla, listo para Power BI."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    destino = destino or EXCEL
    destino.parent.mkdir(parents=True, exist_ok=True)

    libro = Workbook()
    libro.remove(libro.active)

    for tabla, columnas in COLUMNAS.items():
        hoja = libro.create_sheet(tabla)
        hoja.append([nombre for nombre, _, _, _ in columnas])
        for celda in hoja[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="1F4E78")
            celda.alignment = Alignment(horizontal="center")

        anchos = [len(nombre) for nombre, _, _, _ in columnas]
        with (PROCESADOS / f"{tabla}.csv").open(encoding="utf-8-sig", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                valores = [
                    _valor_excel(fila.get(nombre, ""), tipo)
                    for nombre, tipo, _, _ in columnas
                ]
                hoja.append(valores)
                for indice, valor in enumerate(valores):
                    if valor is not None:
                        anchos[indice] = max(anchos[indice], min(len(str(valor)), 45))

        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions
        for indice, (ancho, (_, tipo, formato, _)) in enumerate(
            zip(anchos, columnas), start=1
        ):
            letra = get_column_letter(indice)
            dimension = hoja.column_dimensions[letra]
            dimension.width = min(max(ancho + 2, 10), 45)
            if tipo == "date":
                dimension.number_format = "dd/mm/yyyy"
                # openpyxl asigna un estilo de fecha a cada celda; se quita para
                # que herede el formato de fecha de la columna.
                for fila in range(2, hoja.max_row + 1):
                    hoja.cell(row=fila, column=indice).style = "Normal"
            elif formato in {"0.0%", "0.00%"}:
                dimension.number_format = "0.0%"
            elif tipo in {"int64", "double"}:
                dimension.number_format = formato or "#,##0"

    libro.save(destino)
    LOG.info("Escrito %s", destino.relative_to(RAIZ))
    return destino


def generar(
    usar_csv: bool = False,
    ruta_datos: str | Path | None = None,
    excel: bool = True,
) -> list[Path]:
    """Genera todos los archivos del proyecto y devuelve sus rutas."""
    if DESTINO.exists():
        for archivo in sorted(DESTINO.rglob("*"), reverse=True):
            if archivo.is_file():
                archivo.unlink()
            elif archivo.is_dir() and not any(archivo.iterdir()):
                archivo.rmdir()

    carpeta_modelo = DESTINO / f"{NOMBRE}.SemanticModel"
    carpeta_informe = DESTINO / f"{NOMBRE}.Report"
    generados: list[Path] = []

    def guardar(ruta: Path, datos: Any) -> None:
        escribir_json(ruta, datos)
        generados.append(ruta)

    leeme = DESTINO / "LEEME - COMO ABRIR.txt"
    leeme.parent.mkdir(parents=True, exist_ok=True)
    leeme.write_text(TEXTO_LEEME, encoding="utf-8", newline="\n")
    generados.append(leeme)
    LOG.info("Escrito %s", leeme.relative_to(RAIZ))

    # archivo .pbip
    guardar(        DESTINO / f"{NOMBRE}.pbip",
        {
            "$schema": ESQUEMA_PBIP,
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{NOMBRE}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )

    # modelo semantico
    guardar(
        carpeta_modelo / ".platform",
        {
            "$schema": ESQUEMA_PLATAFORMA,
            "metadata": {"type": "SemanticModel", "displayName": "Modelo Apuestas"},
            "config": {"version": "2.0", "logicalId": guid("modelo")},
        },
    )
    guardar(
        carpeta_modelo / "definition.pbism",
        {"$schema": ESQUEMA_PBISM, "version": "4.0", "settings": {}},
    )
    guardar(carpeta_modelo / "model.bim", construir_modelo(usar_csv, ruta_datos))

    # informe
    guardar(
        carpeta_informe / ".platform",
        {
            "$schema": ESQUEMA_PLATAFORMA,
            "metadata": {"type": "Report", "displayName": "Dashboard Apuestas"},
            "config": {"version": "2.0", "logicalId": guid("informe")},
        },
    )
    guardar(
        carpeta_informe / "definition.pbir",
        {
            "$schema": ESQUEMA_PBIR,
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{NOMBRE}.SemanticModel"}},
        },
    )
    definicion = carpeta_informe / "definition"
    guardar(
        definicion / "version.json",
        {"$schema": ESQUEMA_VERSION, "version": "1.0.0"},
    )
    guardar(
        definicion / "report.json",
        {"$schema": ESQUEMA_REPORT, "themeCollection": {}, "layoutOptimization": "None"},
    )
    guardar(
        definicion / "pages" / "pages.json",
        {
            "$schema": ESQUEMA_PAGINAS,
            "pageOrder": [p["nombre"] for p in PAGINAS],
            "activePageName": PAGINAS[0]["nombre"],
        },
    )

    for pagina, visuales in construir_informe()["paginas"]:
        carpeta_pagina = definicion / "pages" / pagina["nombre"]
        guardar(
            carpeta_pagina / "page.json",
            {
                "$schema": ESQUEMA_PAGINA,
                "name": pagina["nombre"],
                "displayName": pagina["titulo"],
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
            },
        )
        for nombre_visual, datos in visuales:
            guardar(carpeta_pagina / "visuals" / nombre_visual / "visual.json", datos)

    if excel:
        try:
            generados.append(exportar_excel())
        except ImportError:
            LOG.warning("openpyxl no esta instalado: no se genero powerbi/datos_powerbi.xlsx")

    LOG.info("Proyecto generado en %s (%d archivos)", DESTINO, len(generados))
    return generados


def _ruta_del_parametro(modelo: dict[str, Any]) -> Path | None:
    """Extrae la carpeta configurada en el parametro M ``RutaDatos``."""
    for expresion in modelo["model"].get("expressions", []):
        if expresion.get("name") != "RutaDatos":
            continue
        coincidencia = re.match(r'^"((?:[^"\\]|\\.)*)"', expresion.get("expression", ""))
        if coincidencia:
            return Path(json.loads(f'"{coincidencia.group(1)}"'))
    return None


def verificar() -> list[str]:
    """Comprueba la coherencia entre el modelo, los CSV y los visuales."""
    errores: list[str] = []
    modelo = json.loads(
        (DESTINO / f"{NOMBRE}.SemanticModel" / "model.bim").read_text(encoding="utf-8")
    )
    tablas: dict[str, list[str]] = {}
    medidas: set[str] = set()
    carpeta = _ruta_del_parametro(modelo)
    usar_csv = carpeta is not None
    carpeta = carpeta or PROCESADOS

    if not usar_csv:
        for tabla in modelo["model"]["tables"]:
            if tabla["name"] == TABLA_MEDIDAS:
                continue
            consulta = "\n".join(tabla["partitions"][0]["source"]["expression"])
            if "File.Contents" in consulta or "RutaDatos" in consulta:
                errores.append(
                    f"{tabla['name']}: el modelo incrustado no debe leer archivos externos"
                )
            if "#table(" not in consulta:
                errores.append(f"{tabla['name']}: falta la tabla M incrustada")

    for tabla in modelo["model"]["tables"]:
        columnas = [columna["name"] for columna in tabla["columns"]]
        tablas[tabla["name"]] = columnas
        for medida in tabla.get("measures", []):
            if medida["name"] in medidas:
                errores.append(f"medida duplicada: {medida['name']}")
            medidas.add(medida["name"])
        if tabla["name"] == TABLA_MEDIDAS:
            continue
        ruta = carpeta / f"{tabla['name']}.csv"
        if not ruta.exists():
            errores.append(f"falta el archivo {ruta}")
            continue
        with ruta.open(encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            cabecera = [nombre.lstrip("\ufeff") for nombre in (lector.fieldnames or [])]
            filas_csv = sum(1 for _ in lector)
        if cabecera != columnas:
            errores.append(f"{tabla['name']}: el modelo y el CSV no tienen las mismas columnas")
        if not usar_csv:
            consulta = "\n".join(tabla["partitions"][0]["source"]["expression"])
            filas_m = sum(
                1
                for linea in consulta.splitlines()
                if linea.startswith("            { ")
            )
            if filas_m != filas_csv:
                errores.append(
                    f"{tabla['name']}: el modelo incrusta {filas_m} filas y el CSV tiene {filas_csv}"
                )
        else:
            consulta = "\n".join(tabla["partitions"][0]["source"]["expression"])
            esperado = f'File.Contents(RutaDatos & "\\{tabla["name"]}.csv")'
            if esperado not in consulta:
                errores.append(f"{tabla['name']}: la consulta M no usa RutaDatos")

    for relacion in modelo["model"]["relationships"]:
        for tabla, columna in (
            (relacion["fromTable"], relacion["fromColumn"]),
            (relacion["toTable"], relacion["toColumn"]),
        ):
            if columna not in tablas.get(tabla, []):
                errores.append(f"relacion {tabla}[{columna}]: la columna no existe")

    for tabla in modelo["model"]["tables"]:
        for medida in tabla.get("measures", []):
            dax = "\n".join(medida["expression"])
            for referencia, columna in re.findall(r"(\w+)\[([^\]]+)\]", dax):
                if referencia not in tablas:
                    errores.append(f"{medida['name']}: tabla desconocida {referencia}")
                elif columna not in tablas[referencia]:
                    errores.append(f"{medida['name']}: columna desconocida {referencia}[{columna}]")
            for referencia in re.findall(r"\[([^\]]+)\]", re.sub(r"\w+\[[^\]]+\]", "", dax)):
                if referencia not in medidas:
                    errores.append(f"{medida['name']}: medida desconocida [{referencia}]")

    for pagina in PAGINAS:
        vistos: set[str] = set()
        for visual in pagina["visuals"]:
            if visual["nombre"] in vistos:
                errores.append(f"visual duplicado: {visual['nombre']}")
            vistos.add(visual["nombre"])
            for campos in visual["roles"].values():
                for tabla, propiedad, clase in campos:
                    if clase == "col" and propiedad not in tablas.get(tabla, []):
                        errores.append(f"{visual['nombre']}: columna desconocida {tabla}[{propiedad}]")
                    if clase == "med" and propiedad not in medidas:
                        errores.append(f"{visual['nombre']}: medida desconocida [{propiedad}]")
            if visual.get("orden"):
                tabla, propiedad, clase = visual["orden"]
                if clase == "col" and propiedad not in tablas.get(tabla, []):
                    errores.append(f"{visual['nombre']}: orden por columna desconocida")
                if clase == "med" and propiedad not in medidas:
                    errores.append(f"{visual['nombre']}: orden por medida desconocida")

    return errores


def validar(archivos: list[Path]) -> bool:
    """Valida los archivos JSON contra los esquemas publicos de Microsoft."""
    try:
        import jsonschema
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7
    except ImportError:
        LOG.error("Instala 'jsonschema' para usar --validar: pip install jsonschema")
        return False

    cache: dict[str, Any] = {}

    def recuperar(uri: str) -> Any:
        if uri not in cache:
            import urllib.request

            with urllib.request.urlopen(uri, timeout=30) as respuesta:
                cache[uri] = json.loads(respuesta.read().decode("utf-8"))
        return Resource.from_contents(cache[uri], default_specification=DRAFT7)

    registro = Registry(retrieve=recuperar)
    correcto = True
    for archivo in archivos:
        if archivo.suffix not in {".json", ".pbip", ".pbir", ".pbism", ".platform"}:
            continue
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        esquema = datos.get("$schema")
        if not esquema:
            continue
        if esquema not in cache:
            recuperar(esquema)
        errores = sorted(
            jsonschema.Draft7Validator(cache[esquema], registry=registro).iter_errors(datos),
            key=lambda e: list(e.absolute_path),
        )
        if errores:
            correcto = False
            for error in errores:
                LOG.error(
                    "%s -> %s (%s)",
                    archivo.relative_to(RAIZ),
                    error.message,
                    "/".join(str(p) for p in error.absolute_path),
                )
        else:
            LOG.info("OK esquema: %s", archivo.relative_to(RAIZ))
    return correcto


def main() -> int:
    """Punto de entrada del generador."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    analizador = argparse.ArgumentParser(description="Genera el proyecto .pbip de Power BI")
    analizador.add_argument(
        "--validar",
        action="store_true",
        help="valida los JSON contra los esquemas oficiales (requiere Internet)",
    )
    analizador.add_argument(
        "--usar-csv",
        action="store_true",
        help="conecta el modelo a los CSV en lugar de incrustar los datos",
    )
    analizador.add_argument(
        "--ruta-datos",
        type=Path,
        metavar="CARPETA",
        help="carpeta de los CSV (implica --usar-csv)",
    )
    analizador.add_argument(
        "--sin-excel",
        action="store_true",
        help="no genera powerbi/datos_powerbi.xlsx",
    )
    opciones = analizador.parse_args()

    usar_csv = opciones.usar_csv or opciones.ruta_datos is not None
    try:
        archivos = generar(
            usar_csv=usar_csv,
            ruta_datos=opciones.ruta_datos,
            excel=not opciones.sin_excel,
        )
    except FileNotFoundError as error:
        LOG.error("%s", error)
        return 1
    errores = verificar()
    for error in errores:
        LOG.error("Verificación: %s", error)
    if errores:
        return 1
    LOG.info("Verificación de modelo, relaciones y visuales: sin errores")
    if opciones.validar and not validar(archivos):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
