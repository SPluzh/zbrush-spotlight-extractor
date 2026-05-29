@echo off
title ZSL Image Extractor
echo ===================================================
echo               ZSL Image Extractor                  
echo ===================================================
echo.

if "%~1" == "" (
    echo [ERROR] No file specified.
    echo Please drag and drop a .ZSL file onto this BAT script.
    echo.
    pause
    exit /b
)

echo Processing: %~1
echo.

python "%~dp0zsltoimg.py" "%~1"

echo.
echo ===================================================
echo Done! You can close this window now.
echo ===================================================
pause
