<p align="center">
  <img src="assets/logo.png" width="128" alt="GuangPu-TTS Logo" />
</p>

<h1 align="center">像话 XiangHua · 口音 TTS</h1>

<p align="center">
  带口音的中文语音合成（TTS）工具包：台词批量配音，持续扩展实时连续对话<br/>
  <b>说话，就要像话</b>——输入文字，AI 用你想要的口音说出来
</p>

<p align="center">
  <a href="https://github.com/MouYuc/Clone-youself/blob/main/LICENSE"><img src="https://img.shields.io/github/license/MouYuc/Clone-youself?style=for-the-badge" alt="License" /></a>
  <a href="https://github.com/MouYuc/Clone-youself/pkgs/container/clone-youself"><img src="https://img.shields.io/badge/Docker-GHCR-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" /></a>
  <a href="https://hub.docker.com/r/ZeroJy/clone-youself"><img src="https://img.shields.io/docker/pulls/ZeroJy/clone-youself?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Pulls" /></a>
</p>

<p align="center">
  <!-- 运行环境徽章 -->
  <img src="https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10" />
  <img src="https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch 2.6" />
  <img src="https://img.shields.io/badge/CUDA-12-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="CUDA 12" />
  <img src="https://img.shields.io/badge/Windows%20%7C%20Linux%20%7C%20macOS-%E2%9C%93-0969DA?style=for-the-badge" alt="Windows | Linux | macOS" />
  <img src="https://img.shields.io/badge/VRAM-%E2%89%A58GB-8250DF?style=for-the-badge" alt="VRAM ≥ 8GB" />
</p>

<!-- 以上徽章均为 SVG，由 shields.io 实时生成、自动更新；手动添加教程见 docs/BADGES_GUIDE.md -->

---

> ⚠️ 请只使用**自己的声音**录音训练，不要克隆他人（包括动漫角色配音演员）的声音。

## 快速开始

<table align="center" style="width:100%;text-align:center;">
<thead>
<tr><th>步骤</th><th>Windows</th><th>Linux / macOS</th></tr>
</thead>
<tbody>
<tr><td>① 安装环境</td><td><code>.\setup.ps1</code></td><td><code>bash setup.sh</code></td></tr>
<tr><td>② 启动 WebUI</td><td><code>python tools\guangpu_webui.py</code></td><td><code>python tools\guangpu_webui.py</code></td></tr>
<tr><td>③ 在 WebUI 合成</td><td>打开「合成」页，粘贴台词 → 试听 / 下载</td><td>同左</td></tr>
</tbody>
</table>

> 首次试跑：在 WebUI「设置」页把模型路径指到 GPT-SoVITS 自带 v2Pro 底模。不想用浏览器？命令行批量合成 `python tools\guangpu_local_tts.py 台词.txt out\`（`GPT_MODEL` / `SOVITS_MODEL` 指定模型），详见[使用手册](docs/USAGE_GUIDE.md)。

- **用自己的声音**：先按[训练指南](docs/TRAINING_GUIDE.md)录音并训练出专属音色，再把模型路径换成训练产物
- **台词文件**：UTF-8，一行一句（建议 5~20 字），`#` 开头为注释；也可在 WebUI「合成」页直接粘贴台词

## 目录结构

```text
guangpu-tts/
├── setup.ps1 / setup.sh        # 一键环境安装（Windows / Linux·macOS）
├── Dockerfile                  # 环境镜像（不含声音模型）
├── docker-compose.yml
├── .github/workflows/          # 推送 GitHub 后自动构建镜像 → GHCR + Docker Hub
├── patches/
│   ├── guangpu_pinyin.patch    # 广普发音词典补丁（15 个粤字读音）
│   └── README.md               # 补丁说明 + 词典对照表
├── tools/
│   ├── guangpu_local_tts.py    # 批量合成工具（可移植，环境变量配置）
│   └── guangpu_webui.py        # WebUI（浏览器操作）
├── scripts/
│   ├── run_whisper.py          # 切片语音识别
│   ├── fix_transcript.py       # 标注人工修正模板
│   ├── build_train_configs.py  # 训练配置生成
│   └── sitecustomize.py        # Windows torchaudio 修复
├── assets/
│   ├── logo.png                # 项目 Logo
│   └── 广普训练台词本.txt       # 录音参考台词
├── examples/                   # 两个可直接运行的台词示例（含 # 注释行支持）
└── docs/
    ├── USAGE_GUIDE.md          # 使用手册（安装 / CLI / Docker / FAQ）
    ├── WEBUI_GUIDE.md          # WebUI 使用说明
    ├── TRAINING_GUIDE.md       # 训练流程详解
    └── BADGES_GUIDE.md         # 手动添加徽章教程
```

## 特性

<table align="center" style="width:100%;text-align:center;">
<thead>
<tr><th>功能</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td>广普发音词典补丁</td><td>15 个粤字（系/嘅/唔/咩/㗎…）按广普读音念</td></tr>
<tr><td>普通话自动转广普</td><td>是→系、没有→冇、什么→乜嘢…，浓度可调可关</td></tr>
<tr><td>批量合成</td><td>台词文件 → 逐句 mp3</td></tr>
<tr><td>WebUI</td><td>浏览器一站式：合成 / 批量 / 环境检测 / 训练引导 / 历史 / 设置</td></tr>
<tr><td>定稿配方</td><td>轻中浓度 + 自然语气（temperature 0.95 / 64 扩散步）</td></tr>
<tr><td>Docker 双仓库</td><td>推送 GitHub 自动构建，GHCR + Docker Hub 双镜像</td></tr>
</tbody>
</table>

## 技术栈

<table align="center" style="width:100%;text-align:center;">
<thead>
<tr><th>技术</th><th>用途</th></tr>
</thead>
<tbody>
<tr><td><a href="https://github.com/RVC-Boss/GPT-SoVITS">GPT-SoVITS</a> v2Pro</td><td>语音合成引擎：底模 / 训练 / 推理</td></tr>
<tr><td>Python 3.10</td><td>运行环境</td></tr>
<tr><td>PyTorch 2.6 + CUDA 12</td><td>深度学习框架（Windows CUDA 12.6 / Linux 12.1）</td></tr>
<tr><td><a href="https://github.com/SYSTRAN/faster-whisper">faster-whisper</a></td><td>录音自动识别（训练标注）</td></tr>
<tr><td><a href="https://www.gradio.app/">Gradio</a></td><td>WebUI 界面</td></tr>
<tr><td>soundfile + ffmpeg</td><td>音频读写与 mp3 转码</td></tr>
<tr><td>Docker + GitHub Actions</td><td>镜像自动构建，双推 GHCR / Docker Hub</td></tr>
</tbody>
</table>

## 文档

<table align="center" style="width:100%;text-align:center;">
<thead>
<tr><th>文档</th><th>内容</th></tr>
</thead>
<tbody>
<tr><td><a href="docs/USAGE_GUIDE.md">使用手册</a></td><td>一键安装 / 命令行合成 / Docker / 环境变量 / FAQ</td></tr>
<tr><td><a href="docs/TRAINING_GUIDE.md">训练指南</a></td><td>录音 → 切片识别 → 校对 → 训练 → 验收（命令带注释）</td></tr>
<tr><td><a href="docs/WEBUI_GUIDE.md">WebUI 指南</a></td><td>页面详解 / 配置优先级 / WebUI FAQ</td></tr>
</tbody>
</table>

## 许可证

MIT © 2026 MouYuc

GPT-SoVITS 本身为 MIT 协议，请遵守其许可条款。
