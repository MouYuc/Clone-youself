# -*- coding: utf-8 -*-
"""Windows 依赖修复：让 torchaudio.load 使用 soundfile 后端。

新版 torchaudio 默认走 torchcodec，在 Windows 上常因 FFmpeg DLL
版本不匹配而崩溃。把这个文件放进 GPT_SoVITS 目录（PYTHONPATH 里）
即可自动生效。"""

import torch
import torchaudio
import soundfile


def _soundfile_load(path, *args, **kwargs):
    data, sr = soundfile.read(path, dtype="float32", always_2d=True)
    return torch.from_numpy(data.T), sr


torchaudio.load = _soundfile_load
