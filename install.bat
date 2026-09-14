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

:: 升级 pip 并从 requirements.txt 安装所有依赖
python -m pip install --upgrade pip -q
echo 正在安装 requirements.txt 中定义的所有核心依赖包...
python -m pip install -r requirements.txt

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

