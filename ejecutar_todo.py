#!/usr/bin/env python3
"""Ejecuta el proceso completo del proyecto con un solo comando.

Hace, sin intervención manual:

1. Genera/regenera los datos simulados y ejecuta Extract -> Transform -> Load.
2. Genera el proyecto ``.pbip`` autocontenido y el Excel ``datos_powerbi.xlsx``.
3. Verifica el modelo, las relaciones y los visuales.
4. Crea ``entrega_powerbi.zip`` con todo lo necesario para entregar o subir.
5. Abre la carpeta de resultados si se indica ``--abrir``.

Uso::

    python ejecutar_todo.py
    python ejecutar_todo.py --abrir
    python ejecutar_todo.py --sin-graficos --sin-sqlite
    python ejecutar_todo.py --validar
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from types import ModuleType

LOGGER = logging.getLogger("ejecutar_todo")


def _raiz_proyecto() -> Path:
    """Devuelve la carpeta donde deben quedar los resultados."""
    if getattr(sys, "frozen", False):
        # PyInstaller: los resultados van junto al .exe, no en _MEIPASS.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RAIZ = _raiz_proyecto()
if getattr(sys, "frozen", False):
    os.environ["PROYECTO_ETL_ROOT"] = str(RAIZ)
else:
    os.environ.setdefault("PROYECTO_ETL_ROOT", str(RAIZ))

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

DEPENDENCIAS = ("pandas", "openpyxl", "matplotlib")
ARCHIVOS_DOCUMENTACION = (
    "powerbi/SUBIR_A_POWER_BI.md",
    "powerbi/ABRIR_EN_POWER_BI.md",
    "powerbi/GUIA_DASHBOARD.md",
    "powerbi/medidas_DAX.md",
    "COMO_EJECUTAR_TODO.md",
)
IGNORAR_AL_EMPAQUETAR = {".pbi", "__pycache__", ".pytest_cache"}
NOMBRES_IGNORADOS = {"localSettings.json", "cache.abf"}


def _configurar_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        force=True,
    )


def _faltan_dependencias() -> list[str]:
    """Devuelve los paquetes de terceros que no están instalados."""
    faltan: list[str] = []
    for modulo in DEPENDENCIAS:
        if importlib.util.find_spec(modulo) is None:
            faltan.append(modulo)
    return faltan


def _instalar_dependencias() -> bool:
    """Instala requirements.txt cuando se ejecuta desde el código fuente."""
    if getattr(sys, "frozen", False):
        LOGGER.error("El ejecutable ya incluye las dependencias; no hay que instalarlas.")
        return False
    requisitos = RAIZ / "requirements.txt"
    if not requisitos.exists():
        LOGGER.error("No se encuentra %s", requisitos)
        return False
    LOGGER.info("Instalando dependencias desde %s ...", requisitos)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requisitos)],
            check=True,
            cwd=RAIZ,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        LOGGER.error("No se pudieron instalar las dependencias: %s", error)
        return False
    return True


def _ejecutar_etl(opciones: argparse.Namespace) -> int:
    """Ejecuta el pipeline ETL en el mismo proceso."""
    from main import main as pipeline

    # ``main`` instala sus propios handlers; retiramos los de este lanzador
    # para que cada línea no salga dos veces por consola.
    raiz_logs = logging.getLogger()
    for handler in list(raiz_logs.handlers):
        raiz_logs.removeHandler(handler)
    if hasattr(raiz_logs, "_etl_configurado"):
        delattr(raiz_logs, "_etl_configurado")

    argumentos: list[str] = []
    if not opciones.sin_regenerar:
        argumentos.append("--regenerar")
    argumentos.extend(["--semilla", str(opciones.semilla)])
    if opciones.sin_graficos:
        argumentos.append("--sin-graficos")
    if opciones.sin_sqlite:
        argumentos.append("--sin-sqlite")
    return int(pipeline(argumentos))


def _cargar_build_pbip() -> ModuleType:
    """Carga ``powerbi/build_pbip.py`` tanto en código fuente como empaquetado."""
    rutas = [
        RAIZ / "powerbi" / "build_pbip.py",
        Path(getattr(sys, "_MEIPASS", RAIZ)) / "powerbi" / "build_pbip.py",
    ]
    ruta = next((candidata for candidata in rutas if candidata.exists()), None)
    if ruta is None:
        raise FileNotFoundError(
            "No se encuentra powerbi/build_pbip.py. "
            "Ejecuta el programa desde la raíz del proyecto."
        )
    especificacion = importlib.util.spec_from_file_location("_build_pbip", ruta)
    if especificacion is None or especificacion.loader is None:
        raise ImportError(f"No se pudo cargar {ruta}")
    modulo = importlib.util.module_from_spec(especificacion)
    sys.modules[especificacion.name] = modulo
    especificacion.loader.exec_module(modulo)
    return modulo


def _ignorar_al_empaquetar(ruta: Path) -> bool:
    """Indica si un archivo temporal de Power BI no debe entrar en el ZIP."""
    return (
        any(parte in IGNORAR_AL_EMPAQUETAR for parte in ruta.parts)
        or ruta.name in NOMBRES_IGNORADOS
        or ruta.suffix.lower() == ".tmp"
    )


def _texto_entrega() -> str:
    return """ENTREGA DEL PROYECTO ETL DE APUESTAS DEPORTIVAS
================================================

Este paquete se ha generado automáticamente con ejecutar_todo.py.

CONTENIDO
---------
powerbi/PBIP/                   Proyecto editable de Power BI (.pbip)
powerbi/datos_powerbi.xlsx      Libro con las 5 tablas, listo para subir
data/processed/*.csv            Datos limpios y tablas del esquema estrella
powerbi/*.md                    Guías de Power BI

QUÉ HACER CON ELLO
------------------
1) Dashboard completo:
   abre powerbi/PBIP/Dashboard_Apuestas.pbip en Power BI Desktop,
   pulsa Actualizar, guarda como .pbix y publica.

2) Subida rápida de datos al servicio:
   en app.powerbi.com usa Nuevo -> Cargar un archivo y sube
   powerbi/datos_powerbi.xlsx.

3) Si ya tienes un .pbix:
   súbelo directamente desde el área de trabajo de Power BI.

La guía detallada está en powerbi/SUBIR_A_POWER_BI.md.
"""


def _ruta_recurso(nombre: str) -> Path | None:
    """Busca un archivo en la carpeta de trabajo o dentro del ejecutable."""
    for base in (RAIZ, Path(getattr(sys, "_MEIPASS", RAIZ))):
        ruta = base / nombre
        if ruta.is_file():
            return ruta
    return None


def _crear_entrega(destino: Path) -> Path:
    """Crea un ZIP con el proyecto, los datos y la documentación."""
    if destino.exists():
        destino.unlink()

    archivos_contados = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        # Proyecto Power BI completo (incluye modelo, informe y visuales).
        origen_pbip = RAIZ / "powerbi" / "PBIP"
        if origen_pbip.exists():
            for ruta in sorted(origen_pbip.rglob("*")):
                if not ruta.is_file():
                    continue
                relativa = ruta.relative_to(origen_pbip)
                if _ignorar_al_empaquetar(relativa):
                    continue
                paquete.write(ruta, f"powerbi/PBIP/{relativa.as_posix()}")
                archivos_contados += 1

        # Libro Excel y documentación.
        for nombre in ("powerbi/datos_powerbi.xlsx", *ARCHIVOS_DOCUMENTACION):
            ruta = _ruta_recurso(nombre)
            if ruta is not None:
                paquete.write(ruta, nombre)
                archivos_contados += 1

        # Si el usuario ya guardó un .pbix, se incluye en la entrega.
        for ruta in sorted((RAIZ / "powerbi").glob("*.pbix")):
            paquete.write(ruta, f"powerbi/{ruta.name}")
            archivos_contados += 1

        # CSV del ETL.
        for ruta in sorted((RAIZ / "data" / "processed").glob("*.csv")):
            paquete.write(ruta, f"data/processed/{ruta.name}")
            archivos_contados += 1

        # README principal y requisitos.
        for nombre in ("README.md", "requirements.txt"):
            ruta = _ruta_recurso(nombre)
            if ruta is not None:
                paquete.write(ruta, nombre)
                archivos_contados += 1

        paquete.writestr("LEEME_ENTREGA.txt", _texto_entrega())

    LOGGER.info("Entrega creada: %s (%s archivos)", destino, archivos_contados)
    return destino


def _buscar_power_bi() -> Path | None:
    """Localiza Power BI Desktop en las rutas habituales de Windows."""
    if not sys.platform.startswith("win"):
        return None

    candidatos: list[Path] = []
    en_path = shutil.which("PBIDesktop.exe")
    if en_path:
        candidatos.append(Path(en_path))

    programas = os.environ.get("ProgramFiles", r"C:\Program Files")
    programas_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA")
    for base in (programas, programas_x86):
        candidatos.append(Path(base) / "Microsoft Power BI Desktop" / "bin" / "PBIDesktop.exe")
    if local:
        candidatos.append(Path(local) / "Microsoft" / "WindowsApps" / "PBIDesktop.exe")

    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    return None


def _abrir_dashboard(ruta: Path) -> bool:
    """Abre el .pbip; si se encuentra, usa Power BI Desktop directamente."""
    power_bi = _buscar_power_bi()
    if power_bi is not None:
        try:
            subprocess.Popen([str(power_bi), str(ruta)])
            return True
        except OSError as error:
            LOGGER.warning("No se pudo iniciar Power BI Desktop: %s", error)
    return _abrir_archivo(ruta)


def _abrir_carpeta(ruta: Path) -> None:
    """Abre la carpeta de resultados en el explorador del sistema."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(ruta))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(ruta)], check=False)
        else:
            subprocess.run(["xdg-open", str(ruta)], check=False)
    except Exception as error:  # noqa: BLE001 - abrir el explorador es opcional
        LOGGER.warning("No se pudo abrir la carpeta %s: %s", ruta, error)


def _abrir_archivo(ruta: Path) -> bool:
    """Abre un archivo con la aplicación predeterminada del sistema."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(ruta))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(ruta)], check=False)
        else:
            subprocess.run(["xdg-open", str(ruta)], check=False)
        return True
    except Exception as error:  # noqa: BLE001 - abrir el dashboard es opcional
        LOGGER.warning("No se pudo abrir %s: %s", ruta, error)
        return False


def _formatear_tamano(bytes_totales: int) -> str:
    tamano = float(bytes_totales)
    for unidad in ("B", "KB", "MB", "GB"):
        if tamano < 1024 or unidad == "GB":
            return f"{tamano:.0f} {unidad}" if unidad == "B" else f"{tamano:.1f} {unidad}"
        tamano /= 1024
    return f"{bytes_totales} B"


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ejecuta el ETL y genera todos los entregables de Power BI."
    )
    parser.add_argument(
        "--sin-regenerar",
        action="store_true",
        help="usa los datos crudos existentes en vez de regenerarlos",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=42,
        help="semilla de los datos simulados (por defecto 42)",
    )
    parser.add_argument(
        "--sin-graficos",
        action="store_true",
        help="omite las figuras de Matplotlib (más rápido)",
    )
    parser.add_argument(
        "--sin-sqlite",
        action="store_true",
        help="omite la base de datos SQLite",
    )
    parser.add_argument(
        "--sin-excel",
        action="store_true",
        help="no genera powerbi/datos_powerbi.xlsx",
    )
    parser.add_argument(
        "--sin-zip",
        action="store_true",
        help="no crea entrega_powerbi.zip",
    )
    parser.add_argument(
        "--validar",
        action="store_true",
        help="valida los JSON contra los esquemas de Microsoft (requiere Internet)",
    )
    parser.add_argument(
        "--abrir",
        action="store_true",
        help="abre la carpeta powerbi al terminar",
    )
    parser.add_argument(
        "--abrir-dashboard",
        action="store_true",
        help="abre el .pbip en Power BI Desktop al terminar",
    )
    parser.add_argument(
        "--instalar-dependencias",
        action="store_true",
        help="instala requirements.txt antes de empezar (solo código fuente)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ejecuta el proceso completo y devuelve un código de salida."""
    opciones = _construir_parser().parse_args(argv)
    _configurar_logging()
    inicio = time.perf_counter()

    LOGGER.info("=" * 70)
    LOGGER.info("PROYECTO ETL DE APUESTAS DEPORTIVAS")
    LOGGER.info("=" * 70)
    LOGGER.info("Carpeta de trabajo: %s", RAIZ)

    if opciones.instalar_dependencias and not _instalar_dependencias():
        return 2

    faltan = _faltan_dependencias()
    if faltan:
        LOGGER.error("Faltan dependencias: %s", ", ".join(faltan))
        if getattr(sys, "frozen", False):
            LOGGER.error("El ejecutable está incompleto; vuelve a generarlo.")
        else:
            LOGGER.error(
                "Instálalas con: %s -m pip install -r requirements.txt",
                Path(sys.executable).name,
            )
            LOGGER.error("O ejecuta este script con --instalar-dependencias.")
        return 2

    LOGGER.info("")
    LOGGER.info("--- PASO 1/3: ETL (extraer, transformar y cargar) ---")
    try:
        codigo = _ejecutar_etl(opciones)
    except Exception:
        LOGGER.exception("El ETL ha fallado.")
        return 1
    if codigo != 0:
        LOGGER.error("El ETL terminó con errores (código %s).", codigo)
        return codigo

    LOGGER.info("")
    LOGGER.info("--- PASO 2/3: PROYECTO POWER BI Y EXCEL ---")
    try:
        modulo = _cargar_build_pbip()
        archivos = modulo.generar(excel=not opciones.sin_excel)
        errores = modulo.verificar()
    except Exception:
        LOGGER.exception("No se pudo generar el proyecto de Power BI.")
        return 1
    for error in errores:
        LOGGER.error("Verificación: %s", error)
    if errores:
        return 1
    LOGGER.info("Modelo, relaciones y visuales verificados correctamente.")

    if opciones.validar:
        try:
            if not modulo.validar(archivos):
                LOGGER.error("La validación contra los esquemas de Microsoft ha fallado.")
                return 1
        except Exception as error:  # noqa: BLE001 - la validación es opcional
            LOGGER.warning("No se pudo validar contra los esquemas: %s", error)

    LOGGER.info("")
    LOGGER.info("--- PASO 3/3: PAQUETE DE ENTREGA ---")
    entrega: Path | None = None
    if not opciones.sin_zip:
        try:
            entrega = _crear_entrega(RAIZ / "entrega_powerbi.zip")
        except Exception:
            LOGGER.exception("No se pudo crear el ZIP de entrega.")
            return 1

    pbip = modulo.DESTINO / f"{modulo.NOMBRE}.pbip"
    excel = modulo.EXCEL
    duracion = time.perf_counter() - inicio

    LOGGER.info("")
    LOGGER.info("=" * 70)
    LOGGER.info("PROCESO COMPLETO TERMINADO en %.1f segundos", duracion)
    LOGGER.info("=" * 70)
    LOGGER.info("Dashboard editable: %s", pbip)
    if excel.exists():
        LOGGER.info(
            "Excel para subir:   %s (%s)",
            excel,
            _formatear_tamano(excel.stat().st_size),
        )
    if entrega is not None and entrega.exists():
        LOGGER.info(
            "Paquete completo:   %s (%s)",
            entrega,
            _formatear_tamano(entrega.stat().st_size),
        )
    LOGGER.info("")
    LOGGER.info(
        "Para publicar: abre el .pbip en Power BI Desktop y pulsa Publicar, "
        "o sube el Excel desde app.powerbi.com."
    )
    LOGGER.info("Guía: %s", RAIZ / "powerbi" / "SUBIR_A_POWER_BI.md")

    if opciones.abrir:
        _abrir_carpeta(RAIZ / "powerbi")
    if opciones.abrir_dashboard:
        if not _abrir_dashboard(pbip):
            _abrir_carpeta(RAIZ / "powerbi")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelado por el usuario.", file=sys.stderr)
        raise SystemExit(130)
