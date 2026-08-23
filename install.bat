@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║      🔧 桌面 AI 桌宠 - 依赖安装程序           ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  正在安装 Python 依赖包...
echo  （首次安装可能需要几分钟，请耐心等待）
echo.

:: 升级 pip
python -m pip install --upgrade pip -q

:: 安装核心 UI 依赖
echo [1/6] 安装 PyQt6（UI框架）...
pip install PyQt6 -q

:: 安装 AI 依赖
echo [2/6] 安装 HTTP 客户端...
pip install httpx -q

:: 安装语音相关
echo [3/6] 安装语音识别（faster-whisper，支持GPU）...
pip install faster-whisper -q

echo [4/6] 安装语音合成（edge-tts）...
pip install edge-tts -q

echo [5/6] 安装音频录制（pyaudio）...
pip install pyaudio -q

:: 安装系统控制和文件处理
echo [6/6] 安装其他工具包...
pip install pyautogui pynput pywin32 Pillow python-docx openpyxl PyPDF2 -q

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║      ✅ 安装完成！                             ║
echo  ║                                              ║
echo  ║  现在可以双击 start.bat 启动桌宠了！           ║
echo  ║                                              ║
echo  ║  首次启动会下载 Whisper 语音模型               ║
echo  ║  模型将保存到: E:\Study_Cache\model\whisper   ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
