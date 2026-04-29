@echo off
chcp 65001 >NUL

call :CHECK_VENV
if errorlevel 1 exit /b %ERRORLEVEL%

echo ===============================
echo Ruff lint 검사
echo ===============================
echo (app/ 는 per-file-ignores 로 면제됨. tests/, scripts/ 만 실제 검사)
echo.
venv\Scripts\python.exe -m ruff check app tests scripts
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
    echo [X] ruff 실패. 종료 코드: %EXITCODE%
    echo     자동 수정 시도: venv\Scripts\python.exe -m ruff check app tests scripts --fix
) else (
    echo [OK] ruff 통과
)
pause
exit /b %EXITCODE%

:CHECK_VENV
if not exist "venv\Scripts\python.exe" (
    call :PRINT_VENV_HELP "venv\Scripts\python.exe 가 없습니다."
    exit /b 2
)
venv\Scripts\python.exe -c "import sys" >NUL 2>&1
if errorlevel 1 (
    call :PRINT_VENV_HELP "venv\Scripts\python.exe 가 실행되지 않습니다 (Python 경로 깨짐)."
    exit /b 2
)
exit /b 0

:PRINT_VENV_HELP
echo =====================================
echo [X] %~1
echo =====================================
echo.
echo venv 를 새로 만들고 의존성을 다시 설치하세요:
echo.
echo   1) rmdir /s /q venv
echo   2) python -m venv venv
echo   3) venv\Scripts\python.exe -m pip install -r requirements.txt
echo   4) venv\Scripts\python.exe -m pip install -r requirements-dev.txt
echo.
echo 자세한 내용은 docs\HARNESS.md 의 트러블슈팅 섹션 참조.
pause
exit /b 0
