@echo off
title Desktop AI Assistant v4.0 (NovaDesk)

set OLLAMA_MODELS=E:\Study_Cache\model\ollama
set PYTHON=E:\Study_Cache\anaconda\python.exe
if not exist "%PYTHON%" (
    set PYTHON=python
)
set PROJECT=E:\Demo\desk_tools

cd /d "%PROJECT%"

echo  ==================================================
echo    Desktop AI Assistant v4.0 (NovaDesk WorkBuddy)
echo  ==================================================

echo  Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo  Starting Ollama...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo  Ollama service OK!
)

echo  Starting Desktop AI Assistant...
"%PYTHON%" main.py
pause
