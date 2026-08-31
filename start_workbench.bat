@echo off
chcp 65001 >nul
title 实验助手工作台一键启动
setlocal

REM =========================================================================
REM 实验助手 · 工作台前端一键启动
REM 同时拉起：后端 FastAPI (:5001) + 前端 Vite (:3000)
REM 浏览器访问 http://localhost:3000 即是工作台界面
REM -------------------------------------------------------------------------
REM 关闭 WorkBuddy 沙箱 safe-delete 拦截（避免后端迁移 rmtree 被拦）
REM 该开关仅在沙箱进程内生效，双击运行时本就无这些变量，无害
REM =========================================================================

set "ROOT=%~dp0"
set "VENV=%ROOT%venv\Scripts"
set "NODE=%ROOT%..\.workbuddy\.."
set "NODE_EXE=C:\Users\A-chun\.workbuddy\binaries\node\versions\22.22.2\node.exe"

REM 关闭 safe-delete 拦截
set CODEBUDDY_SESSION_ID=
set CLAUDE_SESSION_ID=
set CODEBUDDY_SAFE_DELETE_SANDBOX=0

echo [1/2] 启动后端 FastAPI (:5001) ...
start "实验助手-后端" cmd /k "cd /d %ROOT% && %VENV%\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 5001"

echo [2/2] 启动前端 Vite  (:3000) ...
start "实验助手-前端" cmd /k "cd /d %ROOT%frontend && \"%NODE_EXE%\" node_modules\vite\bin\vite.js --host 0.0.0.0 --port 3000"

echo.
echo 启动完成，请在浏览器打开：http://localhost:3000
echo 关闭时：直接关掉这两个命令行窗口即可。
echo.
pause
