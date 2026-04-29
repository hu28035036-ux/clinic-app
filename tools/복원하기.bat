@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo.
echo ═══════════════════════════════════════════════════
echo   도수치료예약 - DB 복원 도구
echo ═══════════════════════════════════════════════════
echo.

set "APPDIR=%APPDATA%\도수치료예약"
set "BACKUPS=%APPDIR%\backups"

if not exist "%BACKUPS%" (
    echo [X] 백업 폴더가 없습니다:
    echo     %BACKUPS%
    echo.
    pause
    exit /b 1
)

rem ── 가장 최근 .db 파일 찾기 ──
set "LATEST="
for /f "delims=" %%F in ('dir /b /o:-d "%BACKUPS%\*.db" 2^>nul') do (
    if not defined LATEST set "LATEST=%%F"
)

if not defined LATEST (
    echo [X] 백업 파일 (*.db) 이 없습니다.
    echo     %BACKUPS% 를 확인해주세요.
    echo.
    pause
    exit /b 1
)

echo [ 복원 대상 ]
echo   최신 백업 : %LATEST%
echo   복원 위치 : %APPDIR%\clinic.db
echo.

rem 사용 가능한 백업 목록 10개 미리 보여주기
echo [ 참고: 최신 백업 10개 ]
set "CNT=0"
for /f "delims=" %%F in ('dir /b /o:-d "%BACKUPS%\*.db" 2^>nul') do (
    set /a CNT+=1
    if !CNT! leq 10 echo      !CNT!. %%F
)
echo.

echo [!] 주의사항
echo    - 프로그램이 실행 중이면 먼저 종료해주세요
echo    - 현재 clinic.db 는 자동으로 임시 백업됩니다
echo.

set /p CONFIRM=최신 백업(%LATEST%) 으로 복원하시겠습니까? (Y/N) :
if /i not "%CONFIRM%"=="Y" (
    echo 취소되었습니다.
    pause
    exit /b 0
)

rem ── 현재 DB 를 안전 백업 ──
if exist "%APPDIR%\clinic.db" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "LD=%%I"
    set "TS=!LD:~0,8!_!LD:~8,6!"
    copy "%APPDIR%\clinic.db" "%APPDIR%\clinic_before_restore_!TS!.db" > nul
    echo [OK] 현재 DB 를 임시 백업: clinic_before_restore_!TS!.db
)

rem ── 실제 복원 ──
copy "%BACKUPS%\%LATEST%" "%APPDIR%\clinic.db" /Y > nul

if errorlevel 1 (
    echo [X] 복원 실패
) else (
    echo.
    echo [OK] 복원 완료!
    echo      도수치료예약.exe 를 실행해서 데이터 확인하세요.
)

echo.
echo ═══════════════════════════════════════════════════
pause
