# Medidas DAX para el dashboard

Todas las medidas suponen que las tablas se llaman **`fact_eventos`**,
**`dim_equipos`**, **`dim_deportes`**, **`dim_competiciones`** y
**`dim_fecha`**, y que se crearon las relaciones de
`powerbi/GUIA_DASHBOARD.md`.

Se recomienda crear una tabla vacía llamada **`_Medidas`** y agregar allí todas
las medidas para mantener el modelo ordenado.

---

## 1. Medidas base

```dax
Total Eventos = COUNTROWS ( fact_eventos )
```

```dax
Eventos con Resultado =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] <> "Desconocido"
)
```

```dax
% del Total =
DIVIDE (
    [Total Eventos],
    CALCULATE ( [Total Eventos], ALLSELECTED ( fact_eventos ) )
)
```

```dax
Equipos Distintos = COUNTROWS ( dim_equipos )
```

```dax
Competiciones Distintas = COUNTROWS ( dim_competiciones )
```

```dax
Deportes Distintos = COUNTROWS ( dim_deportes )
```

---

## 2. Resultados (local, empate, visitante)

```dax
Victorias Local =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] = "Local"
)
```

```dax
Victorias Visitante =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] = "Visitante"
)
```

```dax
Empates =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] = "Empate"
)
```

```dax
% Victorias Local =
DIVIDE ( [Victorias Local], [Eventos con Resultado] )
```

```dax
% Victorias Visitante =
DIVIDE ( [Victorias Visitante], [Eventos con Resultado] )
```

```dax
% Empates =
DIVIDE ( [Empates], [Eventos con Resultado] )
```

```dax
Resultados Desconocidos =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] = "Desconocido"
)
```

> El denominador `[Eventos con Resultado]` excluye los 60 eventos sin marcador,
> de modo que los porcentajes suman 100 %.

---

## 3. Cuotas

```dax
Promedio Cuota Local = AVERAGE ( fact_eventos[cuota_local] )
```

```dax
Promedio Cuota Visitante = AVERAGE ( fact_eventos[cuota_visitante] )
```

```dax
Promedio Cuota Empate = AVERAGE ( fact_eventos[cuota_empate] )
```

```dax
Cuota Mínima = MIN ( fact_eventos[cuota_local] )
```

```dax
Cuota Máxima = MAX ( fact_eventos[cuota_local] )
```

```dax
Mediana Cuota Local = MEDIAN ( fact_eventos[cuota_local] )
```

```dax
Desviación Cuota Local = STDEV.P ( fact_eventos[cuota_local] )
```

```dax
Percentil 25 Cuota = PERCENTILE.INC ( fact_eventos[cuota_local], 0.25 )
```

```dax
Percentil 75 Cuota = PERCENTILE.INC ( fact_eventos[cuota_local], 0.75 )
```

```dax
Promedio Cuota Favorita = AVERAGE ( fact_eventos[cuota_favorita] )
```

```dax
Promedio Probabilidad Local = AVERAGE ( fact_eventos[prob_implicita_local] )
```

```dax
Margen Medio del Mercado = AVERAGE ( fact_eventos[margen_mercado] )
```

```dax
% Favorito Local =
DIVIDE (
    CALCULATE ( [Total Eventos], fact_eventos[favorito] = "Local" ),
    [Total Eventos]
)
```

```dax
% Favorito Visitante =
DIVIDE (
    CALCULATE ( [Total Eventos], fact_eventos[favorito] = "Visitante" ),
    [Total Eventos]
)
```

---

## 4. Marcadores

```dax
Promedio Goles Local = AVERAGE ( fact_eventos[goles_local] )
```

```dax
Promedio Goles Visitante = AVERAGE ( fact_eventos[goles_visitante] )
```

```dax
Promedio Puntos Local = AVERAGE ( fact_eventos[puntos_local] )
```

```dax
Promedio Puntos Visitante = AVERAGE ( fact_eventos[puntos_visitante] )
```

```dax
Promedio Diferencia Marcador = AVERAGE ( fact_eventos[diferencia_marcador] )
```

> Al filtrar por `dim_deportes[deporte] = "Fútbol"` se usan las medidas de
> goles; para baloncesto y tenis, las de puntos. En tenis el marcador
> representa sets ganados.

---

## 5. Estadísticas por equipo

La relación activa entre `fact_eventos` y `dim_equipos` es la de **equipo
local**. Para contar la participación como visitante se activa la relación
inactiva con `USERELATIONSHIP`.

```dax
Partidos como Local = [Total Eventos]
```

```dax
Partidos como Visitante =
CALCULATE (
    [Total Eventos],
    USERELATIONSHIP (
        fact_eventos[id_equipo_visitante],
        dim_equipos[id_equipo]
    )
)
```

```dax
Partidos Totales Equipo = [Partidos como Local] + [Partidos como Visitante]
```

```dax
Victorias Equipo =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] = "Local"
)
    + CALCULATE (
        [Total Eventos],
        fact_eventos[resultado_normalizado] = "Visitante",
        USERELATIONSHIP (
            fact_eventos[id_equipo_visitante],
            dim_equipos[id_equipo]
        )
    )
```

```dax
Empates Equipo =
CALCULATE (
    [Total Eventos],
    fact_eventos[resultado_normalizado] = "Empate"
)
    + CALCULATE (
        [Total Eventos],
        fact_eventos[resultado_normalizado] = "Empate",
        USERELATIONSHIP (
            fact_eventos[id_equipo_visitante],
            dim_equipos[id_equipo]
        )
    )
```

```dax
Derrotas Equipo =
[Partidos Totales Equipo] - [Victorias Equipo] - [Empates Equipo]
```

```dax
% Victorias Equipo =
DIVIDE ( [Victorias Equipo], [Partidos Totales Equipo] )
```

```dax
Ranking Equipos =
RANKX (
    ALLSELECTED ( dim_equipos[id_equipo] ),
    [Partidos Totales Equipo],
    ,
    DESC,
    DENSE
)
```

> Usar `dim_equipos[id_equipo]` en el ranking evita conflictos entre equipos
> homónimos de distintos deportes (por ejemplo, Real Madrid en fútbol y
> baloncesto).

```dax
Etiqueta Equipo =
dim_equipos[equipo] & " (" & dim_equipos[deporte] & ")"
```

---

## 6. Inteligencia de tiempo

Requiere que `dim_fecha` esté marcada como **tabla de fechas** y relacionada
con `fact_eventos`.

```dax
Eventos Últimos 12 Meses =
CALCULATE (
    [Total Eventos],
    DATESINPERIOD (
        dim_fecha[fecha],
        MAX ( dim_fecha[fecha] ),
        -12,
        MONTH
    )
)
```

```dax
Eventos Año Anterior =
CALCULATE (
    [Total Eventos],
    SAMEPERIODLASTYEAR ( dim_fecha[fecha] )
)
```

```dax
Variación YoY =
DIVIDE (
    [Total Eventos] - [Eventos Año Anterior],
    [Eventos Año Anterior]
)
```

```dax
Eventos Acumulados Año =
CALCULATE (
    [Total Eventos],
    DATESYTD ( dim_fecha[fecha] )
)
```

```dax
Promedio Eventos por Mes =
AVERAGEX (
    VALUES ( dim_fecha[año] ),
    CALCULATE ( [Total Eventos], ALLEXCEPT ( dim_fecha, dim_fecha[año] ) )
)
```

---

## 7. Títulos dinámicos (opcional)

```dax
Título Total Eventos =
"Eventos registrados: " & FORMAT ( [Total Eventos], "#,##0" )
```

```dax
Título Deporte Seleccionado =
"Deporte: "
    & SELECTEDVALUE ( dim_deportes[deporte], "Todos" )
```

Para usarlos: seleccionar el visual → **Formato → Título → Texto → fx** →
elegir la medida correspondiente.

---

## 8. Columnas calculadas opcionales

### 8.1 Rango de cuota (para el histograma)

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

### 8.2 Resultado legible para el equipo

```dax
Resultado del Equipo =
SWITCH (
    SELECTEDVALUE ( fact_eventos[resultado_normalizado] ),
    "Local", "Victoria local",
    "Visitante", "Victoria visitante",
    "Empate", "Empate",
    "Sin resultado"
)
```

### 8.3 Grupo de cuota del favorito

```dax
Favorito Claro =
IF ( fact_eventos[cuota_favorita] < 2.0, "Favorito claro", "Partido abierto" )
```

---

## 9. Formato recomendado de las medidas

| Medida | Formato |
|---|---|
| `Total Eventos`, `Victorias *`, `Empates`, `Partidos *` | Número entero, separador de miles |
| `% *` | Porcentaje, 1 decimal |
| `Promedio Cuota *`, `Cuota Mínima/Máxima`, `Percentil *` | Decimal, 2 posiciones |
| `Promedio Goles *` | Decimal, 2 posiciones |
| `Promedio Puntos *` | Decimal, 1 posición |
| `Margen Medio del Mercado` | Porcentaje, 2 decimales |
| `Variación YoY` | Porcentaje con signo, 1 decimal |

En Power BI: seleccionar la medida → **Herramientas de medida → Formato**.

---

## 10. Notas de uso

- Todas las medidas respetan los filtros de página, visual y segmentadores.
- `ALLSELECTED` se usa para que `% del Total` responda a los filtros externos
  (por ejemplo, si se selecciona un deporte, los porcentajes se calculan dentro
  de esa selección).
- Si se agrega un filtro de fecha, las medidas de cuotas y resultados se
  recalculan automáticamente.
- Evitar arrastrar columnas numéricas a un visual sin medida: Power BI podría
  sumar cuotas, lo que no tiene sentido. Usar siempre `Promedio Cuota *`.
- Los resultados "Desconocido" se conservan en `Total Eventos` para no perder
  eventos, pero se excluyen de los porcentajes de resultado.
