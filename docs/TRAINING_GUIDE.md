# 训练流程详解 · Training Guide

目标：用 5~15 分钟自己的录音，训练出专属"广普"音色（GPT-SoVITS v2Pro）。

## 0. 环境

- Windows：Python 3.10 + PyTorch CUDA（2.6 稳定，2.13 在 Windows 有 gloo 崩溃问题，见 FAQ）
- ffmpeg 需在 PATH（共享版）
- 8GB 显存可训练（batch 8 / 4）
- 把 `scripts/sitecustomize.py` 放进 `GPT_SoVITS/`（Windows torchaudio 修复）

## 1. 录音

按 `assets/广普训练台词本.txt` 录 5~15 分钟：

- 自然、随意、带情绪，模仿你想做的口音（不要播音腔）
- 安静环境，句间停顿半秒到一秒，念错重念那句即可
- WAV 或 MP3，导出后放到 `custom_data/raw/`

## 2. 切片

```bash
cd GPT-SoVITS
python -s tools/slice_audio.py custom_data/raw custom_data/sliced -35 4000 300 10 500 0.9 0.25 0 1
```

## 3. 语音识别 + 人工校对

```bash
python scripts/run_whisper.py --input custom_data/sliced --output custom_data/asr
```

广普/粤语词识别错字多，**必须人工校对**：

```bash
python scripts/fix_transcript.py --input custom_data/asr/sliced_whisper.list --output custom_data/asr/sliced_corrected.list
```

把 `fix_transcript.py` 里的修正表按"你实际说了什么"填写，逐句对齐。

## 4. 特征提取（GPT-SoVITS 自带脚本）

```bash
# 环境变量
set inp_text=custom_data\asr\sliced_corrected.list
set inp_wav_dir=custom_data\sliced
set exp_name=myvoice
set i_part=0
set all_parts=1
set opt_dir=custom_data\dataset
set bert_pretrained_dir=GPT_SoVITS\pretrained_models\chinese-roberta-wwm-ext-large
set version=v2Pro

python -s GPT_SoVITS/prepare_datasets/1-get-text.py        # 文本+BERT
set cnhubert_base_dir=GPT_SoVITS\pretrained_models\chinese-hubert-base
python -s GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py
set sv_path=GPT_SoVITS\pretrained_models\sv\pretrained_eres2netv2w24s4ep4.ckpt
python -s GPT_SoVITS/prepare_datasets/2-get-sv.py
set pretrained_s2G=GPT_SoVITS\pretrained_models\v2Pro\s2Gv2Pro.pth
set s2config_path=GPT_SoVITS\configs\s2v2Pro.json
python -s GPT_SoVITS/prepare_datasets/3-get-semantic.py
```

> 必须先打 `patches/guangpu_pinyin.patch` 再做 1-get-text，粤字读音才会进音素标注。

## 5. 训练

```bash
python scripts/build_train_configs.py --root GPT-SoVITS --dataset custom_data/dataset --exp myvoice
mkdir custom_data\dataset\logs_s2_v2Pro   # s2 保存目录需先建

python -s GPT_SoVITS/s1_train.py --config_file GPT-SoVITS/TEMP/tmp_s1.yaml
python -s GPT_SoVITS/s2_train.py --config GPT-SoVITS/TEMP/tmp_s2.json
```

产出：

- `GPT_weights_v2Pro/myvoice-e*.ckpt`（s1）
- `SoVITS_weights_v2Pro/myvoice_e*.pth`（s2）

## 6. 合成验收

```bash
GPT_MODEL=GPT-SoVITS/GPT_weights_v2Pro/myvoice-e14.ckpt ^
SOVITS_MODEL=GPT-SoVITS/SoVITS_weights_v2Pro/myvoice_e12_s396.pth ^
python tools/guangpu_local_tts.py 台词.txt out/
```

## 常见坑

- **torch 2.13 Windows 崩溃**（gloo all_reduce 访问违例）：降到 torch 2.6
  `pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126`
- **torchcodec DLL 加载失败**：卸载 torchcodec + 用 sitecustomize.py（soundfile 后端）
- **补丁后粤字仍读普通话**：补丁必须**在训练前**生效（重新 1-get-text）
- **s2 训练保存路径不存在报错**：先 `mkdir logs_s2_v2Pro`
- **合成卡顿/噪点**：`SAMPLE_STEPS=64`、换干净参考音频；根治靠更多录音
