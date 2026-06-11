$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  python scripts/package_release.py
}
finally {
  Pop-Location
}
