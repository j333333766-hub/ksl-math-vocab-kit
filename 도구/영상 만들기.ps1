# 영상 원본(html) → mp4. 설치할 것 없이 이 컴퓨터의 Chrome(없으면 Edge)으로 1/30초마다 화면을 찍어 H.264 mp4 로 묶는다.
# 실행:  powershell -NoProfile -ExecutionPolicy Bypass -File "도구\영상 만들기.ps1" -Src "차시\영상 원본\08-2-1 공약수.html" -Out "차시\media\08_2-1_gongyaksu.mp4"
#   미리 보기 그림만:  ... -Src "…html" -Out "…\미리보기.png" -Still "1,5,10"      (그 초의 화면을 …_1s.png 처럼 저장)
#   메뉴 자리 확인:    미리 보기에 -Safe 를 붙이면 화면 메뉴가 얹히는 자리를 빨갛게, 글자를 둘 곳을 초록 점선으로 보여 준다
#   앞부분만 시험:     -Until 5  (처음 5초만 만든다)
# 영상 원본은 draw(t)(t초의 장면을 그림)와 DUR(길이, 초)를 가진 html 이다(도구\영상\공통.js 의 start(draw, DUR)). 견본: 도구\영상\견본\
param(
  [Parameter(Mandatory = $true)][string]$Src,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$Fps = 30,
  [string]$Still = '',
  [switch]$Safe,
  [double]$Until = 0
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$W = 1920; $H = 1080
$src = (Resolve-Path -LiteralPath $Src).Path
$out = [IO.Path]::GetFullPath($Out)
$here = Join-Path $PSScriptRoot '영상'
$browser = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe", "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($env:KSLREC_BROWSER) { $browser = $env:KSLREC_BROWSER }
if (-not $browser) { throw 'Chrome 이나 Edge 를 찾지 못했어요.' }
$work = Join-Path $env:TEMP ('kslrec_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $work | Out-Null
$script:proc = $null; $script:ws = $null; $script:id = 0; $script:prof = $null
$rbuf = New-Object byte[] 1048576

function Cdp([string]$method, [string]$paramsJson, [int]$timeout = 60000) {
  $script:id++
  $bytes = [Text.Encoding]::UTF8.GetBytes('{"id":' + $script:id + ',"method":"' + $method + '","params":' + $paramsJson + '}')
  $script:ws.SendAsync((New-Object ArraySegment[byte] -ArgumentList @(, $bytes)), [Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()
  while ($true) {
    $ms = New-Object IO.MemoryStream
    do {
      $t = $script:ws.ReceiveAsync((New-Object ArraySegment[byte] -ArgumentList @(, $rbuf)), [Threading.CancellationToken]::None)
      if (-not $t.Wait($timeout)) { throw "브라우저가 $([int]($timeout / 1000))초 동안 답하지 않아요($method)." }
      $r = $t.Result; $ms.Write($rbuf, 0, $r.Count)
    } while (-not $r.EndOfMessage)
    $txt = [Text.Encoding]::UTF8.GetString($ms.ToArray())
    if ($txt.StartsWith('{"id":' + $script:id + ',')) {
      if ($txt.Contains('"exceptionDetails"') -or $txt.StartsWith('{"id":' + $script:id + ',"error"')) { throw ('화면 안에서 오류가 났어요: ' + $txt.Substring(0, [Math]::Min(600, $txt.Length))) }
      return $txt
    }
  }
}
function Js([string]$expr) { Cdp 'Runtime.evaluate' ('{"expression":' + (ConvertTo-Json $expr -Compress) + ',"awaitPromise":true,"returnByValue":true}') }
function JsVal([string]$expr) { (ConvertFrom-Json (Js $expr)).result.result.value }
# 그릴 때마다 오른쪽 아래 눈에 안 보이는 점도 바꾼다(앞 장과 똑같은 화면이면 새 화면을 안 만들어 찍기가 늦어진다)
function Draw([double]$t) { $null = Js ('draw(' + $t.ToString([Globalization.CultureInfo]::InvariantCulture) + ");(()=>{let d=document.getElementById('__tick');if(!d){d=document.createElement('div');d.id='__tick';d.style.cssText='position:fixed;right:0;bottom:0;width:2px;height:2px;z-index:2147483647;pointer-events:none';document.body.append(d)}d.dataset.k=d.dataset.k==='1'?'2':'1';d.style.background='rgba(0,0,0,0.0'+d.dataset.k+')'})()") }
function Shot([string]$fmt) {
  $t = Cdp 'Page.captureScreenshot' -timeout 10000 -paramsJson ('{"format":"' + $fmt + '"' + $(if ($fmt -eq 'jpeg') { ',"quality":92' } else { '' }) + ',"clip":{"x":0,"y":0,"width":' + $W + ',"height":' + $H + ',"scale":1}}')
  $a = $t.IndexOf('"data":"') + 8; [Convert]::FromBase64String($t.Substring($a, $t.IndexOf('"', $a) - $a))
}
function StopBrowser {
  if ($script:ws) { try { $script:ws.Dispose() } catch {}; $script:ws = $null }
  if ($script:proc) { try { Stop-Process -Id $script:proc.Id -Force -ErrorAction SilentlyContinue } catch {}; $script:proc = $null }
  if ($script:prof) {
    Start-Sleep -Milliseconds 300
    $pf = $script:prof
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($pf) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    $script:prof = $null
  }
}
# 브라우저를 켜고 url 을 연다. $wait 이면 영상 원본이 준비될 때까지 기다려 길이(초)를 돌려준다
function OpenPage([string]$url, [bool]$wait) {
  StopBrowser
  $port = Get-Random -Minimum 9300 -Maximum 9900
  $script:prof = Join-Path $work ('p' + [guid]::NewGuid().ToString('N').Substring(0, 8))
  $script:proc = Start-Process -FilePath $browser -PassThru -WindowStyle Hidden -ArgumentList @('--headless', '--disable-gpu', '--hide-scrollbars', '--mute-audio', '--no-first-run', "--remote-debugging-port=$port", "--user-data-dir=`"$($script:prof)`"", "--window-size=$W,$H", '--force-device-scale-factor=1', '--allow-file-access-from-files', 'about:blank')
  $wsUrl = $null
  for ($k = 0; $k -lt 80 -and -not $wsUrl; $k++) {
    Start-Sleep -Milliseconds 250
    try { $list = ConvertFrom-Json (Invoke-WebRequest "http://127.0.0.1:$port/json/list" -UseBasicParsing).Content; foreach ($t in $list) { if ($t.type -eq 'page' -and -not $wsUrl) { $wsUrl = [string]$t.webSocketDebuggerUrl } } } catch {}
  }
  if (-not $wsUrl) { throw '브라우저를 열지 못했어요.' }
  $script:ws = New-Object Net.WebSockets.ClientWebSocket
  $script:ws.Options.KeepAliveInterval = [TimeSpan]::Zero
  $script:ws.ConnectAsync([Uri]$wsUrl, [Threading.CancellationToken]::None).Wait()
  $null = Cdp 'Emulation.setDeviceMetricsOverride' ('{"width":' + $W + ',"height":' + $H + ',"deviceScaleFactor":1,"mobile":false}')
  $null = Cdp 'Page.navigate' ('{"url":' + (ConvertTo-Json $url -Compress) + '}')
  if (-not $wait) { Start-Sleep -Milliseconds 800; return $null }
  for ($k = 0; $k -lt 80; $k++) { Start-Sleep -Milliseconds 250; try { $d = JsVal 'window.ready ? window.ready.then(() => window.DUR) : null'; if ($null -ne $d) { return $d } } catch {} }
  throw '영상 원본이 준비되지 않았어요(공통.js 의 start(draw, DUR)를 부르는지 확인).'
}

try {
  $url = ([Uri]$src).AbsoluteUri + '?rec' + $(if ($Safe) { '&safe' } else { '' })   # ?rec: 저절로 재생하지 않고 draw(t)로만 그린다
  $dur = [double](OpenPage $url $true)
  $broken = JsVal '[...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute(''src'')).join('', '')'
  if ($broken) { Write-Output "주의: 그림을 찾지 못했어요 → $broken" }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null

  if ($Still) {
    foreach ($s in ($Still -split ',')) {
      Draw ([double]$s.Trim())
      $f = ($out -replace '\.(png|mp4)$', '') + '_' + $s.Trim() + 's.png'
      [IO.File]::WriteAllBytes($f, (Shot 'png')); Write-Output "그림: $f"
    }
  } else {
    if ($Until -gt 0) { $dur = [Math]::Min($dur, $Until) }
    $n = [int][Math]::Round($dur * $Fps)
    $fd = Join-Path $work 'frames'; New-Item -ItemType Directory -Force -Path $fd | Out-Null
    $sw = [Diagnostics.Stopwatch]::StartNew()
    # ① 1/Fps 초마다 그려서 찍어 둔다. Edge 는 가끔 찍기에 답하지 않아 멈추므로, 그러면 다시 켜서 그 장면부터 잇는다
    $retry = 0
    for ($i = 0; $i -le $n; $i++) {
      try { Draw ($i / $Fps); $jpg = Shot 'jpeg' }
      catch {
        if (++$retry -gt 20) { throw }
        Write-Output ('  {0:N1}초에서 브라우저를 다시 켜요' -f ($i / $Fps)); $null = OpenPage $url $true; $i--; continue
      }
      [IO.File]::WriteAllBytes((Join-Path $fd ('{0:D5}.jpg' -f $i)), $jpg)
      if ($i % ($Fps * 4) -eq 0) { Write-Output ('  {0,5:N1}초 / {1}초 찍음' -f ($i / $Fps), $dur) }
    }
    # ② 찍은 그림을 브라우저 안에서 차례로 읽어 H.264 로 묶는다(WebCodecs + mp4-muxer)
    Write-Output '  묶는 중…'
    $null = OpenPage ([Uri](Join-Path $here 'blank.html')).AbsoluteUri $false
    $null = Js ([IO.File]::ReadAllText((Join-Path $here 'mp4-muxer.js'), [Text.Encoding]::UTF8) + ';0')
    $null = Js ([IO.File]::ReadAllText((Join-Path $here '녹화기.js'), [Text.Encoding]::UTF8) + ';0')
    $null = JsVal "__rec.init($W, $H, $Fps)"
    $base = ([Uri](Join-Path $fd 'x')).AbsoluteUri -replace 'x$', ''
    $null = JsVal ('__rec.encodeDir(' + (ConvertTo-Json $base -Compress) + ", $n)")
    $size = [int](JsVal '__rec.finish()')
    $fs = [IO.File]::Create($out)
    try {
      $part = 1048576
      for ($k = 0; $k * $part -lt $size; $k++) { $b = [Convert]::FromBase64String((JsVal "__rec.part($k, $part)")); $fs.Write($b, 0, $b.Length) }
    } finally { $fs.Close() }
    Write-Output ('만들었어요: {0} ({1:N1}MB, {2}초, {3}장, {4:N0}초 걸림)' -f $out, ($size / 1MB), $dur, ($n + 1), $sw.Elapsed.TotalSeconds)
  }
} finally {
  StopBrowser
  Start-Sleep -Milliseconds 300
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
