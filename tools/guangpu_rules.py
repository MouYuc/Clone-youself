# -*- coding: utf-8 -*-
"""广普"轻中浓度"转换规则（CLI 与 WebUI 共用）。

维护说明：改这里即可同时影响 tools/guangpu_local_tts.py 与 tools/guangpu_webui.py。
规则顺序很重要：长词在前，避免"是"先吃掉"不是/是不是"。
"""

import re

# 轻中浓度：普通话台词 -> 广普混合写法
WORD_RULES = [
    ("是不是", "系唔系"),
    ("不是", "唔系"),
    ("什么人", "咩人"),
    ("最重要", "最紧要"),
    ("什么", "乜嘢"),
    ("没有", "冇"),
    ("没", "冇"),
    ("你说", "你话"),
    ("我说", "我话"),
    ("的", "嘅"),
    ("是", "系"),
]


def to_lightmid(text: str) -> str:
    """把普通话台词转成轻中浓度广普写法；设为 0 关闭时由调用方直接透传。"""
    for src, dst in WORD_RULES:
        text = text.replace(src, dst)
    return text


def safe_name(text: str) -> str:
    """生成安全文件名前缀（去非法字符，最长 12 字符）。"""
    name = re.sub(r'[\\/:*?"<>|\s]+', "", text)[:12]
    return name or "line"
