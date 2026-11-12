# Guía para construir el dashboard en Power BI

> **¿Solo necesitas abrir el dashboard?** El proyecto ya está generado en
> `powerbi/PBIP/`. Abre `Dashboard_Apuestas.pbip` con Power BI Desktop y pulsa
> **Actualizar**; no hay que crear nada a mano. Instrucciones completas en
> [`ABRIR_EN_POWER_BI.md`](ABRIR_EN_POWER_BI.md). Esta guía queda como
> alternativa manual y como documentación del paso a paso.

Esta guía permite armar el dashboard del proyecto en **Power BI Desktop** a
partir de los CSV generados por el ETL. No requiere escribir código M salvo que
se quiera automatizar la actualización.

**Archivos de entrada** (en `data/processed/`):

| Archivo | Tabla sugerida | Filas aprox. |
|---|---|---:|
| `fact_eventos.csv` | `fact_eventos` | 3.278 |
| `dim_equipos.csv` | `dim_equipos` | 76 |
| `dim_deportes.csv` | `dim_deportes` | 3 |
| `dim_competiciones.csv` | `dim_competiciones` | 33 |
| `dim_fecha.csv` | `dim_fecha` | 1.305 |

Los conteos corresponden a la semilla 42. Si se regeneran los datos, pueden
cambiar ligeramente.

---

## 1. Requisitos previos

1. Haber ejecutado el pipeline:

   ```powershell
   python main.py --regenerar
   ```

2. Verificar que existan los archivos en `data/processed/`.
3. Abrir **Power BI Desktop** (versión reciente, idealmente en español).

---

## 2. Importar los datos

### 2.1 Importar cada CSV

Para cada archivo:

1. **Inicio → Obtener datos → Texto/CSV**.
2. Seleccionar el archivo.
3. En el cuadro de vista previa, confirmar:
   - **Origen del archivo:** UTF-8.
   - **Delimitador:** coma.
   - **Primera fila como encabezado:** sí.
4. Pulsar **Transformar datos** (no "Cargar" todavía) para revisar los tipos.

### 2.2 Tipos de datos recomendados

| Tabla | Columna | Tipo |
|---|---|---|
| `fact_eventos` | `id_evento`, `id_fecha`, `id_deporte`, `id_competicion`, `id_equipo_local`, `id_equipo_visitante` | Texto |
| `fact_eventos` | `fecha_evento` | Fecha |
| `fact_eventos` | `resultado_normalizado`, `favorito`, `fuente_archivo` | Texto |
| `fact_eventos` | `marcador_local`, `marcador_visitante`, `goles_*`, `puntos_*`, `diferencia_marcador` | Número entero |
| `fact_eventos` | `cuota_*`, `cuota_favorita`, `prob_implicita_*`, `margen_mercado` | Número decimal |
| `dim_equipos` | `id_equipo`, `equipo`, `deporte` | Texto |
| `dim_equipos` | `partidos`, `victorias`, `empates`, `derrotas` | Número entero |
| `dim_equipos` | `tasa_victoria` | Número decimal |
| `dim_deportes` | `id_deporte`, `deporte` | Texto |
| `dim_deportes` | `n_eventos` | Número entero |
| `dim_competiciones` | `id_competicion`, `competicion`, `deporte` | Texto |
| `dim_competiciones` | `n_eventos` | Número entero |
| `dim_fecha` | `id_fecha`, `trimestre`, `nombre_mes`, `dia_semana` | Texto |
| `dim_fecha` | `fecha` | Fecha |
| `dim_fecha` | `año`, `mes`, `semana_iso`, `dia` | Número entero |
| `dim_fecha` | `es_fin_semana` | Verdadero/Falso |

> **Importante:** si el sistema está en español, Power BI puede interpretar mal
> los decimales. En Power Query usa **Transformar → Tipo de uso → Decimal** o
> cambia la configuración regional del archivo a **Español (España)**. Los CSV
> se generaron con punto decimal en las columnas numéricas y coma como
> separador de campos, por lo que la detección automática suele funcionar.

### 2.3 Marcar la tabla de fechas

1. Ir a la vista **Modelo** o **Datos**.
2. Seleccionar `dim_fecha`.
3. **Herramientas de tabla → Marcar como tabla de fechas**.
4. Elegir la columna `fecha`.

Esto habilita inteligencia de tiempo (`DATESINPERIOD`, `SAMEPERIODLASTYEAR`,
etc.).

### 2.4 Opcional: cargar desde SQLite

Si se prefiere la base `data/processed/apuestas.db`:

1. Instalar un controlador ODBC de SQLite.
2. **Obtener datos → ODBC** y apuntar al archivo.
3. Importar las cinco tablas.

Para este proyecto se recomienda **CSV**, porque evita dependencias y es más
sencillo de compartir.

---

## 3. Crear el modelo estrella

En la vista **Modelo**, arrastrar las claves para crear estas relaciones:

| Desde (muchos) | Hacia (uno) | Cardinalidad | Dirección | Activa |
|---|---|---|---|---|
| `fact_eventos[id_deporte]` | `dim_deportes[id_deporte]` | * a 1 | Única | Sí |
| `fact_eventos[id_competicion]` | `dim_competiciones[id_competicion]` | * a 1 | Única | Sí |
| `fact_eventos[id_fecha]` | `dim_fecha[id_fecha]` | * a 1 | Única | Sí |
| `fact_eventos[id_equipo_local]` | `dim_equipos[id_equipo]` | * a 1 | Única | **Sí** |
| `fact_eventos[id_equipo_visitante]` | `dim_equipos[id_equipo]` | * a 1 | Única | **No** |

Notas:

- La relación con `dim_equipos` se crea dos veces. Power BI solo permite una
  activa: dejar activa la de **equipo local**. La de visitante se activa en las
  medidas con `USERELATIONSHIP`.
- Si se relaciona por `fecha_evento` ↔ `fecha` (ambas tipo Fecha), funciona
  igual que por `id_fecha`. Usar una sola de las dos para evitar ambigüedad.
- `dim_equipos` tiene una fila por combinación **equipo + deporte**. Para
  analizar por equipo sin mezclar deportes, usar `dim_equipos[equipo]` junto a
  `dim_equipos[deporte]` o el `id_equipo`.
- Los eventos con equipo "Desconocido" no están en `dim_equipos`; la tabla de
  hechos conserva su clave vacía y aparecen como **En blanco** en la matriz.

### 3.1 Ordenar columnas descriptivas

- `dim_fecha[nombre_mes]` → **Ordenar por columna** → `mes`.
- `dim_fecha[dia_semana]` → **Ordenar por columna** → `dia` (o crear una
  columna numérica de día de semana si se requiere orden lunes→domingo).
- `dim_competiciones[competicion]` puede ordenarse por `n_eventos` si se desea.

### 3.2 Ocultar columnas técnicas

En la vista **Modelo**, ocultar de la vista de informe las claves foráneas
(`id_*`) y `id_fecha`, para que el panel de campos quede limpio. No borrarlas:
son necesarias para las relaciones.

---

## 4. Medidas DAX

Copiar las medidas de `powerbi/medidas_DAX.md` en una tabla de medidas:

1. **Inicio → Introducir datos** → crear una tabla vacía llamada `_Medidas`.
2. Con la tabla seleccionada, **Nueva medida** y pegar cada definición.
3. Asignar formato: porcentajes a 1 decimal, cuotas a 2 decimales, conteos
   como número entero.

Medidas mínimas para el dashboard:

- `Total Eventos`
- `Victorias Local`, `Victorias Visitante`, `Empates`
- `% Victorias Local`, `% Victorias Visitante`, `% Empates`
- `Promedio Cuota Local`, `Cuota Mínima`, `Cuota Máxima`, `Mediana Cuota Local`
- `Partidos Totales Equipo`, `Victorias Equipo`, `% Victorias Equipo`
- `Eventos Últimos 12 Meses`

---

## 5. Diseño de la página

Configurar el lienzo en **16:9** (1280 × 720) y usar el tema de colores del
proyecto:

| Uso | Color |
|---|---|
| Principal | `#1F4E79` |
| Secundario | `#2E75B6` |
| Apoyo claro | `#9DC3E6` |
| Visitante / alerta | `#C55A11` |
| Éxito | `#548235` |
| Empate / neutro | `#A6A6A6` |
| Fondo | `#FFFFFF` |

### 5.1 Distribución sugerida

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ TÍTULO: "Análisis de eventos deportivos"                                 │
│ Segmentadores: Deporte | Competición | Fecha (entre)                     │
├───────────────┬───────────────┬───────────────┬─────────────────────────┤
│ Total eventos │ % Local       │ % Empate      │ % Visitante             │
│ (tarjeta)     │ (tarjeta)     │ (tarjeta)     │ (tarjeta)               │
├───────────────┴───────────────┴───────────────┴─────────────────────────┤
│ Eventos por deporte (barras)  │ Análisis de cuotas (histograma/barras)  │
├───────────────────────────────┼─────────────────────────────────────────┤
│ Resultados por equipo (matriz)│ Distribución por competición (dona)     │
├───────────────────────────────┴─────────────────────────────────────────┤
│ Comparación local vs. visitante (barras agrupadas)                      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Especificación de cada visual

#### Visual 1 — Tarjeta: total de eventos

| Propiedad | Valor |
|---|---|
| Tipo | Tarjeta |
| Campo | `Total Eventos` |
| Título | "Eventos registrados" |
| Formato | Número entero con separador de miles |
| Tamaño | 200 × 110 px |

#### Visual 2 — Barras: eventos por deporte

| Propiedad | Valor |
|---|---|
| Tipo | Gráfico de barras agrupadas |
| Eje Y | `dim_deportes[deporte]` |
| Eje X | `Total Eventos` |
| Etiquetas de datos | Activadas |
| Título | "Distribución de eventos por deporte" |
| Color | `#2E75B6` |
| Orden | Descendente por total |

Alternativa: gráfico de dona con `% del Total` y leyenda por deporte.

#### Visual 3 — Matriz: resultados históricos por equipo

| Propiedad | Valor |
|---|---|
| Tipo | Matriz |
| Filas | `dim_equipos[equipo]`, `dim_equipos[deporte]` |
| Valores | `Partidos Totales Equipo`, `Victorias Equipo`, `Empates Equipo`, `% Victorias Equipo` |
| Filtro de visual | Top N = 10 por `Partidos Totales Equipo` |
| Título | "Resultados históricos por equipo (top 10)" |
| Formato condicional | Escala de color en `% Victorias Equipo` |

#### Visual 4 — Comparación local vs. visitante

| Propiedad | Valor |
|---|---|
| Tipo | Gráfico de barras agrupadas (o columnas agrupadas) |
| Eje X | `dim_deportes[deporte]` |
| Valores | `Victorias Local`, `Empates`, `Victorias Visitante` |
| Colores | Local `#2E75B6`, Empate `#A6A6A6`, Visitante `#C55A11` |
| Título | "Resultados: local vs. visitante" |
| Etiquetas | Activadas |

Complemento recomendado: tarjetas con `Promedio Goles Local` y
`Promedio Goles Visitante` filtradas a fútbol.

#### Visual 5 — Distribución por competición

| Propiedad | Valor |
|---|---|
| Tipo | Dona (o barras horizontales si hay muchas categorías) |
| Leyenda | `dim_competiciones[competicion]` |
| Valores | `Total Eventos` |
| Título | "Eventos por competición" |
| Etiquetas | Porcentaje y categoría |
| Filtro | Top 10 por total, para evitar saturación |

#### Visual 6 — Análisis descriptivo de cuotas

| Propiedad | Valor |
|---|---|
| Tipo | Gráfico de columnas (histograma) + tarjetas de estadísticos |
| Eje X | `fact_eventos[Rango Cuota]` (columna calculada, ver abajo) |
| Eje Y | `Total Eventos` |
| Título | "Distribución de la cuota local" |
| Tarjetas | `Promedio Cuota Local`, `Mediana Cuota Local`, `Cuota Mínima`, `Cuota Máxima` |

Columna calculada opcional para el histograma:

```dax
Rango Cuota =
VAR c = fact_eventos[cuota_local]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( c ), "Sin dato",
        c < 1.5, "1,0 – 1,5",
        c < 2.0, "1,5 – 2,0",
        c < 3.0, "2,0 – 3,0",
        c < 4.0, "3,0 – 4,0",
        c < 5.0, "4,0 – 5,0",
        "5,0 o más"
    )
```

Para un boxplot real se puede instalar el visual personalizado **Box and
Whisker** (Microsoft) o usar las medidas `Percentil 25`, `Mediana Cuota Local` y
`Percentil 75` en un gráfico de barras con barras de error.

#### Visual 7 — Tendencia mensual (opcional)

| Propiedad | Valor |
|---|---|
| Tipo | Gráfico de líneas |
| Eje X | `dim_fecha[fecha]` (jerarquía año-mes) |
| Eje Y | `Total Eventos` |
| Título | "Evolución mensual de eventos" |
| Línea | `#1F4E79`, con marcadores |

#### Segmentadores

| Segmentador | Campo | Estilo |
|---|---|---|
| Deporte | `dim_deportes[deporte]` | Lista desplegable |
| Competición | `dim_competiciones[competicion]` | Lista con búsqueda |
| Fecha | `dim_fecha[fecha]` | Entre (rango de fechas) |
| Resultado (opcional) | `fact_eventos[resultado_normalizado]` | Botones |

Agregar un botón **"Limpiar filtros"** con la acción *Marcador → Restablecer
todos los filtros*.

---

## 6. Formato y estilo

1. **Título de la página:** "Análisis de datos de apuestas deportivas
   (simulados)".
2. **Subtítulo:** "Proyecto ETL académico — 3.278 eventos".
3. Fondo blanco, tarjetas con borde redondeado de 8 px y sombra suave.
4. Tipografía **Segoe UI**, títulos en 14–16 pt y etiquetas en 10–11 pt.
5. Habilitar **Información sobre herramientas** con `Total Eventos`,
   `Promedio Cuota Local` y `% Victorias Local`.
6. Revisar que los porcentajes se muestren con coma decimal si el informe está
   en español.

---

## 7. Actualización de datos

### Opción A — Ruta fija

1. **Inicio → Actualizar**. Power BI usará la ruta original del CSV.
2. Si el proyecto se mueve de carpeta, ir a **Transformar datos → Configuración
   del origen de datos** y actualizar la ruta.

### Opción B — Parámetro de ruta (recomendado)

1. **Inicio → Administrar parámetros → Nuevo parámetro**.
2. Nombre: `RutaDatos`, tipo Texto, valor actual:
   `C:\ruta\al\proyecto\proyecto_etl_apuestas\data\processed`.
3. En Power Query, reemplazar la ruta de cada consulta por `RutaDatos`.
4. Al mover el proyecto, basta cambiar el parámetro.

### Opción C — Script de Power Query

El archivo `powerbi/power_query.m` contiene una consulta lista para conectar a
`data/processed/eventos_limpios.csv` con tipos explícitos. También incluye una
variante para combinar todos los CSV de la carpeta.

---

## 8. Validación del dashboard

Antes de entregar, comprobar:

- [ ] `Total Eventos` = **3.278** con todos los filtros limpios.
- [ ] La suma de eventos por deporte coincide con las tarjetas: fútbol 1.762,
      baloncesto 877, tenis 639.
- [ ] `Victorias Local + Empates + Victorias Visitante` = `Total Eventos`
      (incluye 60 resultados desconocidos; ajustar la comprobación o filtrarlos).
- [ ] Las cuotas mínimas son mayores que 1,0 y las máximas no superan 50.
- [ ] `dim_fecha` está marcada como tabla de fechas.
- [ ] La relación de equipo visitante está inactiva y las medidas usan
      `USERELATIONSHIP`.
- [ ] Los segmentadores filtran todos los visuales de la página.
- [ ] Los títulos, unidades y leyendas están en español.
- [ ] El archivo `.pbix` se guarda dentro del proyecto (`powerbi/`).

> Los 60 resultados "Desconocido" corresponden a eventos cuyo marcador faltaba
> en la fuente. Se conservan para no perder el evento, pero se excluyen de los
> porcentajes de resultado si se filtra `resultado_normalizado <> "Desconocido"`.

---

## 9. Solución de problemas

| Problema | Solución |
|---|---|
| Los acentos se ven mal | Importar con codificación **UTF-8**; los CSV usan BOM |
| Las cuotas aparecen como texto | Cambiar el tipo a **Número decimal** en Power Query |
| Las fechas se interpretan como texto | Configurar la referencia cultural **Español (España)** y tipo **Fecha** |
| Solo se puede crear una relación activa con equipos | Es lo esperado; usar `USERELATIONSHIP` para visitante |
| Los totales no coinciden | Revisar filtros de página/visual y que no haya duplicados en dimensiones |
| Power BI no encuentra los CSV | Actualizar la ruta o usar el parámetro `RutaDatos` |
| El histograma no aparece | Usar la columna calculada `Rango Cuota` o instalar el visual de histograma |

---

## 10. Publicación (opcional)

1. Guardar como `powerbi/dashboard_apuestas.pbix`.
2. **Publicar** en un área de trabajo de Power BI Service.
3. Configurar la puerta de enlace si los CSV están en un equipo local.
4. Programar la actualización si se ejecuta el ETL periódicamente.

> Recordatorio académico: el dashboard muestra datos simulados con fines
> educativos y no constituye una herramienta de apuestas.
