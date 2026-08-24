@echo off
REM Start backend (Windows batch). Uses managed Python venv.
setlocal
set PY=C:\Users\admin\.workbuddy\binaries\python\envs\btplat\Scripts\python.exe
pushd "%~dp0..\backend"
echo Starting uvicorn...
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
popd
endlocal