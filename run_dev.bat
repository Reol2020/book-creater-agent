@echo off
REM Dev mode: backend (8000) + frontend (3000) in separate windows.

set ROOT=%~dp0
start "backend"  cmd /k "cd /d %ROOT%backend  && (if not exist .venv (py -3.11 -m venv .venv)) && call .venv\Scripts\activate && pip install -e . >nul && uvicorn app.main:app --reload --port 8000"
start "frontend" cmd /k "cd /d %ROOT%frontend && (if not exist node_modules (npm install)) && npm run dev"
