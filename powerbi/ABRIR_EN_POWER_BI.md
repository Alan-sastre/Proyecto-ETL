# Cómo abrir el dashboard ya construido en Power BI

Este documento explica cómo abrir el dashboard **sin tener que armarlo a mano**.
El proyecto de Power BI se genera por código en `powerbi/PBIP/` e incluye el
modelo estrella, las relaciones, las 33 medidas DAX y las tres páginas con sus
24 visuales.

> **Resumen en tres pasos:** instalar Power BI Desktop → abrir
> `powerbi/PBIP/Dashboard_Apuestas.pbip` → pulsar **Actualizar**.

> **¿Quieres subirlo al servicio de Power BI?** El servicio **no acepta
> `.pbip`**. Abre el proyecto en Desktop, guárdalo como `.pbix` y publícalo.
> El paso a paso está en [`SUBIR_A_POWER_BI.md`](SUBIR_A_POWER_BI.md).

---

## 1. ¿Por qué un `.pbip` y no un `.pbix`?

El formato `.pbix` es propietario y solo Power BI Desktop puede escribirlo, por
lo que no se puede fabricar desde Python. El formato **`.pbip`** (Power BI
Project) sí es texto plano y está documentado por Microsoft: contiene la misma
información que un `.pbix` (modelo + informe) repartida en archivos JSON y TMSL.

Al abrir un `.pbip` en Power BI Desktop se obtiene exactamente el mismo
resultado que con un `.pbix`, y desde **Archivo → Guardar como** se puede
exportar a `.pbix` si la entrega lo exige o si quieres subirlo al servicio.

> **Importante:** `app.powerbi.com` no admite `.pbip` en **Cargar un archivo**.
> Para publicar hay que convertirlo antes a `.pbix` o subir los datos en Excel
> o CSV. Consulta [`SUBIR_A_POWER_BI.md`](SUBIR_A_POWER_BI.md).

---

## 2. Requisitos

| Requisito | Detalle |
|---|---|
| Power BI Desktop | Versión de 2024 o posterior (descarga gratuita en <https://powerbi.microsoft.com/desktop/>) |
| Windows | 10 u 11 (Power BI Desktop solo existe para Windows) |
| Datos | **No hacen falta**: el `.pbip` generado lleva los 3.278 eventos incrustados en el modelo |

No hace falta activar ninguna vista previa: el formato PBIR y los proyectos
`.pbip` son características estables de Power BI Desktop.

---

## 3. Pasos detallados

1. **Genera los datos** (solo si vas a regenerar el proyecto):

   ```powershell
   python main.py --regenerar --semilla 42
   python powerbi/build_pbip.py
   ```

   Si acabas de clonar el repositorio, el `.pbip` ya está generado y este paso
   no es necesario.

2. **Abre el proyecto** con doble clic sobre
   `powerbi/PBIP/Dashboard_Apuestas.pbip`, o desde Power BI Desktop:
   **Archivo → Abrir** y selecciona ese archivo.

3. Power BI carga el modelo y el informe. Pulsa **Inicio → Actualizar**: al
   abrir un `.pbip` sin caché, el modelo ejecuta las consultas M. Como los datos
   van incrustados en el propio proyecto, no pedirá rutas ni credenciales.

4. Revisa las tres páginas:

   | Página | Contenido |
   |---|---|
   | **Resumen general** | Segmentador de deporte, 4 tarjetas (eventos, equipos, competiciones, margen), eventos por deporte, dona de resultados, tendencia mensual, barras por competición y tabla de equipos |
   | **Cuotas y mercado** | Evolución mensual de cuotas, margen por deporte, favorito por competición y tarjetas de cuota mínima, máxima y del favorito |
   | **Detalle por equipo** | Tabla con partidos, victorias, empates, derrotas, % de victorias y ranking, más tarjetas de resultados globales |

5. **Guarda una copia en `.pbix`** (necesario para subirlo al servicio):
   **Archivo → Guardar como → Power BI (.pbix)**. Guárdalo como
   `powerbi/dashboard_apuestas.pbix`.
6. **Para publicarlo**, pulsa **Inicio → Publicar** y elige el área de trabajo.
   El proceso completo está en [`SUBIR_A_POWER_BI.md`](SUBIR_A_POWER_BI.md).

---

## 4. Qué contiene el proyecto

```text
powerbi/PBIP/
├── Dashboard_Apuestas.pbip              # Punto de entrada
├── LEEME - COMO ABRIR.txt
├── Dashboard_Apuestas.SemanticModel/
│   ├── .platform
│   ├── definition.pbism
│   └── model.bim                        # Modelo TMSL: tablas, tipos, medidas y relaciones
└── Dashboard_Apuestas.Report/
    ├── .platform
    ├── definition.pbir                  # Referencia al modelo (byPath)
    └── definition/
        ├── version.json
        ├── report.json
        └── pages/
            ├── pages.json
            ├── pResumen/                # page.json + visuals/<visual>/visual.json
            ├── pCuotas/
            └── pEquipos/
```

| Elemento | Cantidad |
|---|---:|
| Tablas del modelo | 6 (5 de datos + `_Medidas`) |
| Relaciones | 5 (una inactiva para el equipo visitante) |
| Medidas DAX | 33 |
| Páginas | 3 |
| Visuales | 24 |
| Filas del hecho | 3.278 |

El modelo ya trae los tipos de datos, los formatos (porcentajes con un decimal,
cuotas con dos decimales, fechas `dd/MM/yyyy`), las columnas técnicas ocultas,
`nombre_mes` ordenado por `mes` y la tabla `_Medidas` para agrupar los cálculos.
Los 3.278 eventos y las cuatro dimensiones están **incrustados** en las
particiones M de `model.bim`; no hay rutas externas.

Fuera de la carpeta `PBIP/`, el generador también escribe
`powerbi/datos_powerbi.xlsx` con una hoja por tabla, listo para subir al
servicio de Power BI.

---

## 5. Ruta de los datos

Por defecto **no hay ninguna ruta**: `build_pbip.py` incrusta los 3.278 eventos
y las cuatro dimensiones como tablas M dentro de `model.bim`. Por eso el
proyecto funciona aunque se mueva de carpeta, se copie a un USB o se abra en
otro equipo.

Si necesitas que el modelo se actualice desde los CSV (por ejemplo, mientras
trabajas en el ETL), genera el proyecto en modo conectado:

```powershell
python powerbi/build_pbip.py --usar-csv
```

Ese modo crea el parámetro **`RutaDatos`** con la ruta de `data/processed` en el
equipo donde se ejecuta el script. Para cambiarla:

1. **Inicio → Transformar datos → Transformar datos**.
2. Selecciona la consulta **`RutaDatos`**.
3. Escribe la ruta nueva (sin barra final), por ejemplo
   `C:\Users\tu.usuario\Desktop\proyecto_etl_apuestas\data\processed`.
4. **Inicio → Cerrar y aplicar** y luego **Actualizar**.

También puedes indicar otra carpeta directamente:

```powershell
python powerbi/build_pbip.py --ruta-datos "C:\datos\processed"
```

> Para entregar o subir a Power BI vuelve a generar el proyecto **sin**
> `--usar-csv`: el modo incrustado no necesita puerta de enlace ni rutas.

---

## 6. Regenerar o personalizar el dashboard

El proyecto completo se reconstruye desde el script `powerbi/build_pbip.py`:

```powershell
# Generar el proyecto autocontenido + powerbi/datos_powerbi.xlsx
python powerbi/build_pbip.py

# Generar y validar los JSON contra los esquemas oficiales de Microsoft
python powerbi/build_pbip.py --validar

# Modo conectado a los CSV (para seguir trabajando con el ETL)
python powerbi/build_pbip.py --usar-csv
```

El script calcula las rutas del repositorio con `pathlib`, escribe JSON con
formato legible y, antes de terminar, comprueba que:

- las columnas del modelo coinciden exactamente con las de los CSV;
- en el modo incrustado no queda ninguna referencia a `File.Contents` ni a
  `RutaDatos`, y el número de filas incrustadas coincide con el CSV;
- las relaciones apuntan a columnas existentes;
- las medidas no referencian tablas, columnas ni medidas inexistentes;
- los visuales usan campos que existen en el modelo.

Además genera `powerbi/datos_powerbi.xlsx`, un libro con una hoja por tabla
listo para subir al servicio de Power BI. Puedes omitirlo con `--sin-excel`.

Las páginas, visuales y medidas están declarados en las listas `PAGINAS` y
`MEDIDAS` del propio script: para añadir una tarjeta o un gráfico basta con
agregar una entrada y volver a ejecutarlo.

`--validar` requiere el paquete `jsonschema` (incluido en `requirements.txt`) y
conexión a Internet, porque descarga los esquemas públicos de Microsoft.

---

## 7. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Las tarjetas aparecen vacías | El modelo se abrió sin ejecutar las consultas | **Inicio → Actualizar** |
| Error «No se encuentra el archivo» al actualizar | Generaste el proyecto con `--usar-csv` y moviste la carpeta | Vuelve a generar sin `--usar-csv`, o actualiza `RutaDatos` (sección 5) |
| El servicio no acepta el archivo al subirlo | Estás subiendo un `.pbip` | Guarda como `.pbix` y publica (sección 9) |
| Power BI avisa de que la versión es antigua | Desktop anterior a 2024 | Actualizar Power BI Desktop |
| Falta una medida o un visual | Se editó el `.pbip` a mano | Volver a ejecutar `python powerbi/build_pbip.py` |
| Los acentos se ven raros | El CSV se guardó con otra codificación | Regenerar con `python main.py --regenerar --semilla 42` |
| Se pide una vista previa | Versión muy antigua de Desktop | Actualizar Desktop; en versiones recientes no hace falta |
| Error al publicar por licencia | Área de trabajo compartida sin Pro/PPU | Publica en **Mi área de trabajo** o pide licencia |

---

## 8. Alternativa manual

Si prefieres construir el dashboard paso a paso (por ejemplo, para la
sustentación del proyecto), la guía detallada sigue disponible en
[`GUIA_DASHBOARD.md`](GUIA_DASHBOARD.md) y las medidas en
[`medidas_DAX.md`](medidas_DAX.md). El proyecto `.pbip` es simplemente esa
misma guía ya ejecutada.

---

## 9. Publicación en el servicio de Power BI

El servicio **no acepta `.pbip`**: hay que guardar primero una copia en `.pbix`.

1. **Archivo → Guardar como → Power BI (.pbix)** y guarda
   `powerbi/dashboard_apuestas.pbix`.
2. **Inicio → Publicar** y elige **Mi área de trabajo** o el área de trabajo de
   destino.
3. En <https://app.powerbi.com>, abre el informe publicado y fija los visuales
   en un panel si lo necesitas.

También puedes subir directamente el `.pbix` desde el servicio
(**Nuevo → Cargar un archivo**) o crear un conjunto de datos con
`powerbi/datos_powerbi.xlsx`. El paso a paso completo, las alternativas con
Excel/CSV y la solución de errores están en
[`SUBIR_A_POWER_BI.md`](SUBIR_A_POWER_BI.md).

Para un proyecto académico basta con el `.pbix`, el informe publicado y las
capturas de pantalla de las tres páginas.
