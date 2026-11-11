@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG=%~dp0build_log.txt"
echo ===== PeripheralBattery build %DATE% %TIME% ===== > "%LOG%"

echo.
echo Working directory: %CD%
echo Log file: %LOG%
echo.

rem Prefer "py -3", then "python". Windows Store stub often makes bare "python" fail.
set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
    if not errorlevel 1 set "PY=python"
  )
)

if not defined PY (
  echo [ERROR] 没找到可用的 Python。
  echo.
  echo 请先安装 Python 3.10+：https://www.python.org/downloads/
  echo 安装时务必勾选 "Add python.exe to PATH"。
  echo 装好后重新打开命令行，再运行本脚本。
  echo.
  echo 也可在「开始菜单」打开 "x64 Native Tools" 或普通 cmd，执行：
  echo   py -3 --version
  echo   或  python --version
  echo.
  goto :end_fail
)

echo Using: %PY%
%PY% -c "import sys; print('Python', sys.version)" 
if errorlevel 1 goto :end_fail

echo.
echo [1/3] Installing runtime + PyInstaller...
%PY% -m pip install --upgrade pip >> "%LOG%" 2>&1
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo [ERROR] pip install 失败。完整日志见 build_log.txt
  goto :end_fail
)

echo.
echo [2/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Building PeripheralBattery.exe ...
%PY% -m PyInstaller --noconfirm PeripheralBattery.spec
if errorlevel 1 (
  echo [ERROR] PyInstaller 失败。完整日志见 build_log.txt
  goto :end_fail
)

if not exist "dist\PeripheralBattery.exe" (
  echo [ERROR] 构建结束但找不到 dist\PeripheralBattery.exe
  goto :end_fail
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
echo 请把上面的报错，或同目录下的 build_log.txt 发给我。
echo.
pause
exit /b 1
