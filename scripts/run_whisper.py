# -*- coding: utf-8 -*-
"""用 faster-whisper 对切片做中文识别，生成 GPT-SoVITS 训练标注。

用法：
    python run_whisper.py --input 切片目录 --output 输出目录 [--model large-v3]
输出：<output>/<input目录名>_whisper.list（格式：wav路径|说话人|ZH|文本）
"""

import argparse
import os

from faster_whisper import WhisperModel
from tqdm import tqdm


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="切片 wav 目录（32k 单声道）")
    p.add_argument("--output", required=True, help="标注输出目录")
    p.add_argument("--model", default="large-v3", help="whisper 模型名")
    p.add_argument("--language", default="zh")
    args = p.parse_args()

    os.makedirs(args.output, exist_ok=True)
    model = WhisperModel(args.model, device="cuda", compute_type="float16")
    files = sorted(os.listdir(args.input))
    rows = []
    for name in tqdm(files):
        path = os.path.join(args.input, name)
        try:
            segments, info = model.transcribe(
                path,
                beam_size=5,
                vad_filter=True,
                language=args.language,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            text = "".join(s.text for s in segments).strip()
            rows.append(f"{path}|sliced|ZH|{text}")
        except Exception as exc:
            print(f"{name}: FAIL {exc}")

    out_name = os.path.basename(args.input.rstrip("/\\"))
    out_path = os.path.join(args.output, f"{out_name}_whisper.list")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    print(f"完成 {len(rows)} 段 -> {out_path}")


if __name__ == "__main__":
    main()
