@echo off
title Desktop AI Pet

:: 设置环境变量：指定 Ollama 与 Whisper 模型缓存均在 E 盘
set OLLAMA_MODELS=E:\Study_Cache\model\ollama
set PYTHON=E:\Study_Cache\anaconda\python.exe
set PROJECT=E:\Demo\desk_tools

echo.
echo  ========================================
echo    Desktop AI Pet - Starting...
echo  ========================================
echo.

if not exist "%PYTHON%" (
    echo  ERROR: Python not found at %PYTHON%
    pause
    exit /b 1
)

echo  Python : %PYTHON%
echo  Project: %PROJECT%
echo  Models : E:\Study_Cache\model\ollama
echo.

echo  Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo  Ollama not running, starting it with E:\Study_Cache\model\ollama ...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo  Ollama OK
)

echo.
echo  Launching pet window...
echo.

cd /d "%PROJECT%"
"%PYTHON%" main.py

echo.
echo  ----------------------------------------
echo  Program exited. Error code: %errorlevel%
echo  ----------------------------------------
pause
