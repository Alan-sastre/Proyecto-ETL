# PROYECTO ETL: ANÁLISIS DE DATOS DE APUESTAS DEPORTIVAS

**Autores**

- Camilo Andrés Ardila Beleño — 834328
- Yesli Eliana Malaver Cangrejo — 854165
- Alan Gabo Sastre — 865413

> **Aviso académico.** Este proyecto tiene fines exclusivamente educativos y
> estadísticos. Trabaja con **datos históricos simulados** generados con una
> semilla fija; no utiliza apuestas reales, no se conecta a casas de apuestas y
> no realiza scraping. **No promueve ni recomienda las apuestas reales.**

---

## Inicio rápido

**Repositorio:** <https://github.com/Alan-sastre/Proyecto-ETL>

```powershell
git clone https://github.com/Alan-sastre/Proyecto-ETL.git
cd Proyecto-ETL
```

### Opción A — Ver el dashboard en Power BI (sin construir nada)

El dashboard ya está generado como proyecto de Power BI en `powerbi/PBIP/`.

1. Instala **Power BI Desktop** (gratis):
   <https://powerbi.microsoft.com/desktop/>
2. Abre [`powerbi/PBIP/Dashboard_Apuestas.pbip`](powerbi/PBIP/Dashboard_Apuestas.pbip)
   con doble clic (o **Archivo → Abrir**).
3. Pulsa **Inicio → Actualizar** para cargar los datos de `data/processed/`.
4. Listo: verás las tres páginas (**Resumen general**, **Cuotas y mercado** y
   **Detalle por equipo**) con sus 24 visuales.
5. Si la entrega exige `.pbix`: **Archivo → Guardar como → Power BI (.pbix)**.

> El proyecto incluye el modelo estrella, las 5 relaciones, las 33 medidas DAX y
> los 24 visuales ya armados. Instrucciones detalladas, ruta del parámetro
> `RutaDatos` y solución de problemas en
> [`powerbi/ABRIR_EN_POWER_BI.md`](powerbi/ABRIR_EN_POWER_BI.md).

### Opción B — Ejecutar el ETL desde cero

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py --regenerar --semilla 42
python -m pytest
python powerbi/build_pbip.py
```

En macOS o Linux: `python3 -m venv .venv`, `source .venv/bin/activate` y el
resto es igual.

---

## 1. Introducción

Los datos de eventos deportivos llegan en formatos heterogéneos: archivos CSV
con separadores distintos, hojas de Excel, nombres de columnas que cambian
entre fuentes, fechas escritas de múltiples maneras y cuotas almacenadas como
texto. Antes de analizarlos es necesario un proceso **ETL (Extract, Transform,
Load)** que los integre, limpie y estructure.

Este proyecto construye un pipeline ETL completo con **Python y Pandas** que
parte de tres fuentes simuladas y deliberadamente "sucias", aplica un conjunto
documentado de reglas de calidad y deja los datos listos para analizarlos con
**Matplotlib** y visualizarlos en **Power BI**.

El resultado final es un dataset limpio de más de 3.000 eventos, un reporte de
calidad antes/después, un modelo estrella simple y una guía para construir el
dashboard en Power BI.

---

## 2. Planteamiento del problema

Las fuentes de datos deportivos suelen presentar los siguientes problemas:

- **Duplicados**: el mismo evento aparece más de una vez, a veces con pequeños
  cambios entre copias.
- **Valores nulos** en columnas críticas como fecha, resultado, competición o
  cuotas.
- **Nombres inconsistentes**: mayúsculas, espacios extra, tildes, abreviaturas
  y errores tipográficos (`Real Madird`, `Barca`, `R. Madrid`).
- **Fechas en formatos mezclados**: `DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`,
  texto en español e incluso fechas imposibles como `31/02/2024`.
- **Cuotas como texto** (`"1,85"`, `"N/A"`) o fuera de rango (negativas, cero,
  valores atípicos).
- **Esquemas distintos** entre archivos: `Equipo_Local`, `home_team` y
  `Jugador_Local` representan el mismo concepto.
- **Falta de trazabilidad** sobre el origen de cada registro.

Si estos problemas no se corrigen, los totales, promedios y visualizaciones
resultan engañosos. El proyecto demuestra cómo detectarlos, cuantificarlos y
tratarlos de forma reproducible.

---

## 3. Objetivos

### 3.1 Objetivo general

Extraer, transformar y cargar datos de eventos deportivos para obtener
información organizada que facilite el análisis estadístico y la creación de
visualizaciones en Power BI.

### 3.2 Objetivos específicos

1. Extraer información deportiva desde diferentes fuentes (CSV y Excel).
2. Identificar y corregir errores en los registros.
3. Eliminar duplicados y tratar valores nulos.
4. Organizar los datos con Python y Pandas.
5. Crear una base de datos limpia y estructurada.
6. Dejar todo listo para construir visualizaciones y reportes en Power BI.

---

## 4. Herramientas utilizadas

| Herramienta | Uso en el proyecto |
|---|---|
| **Python 3.10+** | Lenguaje del pipeline |
| **Pandas** | Extracción, limpieza, transformación y agregaciones |
| **Matplotlib** | Gráficos estadísticos en PNG |
| **OpenPyXL** | Lectura y escritura de Excel |
| **SQLite** | Carga opcional de las tablas del modelo estrella |
| **pytest** | Pruebas automatizadas de las transformaciones |
| **Power BI** | Dashboard interactivo (proyecto `.pbip` generado por código y exportable a `.pbix`) |
| **CSV / Excel** | Almacenamiento e intercambio de datos |

---

## 5. Estructura del proyecto

```text
proyecto_etl_apuestas/
├── data/
│   ├── raw/                          # Fuentes simuladas sucias
│   │   ├── eventos_futbol.csv
│   │   ├── eventos_baloncesto.csv
│   │   └── eventos_tenis.xlsx
│   └── processed/                    # Salidas del ETL
│       ├── eventos_limpios.csv
│       ├── eventos_limpios.xlsx
│       ├── dim_equipos.csv
│       ├── dim_deportes.csv
│       ├── dim_competiciones.csv
│       ├── dim_fecha.csv
│       ├── fact_eventos.csv
│       └── apuestas.db               # SQLite (opcional)
├── src/
│   ├── __init__.py
│   ├── config.py                     # Rutas, esquemas, alias y logging
│   ├── generate_sample_data.py       # Datos simulados sucios (semilla fija)
│   ├── extract.py                    # Fase Extract
│   ├── transform.py                  # Fase Transform + reporte de calidad
│   ├── load.py                       # Fase Load + modelo estrella
│   └── visualizations.py             # Figuras con Matplotlib
├── notebooks/
│   └── analisis_exploratorio.ipynb   # Recorrido del ETL y análisis
├── reports/
│   ├── reporte_calidad.md
│   ├── reporte_calidad.csv
│   ├── logs/pipeline.log
│   └── figures/
│       ├── 01_total_eventos.png
│       ├── 02_eventos_por_deporte.png
│       ├── 03_resultados_por_equipo.png
│       ├── 04_local_vs_visitante.png
│       ├── 05_eventos_por_competicion.png
│       ├── 06_analisis_cuotas.png
│       └── 07_tendencia_mensual.png
├── powerbi/
│   ├── GUIA_DASHBOARD.md             # Construcción manual paso a paso
│   ├── ABRIR_EN_POWER_BI.md          # Cómo abrir el dashboard ya generado
│   ├── medidas_DAX.md
│   ├── power_query.m
│   ├── build_pbip.py                 # Genera el proyecto .pbip por código
│   └── PBIP/                         # Proyecto listo para Power BI Desktop
│       ├── Dashboard_Apuestas.pbip
│       ├── Dashboard_Apuestas.SemanticModel/
│       └── Dashboard_Apuestas.Report/
├── tests/
│   ├── conftest.py
│   ├── test_extract.py
│   ├── test_transform.py
│   ├── test_load.py
│   └── test_pbip.py
├── main.py                           # Orquestador ETL + gráficos
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 6. Datos de entrada (Paso 0)

No se utilizan datos reales. El script `src/generate_sample_data.py` genera
**3.425 registros crudos** repartidos en tres fuentes con esquemas distintos:

| Fuente | Formato | Deporte | Registros | Particularidad |
|---|---|---|---:|---|
| `eventos_futbol.csv` | CSV | Fútbol | 1.841 | Esquema en español estándar |
| `eventos_baloncesto.csv` | CSV | Baloncesto | 920 | Columnas con espacios y mayúsculas (`Cuota Local`) |
| `eventos_tenis.xlsx` | Excel | Tenis | 664 | Columnas `Jugador_Local`, `Torneo`; sin columna de empate |

### 6.1 Campos del esquema estándar

`id_evento`, `deporte`, `equipo_local`, `equipo_visitante`, `fecha_evento`,
`resultado`, `competicion`, `cuota_local`, `cuota_empate` (no aplica en todos
los deportes) y `cuota_visitante`.

### 6.2 Problemas inyectados deliberadamente

| Problema | Detalle |
|---|---|
| Duplicados exactos | ~1,5 % de filas duplicadas literalmente |
| Duplicados por `id_evento` | Copias con cuota o nombre de equipo alterados |
| Nulos | En equipos, competición, resultado, fechas y cuotas |
| Nombres de equipos | Mayúsculas, espacios dobles, sin tildes, abreviaturas y typos |
| Fechas | Cuatro formatos distintos, texto en español y valores imposibles |
| Cuotas | Coma decimal, `"N/A"`, negativas, cero y valores > 80 |
| Columnas | Nombres distintos en cada fuente y columna ausente en Excel |

La semilla por defecto es **42**, por lo que los datos y los resultados son
reproducibles. El pipeline funciona igual si se reemplazan los archivos por
datos reales que respeten (o no) el esquema, gracias al mapeo de alias.

---

## 7. Fase 1 — Extract (`src/extract.py`)

1. **Descubre archivos automáticamente** en `data/raw/`: CSV, XLSX y XLS,
   ignorando archivos temporales de Excel (`~$...`).
2. **Lee con tolerancia a errores**: prueba codificaciones `utf-8-sig`,
   `utf-8` y `latin-1`, y detecta automáticamente el separador.
3. **Unifica columnas** mediante un diccionario de alias: `ID`, `id_partido`,
   `home_team`, `Jugador_Local`, `Torneo`, etc. se convierten al esquema
   estándar.
4. **Completa columnas ausentes** con nulos y registra una advertencia.
5. **Agrega `fuente_archivo`** para auditar el origen de cada registro.
6. **Registra en el log** cuántos registros se leyeron por fuente.
7. Si un archivo está corrupto, registra el error y continúa con las demás
   fuentes en lugar de detener el pipeline.

---

## 8. Fase 2 — Transform (`src/transform.py`)

Cada paso es una función independiente, documentada y con logging del número
de registros afectados.

### 8.1 Eliminación de duplicados

- Se eliminan primero los **duplicados exactos**.
- Luego se deduplica por `id_evento`, conservando la fila con **más valores no
  nulos**. En caso de empate se mantiene la primera aparición.
- Las filas sin identificador no se deduplican: se eliminan en el paso de
  nulos.

### 8.2 Tratamiento de nulos

| Columna | Estrategia | Justificación |
|---|---|---|
| `id_evento` | Eliminar fila | Sin identificador no hay trazabilidad ni deduplicación posible |
| `fecha_evento` | Eliminar fila | Es la base del modelo temporal; imputarla introduciría sesgo |
| `deporte` | Imputar `Desconocido` | Conserva el evento y hace explícita la ausencia |
| `equipo_local` / `equipo_visitante` | Imputar `Desconocido` | Conserva el evento; el equipo no entra en rankings |
| `competicion` | Imputar `Desconocida` | Categoría explícita para no perder registros |
| `resultado` | Imputar `Desconocido` | El marcador derivado queda nulo y el resultado se marca |
| `cuota_local` / `cuota_visitante` | Mediana por deporte | Robusta a extremos y respeta la escala de cada deporte |
| `cuota_empate` | Nulo estructural / mediana en deportes con empate | Baloncesto y tenis no admiten empate: no se inventa una cuota |
| `fuente_archivo` | Imputar `desconocida` | Columna de trazabilidad |

### 8.3 Corrección de nombres de equipos

1. Limpieza de espacios repetidos y extremos.
2. Normalización (minúsculas, sin tildes, separadores uniformes).
3. Diccionario de **alias** para abreviaturas y errores conocidos
   (`R. Madrid`, `Barca`, `Atleti`, `GSW`, `Penya`…).
4. Coincidencia exacta contra el catálogo de equipos del deporte.
5. Corrección de **typos por similitud** con `difflib.get_close_matches`
   (umbral 0,80), por ejemplo `Real Madird` → `Real Madrid`.
6. Si no hay coincidencia fiable, se conserva el nombre limpio.

### 8.4 Estandarización de fechas

- Formatos soportados: `DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`,
  `YYYY/MM/DD`, `YYYYMMDD` y texto como `5 de marzo de 2024`.
- Resultado en tipo fecha ISO (`YYYY-MM-DD`).
- Fechas imposibles (`31/02/2024`), vacías, `N/A` o fuera del rango
  1990–2100 devuelven `NaT` y la fila se elimina.

### 8.5 Organización y tipos de datos

- Orden final de 30 columnas: identificación, dimensión temporal, competición,
  marcador, resultado, cuotas y probabilidades, trazabilidad.
- `id_evento` como texto; cuotas como `float`; marcadores como enteros
  *nullable* (`Int64`); variables descriptivas como categóricas.

### 8.6 Validación de cuotas y valores atípicos

- Conversión de texto a número con soporte de coma decimal y separador de
  miles.
- Se consideran inválidas las cuotas `<= 1.0` y atípicas las `> 50`.
- Ambas se sustituyen por la **mediana del deporte**.
- La cuota de empate solo se imputa en deportes que admiten empate.

### 8.7 Columnas nuevas

| Columna | Descripción |
|---|---|
| `año`, `mes`, `nombre_mes`, `dia`, `dia_semana` | Dimensiones temporales en español |
| `marcador_local`, `marcador_visitante` | Marcador numérico extraído del resultado |
| `goles_local` / `goles_visitante` | Solo para fútbol |
| `puntos_local` / `puntos_visitante` | Baloncesto y tenis (en tenis, sets) |
| `diferencia_marcador` | Marcador local menos visitante |
| `resultado_normalizado` | `Local`, `Empate`, `Visitante` o `Desconocido` |
| `cuota_favorita`, `favorito` | Cuota mínima y etiqueta del favorito |
| `prob_implicita_local/empate/visitante` | `1 / cuota` |
| `margen_mercado` | Suma de probabilidades implícitas − 1 |

### 8.8 Reporte de calidad

Se genera automáticamente:

- `reports/reporte_calidad.md`: resumen, nulos antes/después, estrategia por
  columna, correcciones y conclusiones.
- `reports/reporte_calidad.csv`: formato largo
  (`seccion, metrica, valor_antes, valor_despues, detalle`) para analizarlo o
  graficarlo.

---

## 9. Fase 3 — Load (`src/load.py`)

### 9.1 Dataset limpio

- `data/processed/eventos_limpios.csv` (UTF-8 con BOM, fechas ISO).
- `data/processed/eventos_limpios.xlsx`.

Ambos son compatibles con Power BI: codificación UTF-8, primera fila como
encabezado y fechas en formato ISO.

### 9.2 Modelo estrella simple

```text
                 dim_deportes
                      │ 1
                      │
                      ▼ *
dim_fecha ──1──► fact_eventos ◄──*── dim_competiciones
    1                 │ *
                      │
          ┌───────────┴───────────┐
          ▼ *                     ▼ *
  dim_equipos (local)     dim_equipos (visitante)
```

| Tabla | Grano | Columnas principales |
|---|---|---|
| `fact_eventos` | Un evento | `id_evento`, claves foráneas, marcador, cuotas, probabilidades |
| `dim_equipos` | Equipo + deporte | `id_equipo`, `equipo`, `deporte`, partidos, victorias, empates, derrotas, tasa de victoria |
| `dim_deportes` | Deporte | `id_deporte`, `deporte`, `n_eventos` |
| `dim_competiciones` | Competición + deporte | `id_competicion`, `competicion`, `deporte`, `n_eventos` |
| `dim_fecha` | Fecha | `id_fecha`, `fecha`, año, trimestre, mes, semana ISO, día, día de la semana, fin de semana |

La relación con equipos es doble (local y visitante). En Power BI se deja
**activa la relación local** y la de visitante se usa con `USERELATIONSHIP` en
las medidas correspondientes (ver `powerbi/medidas_DAX.md`).

Los eventos cuyo equipo no pudo recuperarse se conservan en `fact_eventos` con
clave de equipo vacía (82 registros con la semilla 42). No se incluyen en
`dim_equipos` para no contaminar los rankings; en Power BI aparecen como
"En blanco" al analizar por equipo.

### 9.3 Carga opcional a SQLite

`data/processed/apuestas.db` contiene las cinco tablas con los mismos nombres.
Se puede consultar con cualquier cliente SQLite o con Python:

```python
import sqlite3
conexion = sqlite3.connect("data/processed/apuestas.db")
print(conexion.execute("SELECT COUNT(*) FROM fact_eventos").fetchone())
```

---

## 10. Fase 4 — Visualización

### 10.1 Gráficos Matplotlib

Se guardan en `reports/figures/`:

| Archivo | Indicador |
|---|---|
| `01_total_eventos.png` | Cantidad total de eventos registrados |
| `02_eventos_por_deporte.png` | Distribución de eventos por deporte |
| `03_resultados_por_equipo.png` | Victorias, empates y derrotas del top 10 de equipos |
| `04_local_vs_visitante.png` | Marcador promedio por deporte y % de resultados |
| `05_eventos_por_competicion.png` | Distribución de registros por competición |
| `06_analisis_cuotas.png` | Histograma, boxplot y estadísticos de cuotas |
| `07_tendencia_mensual.png` | Evolución mensual de los eventos |

Todos los títulos, ejes y leyendas están en español.

### 10.2 Dashboard en Power BI

El dashboard se entrega **ya construido** como proyecto de Power BI en
`powerbi/PBIP/`. Se genera por código con `powerbi/build_pbip.py`, que escribe
un proyecto `.pbip` (formato de texto documentado por Microsoft) equivalente a
un `.pbix`:

| Elemento | Contenido |
|---|---|
| Modelo | 6 tablas, tipos y formatos, columnas técnicas ocultas, tabla `_Medidas` |
| Relaciones | 5 (una inactiva para el equipo visitante) |
| Medidas DAX | 33 |
| Informe | 3 páginas y 24 visuales |

Páginas incluidas:

1. **Resumen general**: segmentador de deporte, tarjetas de eventos, equipos y
   competiciones, margen medio, eventos por deporte, dona de resultados,
   tendencia mensual, barras por competición y tabla de equipos.
2. **Cuotas y mercado**: evolución mensual de cuotas, margen por deporte,
   favorito por competición y tarjetas de cuota mínima, máxima y del favorito.
3. **Detalle por equipo**: tabla de partidos, victorias, empates, derrotas, %
   de victorias y ranking, más tarjetas de resultados globales.

Pasos para verlo: instalar **Power BI Desktop**, abrir
`powerbi/PBIP/Dashboard_Apuestas.pbip` y pulsar **Actualizar**. El detalle está
en [`powerbi/ABRIR_EN_POWER_BI.md`](powerbi/ABRIR_EN_POWER_BI.md).

Como respaldo y como documentación del proceso, también se entregan:

- **`powerbi/GUIA_DASHBOARD.md`**: construcción manual (importación, tipos,
  relaciones, diseño de la página, segmentadores y validación).
- **`powerbi/medidas_DAX.md`**: las 33 medidas con su formato recomendado.
- **`powerbi/power_query.m`**: script opcional para conectar directo a
  `data/processed/`.

> El formato `.pbix` es propietario y solo Power BI Desktop puede escribirlo;
> por eso se entrega el `.pbip`, que se abre igual y desde **Archivo → Guardar
> como** se convierte en `.pbix`.

---

## 11. Resultados esperados y obtenidos

Se espera obtener un dataset consistente de más de 3.000 eventos, sin
duplicados por identificador, con fechas válidas, cuotas en rango y nombres de
equipos normalizados; además de un reporte que cuantifique cada corrección, un
modelo estrella listo para Power BI y un conjunto de figuras estadísticas.

Ejecución de referencia con `semilla=42`:

| Métrica | Antes | Después |
|---|---:|---:|
| Registros | 3.425 | **3.278** |
| Columnas | 11 | **30** |
| Duplicados exactos | 49 | 0 |
| Duplicados por `id_evento` | 26 | 0 |
| Fechas inválidas o nulas | 72 | 0 |
| Nombres de equipo corregidos | 1.406 | — |
| Cuotas inválidas (`<= 1,0`) | 241 | 0 |
| Cuotas atípicas (`> 50`) | 105 | 0 |
| Cuotas nulas imputadas | 510 | 0 |
| Resultados desconocidos | 62 | 60 |

Distribución final: **1.762** eventos de fútbol, **877** de baloncesto y
**639** de tenis. El dataset conserva 75 equipos/jugadores distintos (76
combinaciones equipo–deporte, porque Real Madrid y Barcelona compiten en dos
deportes).

Los resultados pueden variar ligeramente si se cambia la semilla, pero el
pipeline mantiene las mismas garantías: sin duplicados por identificador, sin
fechas inválidas, cuotas en rango y nombres normalizados.

---

## 12. Conclusiones

- Un pipeline ETL bien documentado convierte fuentes heterogéneas y sucias en
  un dataset confiable y reproducible.
- La **deduplicación por identificador conservando la fila más completa**
  evita perder información valiosa.
- El tratamiento diferenciado de nulos (eliminar, imputar o marcar) es más
  honesto que aplicar una única regla global.
- La combinación de **alias + similitud** corrige nombres sin necesidad de un
  catálogo perfecto y sin modificar nombres desconocidos de forma agresiva.
- La validación de cuotas y la imputación por mediana reducen el impacto de
  errores de captura y valores extremos.
- Un **modelo estrella simple** facilita las relaciones, los filtros y las
  medidas DAX en Power BI.
- El reporte de calidad antes/después hace auditable cada decisión y permite
  comunicar el impacto del ETL.

---

## 13. Recomendaciones

1. **Verificar la calidad de los datos** en cada carga: conteos, nulos,
   duplicados, rangos y categorías inesperadas.
2. **Usar fuentes confiables y documentadas**; registrar siempre el origen en
   `fuente_archivo`.
3. **Mantener la base actualizada** con una periodicidad definida y conservar
   históricos para comparar temporadas.
4. **Documentar cada etapa** (reglas, supuestos y umbrales) para que el proceso
   sea auditable y transferible.
5. **Diseñar visualizaciones claras**: títulos descriptivos, unidades visibles,
   colores consistentes y filtros intuitivos.
6. **Usar datos históricos o simulados con fines educativos y estadísticos**,
   evitando cualquier interpretación como recomendación de apuesta.
7. Validar el reporte de calidad después de cada ejecución y versionar los
   cambios del pipeline.
8. Si se incorporan datos reales, revisar previamente los términos de uso de la
   fuente y no automatizar scraping sin autorización.

---

## 14. Instalación y ejecución

### 14.1 Requisitos

- Python 3.10 o superior (probado con Python 3.12).
- Power BI Desktop (solo para el dashboard).

### 14.2 Windows (PowerShell)

```powershell
cd proyecto_etl_apuestas

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Pipeline completo (genera datos si no existen)
python main.py

# Regenerar datos simulados y ejecutar todo
python main.py --regenerar --semilla 42

# Pruebas
python -m pytest
```

Si PowerShell bloquea la activación del entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 14.3 macOS / Linux

```bash
cd proyecto_etl_apuestas

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python main.py --regenerar
python -m pytest
```

### 14.4 Opciones del orquestador

| Opción | Efecto |
|---|---|
| `--regenerar` | Vuelve a crear las fuentes simuladas crudas |
| `--semilla N` | Cambia la semilla (por defecto 42) |
| `--sin-graficos` | Omite las figuras de Matplotlib |
| `--sin-sqlite` | Omite la carga a SQLite |

### 14.5 Ejecutar fases por separado

```bash
python -m src.generate_sample_data --semilla 42
python -m src.extract
python -m src.transform
python -m src.load
python -m src.visualizations
```

### 14.6 Notebook

```bash
python -m pip install jupyter
jupyter notebook notebooks/analisis_exploratorio.ipynb
```

El notebook recorre el ETL paso a paso y muestra los resultados intermedios.
Ejecuta `python main.py` antes para disponer de los archivos procesados.

### 14.7 Generar el proyecto de Power BI

```powershell
# Regenera powerbi/PBIP a partir de data/processed
python powerbi/build_pbip.py

# Además valida los JSON contra los esquemas oficiales (requiere Internet)
python powerbi/build_pbip.py --validar
```

El script verifica las columnas, las relaciones y las referencias de las
medidas y los visuales antes de terminar. Después basta con abrir
`powerbi/PBIP/Dashboard_Apuestas.pbip` y pulsar **Actualizar**.

---

## 15. Cómo abrir los resultados en Power BI

### 15.1 Opción rápida (dashboard ya construido)

1. Instala **Power BI Desktop**
   (<https://powerbi.microsoft.com/desktop/>).
2. Abre `powerbi/PBIP/Dashboard_Apuestas.pbip` con doble clic.
3. Pulsa **Inicio → Actualizar** para cargar los datos de `data/processed/`.
4. Recorre las tres páginas: **Resumen general**, **Cuotas y mercado** y
   **Detalle por equipo**.
5. Si necesitas el archivo clásico: **Archivo → Guardar como → Power BI
   (.pbix)** y guárdalo como `powerbi/dashboard_apuestas.pbix`.

> La guía completa, la ruta del parámetro `RutaDatos` y la solución de
> problemas están en
> [`powerbi/ABRIR_EN_POWER_BI.md`](powerbi/ABRIR_EN_POWER_BI.md).

### 15.2 Opción manual (para la sustentación paso a paso)

1. Abre Power BI Desktop.
2. **Inicio → Obtener datos → Texto/CSV** e importa
   `data/processed/fact_eventos.csv`.
3. Repite con `dim_equipos.csv`, `dim_deportes.csv`, `dim_competiciones.csv` y
   `dim_fecha.csv`.
4. En Power Query, comprueba que:
   - `fecha_evento` y `fecha` sean **Fecha**.
   - `cuota_*`, `prob_implicita_*` y `margen_mercado` sean **Número decimal**.
   - `id_*` sean **Texto**.
5. Crea las relaciones del modelo estrella descritas en
   `powerbi/GUIA_DASHBOARD.md`.
6. Copia las medidas de `powerbi/medidas_DAX.md`.
7. Arma la página siguiendo la especificación de visuales de la guía.
8. Guarda el archivo como `dashboard_apuestas.pbix`.

> La guía incluye una tabla de comprobación para verificar que los totales del
> dashboard coincidan con el reporte de calidad (3.278 eventos con semilla 42).

---

## 16. Reproducibilidad

- Semilla fija `42` en `src/generate_sample_data.py`.
- Fechas y orden de duplicados deterministas.
- Funciones puras sobre copias del DataFrame (no hay efectos ocultos).
- Rutas construidas con `pathlib` a partir de la raíz del proyecto; no hay
  rutas absolutas en el código.
- Logging a consola y a `reports/logs/pipeline.log`.

Para reproducir exactamente los resultados:

```bash
python main.py --regenerar --semilla 42
```

---

## 17. Limitaciones

- Los datos son **simulados**; las conclusiones estadísticas describen el
  dataset generado, no la realidad deportiva.
- La corrección por similitud puede fallar con nombres muy cortos o muy
  parecidos entre sí; el umbral y los alias son configurables en
  `src/config.py`.
- El modelo estrella es intencionalmente simple y no incluye dimensiones de
  jugadores, entrenadores ni estadísticas detalladas por evento.
- Power BI: se entrega el proyecto `.pbip` ya generado y validado, además de la
  guía manual. El archivo `.pbix` final se obtiene con **Archivo → Guardar
  como**, porque el formato `.pbix` es propietario y solo Power BI Desktop
  puede escribirlo.

---

## 18. Aclaración final

Este proyecto es **académico y analítico**. Los datos son históricos
simulados, no provienen de apuestas reales y no se realizó scraping de casas de
apuestas. El objetivo es demostrar competencias de ingeniería de datos:
extracción, limpieza, validación, modelado y visualización.

**No promueve, recomienda ni facilita las apuestas reales.**
