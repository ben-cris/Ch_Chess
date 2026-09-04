# 开发脚本：建 venv、装依赖、跑测试
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
& ".venv\Scripts\python.exe" -m pytest
Write-Host "运行程序：.venv\Scripts\python.exe main.py"