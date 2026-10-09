# Run ActivityFlow from source.  Use -Demo to try it with sample data in a separate folder.
param([switch]$Demo)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if ($Demo) {
    $env:ACTIVITYFLOW_DATA_DIR = Join-Path $root "demo-data"
    & $python scripts\demo_data.py
}
& $python main.py
