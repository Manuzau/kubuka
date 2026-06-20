@echo off
title KUBUKA - Iniciar Sistema
cd /d "%~dp0"

echo.
echo  Bem-vindo ao KUBUKA
echo  A iniciar todos os servicos...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"

echo.
pause
