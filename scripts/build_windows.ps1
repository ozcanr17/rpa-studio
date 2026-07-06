param(
    [switch]$Console,
    [switch]$Headless,
    [switch]$DryRun,
    [switch]$SkipSelftest,
    [switch]$NoZip
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
if ($Console) { $buildArgs += "--console" }
if ($Headless) { $buildArgs += "--headless" }
if ($DryRun) { $buildArgs += "--dry-run" }

Push-Location $root
try {
    & $python -m rpa_framework.packaging.build @buildArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($DryRun) { exit 0 }

    if ($Headless) {
        $built = Join-Path $root "dist\runner_app.dist"
        $stage = Join-Path $root "dist\rpa-run-windows"
        $exeName = "rpa-run.exe"
    } else {
        $built = Join-Path $root "dist\app.dist"
        $stage = Join-Path $root "dist\rpa-studio-windows"
        $exeName = "RPAStudio.exe"
    }

    if (-not (Test-Path (Join-Path $built $exeName))) {
        Write-Host "Build finished but $built\$exeName is missing"
        exit 1
    }
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force -Confirm:$false }
    Move-Item $built $stage
    $exe = Join-Path $stage $exeName

    if (-not $Headless -and -not $SkipSelftest) {
        $report = Join-Path $root "dist\selftest.txt"
        if (Test-Path $report) { Remove-Item $report -Force -Confirm:$false }
        Start-Process -FilePath $exe -ArgumentList "--selftest", $report -Wait
        if (-not (Test-Path $report)) {
            Write-Host "Selftest produced no report"
            exit 1
        }
        Get-Content $report
        $failures = Select-String -Path $report -Pattern "\[fail\]" -CaseSensitive:$false
        if ($failures) {
            Write-Host "SELFTEST FAILED"
            exit 1
        }
        Write-Host "Selftest passed."
    }

    if (-not $NoZip) {
        $zip = "$stage.zip"
        if (Test-Path $zip) { Remove-Item $zip -Force -Confirm:$false }
        Compress-Archive -Path $stage -DestinationPath $zip
        Write-Host "Artifact: $zip"
    }
    Write-Host "Portable folder: $stage"
} finally {
    Pop-Location
}
