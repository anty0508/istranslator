# Build iSTranslater into a single headless istranslator.exe
# Usage:  ./build.ps1

$ErrorActionPreference = "Stop"

# ensure PyInstaller is available (invoked via `python -m` so PATH doesn't matter)
python -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller
}

# regenerate the app icon (icon.ico is already committed; this just refreshes it)
python scripts/make_icon.py

# bundle the .env INTO the exe so it is self-contained (key is baked in — keep the exe private)
$addData = @()
if (Test-Path .env) { $addData = @("--add-data", ".env;.") }

python -m PyInstaller --noconfirm --clean `
    --onefile `
    --windowed `
    --name istranslator `
    --icon assets/icon.ico `
    --collect-all openai `
    --collect-all certifi `
    @addData `
    main.py

Write-Host ""
Write-Host "Built dist\istranslator.exe" -ForegroundColor Green
Write-Host "Place your .env (with OPENAI_API_KEY) next to the exe, then run it." -ForegroundColor Yellow
