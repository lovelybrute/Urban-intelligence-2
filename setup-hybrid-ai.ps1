param(
    [switch]$TrainCustom
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "frontend\ml\.venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PythonLauncher) {
        & $PythonLauncher.Source -m venv (Join-Path $RepoRoot "frontend\ml\.venv")
    } else {
        $PythonCommand = Get-Command python -ErrorAction Stop
        & $PythonCommand.Source -m venv (Join-Path $RepoRoot "frontend\ml\.venv")
    }
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $RepoRoot "frontend\ml\requirements-hybrid.txt")
& $VenvPython (Join-Path $RepoRoot "frontend\ml\training\prepare_hybrid_models.py")

if (-not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
    Write-Warning "Tesseract is not on PATH. Install Tesseract OCR before using number-plate reading."
}

if ($TrainCustom) {
    & $VenvPython (Join-Path $RepoRoot "frontend\ml\training\train_custom_models.py") --batch 4 --imgsz 640 --workers 2
    & $VenvPython (Join-Path $RepoRoot "frontend\ml\training\prepare_hybrid_models.py")
}

Write-Host "Hybrid AI preparation complete. Read frontend\ml\model_manifest.json for verified status."
