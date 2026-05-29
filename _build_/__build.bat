@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"
set "PATH=%~dp0upx;%~dp0bin;%PATH%"

echo ==================================================
echo  zbrush-spotlight-extractor - BUILD
echo ==================================================
echo.

REM --- check python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

REM --- check pyinstaller ---
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller not installed
    echo Install: pip install pyinstaller pillow
    pause
    exit /b 1
)

REM --- clean previous builds ---
if exist build (
    echo Cleaning build/
    rmdir /s /q build
)

if exist dist (
    echo Cleaning dist/
    rmdir /s /q dist
)

if exist zsltoimg.exe (
    echo Cleaning previous exe...
    del /f /q zsltoimg.exe
)

REM --- build ---
echo.
echo Building...
echo.

python -OO -m PyInstaller zsltoimg.spec
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b 1
)

REM --- Move the EXE to _build_ root ---
if exist dist\zsltoimg.exe (
    move /y dist\zsltoimg.exe .\zsltoimg.exe >nul
)

REM --- Cleaning up build folder after build ---
if exist build (
    rmdir /s /q build
)
if exist dist (
    rmdir /s /q dist
)

REM --- Post-process with ultra-brute UPX compression ---
if exist zsltoimg.exe (
    if exist upx\upx.exe (
        echo Post-processing with ultra-brute UPX compression...
        upx\upx.exe --ultra-brute --force zsltoimg.exe >nul 2>&1
    )
)

echo.
echo ==========================================
echo  BUILD SUCCESSFUL
echo ==========================================
echo.
echo Output:
echo   _build_\zsltoimg.exe
echo.

REM --- Open output folder ---
start "" "%~dp0"
