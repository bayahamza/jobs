@echo off
chcp 65001 >nul
title Planificateur — Concours Watcher

:: Ce script crée une tâche planifiée Windows pour lancer le watcher chaque matin à 8h00

set SCRIPT_DIR=%~dp0
set SCRIPT_PATH=%SCRIPT_DIR%run.bat

echo.
echo ══════════════════════════════════════════════════════
echo   INSTALLATION — Tâche Planifiée Quotidienne (08h00)
echo ══════════════════════════════════════════════════════
echo.
echo Dossier du script : %SCRIPT_DIR%
echo.

:: Supprime l'ancienne tâche si elle existe
schtasks /delete /tn "ConcoursMarocWatcher" /f >nul 2>&1

:: Crée la nouvelle tâche : chaque jour à 08h00
schtasks /create ^
  /tn "ConcoursMarocWatcher" ^
  /tr "\"%SCRIPT_PATH%\"" ^
  /sc DAILY ^
  /st 08:00 ^
  /rl HIGHEST ^
  /f

if %errorlevel%==0 (
    echo.
    echo [OK] Tâche planifiée créée avec succès !
    echo      Le watcher se lancera chaque jour à 08h00.
    echo.
    echo Pour vérifier : Planificateur de tâches Windows
    echo Pour modifier l'heure : relance ce script après avoir changé /st 08:00
) else (
    echo.
    echo [ERREUR] Impossible de créer la tâche.
    echo Lance ce script en tant qu'Administrateur (clic droit → Exécuter en tant qu'administrateur)
)

echo.
pause
