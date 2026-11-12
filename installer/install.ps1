# 토스트 에이전트 작업 폴더 설치 프로그램
# install.bat 을 더블클릭하면 실행된다. 다시 실행해도 기존 작업 결과와 설정은 지우지 않는다.
param([string]$Target)
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot
$keys = 'DATA_GO_KR_SERVICE_KEY', 'KOCCA_API_URL', 'SHEET_APP_URL', 'SHEET_APP_TOKEN', 'SHEET_URL'

Write-Host ''
Write-Host '=== 토스트 에이전트 작업 폴더 설치 ===' -ForegroundColor Cyan

# 1. 작업 폴더 위치
if (-not $Target) {
    $default = if (Test-Path 'D:\') { 'D:\toast-work' } else { Join-Path $HOME 'toast-work' }
    $Target = Read-Host "작업 폴더 위치 (그냥 Enter = $default)"
    if (-not $Target) { $Target = $default }
}
New-Item -ItemType Directory -Force -Path (Join-Path $Target 'settings') | Out-Null

# 2. 설정 파일과 안내서 복사 (이미 있는 설정은 덮어쓰지 않는다)
foreach ($f in Get-ChildItem (Join-Path $src 'settings') -Filter *.md) {
    $dst = Join-Path $Target "settings\$($f.Name)"
    if (Test-Path $dst) { Write-Host "  유지: settings\$($f.Name)" }
    else { Copy-Item $f.FullName $dst; Write-Host "  복사: settings\$($f.Name)" }
}
Copy-Item (Join-Path $src 'README_install.md') $Target -Force

# 3. .env (기존 값은 Enter로 유지)
$envPath = Join-Path $Target '.env'
$cur = @{}
if (Test-Path $envPath) {
    foreach ($line in [IO.File]::ReadAllLines($envPath)) {
        if ($line -match '^\s*([A-Z_]+)=(.*)$') { $cur[$Matches[1]] = $Matches[2].Trim() }
    }
}
function Ask($key, $label) {
    $has = [bool]$cur[$key]
    $hint = if ($has) { '입력됨, Enter = 유지' } else { '비어 있음, 모르면 Enter' }
    $v = Read-Host "$label ($hint)"
    if ($v) { $cur[$key] = $v.Trim() }
}

Write-Host ''
Write-Host '[시트 연결] Google 시트에 Apps Script(Code.gs)를 붙여 넣은 상태에서 진행합니다.' -ForegroundColor Yellow
if (-not $cur['SHEET_APP_TOKEN']) {
    $chars = [char[]]'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 40
    $rng.GetBytes($bytes)
    $cur['SHEET_APP_TOKEN'] = -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
    if (-not $env:TOAST_INSTALL_TEST) { Set-Clipboard -Value $cur['SHEET_APP_TOKEN'] }
    Write-Host '  시트 토큰을 만들어 클립보드에 복사했습니다.'
    Write-Host '  Apps Script > 프로젝트 설정 > 스크립트 속성에 이름 TOKEN, 값은 Ctrl+V 로 붙여 넣으세요.'
    Write-Host '  같은 곳에 CEO_EMAIL(알림 받을 메일 주소)도 넣고, 웹 앱으로 배포까지 마치세요.'
    Read-Host '  다 했으면 Enter'
}
Ask 'SHEET_APP_URL' '웹 앱 주소(배포 후 나오는 https://script.google.com/... 주소)'
Ask 'SHEET_URL' 'Google 시트 주소(브라우저 주소창)'

Write-Host ''
Write-Host '[공공데이터포털] 승인 전이면 Enter로 넘기고, 나중에 install.bat 을 다시 실행해 채우면 됩니다.' -ForegroundColor Yellow
Ask 'DATA_GO_KR_SERVICE_KEY' '공공데이터포털 일반 인증키'
Ask 'KOCCA_API_URL' '한콘진 요청 주소'

# .env 는 BOM 없는 UTF-8로 쓴다(파이썬이 utf-8로 읽기 때문)
$lines = @('# 토스트 에이전트 설정값. 다른 사람에게 보내지 않습니다.')
foreach ($k in $keys) { $lines += "$k=$($cur[$k])" }
[IO.File]::WriteAllLines($envPath, $lines, (New-Object Text.UTF8Encoding $false))

# 4. 결과
Write-Host ''
Write-Host "설치 완료: $Target" -ForegroundColor Green
$missing = $keys | Where-Object { -not $cur[$_] }
if ($missing) { Write-Host "아직 비어 있는 값: $($missing -join ', ')  (값을 받으면 install.bat 을 다시 실행)" -ForegroundColor Yellow }
Write-Host ''
Write-Host '다음 단계: README_install.md 의 4단계(Claude 허용 도메인)부터 진행하세요.'
Write-Host 'Claude 허용 도메인 목록:'
'apis.data.go.kr', 'cglink.com', 'script.google.com', 'script.googleusercontent.com',
'www.g2b.go.kr', 'www.bizinfo.go.kr', 'www.kocca.kr' | ForEach-Object { Write-Host "  $_" }
if ($cur['KOCCA_API_URL'] -match '^https?://([^/]+)') { Write-Host "  $($Matches[1])" }
if (-not $env:TOAST_INSTALL_TEST) { Invoke-Item $Target }
