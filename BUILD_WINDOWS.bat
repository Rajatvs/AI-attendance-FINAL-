@echo off
setlocal
echo ==========================================
echo AttendAI - Windows build setup
echo ==========================================

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 64-bit first.
  pause
  exit /b 1
)

py -3.11 -m venv .venv
if errorlevel 1 (
  echo Could not create virtual environment.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Dependencies installed.
echo Building executable...
pyinstaller --noconfirm --clean AttendAI.spec

echo.
echo Build complete. See dist\AttendAI\AttendAI.exe
echo You can also run run_attendance.bat for source-mode development.
pause
