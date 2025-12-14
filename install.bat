@echo off
chcp 65001 >nul
echo Removing old packages...
pip uninstall telegram python-telegram-bot mistralai -y
echo.
echo Upgrading pip...
python -m pip install --upgrade pip
echo.
echo Installing dependencies...
pip install python-telegram-bot>=21.0
pip install mistralai>=1.1.0
pip install pandas>=2.1.0
pip install openpyxl>=3.1.0
pip install python-dotenv>=1.0.0
pip install aiofiles>=23.2.0
echo.
echo Installation complete!
pause

