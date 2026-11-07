@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python topilmadi. https://www.python.org/downloads/ dan o'rnating
  echo O'rnatishda "Add python.exe to PATH" belgisini qo'ying.
  pause
  exit /b 1
)
python -c "import PIL" 2>nul || python -m pip install --user pillow
start "" pythonw desktop_pet.py
