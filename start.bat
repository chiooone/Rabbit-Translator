@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating venv...
  python -m venv .venv || goto :err
)
call .venv\Scripts\activate
echo Installing dependencies...
pip install -r requirements.txt || goto :err

python app.py
goto :eof

:err
echo Failed to start Rabbit Translator.
pause
