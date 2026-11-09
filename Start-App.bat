@echo off
title Waymark APAAR Hub - starting
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run-app.ps1" %*
echo.
pause
