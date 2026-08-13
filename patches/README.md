# 广普发音词典补丁

`guangpu_pinyin.patch` 修改 GPT-SoVITS 的两个中文文本前端文件：

- `GPT_SoVITS/text/chinese.py`
- `GPT_SoVITS/text/chinese2.py`

> ⚠️ 补丁基于 **GPT-SoVITS commit `d523079`（2026-07-22）** 生成。
> Dockerfile 和 setup 脚本已自动锁定该版本；若你手动使用新版 GPT-SoVITS，
> 补丁可能无法直接应用（文件已变），需要基于新版重新生成。

改动内容：

1. 新增 **15 个粤字的广普读音覆盖**（系→hei、嘅→ge、唔→wu、㗎→ga 等），
   让模型训练/推理时不再按普通话字典音读粤字（否则会像"北方人学粤语"）
2. 字符过滤正则扩展 CJK 扩展 A 区（`\u3400-\u4dbf`），否则 `㗎` 等字会在
   文本正规化时被丢弃

## 应用补丁

```bash
cd GPT-SoVITS
git apply ../guangpu-tts/patches/guangpu_pinyin.patch
```

如果 `git apply` 报错（文件已被修改），可以手动按补丁内容编辑两个文件，
或直接复制 `GP_PINYIN` / `GP_PINYIN_FULL` 字典到对应位置。

> 注意：补丁只影响文本前端。改完补丁后，**需要重新执行 1-get-text.py
> 并重训模型**，读音才会生效（详见 README 训练流程）。

## 词典内容（v1.0）

| 字 | 读法 | 说明 |
|---|---|---|
| 系 | hei1 | 是（广东人读音） |
| 嘅 | ge3 | 的 |
| 乜 | me1 | 什么 |
| 嘢 | ye5 | 东西 |
| 冇 | mou5 | 没有 |
| 咁 | gan3 | 这么/那样 |
| 哋 | dei5 | 们 |
| 喺 | hai2 | 在 |
| 咗 | zuo3 | 了 |
| 佢 | qu2 | 他/她 |
| 睇 | di1 | 看 |
| 咩 | mie1 | 什么 |
| 啲 | di1 | 些 |
| 嚟 | lei4 | 来 |
| 㗎 | ga3 | 语气词 |

`唔` 的粤语鼻音（m4）在 GPT-SoVITS 音素表里不存在，目前用近似的 `wu2`。
