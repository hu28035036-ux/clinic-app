@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

rem ═══════════════════════════════════════════════════════════════════
rem  도수치료예약 — 자동 업데이터
rem  본체(도수치료예약.exe)에서 "지금 설치" 를 누르면 이 스크립트가 실행됨.
rem  동작:
rem    1. 본체 프로세스 완전 종료 대기 (최대 20초 · 강제 종료 fallback)
rem    2. 기존 _internal 폴더 / exe 를 .old 로 rename (롤백용)
rem    3. .update\new.zip 압축 해제
rem    4. 새 파일로 교체
rem    5. 본체 재실행
rem  실패 시 .old 파일을 복원해 이전 버전으로 되돌림
rem ═══════════════════════════════════════════════════════════════════

cd /d "%~dp0"

set "LOGFILE=%TEMP%\도수치료예약_updater.log"
echo. > "%LOGFILE%"
echo [%date% %time%] updater 시작 (CWD=%CD%) >> "%LOGFILE%"

rem 로그 표시 창
title 도수치료예약 업데이트 진행 중...
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   도수치료예약 업데이트 진행 중
echo ═══════════════════════════════════════════════════════════════════
echo.

rem ───── [1/5] 본체 프로세스 종료 대기 ─────
echo [1/5] 기존 프로그램 종료 대기...
set /a WAIT=0
:waitloop
tasklist /FI "IMAGENAME eq 도수치료예약.exe" 2>nul | find /I "도수치료예약.exe" > nul
if errorlevel 1 goto terminated
set /a WAIT+=1
if !WAIT! geq 15 (
    echo       15초 경과 - 강제 종료 시도
    echo [%date% %time%] 강제 taskkill >> "%LOGFILE%"
    taskkill /F /IM 도수치료예약.exe > nul 2>&1
    timeout /t 2 /nobreak > nul
    goto terminated
)
timeout /t 1 /nobreak > nul
goto waitloop

:terminated
echo       완료
echo [%date% %time%] 본체 종료 확인 >> "%LOGFILE%"

rem 본체가 종료되었어도 PyInstaller 의 _internal/*.pyd / *.dll 파일이
rem OS 측에서 unlock 되기까지 약간의 시간이 더 필요함 (안티바이러스/인덱싱 영향).
rem 이 대기를 안 주면 다음 단계의 ren 이 잠금 충돌로 실패하고 rollback 됨.
echo       파일 잠금 해제 대기 (3초)...
timeout /t 3 /nobreak > nul

rem ───── [2/5] 이전 .old 잔재 정리 ─────
echo [2/5] 이전 백업 정리...
if exist "_internal.old" (
    rmdir /S /Q "_internal.old" >> "%LOGFILE%" 2>&1
)
if exist "도수치료예약.exe.old" (
    del /F /Q "도수치료예약.exe.old" >> "%LOGFILE%" 2>&1
)
echo       완료

rem ───── [3/5] 기존 파일 .old 로 보존 (롤백용) ─────
rem 안티바이러스/Windows 인덱싱/백업 SW 가 파일을 잠그고 있으면 단발 ren 은 실패.
rem 5회 재시도(2초 간격)로 잠금 해제를 기다림.
rem ⚠ batch 의 label 은 if (...) 블록 안에 두면 안 됨 → 평탄화한 형태로 작성.
echo [3/5] 현재 버전 백업...

if not exist "_internal" goto skip_internal_rename
set /a TRY=0
:retry_internal
ren "_internal" "_internal.old" >> "%LOGFILE%" 2>&1
if not errorlevel 1 goto internal_renamed
set /a TRY+=1
if !TRY! geq 5 (
    echo       [오류] _internal rename 5회 실패 — 파일 잠금 지속.
    echo [ERROR] _internal rename failed after 5 retries >> "%LOGFILE%"
    goto rollback
)
echo       _internal 잠금 대기 중... (재시도 !TRY!/5)
echo [WARN] _internal rename retry !TRY! >> "%LOGFILE%"
timeout /t 2 /nobreak > nul
goto retry_internal
:internal_renamed
:skip_internal_rename

if not exist "도수치료예약.exe" goto skip_exe_rename
set /a TRY=0
:retry_exe
ren "도수치료예약.exe" "도수치료예약.exe.old" >> "%LOGFILE%" 2>&1
if not errorlevel 1 goto exe_renamed
set /a TRY+=1
if !TRY! geq 5 (
    echo       [오류] exe rename 5회 실패.
    echo [ERROR] exe rename failed after 5 retries >> "%LOGFILE%"
    goto rollback
)
echo       exe 잠금 대기 중... (재시도 !TRY!/5)
echo [WARN] exe rename retry !TRY! >> "%LOGFILE%"
timeout /t 2 /nobreak > nul
goto retry_exe
:exe_renamed
:skip_exe_rename
echo       완료

rem ───── [4/5] 압축 해제 ─────
echo [4/5] 새 버전 압축 해제...
if exist ".update\extracted" rmdir /S /Q ".update\extracted" >> "%LOGFILE%" 2>&1
if not exist ".update\new.zip" (
    echo       [오류] .update\new.zip 이 없습니다.
    echo [ERROR] new.zip not found >> "%LOGFILE%"
    goto rollback
)
rem 일부 환경(GPO/그룹정책 잠긴 PC)에서 PowerShell 실행 정책 차단 방지 — Bypass 명시.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '.update\new.zip' -DestinationPath '.update\extracted' -Force" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo       [오류] 압축 해제 실패
    echo [ERROR] Expand-Archive failed >> "%LOGFILE%"
    goto rollback
)

rem ZIP 내부 구조: .update\extracted\도수치료예약\ 안에 exe/_internal 있음
set "SRC=.update\extracted\도수치료예약"
if not exist "%SRC%\도수치료예약.exe" (
    rem 대안: ZIP 이 루트에 바로 파일 담고 있는 경우
    set "SRC=.update\extracted"
    if not exist "!SRC!\도수치료예약.exe" (
        echo       [오류] ZIP 구조가 예상과 다릅니다.
        echo [ERROR] unexpected zip structure >> "%LOGFILE%"
        goto rollback
    )
)
echo       완료

rem ───── [5/5] 파일 교체 ─────
echo [5/5] 파일 교체...
xcopy /E /Y /I /Q "%SRC%\*" "." >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo       [오류] 파일 복사 실패
    echo [ERROR] xcopy failed >> "%LOGFILE%"
    goto rollback
)
echo       완료

rem ───── 정리 ─────
echo.
echo 마무리 정리...
if exist ".update\extracted" rmdir /S /Q ".update\extracted" >> "%LOGFILE%" 2>&1
if exist ".update\new.zip" del /F /Q ".update\new.zip" >> "%LOGFILE%" 2>&1
rem .old 파일은 성공 확인 후 다음 업데이트 때 자동 삭제되므로 여기선 둬도 됨
rem 용량 줄이고 싶으면 아래 2줄 주석 해제:
if exist "_internal.old" rmdir /S /Q "_internal.old" >> "%LOGFILE%" 2>&1
if exist "도수치료예약.exe.old" del /F /Q "도수치료예약.exe.old" >> "%LOGFILE%" 2>&1

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   업데이트 완료 - 프로그램을 다시 시작합니다
echo ═══════════════════════════════════════════════════════════════════
echo [%date% %time%] 업데이트 성공 >> "%LOGFILE%"

rem 재시작 — 새 exe 가 포트 점유까지 여유를 두기 위해 5초 대기 후 종료.
start "" "도수치료예약.exe"
timeout /t 5 /nobreak > nul
exit /b 0

rem ═══════════════════════════════════════════════════════════════════
:rollback
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   [!] 업데이트 실패 — 이전 버전으로 복구합니다
echo ═══════════════════════════════════════════════════════════════════
echo [%date% %time%] 롤백 시작 >> "%LOGFILE%"

rem .old 복원
if exist "도수치료예약.exe.old" (
    if not exist "도수치료예약.exe" (
        ren "도수치료예약.exe.old" "도수치료예약.exe" >> "%LOGFILE%" 2>&1
    )
)
if exist "_internal.old" (
    if not exist "_internal" (
        ren "_internal.old" "_internal" >> "%LOGFILE%" 2>&1
    )
)

echo.
echo 복구 완료. 이전 버전으로 다시 시작합니다.
echo 상세 로그: %LOGFILE%
echo.
echo 이전 버전으로 재시작 중...
start "" "도수치료예약.exe"
echo [%date% %time%] 롤백 완료 >> "%LOGFILE%"
echo.
echo ───────────────────────────────────────────────────────────────────
echo  실패 원인을 위 로그에서 확인하시고, 같은 증상이 계속되면
echo  로그 파일을 캡처해서 문의해 주세요:
echo    %LOGFILE%
echo ───────────────────────────────────────────────────────────────────
echo.
rem 사용자가 메시지를 끝까지 읽고 직접 닫게 — 자동 종료 안 함.
pause
exit /b 1
