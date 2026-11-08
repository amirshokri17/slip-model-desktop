@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build SLIP Model Desktop v0.7 Installer

echo ==========================================================
echo SLIP Model Desktop v0.7 - Windows installer build
echo ORIGINAL SLIP MODEL ONLY - no sprinkler extension
echo ==========================================================
echo.

if not exist "main.py" (
    echo ERROR: main.py is missing. Run this file in the extracted build folder.
    goto :failed
)
if not exist "slip_engine.py" (
    echo ERROR: slip_engine.py is missing.
    goto :failed
)

where py >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python Launcher ^(py^) not found. Install Python 3.15 on this build PC.
    goto :failed
)
py -3.15 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.15 is not installed on the BUILD computer.
    goto :failed
)

if not exist ".buildenv\Scripts\python.exe" (
    echo [1/5] Creating isolated build environment...
    py -3.15 -m venv .buildenv
    if errorlevel 1 goto :failed
)
set "PY=.buildenv\Scripts\python.exe"

"%PY%" -c "import struct; assert struct.calcsize('P') == 8, '64-bit Python required'"
if errorlevel 1 goto :failed

echo [2/5] Installing application dependencies and PyInstaller...
"%PY%" -m pip install --disable-pip-version-check -r requirements.txt "pyinstaller>=6.21,<7"
if errorlevel 1 goto :failed

echo [3/5] Running original v0.7 regression tests...
set "QT_QPA_PLATFORM=offscreen"
"%PY%" -m unittest discover -s . -p "test_*.py" -v
if errorlevel 1 goto :failed
set "QT_QPA_PLATFORM="

echo [4/5] Building the Windows application ^(one-folder distribution^)...
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name SLIP_Model --hidden-import PySide6.QtCharts main.py
if errorlevel 1 goto :failed
if not exist "dist\SLIP_Model\SLIP_Model.exe" (
    echo ERROR: PyInstaller did not produce SLIP_Model.exe.
    goto :failed
)
echo.
echo Application ready: dist\SLIP_Model\SLIP_Model.exe
echo.

echo [5/5] Locating Inno Setup 6 command-line compiler...
set "ISCC="
where ISCC.exe >nul 2>&1
if not errorlevel 1 set "ISCC=ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo.
    echo Inno Setup 6 was not found; the application EXE was still built.
    echo Install Inno Setup from https://jrsoftware.org/isinfo.php
    echo Then rerun BUILD_WINDOWS_INSTALLER.bat or compile SLIP_Model_Installer.iss manually.
    echo.
    echo Do not send the single EXE from the one-folder build without its _internal folder.
    exit /b 2
)

"%ISCC%" "SLIP_Model_Installer.iss"
if errorlevel 1 goto :failed
if not exist "installer\SLIP_Model_Setup_v0_7.exe" (
    echo ERROR: installer output missing.
    goto :failed
)
echo.
echo ==========================================================
echo SUCCESS: installer\SLIP_Model_Setup_v0_7.exe
echo Share only this Setup EXE with your colleagues.
echo TEST the installer on a separate Windows PC before sharing.
echo ==========================================================
exit /b 0

:failed
echo.
echo BUILD FAILED. Read the error above. No installer was finalized.
exit /b 1
