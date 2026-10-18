# 차시\ 의 html 마다 ‘차시 내용’은 그대로 두고 화면 틀만 틀\template.html 로 바꾼다. 이미 같으면 건드리지 않는다.
# 바꾸기 전 파일은 차시\_예전 틀\ 에 남긴다.
# 실행: powershell -NoProfile -ExecutionPolicy Bypass -File "도구\틀 갈아끼우기.ps1"
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Split-Path -Parent $PSScriptRoot
$u8 = New-Object Text.UTF8Encoding($false)
$tplPath = Join-Path $root '틀\template.html'
if (-not (Test-Path -LiteralPath $tplPath)) { Write-Output '틀\template.html 이 없어요. 먼저 도구\최신 지침 받기.ps1 을 실행하세요.'; exit 2 }
$tpl = [IO.File]::ReadAllText($tplPath, [Text.Encoding]::UTF8)
$S = '차시 내용 시작'; $E = '차시 내용 끝'
$ver = ''; $vp = Join-Path $root 'VERSION'; if (Test-Path -LiteralPath $vp) { $ver = ([IO.File]::ReadAllText($vp)).Trim() }
$dir = Join-Path $root '차시'; $bk = Join-Path $dir '_예전 틀'
$files = Get-ChildItem -LiteralPath $dir -Filter '*.html' -File -ErrorAction SilentlyContinue
if (-not $files) { Write-Output '차시\ 에 html 이 없어요.'; exit 0 }
$changed = 0; $same = 0; $bad = 0
foreach ($f in $files) {
  $h = [IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8)
  $i = $h.IndexOf("$S ═"); if ($i -lt 0) { $i = $h.IndexOf($S) }
  $j = $h.IndexOf("$E ═"); if ($j -lt 0) { $j = $h.IndexOf($E) }
  if ($i -lt 0 -or $j -lt 0) { Write-Output "  [건너뜀] $($f.Name): ‘차시 내용’ 표시를 찾지 못했어요"; $bad++; continue }
  $s0 = $h.LastIndexOf('<script>', $i); $a = $h.IndexOf('/*', $s0); $b = $h.IndexOf('*/', $j) + 2
  $content = $h.Substring($a, $b - $a)
  $new = $tpl.Replace('/*__CONTENT__*/', $content)
  if ($new -eq $h) { $same++; continue }
  if (-not (Test-Path -LiteralPath $bk)) { New-Item -ItemType Directory -Path $bk | Out-Null }
  $stamp = (Get-Date).ToString('MMdd-HHmm')
  Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $bk ($f.BaseName + " (틀 바꾸기 전 $stamp).html")) -Force
  [IO.File]::WriteAllText($f.FullName, $new, $u8)
  Write-Output "  새 틀로 바꿈: $($f.Name)"; $changed++
}
Write-Output "틀 갈아끼우기 끝($ver): 바꿈 $changed개, 이미 같음 $same개, 건너뜀 $bad개. 바꾼 차시는 점검(#check)으로 다시 확인한다."
