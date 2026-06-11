$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  python scripts/package_submission.py
}
finally {
  Pop-Location
}
