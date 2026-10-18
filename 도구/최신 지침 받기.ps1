# 공통 지침 저장소(GitHub)에서 최신 지침·자료·틀·샘플·도구를 받아 이 폴더에 덮어쓴다.
# 실행: powershell -NoProfile -ExecutionPolicy Bypass -File "도구\최신 지침 받기.ps1"
# 건드리지 않는 것: 차시\, 업체 전달\, 내 설정.txt, 틀 수정 요청.md, 자료\회의 기록\, 자료\참고(배경 자료)\ 등 저장소 목록(.kit_files)에 없는 모든 것
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$REPO = 'j333333766-hub/ksl-math-vocab-kit'
$root = Split-Path -Parent $PSScriptRoot
$u8 = New-Object Text.UTF8Encoding($false)
function ReadText($p) { if (Test-Path -LiteralPath $p) { [IO.File]::ReadAllText($p, [Text.Encoding]::UTF8) } else { '' } }

$localVer = (ReadText (Join-Path $root 'VERSION')).Trim()
try {
  $remoteVer = (Invoke-WebRequest "https://raw.githubusercontent.com/$REPO/main/VERSION?t=$([DateTime]::Now.Ticks)" -UseBasicParsing -Headers @{ 'Cache-Control' = 'no-cache' }).Content
  if ($remoteVer -is [byte[]]) { $remoteVer = [Text.Encoding]::UTF8.GetString($remoteVer) }
  $remoteVer = $remoteVer.Trim()
} catch { Write-Output "인터넷에서 최신 지침을 확인하지 못했어요: $($_.Exception.Message)"; Write-Output "지금 폴더의 지침($localVer)으로 작업해요."; exit 2 }
if ($remoteVer -eq $localVer) { Write-Output "최신 지침입니다: $localVer"; exit 0 }

$tmp = Join-Path $env:TEMP ('kslkit_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
  Invoke-WebRequest "https://github.com/$REPO/archive/refs/heads/main.zip" -OutFile "$tmp\kit.zip" -UseBasicParsing
  Expand-Archive -LiteralPath "$tmp\kit.zip" -DestinationPath "$tmp\x" -Force
  $src = (Get-ChildItem -LiteralPath "$tmp\x" -Directory | Select-Object -First 1).FullName
  $newList = [IO.File]::ReadAllLines((Join-Path $src '.kit_files'), [Text.Encoding]::UTF8) | Where-Object { $_.Trim() }
  $oldList = @(); $ol = Join-Path $root '.kit_files'
  if (Test-Path -LiteralPath $ol) { $oldList = [IO.File]::ReadAllLines($ol, [Text.Encoding]::UTF8) | Where-Object { $_.Trim() } }
  # 1) 저장소에서 빠진 파일은 지운다(이전에 저장소에서 받았던 파일만)
  foreach ($f in $oldList) {
    if ($newList -notcontains $f -and $f -notmatch '^(차시|업체 전달)/') {
      $p = Join-Path $root ($f -replace '/', '\')
      if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force; Write-Output "  지움: $f" }
    }
  }
  # 2) 저장소의 파일을 덮어쓴다
  $n = 0
  foreach ($f in $newList) {
    if ($f -match '^(차시|업체 전달)/') { continue }
    $from = Join-Path $src ($f -replace '/', '\'); $to = Join-Path $root ($f -replace '/', '\')
    $dir = Split-Path -Parent $to; if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item -LiteralPath $from -Destination $to -Force; $n++
  }
  Copy-Item -LiteralPath (Join-Path $src '.kit_files') -Destination $ol -Force
  Write-Output "지침을 새로 받았어요: $(if ($localVer) { $localVer } else { '처음' }) → $remoteVer (파일 $($n)개)"
  # 3) 바뀐 점: CHANGELOG에서 지금 받은 판부터 전에 쓰던 판 앞까지
  $log = ReadText (Join-Path $root 'CHANGELOG.md')
  $out = @(); $on = $false
  foreach ($line in ($log -split "`n")) {
    if ($line -match '^## (\S+)') { if ($localVer -and $Matches[1] -eq $localVer) { break }; $on = $true }
    if ($on) { $out += $line.TrimEnd() }
  }
  Write-Output ''; Write-Output '── 바뀐 점(CHANGELOG) ──'; $out | ForEach-Object { Write-Output $_ }
  Write-Output ''; Write-Output '다음 할 일: 도구\틀 갈아끼우기.ps1 을 실행해 차시\ 의 html 들을 새 틀로 맞추고, 위의 바뀐 점에 따라 기존 차시를 점검한다.'
} finally { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
exit 1
