param([string]$PythonExecutable = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $PythonExecutable -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 gerekir; bulunan: ' + sys.version.split()[0]"
if ($LASTEXITCODE -ne 0) { throw 'Python sürüm kontrolü başarısız. PythonExecutable ile Python 3.12 yolunu belirtin.' }
if (-not (Test-Path -LiteralPath $appPython)) {
    & $PythonExecutable -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Seçilen Python ile sanal ortam oluşturulamadı. Yukarıdaki hata ayrıntısını inceleyin.' }
}
& $appPython -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend bağımlılıkları kurulamadı.' }
$wheels = @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'vendor\wheels') -Filter 'portunusmcp_sentinel-1.4.0-*.whl' -ErrorAction SilentlyContinue)
if ($wheels.Count -gt 0) {
    & $appPython -m pip install $wheels[0].FullName
} else {
    $upstream = Join-Path $PSScriptRoot '..\..\work\MCP-Sentinel'
    if (Test-Path -LiteralPath $upstream) { & $appPython -m pip install $upstream }
    else { & $appPython -m pip install 'portunusmcp-sentinel==1.4.0' }
}
if ($LASTEXITCODE -ne 0) { throw 'Sentinel kurulamadı.' }
Push-Location frontend
try {
    if (Test-Path -LiteralPath package-lock.json) { & npm.cmd ci } else { & npm.cmd install }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend bağımlılıkları kurulamadı.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend derlemesi başarısız.' }
} finally { Pop-Location }
Write-Host 'Kurulum tamamlandı. .\start.ps1 ile başlatın.'
