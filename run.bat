@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Meridian

:: ── Check for Python ─────────────────────────────────────────────────
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [Meridian] Python was not found on your system.
    echo.
    echo  Please install Python 3.10 or later from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: ── Verify Python version is 3.10+ ──────────────────────────────────
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "pyver=%%v"
for /f "tokens=1,2 delims=." %%a in ("%pyver%") do (
    set "pymajor=%%a"
    set "pyminor=%%b"
)
if %pymajor% lss 3 goto :python_too_old
if %pymajor% equ 3 if %pyminor% lss 10 goto :python_too_old
goto :python_ok

:python_too_old
echo.
echo  [Meridian] Python %pyver% detected, but 3.10 or later is required.
echo  Please upgrade from https://www.python.org/downloads/
echo.
pause
exit /b 1

:python_ok

:: ── Install / update dependencies ────────────────────────────────────
:: Uses a stamp file so pip only runs once per requirements.txt change.
set "stamp=cache\.deps_installed"
set "reqs=requirements.txt"

set "need_install=0"
if not exist "%stamp%" set "need_install=1"

if "!need_install!"=="0" (
    for /f %%A in ('dir /b /o:d "%reqs%" "%stamp%" 2^>nul') do set "newest=%%A"
    if /i "!newest!"=="%reqs%" set "need_install=1"
)

if "!need_install!"=="1" (
    echo.
    echo  [Meridian] Installing dependencies...
    echo.
    if not exist cache mkdir cache
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r "%reqs%"
    if %errorlevel% neq 0 (
        echo.
        echo  [Meridian] Dependency installation failed. Check the output above.
        echo.
        pause
        exit /b 1
    )
    echo.> "%stamp%"
    echo  [Meridian] Dependencies installed successfully.
    echo.
)

:: ── Launch Meridian ──────────────────────────────────────────────────
python main.py
if %errorlevel% neq 0 (
    echo.
    echo  [Meridian] Meridian exited with an error. Check cache\latest.log for details.
    echo.
    pause
)
endlocal
