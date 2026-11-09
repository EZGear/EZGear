@echo off
cd /d "%~dp0"
echo DesktopPet.exe yig'ilmoqda, biroz kuting...
python -m pip install --user pillow pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name DesktopPet desktop_pet.py
if not exist dist\DesktopPet.exe (
  echo Xatolik: exe yig'ilmadi. Python o'rnatilganini tekshiring.
  pause
  exit /b 1
)
copy /Y settings.json dist\ >nul
xcopy /E /I /Y img dist\img >nul
echo.
echo Tayyor: dist papkasida DesktopPet.exe va img papkasi.
echo dist papkasini doimiy joyga qo'ying (masalan C:\DesktopPet) va DesktopPet.exe ni bir marta oching.
echo Shundan keyin kompyuter har yoqilganda o'zi ishga tushadi.
start "" dist\DesktopPet.exe
pause
