@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo   도수치료예약 - 빌드 + 배포
echo ------------------------------------------------------------
echo   1) 먼저 최신 코드를 받습니다 (git pull)
echo   2) 빌드 - ZIP - 배포까지 자동 진행합니다.
echo.
echo   * 미리보기만 하려면 이 창을 닫고
echo     PowerShell 에서:  .\scripts\build_and_publish.ps1 -DryRun
echo ============================================================
echo.
pause

echo.
echo [git pull] 최신 코드 받는 중...
git pull

echo.
echo [배포] 빌드 + 패키징 + 업로드...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\build_and_publish.ps1" %*

echo.
echo ============================================================
echo   작업이 끝났습니다. 위 메시지를 확인하세요.
echo ============================================================
pause
