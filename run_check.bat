@echo off
chcp 65001 >NUL

call :CHECK_VENV
if errorlevel 1 exit /b %ERRORLEVEL%

echo =====================================
echo 도수치료 예약 프로그램 하네스 검증 시작
echo =====================================

echo.
echo [1/3] 테스트 실행 (pytest)
echo -------------------------------------
venv\Scripts\python.exe -m pytest tests -v
if errorlevel 1 (
    echo.
    echo [X] 테스트 실패
    echo     원인: pytest 출력의 FAILED / ERROR 라인을 확인하세요.
    echo     XFAIL / SKIPPED 는 통과로 간주됩니다 (spec 에 정의되었지만 백엔드 미구현).
    pause
    exit /b 1
)

echo.
echo [2/3] Ruff lint 검사
echo -------------------------------------
venv\Scripts\python.exe -m ruff check app tests scripts
if errorlevel 1 (
    echo.
    echo [X] Lint 실패
    echo     자동 수정: venv\Scripts\python.exe -m ruff check app tests scripts --fix
    pause
    exit /b 1
)

echo.
echo [3/3] DB 경로 안전 검사
echo -------------------------------------
venv\Scripts\python.exe scripts\check_db_path.py
if errorlevel 1 (
    echo.
    echo [X] DB 경로 안전 검사 실패
    pause
    exit /b 1
)

echo.
echo =====================================
echo [OK] 모든 하네스 검증 통과
echo =====================================
pause
exit /b 0

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
