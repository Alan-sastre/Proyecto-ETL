// ============================================================================
// PROYECTO ETL: ANÁLISIS DE DATOS DE APUESTAS DEPORTIVAS
// Script opcional de Power Query (M) para conectar con data/processed/.
//
// Uso en Power BI Desktop:
//   1. Inicio -> Obtener datos -> Consulta en blanco.
//   2. Abrir el Editor avanzado y pegar la consulta deseada.
//   3. Crear un parámetro de texto llamado RutaDatos con la ruta absoluta
//      de la carpeta data/processed del proyecto.
//
// Nota: los números de los CSV usan punto decimal y las fechas son ISO
// (YYYY-MM-DD); por eso se usa la referencia cultural "en-US" al convertir
// tipos. Si tu equipo usa coma decimal en los CSV, cambia "en-US" por "es-ES".
// ============================================================================

// ----------------------------------------------------------------------------
// 1. Función reutilizable para leer un CSV del proyecto
//    Crear como consulta nueva llamada fnLeerCSV.
// ----------------------------------------------------------------------------
let
    fnLeerCSV = (nombreArchivo as text) as table =>
        let
            RutaArchivo = RutaDatos & "\" & nombreArchivo,
            Origen = Csv.Document(
                File.Contents(RutaArchivo),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
            SinFilasVacias = Table.SelectRows(
                Encabezados,
                each not List.IsEmpty(
                    List.RemoveMatchingItems(Record.FieldValues(_), {"", null})
                )
            )
        in
            SinFilasVacias
in
    fnLeerCSV


// ----------------------------------------------------------------------------
// 2. Tabla de hechos tipada
//    Crear como consulta nueva llamada fact_eventos.
// ----------------------------------------------------------------------------
let
    Origen = fnLeerCSV("fact_eventos.csv"),
    Tipos = Table.TransformColumnTypes(
        Origen,
        {
            {"id_evento", type text},
            {"id_fecha", type text},
            {"fecha_evento", type date},
            {"id_deporte", type text},
            {"id_competicion", type text},
            {"id_equipo_local", type text},
            {"id_equipo_visitante", type text},
            {"marcador_local", Int64.Type},
            {"marcador_visitante", Int64.Type},
            {"goles_local", Int64.Type},
            {"goles_visitante", Int64.Type},
            {"puntos_local", Int64.Type},
            {"puntos_visitante", Int64.Type},
            {"diferencia_marcador", Int64.Type},
            {"resultado_normalizado", type text},
            {"cuota_local", type number},
            {"cuota_empate", type number},
            {"cuota_visitante", type number},
            {"cuota_favorita", type number},
            {"favorito", type text},
            {"prob_implicita_local", type number},
            {"prob_implicita_empate", type number},
            {"prob_implicita_visitante", type number},
            {"margen_mercado", type number},
            {"fuente_archivo", type text}
        },
        "en-US"
    )
in
    Tipos


// ----------------------------------------------------------------------------
// 3. Dimensión de equipos
//    Crear como consulta nueva llamada dim_equipos.
// ----------------------------------------------------------------------------
let
    Origen = fnLeerCSV("dim_equipos.csv"),
    Tipos = Table.TransformColumnTypes(
        Origen,
        {
            {"id_equipo", type text},
            {"equipo", type text},
            {"deporte", type text},
            {"partidos", Int64.Type},
            {"victorias", Int64.Type},
            {"empates", Int64.Type},
            {"derrotas", Int64.Type},
            {"tasa_victoria", type number}
        },
        "en-US"
    )
in
    Tipos


// ----------------------------------------------------------------------------
// 4. Dimensión de deportes
//    Crear como consulta nueva llamada dim_deportes.
// ----------------------------------------------------------------------------
let
    Origen = fnLeerCSV("dim_deportes.csv"),
    Tipos = Table.TransformColumnTypes(
        Origen,
        {
            {"id_deporte", type text},
            {"deporte", type text},
            {"n_eventos", Int64.Type}
        },
        "en-US"
    )
in
    Tipos


// ----------------------------------------------------------------------------
// 5. Dimensión de competiciones
//    Crear como consulta nueva llamada dim_competiciones.
// ----------------------------------------------------------------------------
let
    Origen = fnLeerCSV("dim_competiciones.csv"),
    Tipos = Table.TransformColumnTypes(
        Origen,
        {
            {"id_competicion", type text},
            {"competicion", type text},
            {"deporte", type text},
            {"n_eventos", Int64.Type}
        },
        "en-US"
    )
in
    Tipos


// ----------------------------------------------------------------------------
// 6. Dimensión de fechas
//    Crear como consulta nueva llamada dim_fecha.
//    Después, en Power BI: Herramientas de tabla -> Marcar como tabla de fechas.
// ----------------------------------------------------------------------------
let
    Origen = fnLeerCSV("dim_fecha.csv"),
    Tipos = Table.TransformColumnTypes(
        Origen,
        {
            {"id_fecha", type text},
            {"fecha", type date},
            {"año", Int64.Type},
            {"trimestre", type text},
            {"mes", Int64.Type},
            {"nombre_mes", type text},
            {"semana_iso", Int64.Type},
            {"dia", Int64.Type},
            {"dia_semana", type text},
            {"es_fin_semana", type logical}
        },
        "en-US"
    )
in
    Tipos


// ----------------------------------------------------------------------------
// 7. (Opcional) Auditoría de archivos disponibles
//    Crear como consulta nueva llamada AuditoriaArchivos.
// ----------------------------------------------------------------------------
let
    Origen = Folder.Files(RutaDatos),
    SoloCSV = Table.SelectRows(
        Origen,
        each [Extension] = ".csv" and not Text.StartsWith([Name], "~$")
    ),
    Resumen = Table.SelectColumns(SoloCSV, {"Name", "Length", "Date modified"}),
    Renombradas = Table.RenameColumns(
        Resumen,
        {
            {"Name", "Archivo"},
            {"Length", "Tamaño (bytes)"},
            {"Date modified", "Última modificación"}
        }
    )
in
    Renombradas
