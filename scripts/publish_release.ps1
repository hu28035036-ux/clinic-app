# ═══════════════════════════════════════════════════════════════════
#  도수치료예약 — 표준 배포 스크립트
#
#  ZIP 을 GitHub Release 자산으로 올리고, clinic-updates 리포에는
#  manifest.json 만 커밋한다.
#
#  ⚠ ZIP 을 clinic-updates 리포에 직접 커밋하지 않는 것이 이 스크립트의
#    존재 이유 — git 히스토리가 릴리스마다 ~26MB 씩 영구 비대해져
#    GitHub Pages 1GB 한도에 도달하면 자동 업데이트 배포가 막힌다.
#    (자세한 배경: 자동 업데이트 배포 가이드.txt [2] 절)
#
#  사전 조건:
#    - gh CLI (있으면 사용) 또는 git credential manager 에 저장된
#      github.com 자격증명 (REST API 폴백 — 이 PC 의 기본 경로)
#    - clinic-updates 리포가 이 프로젝트와 나란히 클론되어 있을 것
#      (..\clinic-updates)
#
#  사용 예:
#    .\scripts\publish_release.ps1 -Version 1.3.23 `
#        -ZipPath "dist\dosu_clinic_v1.3.23_20260611.zip" `
#        -NotesPath "..\clinic-updates\release-v1.3.23.md"
#
#  -DryRun 을 붙이면 실제 업로드/커밋 없이 할 일만 출력.
# ═══════════════════════════════════════════════════════════════════
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$ZipPath,
    [Parameter(Mandatory = $true)][string]$NotesPath,
    # manifest.json 의 notes 에 넣을 짧은 평문 (생략 시 NotesPath 내용 사용).
    # 업데이트 확인 대화상자에 그대로 표시되므로 markdown 기호 없는 평문 권장.
    [string]$ManifestNotesPath = "",
    [string]$Repo = "hu28035036-ux/clinic-updates",
    # 비우면 이 스크립트 기준 ..\..\clinic-updates 로 자동 결정
    [string]$UpdatesDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not $UpdatesDir) {
    # PS5.1 은 param 기본값 평가 시점에 $PSScriptRoot 가 비어 있을 수 있어 본문에서 결정
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $UpdatesDir = Join-Path $scriptDir "..\..\clinic-updates"
}

# ───── 0. 입력 검증 ─────
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version 은 '1.2.3' 형식이어야 합니다 (v prefix 없이): $Version"
}
if (-not (Test-Path $ZipPath)) { throw "ZIP 파일이 없습니다: $ZipPath" }
if (-not (Test-Path $NotesPath)) { throw "릴리스노트 파일이 없습니다: $NotesPath" }
$UpdatesDir = (Resolve-Path $UpdatesDir).Path
$manifestPath = Join-Path $UpdatesDir "manifest.json"
if (-not (Test-Path $manifestPath)) {
    throw "clinic-updates 리포를 찾을 수 없습니다 (manifest.json 부재): $UpdatesDir"
}

$zipName = Split-Path $ZipPath -Leaf
if ($zipName -match '[^\x20-\x7E]') {
    throw "ZIP 파일명에 비ASCII 문자가 있습니다 — Release 자산 URL 이 깨질 수 있으니 영문 파일명을 사용하세요: $zipName"
}

# ───── 1. SHA256 계산 ─────
$sha256 = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
$downloadUrl = "https://github.com/$Repo/releases/download/v$Version/$zipName"

Write-Host ""
Write-Host "════════════════════════════════════════════════"
Write-Host "  배포 요약"
Write-Host "════════════════════════════════════════════════"
Write-Host "  버전        : v$Version"
Write-Host "  ZIP         : $zipName ($sizeMb MB)"
Write-Host "  SHA256      : $sha256"
Write-Host "  download_url: $downloadUrl"
Write-Host "  리포        : $Repo"
Write-Host ""

if ($DryRun) {
    Write-Host "[DryRun] 실제 업로드/커밋 없이 종료합니다."
    exit 0
}

# ───── 2. GitHub Release 생성 + ZIP 자산 업로드 ─────
# 동일 태그 릴리스가 이미 있으면 실패 (중복 배포 방지 — 의도된 동작).
Write-Host "[1/3] GitHub Release v$Version 생성 + ZIP 업로드..."
$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh) {
    gh release create "v$Version" $ZipPath `
        --repo $Repo `
        --title "v$Version" `
        --notes-file $NotesPath
    if ($LASTEXITCODE -ne 0) { throw "gh release create 실패 (exit $LASTEXITCODE)" }
}
else {
    # gh 미설치 → git credential manager 의 github.com 토큰으로 REST API 직접 호출
    Write-Host "      (gh CLI 없음 — git 자격증명으로 REST API 사용)"
    # GCM 의 OAuth 토큰(gho_)은 만료/회전될 수 있음 — 실제 git 작업을 한 번
    # 수행해 GCM 이 토큰을 갱신하게 한 뒤 credential fill 로 꺼낸다.
    Push-Location $UpdatesDir
    try { git fetch origin --quiet 2>$null } catch {} finally { Pop-Location }
    $ghUser = $Repo.Split('/')[0]
    $tmp = New-TemporaryFile
    "protocol=https`nhost=github.com`nusername=$ghUser`n" | Set-Content $tmp -Encoding ascii
    $cred = cmd /c "git credential fill < `"$tmp`" 2>&1"
    Remove-Item $tmp
    $token = (($cred | Where-Object { $_ -match '^password=' }) -replace '^password=', '').Trim()
    if (-not $token) { throw "git credential 에서 github.com 토큰을 찾지 못했습니다. gh CLI 를 설치하거나 git push 를 한 번 수행해 자격증명을 저장하세요." }
    $headers = @{
        Authorization = "token $token"
        'User-Agent'  = 'dosu-clinic-deploy'
        Accept        = 'application/vnd.github+json'
    }
    # [string] 캐스팅 필수 — PS5.1 의 Get-Content -Raw 는 PSPath 등 메타속성이
    # 붙은 문자열을 반환해 ConvertTo-Json 이 객체로 직렬화해버림 (API 422)
    $notesBody = [string](Get-Content $NotesPath -Raw -Encoding UTF8)
    $relPayload = @{
        tag_name = "v$Version"; name = "v$Version"
        body = $notesBody; draft = $false; prerelease = $false
    } | ConvertTo-Json
    $rel = Invoke-RestMethod -Method Post `
        -Uri "https://api.github.com/repos/$Repo/releases" `
        -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($relPayload)) `
        -ContentType 'application/json'
    Write-Host "      Release 생성됨: $($rel.html_url)"
    $uploadUrl = ($rel.upload_url -replace '\{\?name,label\}', '') + "?name=$zipName"
    $asset = Invoke-RestMethod -Method Post -Uri $uploadUrl -Headers $headers `
        -InFile $ZipPath -ContentType 'application/zip'
    Write-Host "      자산 업로드됨: $($asset.browser_download_url)"
    if ($asset.browser_download_url -ne $downloadUrl) {
        Write-Warning "업로드된 자산 URL 이 예상과 다릅니다: $($asset.browser_download_url)"
        $downloadUrl = $asset.browser_download_url
    }
}

# ───── 3. manifest.json 갱신 ─────
Write-Host "[2/3] manifest.json 갱신..."
$notesSrc = if ($ManifestNotesPath) { $ManifestNotesPath } else { $NotesPath }
$notesText = (Get-Content $notesSrc -Raw -Encoding UTF8).Trim()
$manifest = [ordered]@{
    version      = $Version
    download_url = $downloadUrl
    sha256       = $sha256
    notes        = $notesText
    mandatory    = $false
}
# BOM 없는 UTF-8 로 저장 (PS5.1 의 -Encoding utf8 은 BOM 을 붙이므로 .NET API 사용)
$json = ($manifest | ConvertTo-Json -Depth 3)
[System.IO.File]::WriteAllText($manifestPath, $json, (New-Object System.Text.UTF8Encoding($false)))

# ───── 4. manifest 커밋 + 푸시 (ZIP 은 절대 커밋하지 않음) ─────
Write-Host "[3/3] manifest.json 커밋 + 푸시..."
Push-Location $UpdatesDir
try {
    git add manifest.json
    # 릴리스노트 사본도 리포에 보관 (텍스트라 용량 무해)
    $notesCopy = "release-v$Version.md"
    if (-not (Test-Path $notesCopy)) {
        Copy-Item $NotesPath $notesCopy
    }
    git add $notesCopy
    git commit -m "Deploy v$Version (manifest only, ZIP = Release asset)"
    if ($LASTEXITCODE -ne 0) { throw "git commit 실패" }
    git push
    if ($LASTEXITCODE -ne 0) { throw "git push 실패" }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "════════════════════════════════════════════════"
Write-Host "  배포 완료 — 1~2분 뒤 GitHub Pages 반영"
Write-Host "  각 병원 PC: 관리자 → 시스템 → 업데이트 확인"
Write-Host "════════════════════════════════════════════════"
