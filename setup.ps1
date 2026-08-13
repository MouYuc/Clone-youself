# -*- coding: utf-8 -*-
<#
GuangPu-TTS 一键环境安装（Windows）

用法：
    .\setup.ps1                        # 默认从 ModelScope 下载底模
    .\setup.ps1 -Source HF-Mirror      # 换 HuggingFace 镜像
    .\setup.ps1 -GPT_SOVITS_ROOT D:\GPT-SoVITS   # 指定 GPT-SoVITS 位置

会自动完成：克隆 GPT-SoVITS -> Python 3.10 venv -> PyTorch CUDA 2.6
-> 依赖 -> 打广普补丁 -> 下载预训练底模 -> Windows 音频修复。
#>
param(
    [string]$GPT_SOVITS_ROOT = "",
    [ValidateSet("ModelScope", "HF", "HF-Mirror")]
    [string]$Source = "ModelScope"
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot

if (-not $GPT_SOVITS_ROOT) {
    $GPT_SOVITS_ROOT = Join-Path $RepoRoot "..\GPT-SoVITS"
}
$GPT_SOVITS_ROOT = [System.IO.Path]::GetFullPath($GPT_SOVITS_ROOT)
$VENV = Join-Path $GPT_SOVITS_ROOT ".venv"

Write-Host ""
Write-Host "=== GuangPu-TTS 一键环境安装 (Windows) ===" -ForegroundColor Green
Write-Host "GPT-SoVITS 位置: $GPT_SOVITS_ROOT"
Write-Host ""

# ---------- 1. 克隆 GPT-SoVITS ----------
if (-not (Test-Path (Join-Path $GPT_SOVITS_ROOT "requirements.txt"))) {
    Write-Host "[1/6] 克隆 GPT-SoVITS ..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path (Split-Path $GPT_SOVITS_ROOT) | Out-Null
    git clone https://github.com/RVC-Boss/GPT-SoVITS.git $GPT_SOVITS_ROOT
    # 锁定到广普补丁对应的 commit，避免上游更新导致补丁失效
    git -C $GPT_SOVITS_ROOT checkout d523079fc05d9a8028d6085bffe4a2757c32abb6
} else {
    Write-Host "[1/6] GPT-SoVITS 已存在，跳过克隆" -ForegroundColor Cyan
}

# ---------- 2. Python 3.10 虚拟环境 ----------
Write-Host "[2/6] 准备 Python 3.10 虚拟环境 ..." -ForegroundColor Cyan
$PythonExe = "python"
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv python install 3.10 2>$null
    uv venv $VENV --python 3.10
    $PythonExe = Join-Path $VENV "Scripts\python.exe"
} else {
    python -c "import sys; assert sys.version_info[:2] >= (3,10)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "需要 Python 3.10+。请先安装 Python 3.10（勾选 Add to PATH），或安装 uv：pip install uv" -ForegroundColor Yellow
        exit 1
    }
    python -m venv $VENV
    $PythonExe = Join-Path $VENV "Scripts\python.exe"
}

# ---------- 3. PyTorch CUDA 2.6 ----------
Write-Host "[3/6] 安装 PyTorch 2.6 (CUDA 12.6) ..." -ForegroundColor Cyan
& $PythonExe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126

# ---------- 4. GPT-SoVITS 依赖 ----------
Write-Host "[4/6] 安装 GPT-SoVITS 依赖 ..." -ForegroundColor Cyan
& $PythonExe -m pip install -r (Join-Path $GPT_SOVITS_ROOT "extra-req.txt") --no-deps
& $PythonExe -m pip install -r (Join-Path $GPT_SOVITS_ROOT "requirements.txt")
& $PythonExe -m pip install faster-whisper noisereduce

# ---------- 5. 打广普补丁 ----------
Write-Host "[5/6] 应用广普发音补丁 ..." -ForegroundColor Cyan
Push-Location $GPT_SOVITS_ROOT
git apply --check (Join-Path $RepoRoot "patches\guangpu_pinyin.patch") 2>$null
if ($LASTEXITCODE -eq 0) {
    git apply (Join-Path $RepoRoot "patches\guangpu_pinyin.patch")
} else {
    Write-Host "git apply 失败（可能已打过补丁），手动检查 patches/README.md" -ForegroundColor Yellow
}
Pop-Location

# Windows torchaudio 修复
Copy-Item (Join-Path $RepoRoot "scripts\sitecustomize.py") (Join-Path $GPT_SOVITS_ROOT "GPT_SoVITS\sitecustomize.py") -Force

# ---------- 6. 下载预训练底模 ----------
Write-Host "[6/6] 下载预训练底模（$Source）..." -ForegroundColor Cyan
Push-Location $GPT_SOVITS_ROOT
switch ($Source) {
    "ModelScope" { $Base = "https://www.modelscope.cn/models/XXXXRT/GPT-SoVITS-Pretrained/resolve/master" }
    "HF-Mirror"  { $Base = "https://hf-mirror.com/XXXXRT/GPT-SoVITS-Pretrained/resolve/main" }
    "HF"         { $Base = "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main" }
}
if (-not (Test-Path "GPT_SoVITS\pretrained_models\sv")) {
    Invoke-WebRequest "$Base/pretrained_models.zip" -OutFile "pretrained_models.zip"
    Expand-Archive "pretrained_models.zip" "GPT_SoVITS" -Force
    Remove-Item "pretrained_models.zip"
}
if (-not (Test-Path "GPT_SoVITS\text\G2PWModel")) {
    Invoke-WebRequest "$Base/G2PWModel.zip" -OutFile "G2PWModel.zip"
    Expand-Archive "G2PWModel.zip" "GPT_SoVITS\text" -Force
    Remove-Item "G2PWModel.zip"
}
Pop-Location

Write-Host ""
Write-Host "=== 安装完成 ===" -ForegroundColor Green
Write-Host "下一步：按 docs/TRAINING_GUIDE.md 录 5~15 分钟素材并训练你的广普音色"
Write-Host "合成：GPT_SOVITS_ROOT=$GPT_SOVITS_ROOT 后运行 tools\guangpu_local_tts.py 台词.txt 输出目录"
Write-Host "WebUI：GPT_SOVITS_ROOT=$GPT_SOVITS_ROOT 后运行 python tools\guangpu_webui.py（浏览器打开 http://127.0.0.1:7860）"
