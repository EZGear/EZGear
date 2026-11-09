@echo off
setlocal
cd /d "%~dp0"
rem --- Dastur papkasida alohida Python muhiti (.venv) tayyorlash ---
if not exist ".venv\Scripts\python.exe" (
  echo Python muhiti tayyorlanmoqda...
  python -m venv .venv >nul 2>nul
)
if not exist ".venv\Scripts\python.exe" (
  uv venv .venv >nul 2>nul
)
if not exist ".venv\Scripts\python.exe" (
  echo Python topilmadi. https://www.python.org/downloads/ dan o'rnating
  echo O'rnatishda "Add python.exe to PATH" belgisini qo'ying.
  pause
  exit /b 1
)
set "VPY=.venv\Scripts\python.exe"
"%VPY%" -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Kerakli kutubxonalar o'rnatilmoqda...
  "%VPY%" -m pip --version >nul 2>nul
  if errorlevel 1 (
    uv pip install --python "%VPY%" pillow
  ) else (
    "%VPY%" -m pip install --disable-pip-version-check pillow
  )
)
"%VPY%" -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Xatolik: kutubxonalarni o'rnatib bo'lmadi. Internetni tekshiring.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" desktop_pet.py
