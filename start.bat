@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo   ResearchOS V2.6.0 (Stable) - Starting Workspace
echo ========================================================
echo.

:: Detect Python
set PYTHON_EXEC=python
if exist "%~dp0venv\Scripts\python.exe" (
    set PYTHON_EXEC="%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0venv312\Scripts\python.exe" (
    set PYTHON_EXEC="%~dp0venv312\Scripts\python.exe"
)

echo [1/2] Starting Backend FastAPI on http://127.0.0.1:5001 ...
start "ResearchOS-Backend" %PYTHON_EXEC% -m uvicorn backend.main:app --host 127.0.0.1 --port 5001 --reload

echo [2/2] Starting Frontend Vite on http://localhost:3000 ...
start "ResearchOS-Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo Waiting for services to initialize...
timeout /t 3 /nobreak >nul
echo Opening browser: http://localhost:3000/ ...
start http://localhost:3000/

echo.
echo ========================================================
echo   ResearchOS is running!
echo   - Web UI:  http://localhost:3000/
echo   - Backend: http://127.0.0.1:5001/
echo   - Docs:    http://127.0.0.1:5001/docs
echo ========================================================
echo Close the background windows to stop services.
