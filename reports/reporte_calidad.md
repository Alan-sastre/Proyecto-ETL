# Reporte de calidad de datos

**Proyecto:** ETL de análisis de datos de apuestas deportivas  
**Fuente:** datos históricos simulados (semilla fija, sin apuestas reales)  
**Fecha de generación:** 2026-11-11 09:34

## 1. Resumen general

| Métrica | Antes | Después |
|---|---:|---:|
| Filas | 3,425 | 3,278 |
| Columnas | 11 | 30 |
| Duplicados exactos | 49 | 0 |
| Duplicados por `id_evento` | 26 | 0 |
| Filas sin identificador | 0 | 0 |
| Fechas inválidas o nulas | 72 | 0 |
| Nombres de equipo corregidos | 1,406 | 0 |
| Resultados desconocidos | — | 60 |

## 2. Nulos por columna

| Columna | Nulos antes | % antes | Nulos después | % después |
|---|---:|---:|---:|---:|
| `año` | 0 | 0.0% | 0 | 0.0% |
| `competicion` | 59 | 1.7% | 0 | 0.0% |
| `cuota_empate` | 1,596 | 46.6% | 1,516 | 46.2% |
| `cuota_favorita` | 0 | 0.0% | 0 | 0.0% |
| `cuota_local` | 24 | 0.7% | 0 | 0.0% |
| `cuota_visitante` | 20 | 0.6% | 0 | 0.0% |
| `deporte` | 0 | 0.0% | 0 | 0.0% |
| `dia` | 0 | 0.0% | 0 | 0.0% |
| `dia_semana` | 0 | 0.0% | 0 | 0.0% |
| `diferencia_marcador` | 0 | 0.0% | 60 | 1.8% |
| `equipo_local` | 40 | 1.2% | 0 | 0.0% |
| `equipo_visitante` | 43 | 1.3% | 0 | 0.0% |
| `favorito` | 0 | 0.0% | 0 | 0.0% |
| `fecha_evento` | 43 | 1.3% | 0 | 0.0% |
| `fuente_archivo` | 0 | 0.0% | 0 | 0.0% |
| `goles_local` | 0 | 0.0% | 1,546 | 47.2% |
| `goles_visitante` | 0 | 0.0% | 1,546 | 47.2% |
| `id_evento` | 0 | 0.0% | 0 | 0.0% |
| `marcador_local` | 0 | 0.0% | 60 | 1.8% |
| `marcador_visitante` | 0 | 0.0% | 60 | 1.8% |
| `margen_mercado` | 0 | 0.0% | 0 | 0.0% |
| `mes` | 0 | 0.0% | 0 | 0.0% |
| `nombre_mes` | 0 | 0.0% | 0 | 0.0% |
| `prob_implicita_empate` | 0 | 0.0% | 1,516 | 46.2% |
| `prob_implicita_local` | 0 | 0.0% | 0 | 0.0% |
| `prob_implicita_visitante` | 0 | 0.0% | 0 | 0.0% |
| `puntos_local` | 0 | 0.0% | 1,792 | 54.7% |
| `puntos_visitante` | 0 | 0.0% | 1,792 | 54.7% |
| `resultado` | 62 | 1.8% | 0 | 0.0% |
| `resultado_normalizado` | 0 | 0.0% | 0 | 0.0% |

> Los nulos restantes en `cuota_empate` son **estructurales**: baloncesto y
> tenis no admiten empate, por lo que no se inventa una cuota.
> Del mismo modo, `goles_*` solo aplica a fútbol y `puntos_*` a baloncesto
> y tenis; sus nulos cruzados son estructurales y no un problema de calidad.

## 3. Estrategia de tratamiento de nulos

| Columna | Estrategia | Justificación |
|---|---|---|
| `id_evento` | Eliminar fila | Sin identificador no es posible deduplicar ni trazar el evento. |
| `fecha_evento` | Eliminar fila | La fecha es imprescindible para el modelo temporal; imputarla introduciría sesgo. |
| `deporte` | Imputar 'Desconocido' | Se conserva el registro y se hace explícita la ausencia de dato. |
| `equipo_local` | Imputar 'Desconocido' | Se conserva el evento; el equipo no participa en los rankings. |
| `equipo_visitante` | Imputar 'Desconocido' | Se conserva el evento; el equipo no participa en los rankings. |
| `competicion` | Imputar 'Desconocida' | Categoría explícita para no perder el evento. |
| `resultado` | Imputar 'Desconocido' | El marcador derivado queda nulo y el resultado se marca como desconocido. |
| `cuota_local` | Imputar mediana por deporte | La mediana es robusta a valores extremos y respeta el deporte. |
| `cuota_empate` | Nulo estructural / mediana en deportes con empate | Baloncesto y tenis no admiten empate: no se inventa una cuota. |
| `cuota_visitante` | Imputar mediana por deporte | La mediana es robusta a valores extremos y respeta el deporte. |
| `fuente_archivo` | Imputar 'desconocida' | Columna de trazabilidad, nunca debe quedar vacía. |

## 4. Correcciones y validaciones aplicadas

### Duplicados
- Duplicados exactos eliminados: **49**.
- Duplicados por `id_evento` eliminados: **26** (se conservó la fila más completa).

### Fechas
- Formatos normalizados a ISO `YYYY-MM-DD`: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, YYYY/MM/DD y texto en español.
- Registros eliminados por fecha inválida o nula: **72**.

### Nombres de equipos
- Limpieza de mayúsculas, espacios extra y tildes; alias de abreviaturas y corrección de typos por similitud (`difflib`, umbral 0.80).
- Nombres corregidos: **1,406**.

### Cuotas
| Cuota | Inválidas (<= 1.0) | Atípicas (> 50) | Nulos imputados |
|---|---:|---:|---:|
| `cuota_local` | 70 | 40 | 184 |
| `cuota_empate` | 53 | 18 | 110 |
| `cuota_visitante` | 118 | 47 | 216 |

## 5. Resultado final

- Dataset limpio: **3,278 eventos** con **30 columnas**.
- Duplicados por `id_evento`: **0**.
- Fechas nulas: **0**.
- Estado: **apto para análisis estadístico y visualización en Power BI**.

## 6. Observaciones

- Las cuotas se imputaron con la mediana del deporte para no alterar la distribución con valores extremos.
- Los eventos sin fecha o sin identificador se eliminaron porque no son trazables ni ubicables en el tiempo.
- La columna `fuente_archivo` permite auditar el origen de cada registro.
- Este proyecto es académico: los datos son simulados y no se promueven apuestas reales.
