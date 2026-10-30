@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo   Danbooru Library Master - building the .exe
echo ==============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found.
  echo Install Python 3.10 or newer from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer, then run this file again.
  pause
  exit /b 1
)

echo Choose the build type:
echo   1 - folder, starts instantly, all features   ^(about 250 MB^)
echo   2 - ONE .exe file, all features              ^(about 100 MB, starts in 2-6 seconds^)
echo   3 - ONE .exe file, without video support     ^(about 40 MB, videos open in your own player^)
echo.
choice /c 123 /n /m "Your choice [1/2/3]: "
set MODE=%errorlevel%

set "INSTALL=%LOCALAPPDATA%\Programs\DanbooruLibraryMaster"
set "REQ=requests numpy Pillow keyring"
if not "%MODE%"=="3" set "REQ=%REQ% opencv-python-headless"
set "FLAGS=--noconfirm --clean --windowed --name DanbooruLibraryMaster --icon icon.ico --add-data "icon.ico;." --hidden-import dlm.random_viewer --hidden-import dlm.browse --hidden-import dlm.app_paths --hidden-import dlm.locale_en --hidden-import keyring.backends.Windows --exclude-module matplotlib --exclude-module scipy --exclude-module pandas --exclude-module IPython"
if "%MODE%"=="3" set "FLAGS=%FLAGS% --exclude-module cv2"
if not "%MODE%"=="1" set "FLAGS=%FLAGS% --onefile"
if "%MODE%"=="1" (set "BUILT=%~dp0dist\DanbooruLibraryMaster\DanbooruLibraryMaster.exe") else (set "BUILT=%~dp0dist\DanbooruLibraryMaster.exe")

if exist "%~dp0dist" rmdir /s /q "%~dp0dist"
if not exist ".venv_build\Scripts\activate.bat" (
  echo.
  echo Creating a private build environment ^(temporary, removed at the end^)...
  python -m venv .venv_build || goto :fail
)
call ".venv_build\Scripts\activate.bat" || goto :fail

echo.
echo Installing packages ^(a few minutes^)...
python -m pip install --upgrade pip >nul
pip install %REQ% pyinstaller || goto :fail

echo.
echo Building the program ^(a few minutes^)...
pyinstaller %FLAGS% danbooru_library_master.py || goto :fail
if not exist "%BUILT%" goto :fail

echo.
echo Checking the build...
if exist "%LOCALAPPDATA%\DanbooruLibraryMaster\selftest.txt" del "%LOCALAPPDATA%\DanbooruLibraryMaster\selftest.txt"
start /wait "" "%BUILT%" --selftest
if exist "%LOCALAPPDATA%\DanbooruLibraryMaster\selftest.txt" (
  type "%LOCALAPPDATA%\DanbooruLibraryMaster\selftest.txt"
) else (
  echo Self-check did not produce a report - the program may be blocked by an antivirus.
)

echo.
echo Installing the program to %INSTALL% ...
if exist "%INSTALL%" rmdir /s /q "%INSTALL%"
mkdir "%INSTALL%" || goto :fail
if "%MODE%"=="1" (
  robocopy "%~dp0dist\DanbooruLibraryMaster" "%INSTALL%" /E /NFL /NDL /NJH /NJS /NP >nul
  if errorlevel 8 goto :fail
  set "EXE=%INSTALL%\DanbooruLibraryMaster.exe"
) else (
  copy /y "%BUILT%" "%INSTALL%\DanbooruLibraryMaster.exe" >nul || goto :fail
  set "EXE=%INSTALL%\DanbooruLibraryMaster.exe"
)

echo Creating desktop shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcuts.ps1" -Exe "%EXE%"

echo.
echo Removing temporary build files...
call deactivate >nul 2>nul
if exist ".venv_build" rmdir /s /q ".venv_build"
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "DanbooruLibraryMaster.spec" del /q "DanbooruLibraryMaster.spec"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo DONE. Three shortcuts were placed on your desktop:
echo   "Danbooru Library"  - the main program
echo   "Random viewer"     - random-order viewer
echo   "Post browser"      - recommendation feed
echo The program is installed in: %INSTALL%
echo You may now delete this whole folder; keep it only if you want to rebuild/update later.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Read the messages above ^(you can paste them into a GitHub issue^).
pause
exit /b 1
