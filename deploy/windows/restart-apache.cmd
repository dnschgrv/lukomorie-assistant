@echo off
"C:\Apache24\bin\httpd.exe" -t || exit /b 1
"C:\Apache24\bin\httpd.exe" -k restart
