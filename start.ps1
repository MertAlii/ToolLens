param([int]$Port = 8001, [string]$PythonExecutable = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    Write-Host 'İlk kullanım: proje bağımlılıkları kuruluyor.'
    & (Join-Path $PSScriptRoot 'setup.ps1') -PythonExecutable $PythonExecutable
    if (-not (Test-Path -LiteralPath $appPython)) { throw 'Kurulum tamamlanamadı. setup.ps1 çıktısını inceleyin.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'frontend\dist\index.html'))) {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'Arayüzü hazırlamak için Node.js ve npm gerekir. Kurulumdan sonra yeniden başlatın.' }
    Push-Location (Join-Path $PSScriptRoot 'frontend')
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Arayüz bağımlılıkları kurulamadı.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Arayüz derlemesi başarısız.' }
    } finally { Pop-Location }
}
$env:PYTHONIOENCODING = 'utf-8'
if (-not $env:TOOL_LENS_PROJECT_ROOTS) { $env:TOOL_LENS_PROJECT_ROOTS = $PSScriptRoot }
Write-Host "ToolLens http://127.0.0.1:$Port adresinde başlıyor. Durdurmak için Ctrl+C."
& $appPython -m uvicorn backend.app:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
