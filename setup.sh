#!/usr/bin/env bash
# GuangPu-TTS 一键环境安装（Linux / macOS）
#
# 用法：
#   bash setup.sh                 # 默认 ModelScope 下载底模
#   bash setup.sh HF-Mirror       # 换 HuggingFace 镜像
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${1:-ModelScope}"
GPT_ROOT="${GPT_SOVITS_ROOT:-$REPO_ROOT/../GPT-SoVITS}"

echo "=== GuangPu-TTS 一键环境安装 (Linux/macOS) ==="
echo "GPT-SoVITS 位置: $GPT_ROOT"

# 1. 克隆 GPT-SoVITS
if [ ! -f "$GPT_ROOT/requirements.txt" ]; then
  echo "[1/6] 克隆 GPT-SoVITS ..."
  mkdir -p "$(dirname "$GPT_ROOT")"
  git clone https://github.com/RVC-Boss/GPT-SoVITS.git "$GPT_ROOT"
  # 锁定到广普补丁对应的 commit
  git -C "$GPT_ROOT" checkout d523079fc05d9a8028d6085bffe4a2757c32abb6
else
  echo "[1/6] GPT-SoVITS 已存在"
fi

# 2. Python 3.10 venv
echo "[2/6] 创建 Python 3.10 虚拟环境 ..."
PY="python3.10"
command -v $PY >/dev/null 2>&1 || PY=python3
"$PY" -m venv "$GPT_ROOT/.venv"
PYBIN="$GPT_ROOT/.venv/bin/python"

# 3. PyTorch（Linux CUDA 12.1；macOS 自动 CPU）
echo "[3/6] 安装 PyTorch ..."
if [ "$(uname)" = "Darwin" ]; then
  "$PYBIN" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
else
  "$PYBIN" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu121
fi

# 4. 依赖
echo "[4/6] 安装 GPT-SoVITS 依赖 ..."
"$PYBIN" -m pip install -r "$GPT_ROOT/extra-req.txt" --no-deps
"$PYBIN" -m pip install -r "$GPT_ROOT/requirements.txt"
"$PYBIN" -m pip install faster-whisper noisereduce

# 5. 广普补丁
echo "[5/6] 应用广普发音补丁 ..."
cd "$GPT_ROOT"
if git apply --check "$REPO_ROOT/patches/guangpu_pinyin.patch" 2>/dev/null; then
  git apply "$REPO_ROOT/patches/guangpu_pinyin.patch"
else
  echo "补丁可能已应用，跳过（见 patches/README.md）"
fi

# 6. 预训练底模
echo "[6/6] 下载预训练底模（$SOURCE）..."
case "$SOURCE" in
  ModelScope) BASE="https://www.modelscope.cn/models/XXXXRT/GPT-SoVITS-Pretrained/resolve/master" ;;
  HF-Mirror)  BASE="https://hf-mirror.com/XXXXRT/GPT-SoVITS-Pretrained/resolve/main" ;;
  *)          BASE="https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main" ;;
esac
if [ ! -d "GPT_SoVITS/pretrained_models/sv" ]; then
  curl -L -o pretrained_models.zip "$BASE/pretrained_models.zip"
  unzip -o pretrained_models.zip -d GPT_SoVITS
  rm pretrained_models.zip
fi
if [ ! -d "GPT_SoVITS/text/G2PWModel" ]; then
  curl -L -o G2PWModel.zip "$BASE/G2PWModel.zip"
  unzip -o G2PWModel.zip -d GPT_SoVITS/text
  rm G2PWModel.zip
fi

echo ""
echo "=== 安装完成 ==="
echo "训练：见 docs/TRAINING_GUIDE.md"
echo "合成：GPT_SOVITS_ROOT=$GPT_ROOT python tools/guangpu_local_tts.py 台词.txt 输出目录"
echo "WebUI：GPT_SOVITS_ROOT=$GPT_ROOT python tools/guangpu_webui.py（浏览器打开 http://127.0.0.1:7860）"
