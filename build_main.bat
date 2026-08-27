@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "APP_NAME=Larix_Main"
set "ENTRY=main.py"
set "ICON_ARG="

if not exist "%ENTRY%" (
  echo [ERROR] Entry file not found: "%ENTRY%"
  pause
  exit /b 1
)

py -3 --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python launcher "py -3" was not found.
  pause
  exit /b 1
)

py -3 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller was not found. Installing...
  py -3 -m pip install pyinstaller
  if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
  )
)

echo Checking optional runtime dependencies...
py -3 -c "import PySide6" >nul 2>&1
if errorlevel 1 echo [WARN] PySide6 is not installed.
py -3 -c "import pandas" >nul 2>&1
if errorlevel 1 echo [WARN] pandas is not installed.
py -3 -c "import requests" >nul 2>&1
if errorlevel 1 echo [WARN] requests is not installed.
py -3 -c "import openpyxl" >nul 2>&1
if errorlevel 1 echo [WARN] openpyxl is not installed.
py -3 -c "import pyodbc" >nul 2>&1
if errorlevel 1 echo [WARN] pyodbc is not installed.
py -3 -c "import tenacity" >nul 2>&1
if errorlevel 1 echo [WARN] tenacity is not installed.
py -3 -c "import pyarrow" >nul 2>&1
if errorlevel 1 echo [WARN] pyarrow is not installed.
py -3 -c "import certifi" >nul 2>&1
if errorlevel 1 echo [WARN] certifi is not installed.

if exist "icon\logo.ico" set "ICON_ARG=--icon=icon\logo.ico"

echo.
echo =============================================
echo Building %APP_NAME% from %ENTRY%
echo =============================================

py -3 -m PyInstaller --noconfirm --onefile --windowed --name "%APP_NAME%" %ICON_ARG% --add-data "icon;icon" --add-data "shared;shared" --add-data "Adapters;Adapters" --add-data "Sets;Sets" --add-data "Matrix;Matrix" --add-data "Validator;Validator" --add-data "Viewer;Viewer" --add-data "Sync;Sync" --add-data "importxml;importxml" --hidden-import manager_main --hidden-import viewer_main --hidden-import shared.app_common --hidden-import shared.dialogs --hidden-import shared.theme_toggle --hidden-import shared.excel_parser --hidden-import shared.excel_template --hidden-import Adapters.ui --hidden-import Sets.ui --hidden-import Matrix.ui --hidden-import Validator.ui --hidden-import Viewer.ui --hidden-import Viewer.keycloak_auth --hidden-import Sync.ui --hidden-import Sync.odbc --hidden-import Sync.tls --hidden-import importxml.XML "%ENTRY%"

if errorlevel 1 (
  echo [ERROR] Build failed.
  pause
  exit /b 1
)

echo.
echo Done: dist\%APP_NAME%.exe
pause
