# 下载并解压随包 Pikafish 强引擎（Windows x64）到 engine/bin/pikafish。
# 用法：powershell -ExecutionPolicy Bypass -File scripts\fetch_pikafish.ps1
# 下载后，“设置 -> 分析引擎”选“自动（推荐）”即可自动使用。
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$binDir = Join-Path $root "engine\bin"
$outDir = Join-Path $binDir "pikafish"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# 1) 查询最新发布 tag
$releasePage = Invoke-WebRequest -Uri "https://github.com/official-pikafish/Pikafish/releases/latest" -Headers @{ "User-Agent" = "fetch_pikafish" } -UseBasicParsing
$m = [regex]::Match($releasePage.Content, '/official-pikafish/Pikafish/releases/tag/([A-Za-z0-9._-]+)')
if (-not $m.Success) { throw "无法解析 Pikafish 最新发布版本号" }
$tag = $m.Groups[1].Value
$asset = "Pikafish.$tag.7z"
$url = "https://github.com/official-pikafish/Pikafish/releases/download/$tag/$asset"
$tmp = Join-Path $binDir $asset
Write-Host "下载 $url ..."
curl.exe -L --fail -A "fetch_pikafish" -o $tmp $url

# 2) 用 python + py7zr 解压需要的文件（若无 py7zr 自动安装到项目虚拟环境）
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py -c "import py7zr" 2>$null
if ($LASTEXITCODE -ne 0) { & $py -m pip install py7zr | Out-Null }
$code = @"
import os, shutil, py7zr
src = r"$tmp"
out = r"$outDir"
targets = ["Windows/pikafish-sse41-popcnt.exe", "Windows/pikafish-avx2.exe",
           "pikafish.nnue", "Copying.txt", "NNUE-License.md", "README.md"]
with py7zr.SevenZipFile(src, "r") as z:
    z.extract(path=out, targets=targets)
for root, _, files in os.walk(out):
    for fn in files:
        full = os.path.join(root, fn)
        dst = os.path.join(out, fn)
        if os.path.abspath(full) != os.path.abspath(dst) and os.path.exists(full):
            shutil.move(full, dst)
for root, dirs, _ in os.walk(out, topdown=False):
    for d in dirs:
        try: os.rmdir(os.path.join(root, d))
        except OSError: pass
"@
$code | & $py -
Remove-Item $tmp -Force
Write-Host "完成：$outDir"
Write-Host "提示：SSE4.1 版（pikafish-sse41-popcnt.exe）兼容性最广，程序会自动优先使用；AVX2 版已一并备好。"
