$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    throw 'Yerel Python ortamı bulunamadı. Önce .\setup.ps1 çalıştırın.'
}
$env:PYTHONIOENCODING = 'utf-8'
Write-Host 'ToolLens Risk MCP: http://127.0.0.1:8012/mcp — durdurmak için Ctrl+C.'
& $appPython -m backend.risk_mcp
exit $LASTEXITCODE
