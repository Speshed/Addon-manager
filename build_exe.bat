@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

pushd "%PROJECT_DIR%" >nul || (
    echo [ERROR] Failed to open project folder: "%PROJECT_DIR%"
    exit /b 1
)

set "ENTRY_SCRIPT=%PROJECT_DIR%\main.py"
set "APP_NAME=Larix_Plugin_Manager"
set "ICON_FILE=%PROJECT_DIR%\icon\logo_transparent_multi.ico"
set "DIST_DIR=%PROJECT_DIR%\dist"
set "BUILD_DIR=%PROJECT_DIR%\build"
set "SPEC_DIR=%PROJECT_DIR%"

if not exist "%ENTRY_SCRIPT%" (
    echo [ERROR] Entry script not found: "%ENTRY_SCRIPT%"
    popd >nul
    exit /b 1
)

where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Command "py" was not found. Install Python Launcher for Windows.
    popd >nul
    exit /b 1
)

py -3 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed in the selected Python.
    echo Install it with: py -3 -m pip install pyinstaller
    popd >nul
    exit /b 1
)

for %%P in (PySide6 pandas requests openpyxl pyodbc tenacity) do (
    py -3 -c "import %%P" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Missing package: %%P
        echo Install project dependencies and run the build again.
        popd >nul
        exit /b 1
    )
)

set "PYARROW_ARGS="
py -3 -c "import pyarrow" >nul 2>&1
if not errorlevel 1 (
    set "PYARROW_ARGS=--collect-binaries pyarrow --collect-data pyarrow --hidden-import pyarrow --hidden-import pyarrow.lib --hidden-import pyarrow.compute --hidden-import pyarrow._compute --hidden-import pyarrow.parquet --hidden-import pyarrow._parquet --hidden-import pyarrow.dataset --hidden-import pyarrow._dataset --hidden-import pyarrow._dataset_parquet --hidden-import pyarrow.fs --hidden-import pyarrow._fs --hidden-import pyarrow.pandas_compat"
)
if errorlevel 1 (
    echo [WARN] pyarrow was not found.
    echo [WARN] The built EXE will work, but Parquet export in BIM Sync mode will be unavailable.
)

if exist "%DIST_DIR%\%APP_NAME%.exe" del /f /q "%DIST_DIR%\%APP_NAME%.exe" >nul 2>&1
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%SPEC_DIR%\%APP_NAME%.spec" del /f /q "%SPEC_DIR%\%APP_NAME%.spec" >nul 2>&1

echo [INFO] Starting build...

py -3 -m PyInstaller ^
 --noconfirm ^
 --clean ^
 --onefile ^
 --windowed ^
 --name "%APP_NAME%" ^
 --icon "%ICON_FILE%" ^
 --distpath "%DIST_DIR%" ^
 --workpath "%BUILD_DIR%" ^
 --specpath "%SPEC_DIR%" ^
 --paths "%PROJECT_DIR%\Adapters" ^
 --paths "%PROJECT_DIR%\Larix_Set" ^
 --paths "%PROJECT_DIR%\Matrix" ^
 --paths "%PROJECT_DIR%\Parameter" ^
 --paths "%PROJECT_DIR%\Viewer" ^
 --paths "%PROJECT_DIR%\viewer subd" ^
 --hidden-import Adapter ^
 --hidden-import Larix_set ^
 --hidden-import matrix_ui ^
 --hidden-import Parameters ^
 --hidden-import Viewer ^
 --hidden-import bim_sync_gui ^
 --hidden-import odbc_manager ^
 --hidden-import tls_manager ^
 --add-data "%PROJECT_DIR%\icon;icon" ^
 --collect-data certifi ^
 %PYARROW_ARGS% ^
 "%ENTRY_SCRIPT%"

if errorlevel 1 (
    echo [ERROR] Build failed.
    popd >nul
    exit /b 1
)

echo.
echo [OK] Build completed:
echo "%DIST_DIR%\%APP_NAME%.exe"

popd >nul
exit /b 0
