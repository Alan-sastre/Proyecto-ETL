@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Crear ejecutable del Proyecto ETL

echo ============================================================
echo  CREAR EJECUTABLE DE WINDOWS
echo ============================================================
echo.
echo Este proceso hay que hacerlo UNA vez en Windows.
echo Genera: dist\Ejecutar_Proyecto_ETL.exe
echo.

where py >nul 2>nul
if not errorlevel 1 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 goto :sin_python
    set "PY=python"
)

echo Instalando dependencias y PyInstaller...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo.
echo Empaquetando...
%PY% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --name Ejecutar_Proyecto_ETL ^
    --add-data "powerbi\build_pbip.py;powerbi" ^
    --add-data "powerbi\SUBIR_A_POWER_BI.md;powerbi" ^
    --add-data "powerbi\ABRIR_EN_POWER_BI.md;powerbi" ^
    --add-data "powerbi\GUIA_DASHBOARD.md;powerbi" ^
    --add-data "powerbi\medidas_DAX.md;powerbi" ^
    --add-data "COMO_EJECUTAR_TODO.md;." ^
    --add-data "README.md;." ^
    --add-data "requirements.txt;." ^
    --hidden-import main ^
    --collect-submodules src ^
    ejecutar_todo.py
if errorlevel 1 goto :error

if not exist "dist\powerbi" mkdir "dist\powerbi"
if not exist "dist\powerbi\PBIP" mkdir "dist\powerbi\PBIP"
copy /Y "powerbi\SUBIR_A_POWER_BI.md" "dist\powerbi\" >nul
copy /Y "powerbi\ABRIR_EN_POWER_BI.md" "dist\powerbi\" >nul
copy /Y "powerbi\GUIA_DASHBOARD.md" "dist\powerbi\" >nul
copy /Y "powerbi\medidas_DAX.md" "dist\powerbi\" >nul
copy /Y "COMO_EJECUTAR_TODO.md" "dist\" >nul
copy /Y "powerbi\PBIP\LEEME - COMO ABRIR.txt" "dist\powerbi\PBIP\" >nul
copy /Y "README.md" "dist\" >nul
copy /Y "requirements.txt" "dist\" >nul

echo.
echo ============================================================
echo  EJECUTABLE CREADO
echo ============================================================
echo.
echo Archivo: dist\Ejecutar_Proyecto_ETL.exe
echo.
echo Puedes copiar ese .exe a cualquier carpeta de Windows y
echo hacer doble clic. Generara los datos y los entregables
echo en la misma carpeta donde este el .exe.
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

:error
echo.
echo ERROR: No se pudo crear el ejecutable.
echo Revisa los mensajes anteriores.
echo.
pause
exit /b 1
