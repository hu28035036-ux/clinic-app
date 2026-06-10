@echo off
chcp 65001 >NUL

REM dev_run.bat — 개발자 환경 자동 시드 + dev 서버 실행
REM   격리 DB:      tests\temp\dev_clinic.db
REM   격리 APPDATA: tests\temp\dev_appdata\
REM   운영 DB (%APPDATA%\도수치료예약\clinic.db) 절대 미접근
REM
REM 사용법:
REM   dev_run.bat            : 격리 DB 가 없으면 시드 후 실행, 있으면 재사용
REM   dev_run.bat --reseed   : 격리 DB 삭제 후 강제 재시드 (환자/치료사/의사 초기화)

call :CHECK_VENV
if errorlevel 1 exit /b %ERRORLEVEL%

REM ──────── 격리 환경 강제 ────────
set "DOSU_DB_PATH=%CD%\tests\temp\dev_clinic.db"
set "APPDATA=%CD%\tests\temp\dev_appdata"

if not exist "tests\temp" mkdir "tests\temp"
if not exist "tests\temp\dev_appdata" mkdir "tests\temp\dev_appdata"

REM ──────── --reseed 플래그 ────────
if /I "%~1"=="--reseed" (
    echo [INFO] --reseed: 격리 DB 삭제 후 재시드합니다.
    del /q "tests\temp\dev_clinic.db" 2>NUL
    rmdir /s /q "tests\temp\dev_appdata" 2>NUL
    mkdir "tests\temp\dev_appdata"
)

REM ──────── 시드 (격리 DB 없을 때만) ────────
if not exist "tests\temp\dev_clinic.db" (
    echo =====================================
    echo [1/2] 더미 데이터 시드 ^(1회^)
    echo =====================================
    venv\Scripts\python.exe scripts\seed_dev_dummy.py
    if errorlevel 1 (
        echo.
        echo [X] 시드 실패. scripts\seed_dev_dummy.py 출력을 확인하세요.
        pause
        exit /b 1
    )
) else (
    echo [INFO] 기존 격리 DB 재사용: tests\temp\dev_clinic.db
    echo        강제 재시드: dev_run.bat --reseed
)

REM ──────── dev 서버 실행 ────────
echo.
echo =====================================
echo [2/2] dev 서버 실행
echo =====================================
echo 격리 DB:    %DOSU_DB_PATH%
echo APPDATA:    %APPDATA%
echo 브라우저:   http://127.0.0.1:8000/
echo 관리자비번: admin1234
echo 종료:       Ctrl+C
echo =====================================
echo.

venv\Scripts\python.exe run.py
exit /b %ERRORLEVEL%

:CHECK_VENV
if not exist "venv\Scripts\python.exe" (
    echo =====================================
    echo [X] venv\Scripts\python.exe 가 없습니다.
    echo =====================================
    echo.
    echo venv 를 새로 만들고 의존성을 설치하세요:
    echo.
    echo   1^) python -m venv venv
    echo   2^) venv\Scripts\python.exe -m pip install -r requirements.txt
    echo   3^) venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    echo.
    pause
    exit /b 2
)
exit /b 0
