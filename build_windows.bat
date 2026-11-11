@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG=%~dp0build_log.txt"
echo ===== PeripheralBattery build %DATE% %TIME% ===== > "%LOG%"

echo.
echo Working directory: %CD%
echo Log file: %LOG%
echo.

set "PY_CMD="
set "PY_ARGS="

where py >nul 2>&1
if errorlevel 1 goto try_python
py -3 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
if errorlevel 1 goto try_python
set "PY_CMD=py"
set "PY_ARGS=-3"
goto have_python

:try_python
where python >nul 2>&1
if errorlevel 1 goto no_python
python -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
if errorlevel 1 goto no_python
set "PY_CMD=python"
set "PY_ARGS="
goto have_python

:no_python
echo [ERROR] Python not found in PATH.
echo.
echo Install Python 3.10+ from https://www.python.org/downloads/
echo Check "Add python.exe to PATH" during setup.
echo Then open a NEW cmd window and run this script again.
echo.
echo Quick check:
echo   py -3 --version
echo   python --version
echo.
goto end_fail

:have_python
echo Using: %PY_CMD% %PY_ARGS%
%PY_CMD% %PY_ARGS% -c "import sys; print('Python', sys.version)"
if errorlevel 1 goto end_fail

echo.
echo [1/3] Installing runtime + PyInstaller...
%PY_CMD% %PY_ARGS% -m pip install --upgrade pip >> "%LOG%" 2>&1
%PY_CMD% %PY_ARGS% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto pip_fail

echo.
echo [2/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Building PeripheralBattery.exe ...
%PY_CMD% %PY_ARGS% -m PyInstaller --noconfirm PeripheralBattery.spec
if errorlevel 1 goto pyi_fail

if not exist "dist\PeripheralBattery.exe" goto missing_exe

echo.
echo ===== SUCCESS =====
echo EXE: %CD%\dist\PeripheralBattery.exe
echo.
echo Run:   dist\PeripheralBattery.exe
echo Probe: dist\PeripheralBattery.exe --probe
echo.
pause
exit /b 0

:pip_fail
echo [ERROR] pip install failed. See build_log.txt
goto end_fail

:pyi_fail
echo [ERROR] PyInstaller failed. See build_log.txt
goto end_fail

:missing_exe
echo [ERROR] Build finished but dist\PeripheralBattery.exe is missing.
goto end_fail

:end_fail
echo.
echo ===== FAILED =====
echo Send the error above or build_log.txt.
echo.
pause
exit /b 1
