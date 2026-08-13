# GuangPu-TTS · 广普配音工具包

给 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 增加"广普"（广东普通话）配音能力的工具包：

- 🗣️ **广普发音词典补丁**：15 个粤字（系/嘅/唔/咩/㗎…）的广普读音覆盖，让 AI 不再把粤字按普通话字典音念出来
- 🎬 **批量合成工具**：台词文件 → 逐句 mp3，一步到位
- 🖥️ **WebUI**：浏览器界面，写台词、调参数、试听下载、环境体检一站式
- 📚 **训练流程**：从 5 分钟录音到专属广普音色的完整教程
- 🎯 定稿配方：轻中浓度 + 自然语气（temperature 0.95 / 64 扩散步）

## 这是什么 / 不是什么

- **是**：一套给 GPT-SoVITS 的"广普增强包"（补丁 + 工具 + 教程），帮你训练出带广东口音的普通话配音
- **不是**：完整的 GPT-SoVITS 发行版（请自行安装 GPT-SoVITS）、不包含任何预训练声音模型、不包含录音素材

> ⚠️ 本仓库不包含任何人的声音克隆模型。请使用**自己的声音**录音训练，不要克隆他人（包括动漫角色配音演员）的声音。

## 目录结构

```text
guangpu-tts/
├── setup.ps1 / setup.sh        # 一键环境安装（Windows / Linux·macOS）
├── Dockerfile                  # 环境镜像（不含声音模型）
├── docker-compose.yml
├── .github/workflows/          # 推送 GitHub 后自动构建镜像 → GHCR
├── patches/
│   ├── guangpu_pinyin.patch   # 广普发音词典补丁
│   └── README.md              # 补丁说明
├── tools/
│   ├── guangpu_local_tts.py   # 批量合成工具（可移植，环境变量配置）
│   └── guangpu_webui.py       # WebUI（浏览器操作）
├── scripts/
│   ├── run_whisper.py         # 切片语音识别
│   ├── fix_transcript.py      # 标注人工修正模板
│   ├── build_train_configs.py # 训练配置生成
│   └── sitecustomize.py       # Windows torchaudio 修复
├── assets/
│   └── 广普训练台词本.txt       # 录音参考台词
├── examples/
│   ├── 台词示例_普通话输入.txt  # 普通话 → 自动转轻中广普
│   ├── 台词示例_广普直写.txt    # 直接写粤字，精确控制浓度
│   └── README.md
└── docs/
    ├── WEBUI_GUIDE.md         # WebUI 使用说明
    └── TRAINING_GUIDE.md      # 训练流程详解
```

`examples/` 里有两个可直接运行的台词示例（含 `#` 注释行支持）。

## 一键安装（推荐）

本仓库**不携带 GPT-SoVITS 环境**（它本体 + 模型约 15GB，且是独立 MIT 项目），
但一条命令就能帮你把环境全部配好：

**Windows：**

```powershell
.\setup.ps1
```

**Linux / macOS：**

```bash
bash setup.sh
```

脚本会自动完成：克隆 GPT-SoVITS → Python 3.10 虚拟环境 → PyTorch CUDA →
依赖 → 打广普补丁 → 下载预训练底模 → Windows 音频修复。

## WebUI（推荐体验）

一条命令启动图形界面，打开浏览器即可合成、试听、批量产出：

```powershell
# Windows
$env:GPT_SOVITS_ROOT = 'D:\AIVoice\GPT-SoVITS'   # 按你的实际路径
python tools\guangpu_webui.py
```

```bash
# Linux / macOS
export GPT_SOVITS_ROOT=/path/to/GPT-SoVITS
python tools/guangpu_webui.py
```

浏览器打开 <http://127.0.0.1:7860>，六个页面：合成 / 批量合成 / 环境检测 / 训练引导 /
历史记录 / 设置。环境检测页会直接告诉你缺什么依赖，并给出修复命令。
详见 [docs/WEBUI_GUIDE.md](docs/WEBUI_GUIDE.md)。

> 环境就绪后，你还需要**训练自己的广普音色**（见训练章节）才能用到自己的声音；
> 想先试跑，可以把 `tools/guangpu_local_tts.py` 的模型路径指到 GPT-SoVITS
> 自带的 v2Pro 底模（`pretrained_models/s1v3.ckpt` + `pretrained_models/v2Pro/s2Gv2Pro.pth`）。

## Docker 镜像（可选）

仓库内置 Dockerfile，推送到 GitHub 后由 Actions **自动构建**并上传到
[ghcr.io/mouyuc/clone-youself](https://github.com/MouYuc/Clone-youself/pkgs/container/clone-youself)
（不含任何声音模型，只含引擎 + 广普补丁 + 工具）。

```bash
# 1. 拉取镜像
docker pull ghcr.io/mouyuc/clone-youself:latest

# 2. 准备公开底模目录（pretrained_models 与 G2PWModel 从 GPT-SoVITS 官方仓库下载）
mkdir -p models my_voice

# 3. 运行批量合成（挂载你自己的模型/数据集/台词）
docker run --gpus all -it --rm \
  -v $PWD/models/pretrained_models:/workspace/GPT-SoVITS/GPT_SoVITS/pretrained_models \
  -v $PWD/models/G2PWModel:/workspace/GPT-SoVITS/GPT_SoVITS/text/G2PWModel \
  -v $PWD/my_voice:/workspace/GPT-SoVITS/custom_data \
  ghcr.io/mouyuc/clone-youself:latest \
  python /workspace/tools/guangpu_local_tts.py /workspace/GPT-SoVITS/custom_data/台词.txt /workspace/output
```

> 首次推送 main 后约 15~30 分钟出镜像，可在仓库 **Actions** 页查看构建进度；
> 训练自己的音色时，把录音放进 `my_voice/` 后按 TRAINING_GUIDE 在容器内执行。

## 快速开始（合成）

前提：已安装 GPT-SoVITS（Windows 建议 Python 3.10 + PyTorch CUDA），并已训练好你自己的广普音色模型。

```bash
# 1. 打补丁（改文本前端，让粤字按广普读音）
cd GPT-SoVITS
git apply ../guangpu-tts/patches/guangpu_pinyin.patch

# 2. Windows 修复（torchaudio 依赖问题，可选但推荐）
cp ../guangpu-tts/scripts/sitecustomize.py GPT_SoVITS/sitecustomize.py

# 3. 批量合成：一行一句台词
python ../guangpu-tts/tools/guangpu_local_tts.py 台词.txt 输出目录
```

模型/参考音频路径默认按"仓库和 GPT-SoVITS 平级"布局，可用环境变量覆盖：

```bash
GPT_MODEL=... SOVITS_MODEL=... REF_AUDIO=... REF_TEXT=... python guangpu_local_tts.py 台词.txt out/
```

台词写普通普通话即可，工具会自动转"轻中"广普（是→系、不是→唔系、最重要→最紧要、没有→冇、什么→乜嘢…）。

## 训练自己的广普音色（5 分钟录音 → 专属模型）

完整流程见 [docs/TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md)，要点：

1. 用 [广普训练台词本.txt](assets/广普训练台词本.txt) 录 5~15 分钟（模仿你想做的口音，自然随意）
2. 切片 → Whisper 识别 → **人工校对标注**（广普识别错字多，必须校）
3. 提取 BERT / HuBERT / 声纹 / 语义特征（GPT-SoVITS 自带脚本）
4. 训练 s1（GPT）约 15 epoch + s2（SoVITS）约 12 epoch（8GB 显存可跑）
5. 用 `tools/guangpu_local_tts.py` 合成验收

## 常见问题

**Q: 合成声音有噪点/卡顿？**
小数据训练常见。先试：声码器步数调高（`SAMPLE_STEPS=64`）、换更干净的参考音频；根本解法是加录音量（10 分钟以上）重训。

**Q: 粤字还是按普通话念？**
说明补丁没生效：确认 `git apply` 成功，且训练前重新执行了 1-get-text.py（补丁只影响训练阶段）。

**Q: Windows 上 torchaudio/torchcodec 报错？**
见 `scripts/sitecustomize.py`（soundfile 后端）和 TRAINING_GUIDE 的环境章节。

## License

MIT © 2026 MouYuc

GPT-SoVITS 本身为 MIT 协议，请遵守其许可条款。

---

# GuangPu-TTS · Cantonese-accented Mandarin TTS Toolkit

An add-on toolkit for [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) that
enables "GuangPu" (Cantonese-accented Mandarin) voice synthesis:

- 🗣️ **GuangPu pronunciation dictionary patch** — correct readings for 15
  Cantonese characters (系/嘅/唔/咩/㗎…) so the model stops reading them with
  Mandarin dictionary pronunciations
- 🎬 **Batch synthesis tool** — turn a script file into per-line mp3s
- 🖥️ **WebUI** — browser interface: write lines, tune params, preview/download,
  and check your environment in one place
- 📚 **Training guide** — from a 5-minute recording to your own GuangPu voice
- 🎯 Tuned recipe: light-medium accent + natural prosody (temperature 0.95 / 64 diffusion steps)

## What this is / is not

- **Is**: a GuangPu enhancement pack (patch + tools + guide) for GPT-SoVITS
- **Is not**: a GPT-SoVITS distribution, a model repository, or a dataset

> ⚠️ This repo contains **no voice clones**. Train with **your own voice**.
> Do not clone other people's voices (including anime voice actors).

## One-command setup

This repo does **not** bundle the GPT-SoVITS environment (it is ~15GB and a
separate MIT project). Instead, run:

**Windows:**

```powershell
.\setup.ps1
```

**Linux / macOS:**

```bash
bash setup.sh
```

The script clones GPT-SoVITS, creates a Python 3.10 venv, installs PyTorch CUDA
and dependencies, applies the GuangPu patch, downloads the pretrained base
models, and applies the Windows audio fix.

## WebUI (recommended)

One command starts a browser UI for synthesis, preview, and batch output:

```bash
export GPT_SOVITS_ROOT=/path/to/GPT-SoVITS
python tools/guangpu_webui.py
```

Open <http://127.0.0.1:7860> — pages: Synthesize / Batch / Environment check /
Training guide / History / Settings. The environment check page tells you exactly
what is missing and how to fix it. See [docs/WEBUI_GUIDE.md](docs/WEBUI_GUIDE.md).

> After setup you still need to **train your own GuangPu voice** (see below)
> to use your own timbre. To smoke-test first, point the tool's model paths at
> GPT-SoVITS's built-in v2Pro base models.

## Docker image (optional)

This repo ships a Dockerfile; pushing to GitHub triggers an Actions workflow that
auto-builds and uploads the image to
[ghcr.io/mouyuc/clone-youself](https://github.com/MouYuc/Clone-youself/pkgs/container/clone-youself)
(no voice models included — engine + GuangPu patch + tools only).

```bash
docker pull ghcr.io/mouyuc/clone-youself:latest
mkdir -p models my_voice
# download the public base models (pretrained_models, G2PWModel) into models/

docker run --gpus all -it --rm \
  -v $PWD/models/pretrained_models:/workspace/GPT-SoVITS/GPT_SoVITS/pretrained_models \
  -v $PWD/models/G2PWModel:/workspace/GPT-SoVITS/GPT_SoVITS/text/G2PWModel \
  -v $PWD/my_voice:/workspace/GPT-SoVITS/custom_data \
  ghcr.io/mouyuc/clone-youself:latest \
  python /workspace/tools/guangpu_local_tts.py /workspace/GPT-SoVITS/custom_data/台词.txt /workspace/output
```

The first build after pushing `main` takes ~15-30 min; watch the **Actions** tab.

## Quick start (synthesis)

Prereq: GPT-SoVITS installed (Windows: Python 3.10 + CUDA PyTorch recommended)
and your own trained GuangPu voice model.

```bash
cd GPT-SoVITS
git apply ../guangpu-tts/patches/guangpu_pinyin.patch
cp ../guangpu-tts/scripts/sitecustomize.py GPT_SoVITS/sitecustomize.py   # Windows fix
python ../guangpu-tts/tools/guangpu_local_tts.py 台词.txt out/
```

Paths default to a layout where this repo sits next to `GPT-SoVITS`; override
with `GPT_MODEL`, `SOVITS_MODEL`, `REF_AUDIO`, `REF_TEXT` env vars.

Write scripts in plain Mandarin — the tool auto-converts to light-medium
GuangPu (是→系, 不是→唔系, 最重要→最紧要, 没有→冇, 什么→乜嘢 …).

## Train your own GuangPu voice

Full steps in [docs/TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md).

## FAQ

**Q: Noisy / choppy output?** Raise `SAMPLE_STEPS` (64), pick a cleaner
reference clip; the real fix is more training data (10+ min).

**Q: Cantonese characters still read as Mandarin?** The patch wasn't active
during training — re-run 1-get-text.py and retrain.

**Q: torchaudio/torchcodec errors on Windows?** See `scripts/sitecustomize.py`.

## License

MIT © 2026 MouYuc. GPT-SoVITS is MIT-licensed; respect its terms.
