@echo off
setlocal
cd /d "%~dp0"
echo DesktopPet.exe yig'ilmoqda, biroz kuting...
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
"%VPY%" -c "import PIL, PyInstaller" >nul 2>nul
if errorlevel 1 (
  echo Kerakli kutubxonalar o'rnatilmoqda...
  "%VPY%" -m pip --version >nul 2>nul
  if errorlevel 1 (
    uv pip install --python "%VPY%" pillow pyinstaller
  ) else (
    "%VPY%" -m pip install --disable-pip-version-check pillow pyinstaller
  )
)
"%VPY%" -c "import PIL, PyInstaller" >nul 2>nul
if errorlevel 1 (
  echo Xatolik: kutubxonalarni o'rnatib bo'lmadi. Internetni tekshiring.
  pause
  exit /b 1
)
"%VPY%" -m PyInstaller --noconfirm --onefile --windowed --name DesktopPet desktop_pet.py
if not exist "dist\DesktopPet.exe" (
  echo Xatolik: exe yig'ilmadi. Yuqoridagi xabarni Claude'ga yuboring.
  pause
  exit /b 1
)
copy /Y settings.json dist\ >nul
xcopy /E /I /Y img dist\img >nul
echo.
echo Tayyor: dist papkasida DesktopPet.exe va img papkasi.
echo dist papkasini doimiy joyga qo'ying, masalan C:\DesktopPet, va DesktopPet.exe ni bir marta oching.
echo Shundan keyin kompyuter har yoqilganda o'zi ishga tushadi.
start "" "dist\DesktopPet.exe"
pause
