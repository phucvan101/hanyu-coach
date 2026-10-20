@echo off
title Hanyu Coach
cd /d "%~dp0"
echo.
echo  ==== HANYU COACH - Luyen tieng Trung ====
echo.

docker info >nul 2>&1
if %errorlevel%==0 goto dockerok
echo  Docker Desktop chua chay. Dang mo Docker Desktop...
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
set /a tries=0
:waitdocker
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if %errorlevel%==0 goto dockerok
set /a tries+=1
if %tries% lss 60 goto waitdocker
echo.
echo  [LOI] Khong khoi dong duoc Docker Desktop.
echo  Hay mo Docker Desktop bang tay, doi bieu tuong ca voi chuyen sang mau xanh, roi chay lai file nay.
pause
exit /b 1

:dockerok
echo  Dang khoi dong ung dung (lan dau mat 2-5 phut de tai va cai dat)...
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo  [LOI] Khong khoi dong duoc. Kiem tra ket noi mang roi chay lai.
  pause
  exit /b 1
)

set /a tries=0
:waitapp
curl -s http://localhost:8765/api/health >nul 2>&1
if %errorlevel%==0 goto ready
set /a tries+=1
if %tries% gtr 60 goto ready
timeout /t 2 /nobreak >nul
goto waitapp

:ready
start "" http://localhost:8765
echo.
echo  Da mo trinh duyet: http://localhost:8765
echo  Ung dung tiep tuc chay nen. Muon tat han: chay file Stop-Windows.bat
echo.
timeout /t 8
