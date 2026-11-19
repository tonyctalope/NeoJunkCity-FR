@echo off
rem Patch francais non officiel de Neo Junk City
if not exist "%~dp0vf.ps1" goto missing
if not exist "%~dp0patch\manifest.json" goto missing
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0vf.ps1" install %*
set VFCODE=%ERRORLEVEL%
goto end
:missing
echo Fichiers manquants : extrayez d'abord tout le zip dans un dossier, puis relancez ce fichier depuis ce dossier.
set VFCODE=2
:end
echo.
if not defined NJC_NOPAUSE pause
exit /b %VFCODE%
