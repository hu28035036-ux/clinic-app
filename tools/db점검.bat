@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

pushd "%~dp0.."

if not exist "도수치료예약.exe" (
    echo [X] 도수치료예약.exe 를 찾을 수 없습니다.
    popd & pause & exit /b 1
)

set "OUT=%TEMP%\도수치료예약_DB점검.txt"

echo ═══════════════════════════════════════════════════
echo   DB 점검 실행 중... (수 초 소요)
echo ═══════════════════════════════════════════════════
echo.

rem 결과 파일 경로를 환경변수로 전달해서 exe 가 정확히 거기에 쓰도록
set "DOSU_CHECK_OUT=%OUT%"
"도수치료예약.exe" --check

rem exe 가 끝날 때까지 대기 + 파일 생성 대기 (최대 15초)
set /a WAIT=0
:wait_loop
if exist "%OUT%" goto show
set /a WAIT+=1
if %WAIT% gtr 15 goto fail
timeout /t 1 /nobreak > nul
goto wait_loop

:show
echo [OK] 점검 완료. 메모장으로 결과를 엽니다.
start "" notepad.exe "%OUT%"
popd
exit /b 0

:fail
echo [X] 결과 파일이 생성되지 않았습니다: %OUT%
echo     exe 가 정상 실행되지 않았을 수 있습니다.
popd
pause
exit /b 1
