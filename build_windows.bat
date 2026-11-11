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
echo Install Python 3.12 from python.org and check Add to PATH.
echo Then open a NEW cmd and run: py -3.12 --version
goto end_fail

:have_python
echo Using: %PY_CMD% %PY_ARGS%
%PY_CMD% %PY_ARGS% -c "import sys; print('Python', sys.version)"
if errorlevel 1 goto end_fail

%PY_CMD% %PY_ARGS% -c "import sys; v=sys.version_info; print(v[:3]); raise SystemExit(0 if (v.major==3 and 10<=v.minor<=12) else 2)" >> "%LOG%" 2>&1
if errorlevel 1 goto bad_version
goto version_ok

:bad_version
echo.
echo [ERROR] Unsupported Python version.
echo Need 3.10 or 3.11 or 3.12. Do NOT use 3.13 or 3.14.
echo Install 3.12, open NEW cmd, then run this script again.
echo It will auto-pick py -3.12 when available.
goto end_fail

:version_ok
echo.
echo [1/3] Installing runtime + PyInstaller...
echo NOTE: winsdk is optional now. 2.4G keyboard + GPW work without it.
echo ----- pip upgrade ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m pip install --upgrade pip >> "%LOG%" 2>&1
echo ----- pip install requirements ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m pip install -r requirements.txt pyinstaller >> "%LOG%" 2>&1
if errorlevel 1 goto pip_fail

echo ----- optional winsdk for Bluetooth ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m pip install -r requirements-bt.txt >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [WARN] winsdk install skipped or failed. Bluetooth battery disabled.
  echo [WARN] GPW mouse and G87 2.4G keyboard still work.
) else (
  echo winsdk installed. Bluetooth keyboard battery enabled.
)

echo.
echo [2/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Building PeripheralBattery.exe ...
echo ----- pyinstaller ----- >> "%LOG%"
%PY_CMD% %PY_ARGS% -m PyInstaller --noconfirm PeripheralBattery.spec >> "%LOG%" 2>&1
if errorlevel 1 goto pyi_fail

if not exist "dist\PeripheralBattery.exe" goto missing_exe

echo.
echo ===== SUCCESS =====
echo EXE: %CD%\dist\PeripheralBattery.exe
echo Run:   dist\PeripheralBattery.exe
echo Probe: dist\PeripheralBattery.exe --probe
echo.
pause
exit /b 0

:pip_fail
echo [ERROR] pip install failed. See build_log.txt
powershell -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 50"
goto end_fail

:pyi_fail
echo [ERROR] PyInstaller failed. See build_log.txt
powershell -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 50"
goto end_fail

:missing_exe
echo [ERROR] dist\PeripheralBattery.exe missing after build.
goto end_fail

:end_fail
echo.
echo ===== FAILED =====
echo Full log: %LOG%
echo.
pause
exit /b 1
