# ═══════════════════════════════════════════════════════════════════
#  도수치료예약 — 원클릭 빌드+배포 (PC 전용)
#
#  하는 일: PyInstaller 빌드 → ZIP 패키징 → publish_release.ps1 로
#           clinic-updates 에 Release 업로드 + manifest.json 갱신.
#
#  사용법 (PowerShell, 저장소 루트에서):
#     git pull                          # 최신 코드
#     .\scripts\build_and_publish.ps1   # 버전은 config.py 에서 자동
#
#  옵션:
#     -Version 1.3.56   버전 직접 지정 (기본: config.py 의 APP_VERSION)
#     -DryRun           빌드·패키징만 하고 실제 업로드/커밋은 생략(요약만)
#
#  사전 조건:
#     - Windows + Python 3.11 + `pip install -r requirements.txt` (venv 권장)
#     - clinic-updates 가 이 저장소와 나란히 클론돼 있을 것 (..\clinic-updates)
#     - clinic-updates 에 release-v<버전>.md / manifest-notes-v<버전>.txt 존재
#       (없으면 먼저 커밋 — 현재 v1.3.56 은 이미 커밋됨)
#     - GitHub 자격증명(gh auth login 또는 저장된 git 자격증명)
# ═══════════════════════════════════════════════════════════════════
param(
    [string]$Version = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# ── 0. 저장소 루트로 이동 ──
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# ── 1. 버전 결정 (기본: config.py) ──
if (-not $Version) {
    $cfg = Get-Content "app\config.py" -Raw
    if ($cfg -match 'APP_VERSION\s*=\s*"([\d.]+)"') {
        $Version = $Matches[1]
    } else {
        throw "config.py 에서 APP_VERSION 을 찾지 못했습니다. -Version 으로 직접 지정하세요."
    }
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "버전 형식 오류(예: 1.3.56): $Version" }
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  배포 버전: v$Version" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan

# ── 2. clinic-updates + 노트 파일 사전 확인 (빌드 전에 먼저 걸러냄) ──
$updates = Join-Path (Split-Path $root -Parent) "clinic-updates"
if (-not (Test-Path (Join-Path $updates "manifest.json"))) {
    throw "clinic-updates 를 찾을 수 없습니다 (..\clinic-updates). git clone 후 다시 실행하세요."
}
# 최신 노트/manifest 를 받아둔다 (원격에 이미 커밋돼 있음)
try { git -C $updates pull --quiet } catch { Write-Warning "clinic-updates pull 실패(무시): $_" }
$notes  = Join-Path $updates "release-v$Version.md"
$mnotes = Join-Path $updates "manifest-notes-v$Version.txt"
foreach ($n in @($notes, $mnotes)) {
    if (-not (Test-Path $n)) { throw "clinic-updates 에 필요한 노트 파일이 없습니다: $n" }
}

# ── 3. 빌드 ──
Write-Host "[1/3] PyInstaller 빌드..." -ForegroundColor Yellow
$pyi = if (Test-Path "venv\Scripts\pyinstaller.exe") { "venv\Scripts\pyinstaller.exe" } else { "pyinstaller" }
Remove-Item -Recurse -Force "build", "dist\도수치료예약" -ErrorAction SilentlyContinue
& $pyi --noconfirm dosu_clinic.spec
if (-not (Test-Path "dist\도수치료예약\도수치료예약.exe")) {
    throw "빌드 산출물이 없습니다: dist\도수치료예약\도수치료예약.exe"
}

# ── 4. ZIP 패키징 (동봉 파일 + '도수치료예약\' 최상위 구조) ──
Write-Host "[2/3] ZIP 패키징..." -ForegroundColor Yellow
$dist = "dist\도수치료예약"
foreach ($f in @("CHANGELOG.txt", "VERSION.txt")) {
    if (Test-Path $f) { Copy-Item $f $dist -Force }
}
Get-ChildItem -Filter *.txt | Where-Object { $_.Name -match "안내|사용법|업데이트 방법" } |
    ForEach-Object { Copy-Item $_.FullName $dist -Force }
if (Test-Path "tools") { Copy-Item "tools" (Join-Path $dist "도구") -Recurse -Force }

$date = Get-Date -Format "yyyyMMdd"
$zip  = "dist\dosu_clinic_v${Version}_$date.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
# Compress-Archive 에 폴더 경로를 주면 최상위에 '도수치료예약\' 가 포함됨
# → updater.bat 이 기대하는 구조( extracted\도수치료예약\도수치료예약.exe )와 일치.
Compress-Archive -Path $dist -DestinationPath $zip -Force
$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "      → $zip ($mb MB)"

# ── 5. 배포 (기존 검증된 스크립트 재사용) ──
Write-Host "[3/3] 배포 (Release + manifest)..." -ForegroundColor Yellow
$pubArgs = @(
    "-Version", $Version,
    "-ZipPath", $zip,
    "-NotesPath", $notes,
    "-ManifestNotesPath", $mnotes,
    "-UpdatesDir", $updates
)
if ($DryRun) { $pubArgs += "-DryRun" }
& (Join-Path $PSScriptRoot "publish_release.ps1") @pubArgs

Write-Host ""
if ($DryRun) {
    Write-Host "[DryRun] 빌드·패키징 완료, 실제 배포는 생략됨. ZIP: $zip" -ForegroundColor Green
} else {
    Write-Host "✅ v$Version 배포 완료 — 1~2분 뒤 각 병원 PC 업데이트에 노출됩니다." -ForegroundColor Green
}
