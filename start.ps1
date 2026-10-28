param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    $existingRuntime = Join-Path $PSScriptRoot '..\outputs\toollens\.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $existingRuntime) { $appPython = (Resolve-Path -LiteralPath $existingRuntime).Path }
    else { throw 'Yerel Python ortamı bulunamadı. Önce .\setup.ps1 çalıştırın.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'frontend\dist\index.html'))) {
    throw 'Arayüz derlenmedi. Önce .\setup.ps1 veya frontend içinde npm run build çalıştırın.'
}
$env:PYTHONIOENCODING = 'utf-8'
if (-not $env:TOOL_LENS_PROJECT_ROOTS) { $env:TOOL_LENS_PROJECT_ROOTS = $PSScriptRoot }
Write-Host "ToolLens http://127.0.0.1:$Port adresinde başlıyor. Durdurmak için Ctrl+C."
& $appPython -m uvicorn backend.app:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
