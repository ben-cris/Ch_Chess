# EXE 打包（PyInstaller，onedir 模式）
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv")) { Write-Host "请先运行 scripts\dev.ps1 创建虚拟环境"; exit 1 }
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name "XiangqiAssistant" --collect-all PySide6 main.py
Write-Host "输出目录：dist\XiangqiAssistant"