# -*- coding: utf-8 -*-
"""把 whisper 识别结果人工修正为最终训练标注。

whisper 对广普/粤语词识别常有错字，训练前务必校对。
把 corrections 里的文本替换成"你录音实际说的话"即可。

用法：
    python fix_transcript.py --input xxx_whisper.list --output corrected.list
"""

import argparse
import os


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="whisper 输出的 .list")
    p.add_argument("--output", required=True, help="修正后的 .list")
    args = p.parse_args()

    # 示例修正表：{行号: 修正后文本}，按你自己的台词本内容填写
    corrections = {
        1: "今天天气真不错，我们出去走走吧。",
        2: "这条路走到头，左转就到了。",
        3: "老板，这个多少钱啊？你吃饭了吗？",
    }

    with open(args.input, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    out = []
    for i, line in enumerate(lines, 1):
        parts = line.split("|")
        text = corrections.get(i, parts[-1])
        out.append(f"{parts[0]}|sliced|ZH|{text}")
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"修正完成 {len(out)} 段 -> {args.output}")


if __name__ == "__main__":
    main()
