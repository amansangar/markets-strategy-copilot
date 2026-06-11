$ErrorActionPreference = "Stop"

$Root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$WebDir = Join-Path $Root "apps\web"
$NextCli = Join-Path $WebDir "node_modules\next\dist\bin\next"
$Node = "C:\Program Files\nodejs\node.exe"
$Npm = "C:\Program Files\nodejs\npm.cmd"

if (-not (Test-Path -LiteralPath $Node)) {
  $Node = "node"
}

if (-not (Test-Path -LiteralPath $Npm)) {
  $Npm = "npm"
}

Write-Host "Preparing Markets Strategy Copilot demo assets..."
Write-Host "Workspace: $Root"

if (-not (Test-Path -LiteralPath $NextCli)) {
  Write-Host "Web dependencies are missing. Installing local web dependencies; this is slow only the first time."
  Push-Location $WebDir
  try {
    & $Npm install --workspaces=false --include=dev --ignore-scripts --no-audit --no-fund
  }
  finally {
    Pop-Location
  }
}

Write-Host "Generating deterministic demo data..."
Push-Location $Root
try {
  py -3.11 scripts\generate_demo_data.py
}
finally {
  Pop-Location
}

Write-Host "Building the production frontend once so the demo starts faster..."
Push-Location $WebDir
try {
  $env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
  & $Node node_modules\next\dist\bin\next build --webpack
}
finally {
  Pop-Location
}

Write-Host "Demo preparation complete. Use scripts\start_demo.ps1 for the fast presentation startup."
