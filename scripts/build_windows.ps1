param(
    [switch]$NoOnefile,
    [switch]$Console,
    [switch]$Headless,
    [switch]$DryRun,
    [switch]$SkipSelftest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv-build\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Build venv not found: $python"
    Write-Host "Create it with a python.org CPython (Store Python cannot build):"
    Write-Host "  py -V:3.14 -m venv .venv-build"
    Write-Host "  .venv-build\Scripts\pip install -r rpa_framework\requirements.txt nuitka"
    exit 1
}

$buildArgs = @()
if ($NoOnefile) { $buildArgs += "--no-onefile" }
if ($Console) { $buildArgs += "--console" }
if ($Headless) { $buildArgs += "--headless" }
if ($DryRun) { $buildArgs += "--dry-run" }

Push-Location $root
try {
    & $python -m rpa_framework.packaging.build @buildArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($DryRun -or $Headless -or $NoOnefile -or $SkipSelftest) { exit 0 }
    $exe = Join-Path $root "dist\RPAStudio.exe"
    if (-not (Test-Path $exe)) {
        Write-Host "Build finished but $exe is missing"
        exit 1
    }
    $report = Join-Path $root "dist\selftest.txt"
    if (Test-Path $report) { Remove-Item $report -Force -Confirm:$false }
    Start-Process -FilePath $exe -ArgumentList "--selftest", $report -Wait
    if (-not (Test-Path $report)) {
        Write-Host "Selftest produced no report"
        exit 1
    }
    Get-Content $report
    $failures = Select-String -Path $report -Pattern "^fail" -CaseSensitive:$false
    if ($failures) {
        Write-Host "SELFTEST FAILED"
        exit 1
    }
    Write-Host "Selftest passed. Artifact: $exe"
} finally {
    Pop-Location
}
