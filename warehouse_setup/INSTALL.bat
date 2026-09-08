@echo off
echo ============================================
echo   EFL Global IDP - Warehouse Scanner Setup
echo ============================================
echo.
echo Installing required packages...
pip install requests watchdog
echo.
echo Creating scanner folders...
if not exist "scanner_input" mkdir scanner_input
if not exist "scanner_uploaded" mkdir scanner_uploaded
echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo NEXT: Configure your Kodak scanner to save
echo       PDFs into the "scanner_input" folder.
echo.
echo Then double-click "START_SCANNER.bat" to
echo start monitoring.
echo.
pause
