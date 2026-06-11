param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000,
  [switch]$SkipBuild,
  [switch]$NoWarmup
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$ApiDir = Join-Path $Root "apps\api"
$WebDir = Join-Path $Root "apps\web"
$BuildId = Join-Path $WebDir ".next\BUILD_ID"
$NodeCommand = Get-Command node -ErrorAction SilentlyContinue
$Node = if ($NodeCommand) { $NodeCommand.Source } else { "node" }
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
$Python = if ($PythonCommand) { $PythonCommand.Source } else { "python" }
$DemoDbPath = (Join-Path $Root "markets_strategy_copilot_demo.db").Replace("\", "/")

function Wait-Url {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 180
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $lastError = "not checked"
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4
      if ($response.StatusCode -lt 500) {
        return
      }
      $lastError = "HTTP $($response.StatusCode)"
    }
    catch {
      $lastError = $_.Exception.Message
    }
    Start-Sleep -Seconds 1
  }
  throw "Timed out waiting for $Url ($lastError)"
}

if ((-not $SkipBuild) -and (-not (Test-Path -LiteralPath $BuildId))) {
  Write-Host "No production frontend build found. Preparing the demo first..."
  & (Join-Path $PSScriptRoot "prepare_demo.ps1")
}

Write-Host "Starting Markets Strategy Copilot fast demo..."
Write-Host "Workspace: $Root"
Write-Host "Frontend: http://127.0.0.1:$WebPort/demo"
Write-Host "Backend:  http://127.0.0.1:$ApiPort/docs"
Write-Host "No secrets are printed by this script."

$apiCommand = @"
`$env:DATABASE_URL='sqlite:///$DemoDbPath'
`$env:MARKETS_TEST_MODE='demo'
Set-Location -LiteralPath '$ApiDir'
& '$Python' -m uvicorn app.main:app --host 127.0.0.1 --port $ApiPort
"@

$webCommand = @"
`$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:$ApiPort'
Set-Location -LiteralPath '$WebDir'
& '$Node' node_modules\next\dist\bin\next start --hostname 127.0.0.1 --port $WebPort
"@

Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $apiCommand) -WindowStyle Hidden
Wait-Url "http://127.0.0.1:$ApiPort/api/v1/demo/briefing" 180

if (-not $NoWarmup) {
  Write-Host "Priming demo caches..."
  try {
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$ApiPort/api/v1/demo/warmup" -TimeoutSec 120 | Out-Null
    Write-Host "Demo caches are warm."
  }
  catch {
    Write-Host "Warmup was partial; the app will still run and show normal loading states."
  }
}

Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $webCommand) -WindowStyle Hidden
Wait-Url "http://127.0.0.1:$WebPort/demo" 180

Write-Host "Fast demo is ready. Start at /demo, then follow the checklist."
