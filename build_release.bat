@echo off
setlocal enabledelayedexpansion

REM ======================================================================
REM  Book Creater Agent - one-click build
REM  Output: dist\BookCreaterAgent.exe (self-contained, share-ready)
REM
REM  Prerequisites (only on the dev machine):
REM    - Python 3.11+ (py launcher recommended)
REM    - Node.js 18+
REM ======================================================================

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set BACKEND=%ROOT%\backend
set FRONTEND=%ROOT%\frontend
set OUT=%ROOT%\dist

echo.
echo === [1/4] Building frontend static bundle ============================
pushd "%FRONTEND%"
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install --legacy-peer-deps
    if errorlevel 1 (popd & goto :fail)
)
set BUILD_TARGET=static
call npm run build
if errorlevel 1 (popd & goto :fail)
popd
if not exist "%FRONTEND%\out" (
    echo [ERROR] frontend\out not produced. Build aborted.
    goto :fail
)

echo.
echo === [2/4] Preparing backend virtual env ==============================
pushd "%BACKEND%"
if not exist .venv (
    echo Creating Python venv...
    where py >nul 2>nul && (py -3.11 -m venv .venv 2>nul || py -3.12 -m venv .venv 2>nul || py -3.13 -m venv .venv 2>nul || py -m venv .venv) || python -m venv .venv
)
if not exist .venv\Scripts\activate.bat (popd & echo [ERROR] venv creation failed & goto :fail)
call .venv\Scripts\activate.bat
if errorlevel 1 (popd & goto :fail)
python -m pip install --upgrade pip >nul
echo Installing backend deps + pyinstaller...
pip install -e . pyinstaller
if errorlevel 1 (popd & goto :fail)

echo.
echo === [3/4] PyInstaller bundling =======================================
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
pyinstaller --clean --noconfirm build.spec
if errorlevel 1 (popd & goto :fail)
popd

echo.
echo === [4/4] Copying artifact to dist\ ==================================
if not exist "%OUT%" mkdir "%OUT%"
copy /y "%BACKEND%\dist\BookCreaterAgent.exe" "%OUT%\BookCreaterAgent.exe" >nul
if errorlevel 1 goto :fail

echo.
echo ======================================================================
echo  BUILD SUCCESS
echo  Artifact: %OUT%\BookCreaterAgent.exe
echo  Double-click it to launch. Browser opens automatically.
echo  User data lives in the data\ folder next to the exe.
echo ======================================================================
endlocal
exit /b 0

:fail
echo.
echo [ERROR] Build failed. Check the log above.
endlocal
exit /b 1
