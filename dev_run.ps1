# dev_run.ps1 — 개발자 환경 자동 시드 + dev 서버 실행 (PowerShell 진입점)
#   격리 DB:      tests\temp\dev_clinic.db
#   격리 APPDATA: tests\temp\dev_appdata\
#   운영 DB (%APPDATA%\도수치료예약\clinic.db) 절대 미접근
#
# 사용법 (PowerShell):
#   .\dev_run.ps1            : 격리 DB 가 없으면 시드 후 실행, 있으면 재사용
#   .\dev_run.ps1 --reseed   : 격리 DB 삭제 후 강제 재시드
#
# ExecutionPolicy 차단 시:
#   powershell -ExecutionPolicy Bypass -File .\dev_run.ps1
# 또는 (사용자 범위 영구 허용):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# ──────── venv 검증 ────────
$python = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host "[X] venv\Scripts\python.exe 가 없습니다." -ForegroundColor Red
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "venv 를 만들고 의존성을 설치하세요:"
    Write-Host "  python -m venv venv"
    Write-Host "  venv\Scripts\python.exe -m pip install -r requirements.txt"
    Write-Host "  venv\Scripts\python.exe -m pip install -r requirements-dev.txt"
    Read-Host "Press Enter to exit"
    exit 2
}

# ──────── 격리 환경 강제 ────────
$env:DOSU_DB_PATH = Join-Path $root "tests\temp\dev_clinic.db"
$env:APPDATA = Join-Path $root "tests\temp\dev_appdata"

$tempDir = Join-Path $root "tests\temp"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}
if (-not (Test-Path $env:APPDATA)) {
    New-Item -ItemType Directory -Path $env:APPDATA -Force | Out-Null
}

# ──────── --reseed 플래그 ────────
if ($args.Count -gt 0 -and $args[0] -eq "--reseed") {
    Write-Host "[INFO] --reseed: 격리 DB 삭제 후 재시드합니다." -ForegroundColor Yellow
    if (Test-Path $env:DOSU_DB_PATH) {
        Remove-Item -Force $env:DOSU_DB_PATH
    }
    if (Test-Path $env:APPDATA) {
        Remove-Item -Recurse -Force $env:APPDATA
    }
    New-Item -ItemType Directory -Path $env:APPDATA -Force | Out-Null
}

# ──────── 시드 (격리 DB 없을 때만) ────────
if (-not (Test-Path $env:DOSU_DB_PATH)) {
    Write-Host "====================================="
    Write-Host "[1/2] 더미 데이터 시드 (1회)"
    Write-Host "====================================="
    & $python (Join-Path $root "scripts\seed_dev_dummy.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[X] 시드 실패. scripts\seed_dev_dummy.py 출력을 확인하세요." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[INFO] 기존 격리 DB 재사용: tests\temp\dev_clinic.db" -ForegroundColor Cyan
    Write-Host "       강제 재시드: .\dev_run.ps1 --reseed"
}

# ──────── dev 서버 실행 ────────
Write-Host ""
Write-Host "====================================="
Write-Host "[2/2] dev 서버 실행"
Write-Host "====================================="
Write-Host "격리 DB:    $env:DOSU_DB_PATH"
Write-Host "APPDATA:    $env:APPDATA"
Write-Host "브라우저:   http://127.0.0.1:8000/"
Write-Host "관리자비번: admin1234"
Write-Host "종료:       Ctrl+C"
Write-Host "====================================="
Write-Host ""

& $python (Join-Path $root "run.py")
exit $LASTEXITCODE
