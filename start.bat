@echo off
title Desktop AI Pet v2.0 (3D VRM)

set OLLAMA_MODELS=E:\Study_Cache\model\ollama
set PYTHON=E:\Study_Cache\anaconda\python.exe
set PROJECT=E:\Demo\desk_tools

cd /d "%PROJECT%"

echo  ==================================================
echo    Desktop AI Assistant v2.0 (3D VRM + DeepSeek)
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

echo  Starting 3D Desktop Pet...
"%PYTHON%" main.py
pause
