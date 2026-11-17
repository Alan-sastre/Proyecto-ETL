@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Proyecto ETL - Ejecutar todo

echo ============================================================
echo  PROYECTO ETL DE APUESTAS DEPORTIVAS
echo  Ejecutando TODO el proceso...
echo ============================================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 goto :sin_python
    set "PY=python"
)

%PY% -c "import pandas, openpyxl, matplotlib" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias por primera vez...
    echo Esto puede tardar unos minutos.
    echo.
    %PY% -m pip install --upgrade pip
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 goto :error_dependencias
)

%PY% ejecutar_todo.py --abrir-dashboard %*
set "CODIGO=%ERRORLEVEL%"
echo.
if not "%CODIGO%"=="0" goto :error_proceso

echo ============================================================
echo  PROCESO TERMINADO CORRECTAMENTE
echo ============================================================
echo.
echo Se ha abierto el dashboard en Power BI Desktop.
echo Si no se ha abierto, abre manualmente:
echo   powerbi\PBIP\Dashboard_Apuestas.pbip
echo.
echo - Dashboard completo: powerbi\PBIP\Dashboard_Apuestas.pbip
echo - Archivo para subir:  powerbi\datos_powerbi.xlsx
echo - Entrega completa:    entrega_powerbi.zip
echo.
pause
exit /b 0

:sin_python
echo.
echo ERROR: No se ha encontrado Python.
echo Instala Python 3.10 o superior desde https://www.python.org/downloads/
echo y marca la opcion "Add Python to PATH".
echo.
pause
exit /b 1

:error_dependencias
echo.
echo ERROR: No se pudieron instalar las dependencias.
echo Comprueba tu conexion a Internet y vuelve a intentarlo.
echo.
pause
exit /b 1

:error_proceso
echo.
echo ERROR: El proceso ha fallado. Revisa los mensajes anteriores.
echo.
pause
exit /b %CODIGO%
