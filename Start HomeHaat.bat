@echo off
rem Double-click this file to start HomeHaat (Postgres, Django on :8000, Next.js on :3000).
rem It runs start-homehaat.ps1 with "ExecutionPolicy Bypass", so Windows doesn't block the script.
title Start HomeHaat
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo.
    echo Docker Desktop is not installed.
    echo Get it from https://www.docker.com/products/docker-desktop/ and then double-click this file again.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo.
    echo Docker Desktop is not running.
    echo Open Docker Desktop from the Start menu, wait until it says "Engine running",
    echo then double-click "Start HomeHaat" again.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-homehaat.ps1"
if errorlevel 1 (
    echo.
    echo HomeHaat didn't start. Read the red message above to see why.
    echo.
    pause
    exit /b 1
)
echo.
echo Done. Two new windows are starting HomeHaat. Open http://localhost:3000 in a few seconds.
echo This window can be closed.
pause
