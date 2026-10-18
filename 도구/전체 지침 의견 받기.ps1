# 검토위원이 남긴 ‘전체 지침 의견’(구글 시트)을 받아 ‘전체 지침 의견(받은 것).md’로 저장하고, 지난번 뒤로 새로 생기거나 바뀐 의견을 알려 준다.
# 실행: powershell -NoProfile -ExecutionPolicy Bypass -File "도구\전체 지침 의견 받기.ps1"
# 상태: 확정 = 지켜야 할 지침 / 검토 중 = 아직 정하지 않음(소개만) / 보류 = 따르지 않음 / 지침에 반영 = 이미 CLAUDE.md에 들어감
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$root = Split-Path -Parent $PSScriptRoot
$u8 = New-Object Text.UTF8Encoding($false)
$url = 'https://docs.google.com/spreadsheets/d/1eIOEVhjYTogAEFeZJe3kG7yS8dbNx2yjwDJeqonQEyk/gviz/tq?tqx=out:csv&sheet=' + [Uri]::EscapeDataString('전체 지침 의견')
try {
  $r = Invoke-WebRequest $url -UseBasicParsing
  $csv = [Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray())
} catch { Write-Output "전체 지침 의견을 받지 못했어요: $($_.Exception.Message)"; exit 2 }
$rows = $csv | ConvertFrom-Csv
$rows = @($rows | Where-Object { $_.'의견' })
$seenPath = Join-Path $root '.general_seen'
$seen = @{}; if (Test-Path -LiteralPath $seenPath) { foreach ($l in [IO.File]::ReadAllLines($seenPath, [Text.Encoding]::UTF8)) { $p = $l -split "`t", 2; if ($p.Count -eq 2) { $seen[$p[0]] = $p[1] } } }
$order = @{ '확정' = 0; '검토 중' = 1; '보류' = 2; '지침에 반영' = 3 }
$md = @('# 전체 지침 의견 (검토위원 → 집필진 모두)', '', "받은 때: $((Get-Date).ToString('yyyy-MM-dd HH:mm')) · 원본: 검토 의견 구글 시트의 ‘전체 지침 의견’", '',
  '- **확정**: 지켜야 할 지침이다. CLAUDE.md와 다르면 이것을 따른다.', '- **검토 중**: 아직 정하지 않았다. 따르지 않고, 선생님께 이런 의견이 있다고 알리기만 한다.', '- **보류**: 따르지 않는다.', '- **지침에 반영**: 이미 CLAUDE.md에 들어갔다.', '')
$news = @()
foreach ($x in ($rows | Sort-Object { $o = $order[$_.'상태']; if ($o -eq $null) { 1 } else { $o } }, '의견 번호')) {
  $st = if ($x.'상태') { $x.'상태' } else { '검토 중' }
  $line = "- [$st] ($($x.'분야')$(if ($x.'관련 차시') { ' · 관련 차시: ' + $x.'관련 차시' })) $($x.'의견')$(if ($x.'대표 메모') { ' — 대표 메모: ' + $x.'대표 메모' }) `<$($x.'의견 번호')`>"
  $md += $line
  $sig = "$st|$($x.'의견')|$($x.'대표 메모')"
  if (-not $seen.ContainsKey($x.'의견 번호')) { $news += "  새 의견 $line" } elseif ($seen[$x.'의견 번호'] -ne $sig) { $news += "  바뀐 의견 $line" }
  $seen[$x.'의견 번호'] = $sig
}
if (-not $rows.Count) { $md += '(아직 의견이 없어요)' }
[IO.File]::WriteAllText((Join-Path $root '전체 지침 의견(받은 것).md'), ($md -join "`r`n") + "`r`n", $u8)
[IO.File]::WriteAllText($seenPath, (($seen.GetEnumerator() | ForEach-Object { "$($_.Key)`t$($_.Value)" }) -join "`r`n"), $u8)
$c = @($rows | Where-Object { $_.'상태' -eq '확정' }).Count
Write-Output "전체 지침 의견 $($rows.Count)건(확정 $c건)을 ‘전체 지침 의견(받은 것).md’에 저장했어요."
if ($news.Count) { Write-Output '지난번 뒤로 새로 생기거나 바뀐 의견:'; $news | ForEach-Object { Write-Output $_ } } else { Write-Output '지난번 뒤로 새로 생기거나 바뀐 의견은 없어요.' }
