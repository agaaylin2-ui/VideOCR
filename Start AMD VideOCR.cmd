@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-amd-video.ps1"
if errorlevel 1 pause
