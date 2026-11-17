# Ejecutar todo el proyecto en un clic

Este proyecto incluye un lanzador que hace **todo el proceso seguido**:

1. Genera los datos simulados.
2. Ejecuta el ETL completo (extraer, transformar y cargar).
3. Genera el proyecto de Power BI autocontenido (`.pbip`).
4. Genera el Excel con las cinco tablas.
5. Verifica el modelo, las relaciones y los visuales.
6. Crea `entrega_powerbi.zip` con todos los entregables.

---

## Windows: doble clic

Haz doble clic en:

```text
EJECUTAR_TODO.bat
```

La primera vez instala las dependencias automáticamente. Al terminar abre el
dashboard en Power BI Desktop y deja estos archivos:

```text
powerbi/PBIP/Dashboard_Apuestas.pbip   ← dashboard completo editable
powerbi/datos_powerbi.xlsx             ← datos listos para subir al servicio
entrega_powerbi.zip                    ← todo empaquetado para entregar
```

## Windows: crear un `.exe`

Si necesitas un único ejecutable:

1. Haz doble clic en `crear_ejecutable_windows.bat`.
2. Espera a que termine.
3. Usa `dist\Ejecutar_Proyecto_ETL.exe` donde quieras.

Ese `.exe` ya lleva Python y las librerías dentro. Genera los resultados en la
misma carpeta donde esté el ejecutable. No hace falta instalar Python en el
equipo de destino.

## Linux o macOS

```bash
./EJECUTAR_TODO.sh
```

Si tienes `uv` instalado, el lanzador crea el entorno y descarga las
dependencias automáticamente.

---

## Opciones

```text
--sin-regenerar          Usa los datos crudos que ya existen.
--semilla N              Semilla de los datos simulados (por defecto 42).
--sin-graficos           No genera las figuras de Matplotlib (más rápido).
--sin-sqlite             No genera la base de datos SQLite.
--sin-excel              No genera datos_powerbi.xlsx.
--sin-zip                No crea entrega_powerbi.zip.
--validar                Valida los JSON contra los esquemas de Microsoft.
--abrir                  Abre la carpeta powerbi al terminar.
--abrir-dashboard        Abre el .pbip en Power BI Desktop al terminar.
--instalar-dependencias  Instala requirements.txt antes de empezar.
```

Ejemplos:

```powershell
EJECUTAR_TODO.bat --sin-graficos --sin-sqlite
python ejecutar_todo.py --sin-regenerar --abrir
```

---

## Lo único que no se puede automatizar

Power BI exige **iniciar sesión con tu cuenta** para publicar o cargar archivos
en `app.powerbi.com`. Por eso el lanzador deja el archivo preparado, pero el
último clic en **Publicar** o **Cargar** lo tienes que hacer tú.

Tienes dos opciones:

- **Dashboard completo:** abre `powerbi/PBIP/Dashboard_Apuestas.pbip` en Power BI
  Desktop, pulsa **Actualizar** y luego **Publicar**.
- **Solo datos:** sube `powerbi/datos_powerbi.xlsx` desde el área de trabajo de
  Power BI.

El detalle de ambas rutas está en
[`SUBIR_A_POWER_BI.md`](SUBIR_A_POWER_BI.md).
