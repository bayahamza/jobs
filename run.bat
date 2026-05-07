@echo off
chcp 65001 >nul
title Concours Maroc Watcher — Hamza Bayahia

cd /d "%~dp0"

echo.
echo ══════════════════════════════════════════
echo   CONCOURS MAROC WATCHER
echo ══════════════════════════════════════════
echo.

:: Cherche Python
where python >nul 2>&1
if %errorlevel%==0 (
    set PY=python
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        set PY=py
    ) else (
        echo [ERREUR] Python non trouve. Installe Python depuis python.org
        pause
        exit /b 1
    )
)

:: Installe les dependances si besoin
%PY% -c "import bs4" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installation des dependances...
    %PY% -m pip install -r requirements.txt --quiet
)

:: Lance le watcher
%PY% watcher.py

echo.
echo Appuie sur une touche pour fermer...
pause >nul
