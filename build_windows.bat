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

echo Checking py -3.12 ...
py -3.12 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
if errorlevel 1 goto check_311
set "PY_CMD=py"
set "PY_ARGS=-3.12"
goto have_python

:check_311
echo Checking py -3.11 ...
py -3.11 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
if errorlevel 1 goto check_310
set "PY_CMD=py"
set "PY_ARGS=-3.11"
goto have_python

:check_310
echo Checking py -3.10 ...
py -3.10 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
if errorlevel 1 goto check_3
set "PY_CMD=py"
set "PY_ARGS=-3.10"
goto have_python

:check_3
echo Checking py -3 ...
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
echo Install Python 3.12 from https://www.python.org/downloads/release/python-31210/
echo Check "Add python.exe to PATH" during setup.
echo Then open a NEW cmd window and run this script again.
echo.
echo Quick check:
echo   py -3.12 --version
echo   python --version
echo.
goto end_fail

:have_python
echo Using: %PY_CMD% %PY_ARGS%
%PY_CMD% %PY_ARGS% -c "import sys; print('Python', sys.version)"
if errorlevel 1 goto end_fail

rem Require 3.10-3.12 for reliable wheels.
%PY_CMD% %PY_ARGS% -c "import sys; v=sys.version_info; print('version_tuple', v[:3]); raise SystemExit(0 if (v.major==3 and 10<=v.minor<=12) else 2)" >> "%LOG%" 2>&1
if errorlevel 1 goto bad_version
goto version_ok

:bad_version
echo.
echo [ERROR] Unsupported Python version for this build.
echo Need Python 3.10 / 3.11 / 3.12. Python 3.14 is too new for hidapi/winsdk/pywin32 wheels.
echo.
echo Fix:
echo   1. Install Python 3.12: https://www.python.org/downloads/release/python-31210/
echo   2. Open a NEW cmd
echo   3. Run: py -3.12 --version
echo   4. Run this script again. It prefers 3.12 automatically.
echo.
goto end_fail

:version_ok


echo.
echo [1/3] Installing runtime + PyInstaller...
echo ----- pip upgrade ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m pip install --upgrade pip >> "%LOG%" 2>&1
echo ----- pip install requirements ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m pip install -r requirements.txt pyinstaller >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] pip install failed. Showing build_log.txt:
  echo.
  type "%LOG%"
  goto end_fail
)

echo.
echo [2/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Building PeripheralBattery.exe ...
echo ----- pyinstaller ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m PyInstaller --noconfirm PeripheralBattery.spec >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] PyInstaller failed. Last log lines:
  powershell -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 40"
  goto end_fail
)

if not exist "dist\PeripheralBattery.exe" (
  echo [ERROR] Build finished but dist\PeripheralBattery.exe is missing.
  goto end_fail
)

echo.
echo ===== SUCCESS =====
echo EXE: %CD%\dist\PeripheralBattery.exe
echo.
echo Run:   dist\PeripheralBattery.exe
echo Probe: dist\PeripheralBattery.exe --probe
echo.
pause
exit /b 0

:end_fail
echo.
echo ===== FAILED =====
echo Full log: %LOG%
echo.
pause
exit /b 1
