# Cómo subir el dashboard y los datos a Power BI

Guía paso a paso para publicar este proyecto en el **servicio de Power BI**
(`app.powerbi.com`). Si solo quieres verlo en tu equipo, abre primero
[`ABRIR_EN_POWER_BI.md`](ABRIR_EN_POWER_BI.md).

---

## 0. Lo primero: por qué fallaba la subida

El servicio de Power BI **no acepta archivos `.pbip`** en
**Nuevo → Cargar un archivo**. Ese botón solo admite los formatos que el
servicio sabe interpretar directamente:

| Archivo | ¿Se puede subir al servicio? | Para qué sirve |
|---|---|---|
| `Dashboard_Apuestas.pbip` | **No** | Abrirlo en Power BI Desktop |
| `Dashboard_Apuestas.pbix` | **Sí** | Subirlo o publicarlo con informe y modelo |
| `datos_powerbi.xlsx` | **Sí** | Crear un conjunto de datos con las 5 tablas |
| `data/processed/*.csv` | **Sí** | Crear un conjunto de datos de una sola tabla |

Por eso, si intentas cargar el `.pbip` verás un error del tipo
«El tipo de archivo no es compatible» o el archivo ni siquiera aparece
seleccionable.

La solución no es cambiar el `.pbip`, sino **convertirlo a `.pbix` desde Power
BI Desktop** (ruta A) o **subir los datos en Excel/CSV** (rutas C y D).

> El `.pbip` es solo el punto de entrada: necesita las carpetas
> `Dashboard_Apuestas.SemanticModel/` y `Dashboard_Apuestas.Report/` que están a
> su lado. No lo muevas ni lo envíes suelto; si quieres compartir el proyecto,
> comprime la carpeta `powerbi/PBIP/` completa.

> El proyecto `.pbip` ya se genera **con los datos incrustados**. No depende de
> `data/processed/` ni de la ruta `RutaDatos`, así que funciona al abrirlo en
> cualquier equipo.

---

## 1. Antes de empezar

### 1.1 Requisitos

- **Power BI Desktop** actualizado (gratis):
  <https://powerbi.microsoft.com/desktop/>. Solo existe para Windows.
- Una cuenta de Power BI con la que iniciar sesión en el servicio.
- Para publicar en un área de trabajo compartida necesitas licencia
  **Power BI Pro o Premium Per User (PPU)**. En **Mi área de trabajo** puedes
  publicar con una cuenta gratuita, aunque compartir el informe requiere
  licencia.
- Los archivos del proyecto ya generados.

### 1.2 Genera los archivos (solo si hace falta)

Desde la raíz del proyecto:

```powershell
# 1) Datos del ETL (si aún no existen)
python main.py --regenerar --semilla 42

# 2) Proyecto de Power BI y libro de Excel
python powerbi/build_pbip.py
```

Al terminar deben existir:

```text
powerbi/PBIP/Dashboard_Apuestas.pbip   ← se abre en Desktop, NO se sube
powerbi/PBIP/LEEME - COMO ABRIR.txt
powerbi/datos_powerbi.xlsx              ← se puede subir al servicio
data/processed/fact_eventos.csv         ← alternativa CSV
data/processed/dim_fecha.csv
data/processed/dim_deportes.csv
data/processed/dim_competiciones.csv
data/processed/dim_equipos.csv
```

Comprueba que el dato principal tiene **3.278 eventos**:

```powershell
python -c "import pandas as pd; print(len(pd.read_csv('data/processed/fact_eventos.csv')))"
```

---

## 2. Ruta A — Publicar el dashboard completo (recomendada)

Esta es la única ruta que conserva **las tres páginas, los 24 visuales, las 33
medidas y las relaciones** tal como se entregaron. Power BI Desktop convierte el
`.pbip` en un `.pbix` y lo publica.

### Paso 1. Abre el proyecto en Power BI Desktop

1. Abre **Power BI Desktop**.
2. Ve a **Archivo → Abrir** y selecciona
   `powerbi/PBIP/Dashboard_Apuestas.pbip`.
   También puedes hacer doble clic sobre el archivo.
3. Si aparece un aviso de versión o de formato, pulsa **Aceptar/Actualizar**.

### Paso 2. Actualiza y comprueba

1. Pulsa **Inicio → Actualizar**.
2. Espera a que terminen las consultas. Como los datos están incrustados, no
   debe pedir ninguna ruta ni credenciales.
3. Comprueba en la página **Resumen general** que la tarjeta
   **Total Eventos** muestra **3.278**.
4. Recorre las tres páginas:
   - **Resumen general**
   - **Cuotas y mercado**
   - **Detalle por equipo**

Si alguna tarjeta aparece vacía, vuelve a pulsar **Actualizar**.

### Paso 3. Guarda una copia en `.pbix`

1. Ve a **Archivo → Guardar como**.
2. Elige **Power BI (.pbix)**.
3. Guarda como `powerbi/dashboard_apuestas.pbix`.
4. Confirma el aviso de que se perderán las características exclusivas de
   proyecto (es normal: el `.pbip` sigue intacto).

> Guardar el `.pbix` es opcional para publicar, pero es muy recomendable: te
> queda un archivo de entrega y puedes subirlo por la ruta B.

### Paso 4. Inicia sesión

1. En Power BI Desktop, pulsa **Inicio → Iniciar sesión** (arriba a la
   derecha).
2. Usa la misma cuenta con la que entrarás a `app.powerbi.com`.

### Paso 5. Publica

1. Pulsa **Inicio → Publicar** (o **Archivo → Publicar**).
2. Selecciona el destino:
   - **Mi área de trabajo**, o
   - el **área de trabajo** que te haya indicado el profesor/equipo.
3. Pulsa **Seleccionar**.
4. Espera el mensaje **«Publicación correcta»** y pulsa el enlace
   **Abrir 'Dashboard_Apuestas' en Power BI**.

### Paso 6. Comprueba en el servicio

1. Entra en <https://app.powerbi.com>.
2. Abre el área de trabajo donde publicaste.
3. Deben aparecer dos elementos:
   - un **informe** llamado `Dashboard_Apuestas`;
   - un **conjunto de datos** (modelo semántico) asociado.
4. Abre el informe y verifica las tres páginas y el total de 3.278.

### Paso 7. Crea un panel (opcional)

1. Abre el informe en el servicio.
2. Pasa el ratón por un visual y pulsa el icono de **chincheta**.
3. Elige **Nuevo panel** y ponle un nombre, por ejemplo
   `Panel de apuestas`.
4. Repite con las tarjetas y gráficos que quieras destacar.

> No hace falta configurar puerta de enlace ni actualización programada: el
> modelo publicado lleva los datos importados. Si más adelante cambias los
> datos, vuelve a ejecutar el ETL y a publicar desde Desktop.

---

## 3. Ruta B — Subir directamente el `.pbix` al servicio

Úsala si ya guardaste `powerbi/dashboard_apuestas.pbix` y prefieres no publicar
desde Desktop.

1. Entra en <https://app.powerbi.com> e inicia sesión.
2. Entra en el **área de trabajo** de destino.
3. Pulsa **Nuevo → Cargar un archivo**.
   En algunas versiones el botón se llama **Cargar** o **Importar**.
4. Pulsa **Examinar** y selecciona `powerbi/dashboard_apuestas.pbix`.
5. Pulsa **Cargar**.
6. Cuando termine, abre el informe desde el área de trabajo.

**Importante:** si seleccionas el `.pbip` en este paso, la carga fallará. Debes
seleccionar el `.pbix`.

Limitaciones de esta ruta:

- El informe se puede **ver y compartir**, pero no editar como un `.pbip`.
- Para cambiar visuales hay que editarlo en Desktop y volver a subirlo.
- El tamaño máximo de archivo depende de la licencia y del área de trabajo.

---

## 4. Ruta C — Subir el Excel con las cinco tablas

El libro `powerbi/datos_powerbi.xlsx` contiene una hoja por tabla:
`fact_eventos`, `dim_fecha`, `dim_deportes`, `dim_competiciones` y
`dim_equipos`. Sirve para crear un conjunto de datos sin usar Power BI Desktop.

### Paso 1. Sube el libro

1. Entra en <https://app.powerbi.com> e inicia sesión.
2. Entra en el **área de trabajo** de destino.
3. Pulsa **Nuevo → Cargar un archivo** y selecciona
   `powerbi/datos_powerbi.xlsx`.

   Si tu versión del servicio no muestra Excel en **Cargar un archivo**, usa:
   **Nuevo → Conjunto de datos → Excel** (o **Obtener datos → Archivos →
   Archivo local**) y selecciona el mismo libro.

4. Espera a que el servicio cree el elemento. Según la versión, aparecerá como
   **libro de Excel** con un **conjunto de datos** asociado o directamente como
   **conjunto de datos**.

### Paso 2. Abre el conjunto de datos y crea relaciones

1. En el área de trabajo, abre el conjunto de datos creado.
2. Pulsa **Crear un informe** o **Abrir modelo**.
3. En la vista **Modelo**, crea las relaciones si no se importaron:
   - `fact_eventos[id_fecha]` → `dim_fecha[id_fecha]`
   - `fact_eventos[id_deporte]` → `dim_deportes[id_deporte]`
   - `fact_eventos[id_competicion]` → `dim_competiciones[id_competicion]`
   - `fact_eventos[id_equipo_local]` → `dim_equipos[id_equipo]`
   - `fact_eventos[id_equipo_visitante]` → `dim_equipos[id_equipo]`
     (esta última **inactiva**)
4. Comprueba que las columnas de fecha son de tipo **Fecha** y que las cuotas
   son **Número decimal**.

### Paso 3. Crea el informe

Tienes dos opciones:

- **Rápida:** crea una página con las tarjetas y gráficos que necesites.
- **Completa:** sigue [`GUIA_DASHBOARD.md`](GUIA_DASHBOARD.md) y
  [`medidas_DAX.md`](medidas_DAX.md) para reproducir las 33 medidas y los 24
  visuales.

> Esta ruta no conserva los visuales del `.pbip`; solo los datos. Es útil si el
> objetivo es demostrar la carga en el servicio o si no tienes acceso a Power BI
> Desktop.

---

## 5. Ruta D — Subir un CSV suelto

Si solo necesitas una tabla rápida (por ejemplo, para comprobar que el servicio
acepta los datos):

1. En <https://app.powerbi.com>, entra en el área de trabajo.
2. Pulsa **Nuevo → Cargar un archivo** y selecciona
   `data/processed/eventos_limpios.csv` o `data/processed/fact_eventos.csv`.
   Si esa opción no está disponible, usa **Nuevo → Conjunto de datos → CSV** o
   **Obtener datos → Archivos → Archivo local**.
3. Revisa en Power Query que:
   - el delimitador sea **coma**;
   - la codificación sea **UTF-8**;
   - `fecha_evento` sea **Fecha**;
   - las columnas de cuotas sean **Número decimal**.
4. Pulsa **Crear** / **Cargar**.

Limitación: un CSV crea **una sola tabla**, sin las dimensiones ni las
relaciones del esquema estrella. Para el dashboard completo usa la ruta A.

---

## 6. Errores frecuentes y solución

| Mensaje o síntoma | Causa | Solución |
|---|---|---|
| «El tipo de archivo no es compatible» al cargar | Estás subiendo el `.pbip` | Abre el `.pbip` en Desktop y guárdalo como `.pbix` (ruta A) |
| El `.pbip` no aparece para seleccionar | El servicio no admite proyectos | Usa `.pbix`, `.xlsx` o `.csv` |
| «No se encuentra el archivo» al actualizar | `.pbip` antiguo generado con la ruta `RutaDatos` de otro equipo | Vuelve a ejecutar `python powerbi/build_pbip.py` (ahora incrusta los datos) |
| «No se puede actualizar: el origen de datos es local» | El modelo se generó en modo `--usar-csv` y apunta a una carpeta local | Vuelve a generar sin `--usar-csv`, o instala una puerta de enlace personal |
| «No tienes licencia para publicar aquí» | El área de trabajo compartida requiere Pro/PPU | Publica en **Mi área de trabajo** o pide licencia |
| «No se pudo publicar el informe» | Sesión caducada o sin conexión | Vuelve a iniciar sesión y publica de nuevo |
| El Excel tarda o falla al subir | Tamaño o conexión | El libro pesa unos 424 KB; reintenta o usa la ruta A |
| Los acentos se ven mal | Codificación incorrecta al importar un CSV | Usa **UTF-8**; los CSV del proyecto llevan BOM |
| Las cuotas aparecen como texto | Tipo inferido incorrectamente | Cámbialo a **Número decimal** en Power Query |
| Las fechas aparecen como texto | Configuración regional | Tipo **Fecha** y referencia cultural **Español (España)** |
| Faltan relaciones tras subir el Excel | El libro no guarda el modelo relacional | Créalas a mano en la vista **Modelo** (paso 4.2) |
| El informe publicado está vacío | No se actualizó antes de publicar | Abre el `.pbip`, pulsa **Actualizar** y vuelve a publicar |
| «Actualizar» no está disponible en el servicio | El informe se subió como `.pbix` sin programar actualización | No es necesario: los datos van importados; para cambiarlos, republica |
| Power BI Desktop no abre el `.pbip` | Versión antigua o falta la vista previa de PBIR | Actualiza Desktop a una versión de 2024 o posterior |

---

## 7. Comprobación final

Antes de dar por terminada la subida:

- [ ] En el servicio aparece el **informe** `Dashboard_Apuestas`.
- [ ] Se ven las tres páginas: **Resumen general**, **Cuotas y mercado** y
      **Detalle por equipo**.
- [ ] La tarjeta **Total Eventos** muestra **3.278**.
- [ ] El segmentador de deporte filtra los visuales.
- [ ] Las fechas se ven como `dd/mm/aaaa`.
- [ ] Los porcentajes tienen un decimal y las cuotas dos.
- [ ] El informe se abre en un navegador distinto o en modo incógnito.
- [ ] Si compartes, el usuario de destino tiene licencia y permiso.

---

## 8. Qué archivo usar según el objetivo

| Objetivo | Archivo | Ruta |
|---|---|---|
| Ver el dashboard completo en mi PC | `powerbi/PBIP/Dashboard_Apuestas.pbip` | Abrir en Desktop |
| Entregar un archivo clásico | `powerbi/dashboard_apuestas.pbix` | Guardar como desde Desktop |
| Publicar el dashboard completo | `powerbi/dashboard_apuestas.pbix` | A o B |
| Crear un dataset con las 5 tablas | `powerbi/datos_powerbi.xlsx` | C |
| Probar una carga rápida | `data/processed/fact_eventos.csv` | D |
| Rehacer el dashboard a mano | CSV de `data/processed/` | `GUIA_DASHBOARD.md` |

---

## 9. Regenerar todo

Si cambias los datos o quieres volver a empezar:

```powershell
# Datos del ETL
python main.py --regenerar --semilla 42

# Proyecto autocontenido + Excel listo para subir
python powerbi/build_pbip.py

# Validar los JSON contra los esquemas de Microsoft (opcional)
python powerbi/build_pbip.py --validar

# Modo avanzado: conectar el modelo a los CSV en lugar de incrustarlos
python powerbi/build_pbip.py --usar-csv
python powerbi/build_pbip.py --ruta-datos "C:\ruta\a\data\processed"
```

> En el modo `--usar-csv` el `.pbip` vuelve a depender de una carpeta local. Si
> lo publicas, necesitarás una **puerta de enlace personal** para actualizarlo.
> Para entregar o subir a Power BI usa el modo por defecto (datos incrustados).
