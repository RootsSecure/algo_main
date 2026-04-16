$ErrorActionPreference = "Stop"

$pythonRoot = "C:\Users\Gunjan\AppData\Local\Programs\Python\Python311"
$pythonExe = Join-Path $pythonRoot "python.exe"
$venvPath = "D:\Nri project\sentinel_edge\directml_venv"
$requirementsPath = "D:\Nri project\sentinel_edge\training\requirements-directml.txt"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    $installer = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installer
    Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=0 Include_pip=1 Include_test=0 TargetDir="C:\Users\Gunjan\AppData\Local\Programs\Python\Python311"' -Wait
}

if (-not (Test-Path -LiteralPath $venvPath)) {
    & $pythonExe -m venv $venvPath
}

& "$venvPath\Scripts\python.exe" -m pip install --upgrade pip
& "$venvPath\Scripts\pip.exe" install -r $requirementsPath

Write-Host "DirectML environment ready at $venvPath"
Write-Host "Train with:"
Write-Host "$venvPath\Scripts\python.exe -m sentinel_edge.training.train_detector --prepare --device directml --epochs 50 --imgsz 640"
