# 安装 Android SDK 到 D:\Android（Chaquopy 构建无需 NDK；后续接 C/C++ 或原生引擎再加）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\setup_android_sdk.ps1
$ErrorActionPreference = "Stop"
$sdk = "D:\Android"
$cmdline = Join-Path $sdk "cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $cmdline)) {
    New-Item -ItemType Directory -Force -Path $sdk | Out-Null
    $url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    $zip = Join-Path $sdk "cmdline-tools.zip"
    Write-Host "下载 commandline-tools ..."
    curl.exe -L --fail -o $zip $url
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $sdk "tmp") -Force
    New-Item -ItemType Directory -Force -Path (Join-Path $sdk "cmdline-tools") | Out-Null
    Move-Item -LiteralPath (Join-Path $sdk "tmp\cmdline-tools\bin") -Destination (Join-Path $sdk "cmdline-tools\bin") -Force
    Remove-Item -LiteralPath (Join-Path $sdk "tmp") -Recurse -Force
    Remove-Item -LiteralPath $zip -Force
}
$packages = "platform-tools", "platforms;android-34", "build-tools;34.0.0"
Write-Host "安装 SDK 组件（首次较大，需数分钟）..."
("y" | & $cmdline --sdk_root=$sdk ($packages -join " ")) | Out-Host
Write-Host "完成。请确认 android\local.properties 内容为: sdk.dir=D:\\Android"