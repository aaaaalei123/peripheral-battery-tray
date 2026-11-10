@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing runtime + PyInstaller...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo [2/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/3] Building PeripheralBattery.exe ...
python -m PyInstaller --noconfirm PeripheralBattery.spec
if errorlevel 1 goto :fail

echo.
echo Done: dist\PeripheralBattery.exe
echo Run tray:  dist\PeripheralBattery.exe
echo Probe:     dist\PeripheralBattery.exe --probe
exit /b 0

:fail
echo Build failed.
exit /b 1
