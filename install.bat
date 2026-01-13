@echo off
setlocal EnableDelayedExpansion
title Python Dependencies Installer - Auto Fix
echo ======================================
echo   Project Dependencies Installer
echo ======================================
echo.

:: Check if Python exists
py --version >nul 2>&1
if errorlevel 1 (
    echo Python not found.
    echo Please install Python 3.10 or newer.
    pause
    exit /b
)

echo Detected Python version:
py --version
echo.

set /p choice=Do you want to check and install dependencies? (Y/N): 
if /I "%choice%" NEQ "Y" (
    echo Canceled.
    exit /b
)

echo.
echo Checking for existing dependencies...

set "MISSING_PACKAGES="
call :CheckPackage PyQt6
call :CheckPackage Pillow
call :CheckPackage torch
call :CheckPackage torchvision
call :CheckPackage opencv-python
call :CheckPackage numpy
call :CheckPackage check_basicsr
call :CheckPackage realesrgan
call :CheckPackage pyqtdarktheme
call :CheckPackage noise
call :CheckPackage onnxruntime
call :CheckPackage rembg
call :CheckPackage PyOpenGL
call :CheckPackage pygame

echo.
if "!MISSING_PACKAGES!"=="" (
    echo All dependencies are already installed!
    goto :Success
)

echo Missing: !MISSING_PACKAGES!
echo.
echo Installing...

:: Handle basicsr specifically if missing
echo !MISSING_PACKAGES! | findstr /C:"basicsr" >nul
if not errorlevel 1 (
    echo.
    echo [FIX] Installing basicsr via local patch for Python 3.14...
    
    :: 1. Download source if not exists
    if not exist "BasicSR-1.4.2" (
        echo Downloading source code...
        if not exist "download_basicsr.py" (
             echo import urllib.request; import tarfile; url = "https://github.com/XPixelGroup/BasicSR/archive/refs/tags/v1.4.2.tar.gz"; filename = "basicsr-1.4.2.tar.gz"; opener = urllib.request.build_opener(); opener.addheaders = [('User-agent', 'Mozilla/5.0')]; urllib.request.install_opener(opener); urllib.request.urlretrieve(url, filename); t = tarfile.open(filename, "r:gz"); t.extractall(); t.close() > download_basicsr.py
        )
        py download_basicsr.py
        
        :: 2. Patch setup.py (simple replacement using python)
        echo Patching setup.py...
        py -c "import os; content = open('BasicSR-1.4.2/setup.py').read().replace('version=get_version(),', \"version='1.4.2',\").replace('version_file =', '#'); open('BasicSR-1.4.2/setup.py', 'w').write(content); open('BasicSR-1.4.2/basicsr/version.py', 'w').write(\"__version__ = '1.4.2'\")"
    )
    
    :: 3. Install from local directory
    py -m pip install ./BasicSR-1.4.2
    
    if errorlevel 1 (
        echo ERROR: Manual install failed.
        pause
        exit /b
    )
    echo [FIX] basicsr installed successfully.
)

:: Install others
py -m pip install -r requirements.txt

:Success
echo.
echo ======================================
echo   Installation completed successfully!
echo ======================================
timeout /t 5 >nul
endlocal
exit

:CheckPackage
set "PKG_NAME=%~1"
if "%PKG_NAME%"=="check_basicsr" set "PKG_NAME=basicsr"
py -c "import importlib.util; exit(0) if importlib.util.find_spec('%PKG_NAME%') else exit(1)" >nul 2>&1
if errorlevel 1 set "MISSING_PACKAGES=!MISSING_PACKAGES! %PKG_NAME%"
exit /b
