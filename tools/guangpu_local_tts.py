# -*- coding: utf-8 -*-
"""
广普本地配音工具（基于 GPT-SoVITS v2Pro）

用法：
    python guangpu_local_tts.py 台词.txt [输出目录]

台词文件：UTF-8，一行一句（建议一句 5~20 字）。
输出：每句一个 mp3，命名 001_台词前几字.mp3。

路径配置：全部通过环境变量覆盖（默认按"仓库旁放 GPT-SoVITS"布局）：
    GPT_SOVITS_ROOT    GPT-SoVITS 仓库根目录（默认 ../GPT-SoVITS）
    GPT_MODEL          GPT 模型路径
    SOVITS_MODEL       SoVITS 模型路径
    REF_AUDIO          参考音频路径
    REF_TEXT           参考音频对应文本
"""

import os
import subprocess
import sys

GPT_SOVITS_ROOT = os.path.abspath(os.environ.get("GPT_SOVITS_ROOT", r"..\GPT-SoVITS"))
sys.path.insert(0, GPT_SOVITS_ROOT)
sys.path.insert(0, os.path.join(GPT_SOVITS_ROOT, "GPT_SoVITS"))
os.chdir(GPT_SOVITS_ROOT)

import soundfile as sf

from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav
from guangpu_rules import to_lightmid, safe_name

# ================= 配置区（可用环境变量覆盖） =================
GPT_MODEL = os.environ.get("GPT_MODEL", os.path.join(GPT_SOVITS_ROOT, "GPT_weights_v2Pro", "guangpu07-e14.ckpt"))
SOVITS_MODEL = os.environ.get(
    "SOVITS_MODEL", os.path.join(GPT_SOVITS_ROOT, "SoVITS_weights_v2Pro", "guangpu07_e12_s396.pth")
)
REF_AUDIO = os.environ.get("REF_AUDIO", os.path.join(GPT_SOVITS_ROOT, "custom_data", "sliced", "训练.wav_0000191040_0000343680.wav"))
REF_TEXT = os.environ.get("REF_TEXT", "这条路走到头，左转就到了。")

TOP_K = int(os.environ.get("TOP_K", "30"))
TOP_P = float(os.environ.get("TOP_P", "0.88"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.95"))
SAMPLE_STEPS = int(os.environ.get("SAMPLE_STEPS", "64"))
SPEED = float(os.environ.get("SPEED", "1.0"))
PAUSE_SECOND = float(os.environ.get("PAUSE_SECOND", "0.15"))

# 轻中浓度自动转换（设为 0 关闭）
AUTO_LIGHTMID = os.environ.get("AUTO_LIGHTMID", "1") == "1"
# =============================================================


def synth_line(text):
    res = get_tts_wav(
        ref_wav_path=REF_AUDIO,
        prompt_text=REF_TEXT,
        prompt_language="中文",
        text=text,
        text_language="中文",
        how_to_cut="不切",
        top_k=TOP_K,
        top_p=TOP_P,
        temperature=TEMPERATURE,
        speed=SPEED,
        pause_second=PAUSE_SECOND,
        sample_steps=SAMPLE_STEPS,
    )
    last = list(res)[-1]
    return last[1], last[0]


def main():
    if len(sys.argv) < 2:
        print("用法: python guangpu_local_tts.py 台词.txt [输出目录]")
        return
    src = sys.argv[1]
    if not os.path.exists(src):
        print("找不到文件:", src)
        return
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(src))
    os.makedirs(outdir, exist_ok=True)

    with open(src, encoding="utf-8-sig") as f:
        lines = [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        print("台词文件为空")
        return

    change_gpt_weights(gpt_path=GPT_MODEL)
    change_sovits_weights(sovits_path=SOVITS_MODEL)

    print(f"共 {len(lines)} 句，开始合成（每句约 10~30 秒）...")
    ok = 0
    for i, line in enumerate(lines, 1):
        text = to_lightmid(line) if AUTO_LIGHTMID else line
        out_wav = os.path.join(outdir, f"{i:03d}_{safe_name(line)}.wav")
        out_mp3 = out_wav[:-4] + ".mp3"
        try:
            audio, sr = synth_line(text)
            sf.write(out_wav, audio, sr)
            subprocess.run(
                ["ffmpeg", "-y", "-i", out_wav, "-b:a", "192k", out_mp3],
                capture_output=True,
                check=True,
            )
            os.remove(out_wav)
            ok += 1
            print(f"  OK {os.path.basename(out_mp3)}  [{text[:20]}]")
        except Exception as exc:
            print(f"  FAIL 第 {i} 句: {exc}")
    print(f"完成：{ok}/{len(lines)} 句成功 -> {outdir}")


if __name__ == "__main__":
    main()
