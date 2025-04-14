@echo off
:: Script to create Python 3.12 virtual environment and install dependencies

:: Check if Python 3.12 is available
python3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python 3.12 not found. Please install Python 3.12 first.
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python3.12 -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment
    pause
    exit /b 1
)

:: Activate virtual environment and install dependencies
echo Installing dependencies...
call venv\Scripts\activate
pip install --upgrade pip
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo requirements.txt file not found
)
deactivate

echo Virtual environment setup completed!
pause