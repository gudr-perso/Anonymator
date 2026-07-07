# scripts/build.ps1
# Build + zip d'une (ou des) marque(s) Anonymator.
#   .\scripts\build.ps1 cap | cuma | dev | all
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('cap', 'cuma', 'dev', 'all')]
    [string]$Brand
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$spec = Join-Path $root 'anonymator.spec'

# Version lue depuis anonymator/__init__.py (source de vérité unique)
$initPy = Join-Path $root 'anonymator\__init__.py'
$version = (Select-String -Path $initPy -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value

$meta = @{
    cap  = @{ exe = 'capnonyme';  zip = "CAPnonyme-v$version.zip" }
    cuma = @{ exe = 'cumanonyme'; zip = "CumAnonyme-v$version.zip" }
    dev  = @{ exe = 'anonymator'; zip = $null }
}
$targets = if ($Brand -eq 'all') { @('cap', 'cuma') } else { @($Brand) }

foreach ($b in $targets) {
    Write-Host "== Build $b (v$version) =="
    $env:ANONYMATOR_BUILD_BRAND = $b
    & $python -m PyInstaller --noconfirm $spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller a echoue pour la marque '$b'" }

    $zip = $meta[$b].zip
    if ($zip) {
        $distDir = Join-Path $root "dist\$($meta[$b].exe)"
        # LICENSE visible a la racine du dossier distribue (AGPL) - cf. docs/RELEASE.md.
        # Le .spec le place dans _internal\ ; on le copie a cote de l'exe avant de zipper.
        $lic = Join-Path $distDir '_internal\LICENSE'
        if (Test-Path $lic) { Copy-Item $lic (Join-Path $distDir 'LICENSE') -Force }
        $zipPath = Join-Path $root "dist\$zip"
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
        Compress-Archive -Path $distDir -DestinationPath $zipPath
        Write-Host "Zip cree : $zipPath"
    }
}
Remove-Item Env:\ANONYMATOR_BUILD_BRAND -ErrorAction SilentlyContinue
Write-Host "Termine."
