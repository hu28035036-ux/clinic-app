@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo.
echo ═══════════════════════════════════════════════════
echo   도수치료예약 - 데이터 백업 도구
echo ═══════════════════════════════════════════════════
echo.

set "SRC=%APPDATA%\도수치료예약"

if not exist "%SRC%" (
    echo [X] 데이터 폴더를 찾을 수 없습니다:
    echo     %SRC%
    echo.
    echo 프로그램을 한 번이라도 실행했는지 확인해주세요.
    echo.
    pause
    exit /b 1
)

rem ── 타임스탬프 생성 (YYYYMMDD_HHMMSS) ──
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "LD=%%I"
set "STAMP=%LD:~0,8%_%LD:~8,6%"
set "DEST=%USERPROFILE%\Desktop\도수치료예약_백업_%STAMP%"

echo [ 백업 시작 ]
echo   원본 : %SRC%
echo   대상 : %DEST%
echo.

xcopy "%SRC%" "%DEST%" /E /I /Y /Q > nul

if errorlevel 1 (
    echo [X] 백업 실패
    echo     바탕화면 쓰기 권한을 확인해주세요.
) else (
    echo [OK] 백업 완료!
    echo.
    echo      바탕화면을 확인하세요:
    echo      %DEST%
    echo.
    rem 크기 계산
    for /f "tokens=3" %%A in ('dir /s /-c "%DEST%" ^| findstr /C:"File(s)"') do set "SIZE=%%A"
    if defined SIZE echo      용량: !SIZE! bytes
)

echo.
echo ═══════════════════════════════════════════════════
pause
