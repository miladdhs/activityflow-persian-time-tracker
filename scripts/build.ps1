# Build the Windows executable.
#   .\scripts\build.ps1                 -> dist\ActivityFlow\ActivityFlow.exe (folder build, fast start)
#   .\scripts\build.ps1 -OneFile        -> dist\ActivityFlow.exe (single portable file)
#   .\scripts\build.ps1 -OneFile -Zip   -> also dist\ActivityFlow-<version>-windows-x64.zip (release asset)
# Name and version are read from app/__init__.py.
param([switch]$OneFile, [switch]$Zip, [switch]$SkipTests)

# Native tools log progress to stderr, so failures are detected via $LASTEXITCODE instead of "Stop".
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$name = (& $python -c "import app; print(app.APP_NAME)").Trim()
$version = (& $python -c "import app; print(app.APP_VERSION)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $version) { throw "Could not read the app version." }
Write-Host "$name $version" -ForegroundColor Cyan

if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    $env:QT_QPA_PLATFORM = "offscreen"
    & $python -m pytest -q
    Remove-Item Env:QT_QPA_PLATFORM
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; build aborted." }
}

Write-Host "Generating icon..." -ForegroundColor Cyan
$env:QT_QPA_PLATFORM = "offscreen"
& $python scripts\make_icon.py
Remove-Item Env:QT_QPA_PLATFORM
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed." }

$env:ACTIVITYFLOW_ONEFILE = if ($OneFile) { "1" } else { "0" }
Write-Host "Building ($(if ($OneFile) { 'onefile' } else { 'onedir' }))..." -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\ActivityFlow.spec
Remove-Item Env:ACTIVITYFLOW_ONEFILE
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

$exe = if ($OneFile) { "dist\$name.exe" } else { "dist\$name\$name.exe" }
Write-Host "Done: $exe" -ForegroundColor Green

if ($Zip) {
    $archive = "dist\$name-$version-windows-x64.zip"
    $source = if ($OneFile) { $exe } else { "dist\$name" }
    if (Test-Path $archive) { Remove-Item $archive }
    Compress-Archive -Path $source -DestinationPath $archive -CompressionLevel Optimal
    Write-Host "Archive: $archive" -ForegroundColor Green
}
