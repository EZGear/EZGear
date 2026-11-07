@echo off
cd /d "%~dp0"
python -m pip install --user pillow pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name DesktopPet desktop_pet.py
copy /Y settings.json dist\ >nul
xcopy /E /I /Y img dist\img >nul
echo.
echo Tayyor: dist\DesktopPet.exe  (img papkasi yonida turishi kerak)
pause
