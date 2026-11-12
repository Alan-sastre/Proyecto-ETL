# Cómo abrir el dashboard ya construido en Power BI

Este documento explica cómo abrir el dashboard **sin tener que armarlo a mano**.
El proyecto de Power BI se genera por código en `powerbi/PBIP/` e incluye el
modelo estrella, las relaciones, las 33 medidas DAX y las tres páginas con sus
24 visuales.

> **Resumen en tres pasos:** instalar Power BI Desktop → abrir
> `powerbi/PBIP/Dashboard_Apuestas.pbip` → pulsar **Actualizar**.

---

## 1. ¿Por qué un `.pbip` y no un `.pbix`?

El formato `.pbix` es propietario y solo Power BI Desktop puede escribirlo, por
lo que no se puede fabricar desde Python. El formato **`.pbip`** (Power BI
Project) sí es texto plano y está documentado por Microsoft: contiene la misma
información que un `.pbix` (modelo + informe) repartida en archivos JSON y TMSL.

Al abrir un `.pbip` en Power BI Desktop se obtiene exactamente el mismo
resultado que con un `.pbix`, y desde **Archivo → Guardar como** se puede
exportar a `.pbix` si la entrega lo exige.

---

## 2. Requisitos

| Requisito | Detalle |
|---|---|
| Power BI Desktop | Versión de 2024 o posterior (descarga gratuita en <https://powerbi.microsoft.com/desktop/>) |
| Windows | 10 u 11 (Power BI Desktop solo existe para Windows) |
| Datos del ETL | La carpeta `data/processed/` con los CSV generados por `python main.py` |

No hace falta activar ninguna vista previa: el formato PBIR y los proyectos
`.pbip` son características estables de Power BI Desktop.

---

## 3. Pasos detallados

1. **Genera los datos** (solo si aún no existen):

   ```powershell
   python main.py --regenerar --semilla 42
   ```

2. **Abre el proyecto** con doble clic sobre
   `powerbi/PBIP/Dashboard_Apuestas.pbip`, o desde Power BI Desktop:
   **Archivo → Abrir** y selecciona ese archivo.

3. Power BI carga el modelo y el informe. Si muestra las tarjetas vacías,
   pulsa **Inicio → Actualizar**: al abrir un `.pbip` sin caché, el modelo
   trae la estructura pero no los datos hasta la primera actualización.

4. Revisa las tres páginas:

   | Página | Contenido |
   |---|---|
   | **Resumen general** | Segmentador de deporte, 4 tarjetas (eventos, equipos, competiciones, margen), eventos por deporte, dona de resultados, tendencia mensual, barras por competición y tabla de equipos |
   | **Cuotas y mercado** | Evolución mensual de cuotas, margen por deporte, favorito por competición y tarjetas de cuota mínima, máxima y del favorito |
   | **Detalle por equipo** | Tabla con partidos, victorias, empates, derrotas, % de victorias y ranking, más tarjetas de resultados globales |

5. **Guarda una copia en `.pbix`** (opcional pero recomendado para entregar):
   **Archivo → Guardar como → Power BI (.pbix)**. Guárdalo como
   `powerbi/dashboard_apuestas.pbix`.

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

---

## 5. Ruta de los datos

Las consultas leen los CSV a través del parámetro **`RutaDatos`**, que se
genera con la ruta absoluta de `data/processed` en el equipo donde se ejecutó
`build_pbip.py`.

Si mueves el proyecto a otro equipo o carpeta:

1. **Inicio → Transformar datos → Transformar datos**.
2. Selecciona la consulta **`RutaDatos`**.
3. Escribe la ruta nueva (sin barra final), por ejemplo
   `C:\Users\tu.usuario\Desktop\proyecto_etl_apuestas\data\processed`.
4. **Inicio → Cerrar y aplicar** y luego **Actualizar**.

También puedes cambiar la ruta y volver a generar el proyecto:

```powershell
python powerbi/build_pbip.py
```

---

## 6. Regenerar o personalizar el dashboard

El proyecto completo se reconstruye desde el script `powerbi/build_pbip.py`:

```powershell
# Generar el proyecto (sobrescribe powerbi/PBIP)
python powerbi/build_pbip.py

# Generar y validar los JSON contra los esquemas oficiales de Microsoft
python powerbi/build_pbip.py --validar
```

El script no usa rutas absolutas en el código (las calcula con `pathlib` a
partir de la raíz del proyecto), escribe JSON con formato legible y, antes de
terminar, comprueba que:

- las columnas del modelo coinciden exactamente con las de los CSV;
- las relaciones apuntan a columnas existentes;
- las medidas no referencian tablas, columnas ni medidas inexistentes;
- los visuales usan campos que existen en el modelo.

Las páginas, visuales y medidas están declarados en las listas `PAGINAS` y
`MEDIDAS` del propio script: para añadir una tarjeta o un gráfico basta con
agregar una entrada y volver a ejecutarlo.

`--validar` requiere el paquete `jsonschema` (incluido en `requirements.txt`) y
conexión a Internet, porque descarga los esquemas públicos de Microsoft.

---

## 7. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Las tarjetas aparecen vacías | El modelo se abrió sin datos (no hay caché) | **Inicio → Actualizar** |
| Error «No se encuentra el archivo» al actualizar | La carpeta del proyecto cambió de ubicación | Actualizar el parámetro `RutaDatos` (sección 5) |
| Power BI avisa de que la versión es antigua | Desktop anterior a 2024 | Actualizar Power BI Desktop |
| Falta una medida o un visual | Se editó el `.pbip` a mano | Volver a ejecutar `python powerbi/build_pbip.py` |
| Los acentos se ven raros | El CSV se guardó con otra codificación | Regenerar con `python main.py --regenerar --semilla 42` |
| Se pide una vista previa | Versión muy antigua de Desktop | Actualizar Desktop; en versiones recientes no hace falta |

---

## 8. Alternativa manual

Si prefieres construir el dashboard paso a paso (por ejemplo, para la
sustentación del proyecto), la guía detallada sigue disponible en
[`GUIA_DASHBOARD.md`](GUIA_DASHBOARD.md) y las medidas en
[`medidas_DAX.md`](medidas_DAX.md). El proyecto `.pbip` es simplemente esa
misma guía ya ejecutada.

---

## 9. Publicación (opcional)

Con el `.pbix` guardado:

1. **Archivo → Publicar → Mi área de trabajo**.
2. En el servicio, crea el panel fijando los visuales del informe.
3. Configura la actualización si publicas el modelo en un área de trabajo con
   puerta de enlace.

Para un proyecto académico no es necesario: basta con el `.pbix` y las capturas
de pantalla de las tres páginas.
