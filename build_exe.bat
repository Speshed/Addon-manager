@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

pushd "%PROJECT_DIR%" >nul || (
    echo [ERROR] Failed to open project folder: "%PROJECT_DIR%"
    exit /b 1
)

set "MANAGER_SCRIPT=%PROJECT_DIR%\manager_main.py"
set "VIEWER_SCRIPT=%PROJECT_DIR%\viewer_main.py"
set "MANAGER_NAME=Larix_Plugin_Manager"
set "VIEWER_NAME=Larix_Viewer"
set "ICON_FILE=%PROJECT_DIR%\icon\logo.ico"
set "DIST_DIR=%PROJECT_DIR%\dist"
set "BUILD_DIR=%PROJECT_DIR%\build"
set "SPEC_DIR=%PROJECT_DIR%"

for %%S in ("%MANAGER_SCRIPT%" "%VIEWER_SCRIPT%") do (
    if not exist %%S (
        echo [ERROR] Entry script not found: %%S
        popd >nul
        exit /b 1
    )
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

set "COMMON_ARGS=--noconfirm --clean --onefile --windowed --distpath "%DIST_DIR%" --specpath "%SPEC_DIR%" --paths "%PROJECT_DIR%\Adapters" --paths "%PROJECT_DIR%\Sets" --paths "%PROJECT_DIR%\Matrix" --paths "%PROJECT_DIR%\Validator" --paths "%PROJECT_DIR%\Viewer" --paths "%PROJECT_DIR%\Sync" --paths "%PROJECT_DIR%\shared" --add-data "%PROJECT_DIR%\Adapters;Adapters" --add-data "%PROJECT_DIR%\Sets;Sets" --add-data "%PROJECT_DIR%\Matrix;Matrix" --add-data "%PROJECT_DIR%\Validator;Validator" --add-data "%PROJECT_DIR%\Viewer;Viewer" --add-data "%PROJECT_DIR%\Sync;Sync" --add-data "%PROJECT_DIR%\shared;shared" --add-data "%PROJECT_DIR%\icon;icon" --hidden-import pyodbc --hidden-import tenacity --hidden-import pandas --hidden-import requests --hidden-import openpyxl --collect-binaries pyodbc --collect-data certifi %PYARROW_ARGS%"

rem --- Clean previous builds ---
if exist "%DIST_DIR%\%MANAGER_NAME%.exe" del /f /q "%DIST_DIR%\%MANAGER_NAME%.exe" >nul 2>&1
if exist "%DIST_DIR%\%VIEWER_NAME%.exe" del /f /q "%DIST_DIR%\%VIEWER_NAME%.exe" >nul 2>&1
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%" >nul 2>&1
if exist "%SPEC_DIR%\%MANAGER_NAME%.spec" del /f /q "%SPEC_DIR%\%MANAGER_NAME%.spec" >nul 2>&1
if exist "%SPEC_DIR%\%VIEWER_NAME%.spec" del /f /q "%SPEC_DIR%\%VIEWER_NAME%.spec" >nul 2>&1

rem =============================================
echo [INFO] Building %MANAGER_NAME%...
echo =============================================
py -3 -m PyInstaller %COMMON_ARGS% --workpath "%BUILD_DIR%\manager" --name "%MANAGER_NAME%" --icon "%ICON_FILE%" "%MANAGER_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] %MANAGER_NAME% build failed.
    popd >nul
    exit /b 1
)
echo [OK] %MANAGER_NAME% done: "%DIST_DIR%\%MANAGER_NAME%.exe"
echo.

rem =============================================
echo [INFO] Building %VIEWER_NAME%...
echo =============================================
py -3 -m PyInstaller %COMMON_ARGS% --workpath "%BUILD_DIR%\viewer" --name "%VIEWER_NAME%" --icon "%ICON_FILE%" "%VIEWER_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] %VIEWER_NAME% build failed.
    popd >nul
    exit /b 1
)
echo [OK] %VIEWER_NAME% done: "%DIST_DIR%\%VIEWER_NAME%.exe"

echo.
echo =============================================
echo [DONE] Both builds completed:
echo   "%DIST_DIR%\%MANAGER_NAME%.exe"
echo   "%DIST_DIR%\%VIEWER_NAME%.exe"
echo =============================================

popd >nul
exit /b 0
