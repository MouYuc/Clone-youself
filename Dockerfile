# GuangPu-TTS 环境镜像（不含任何声音模型）
# 基于 GPT-SoVITS 官方 torch-base，构建时克隆引擎并打广普补丁
FROM xxxxrt666/torch-base:cu12.6-full

LABEL maintainer="MouYuc"
LABEL description="GuangPu-TTS: GPT-SoVITS + Cantonese-accented Mandarin patch"

SHELL ["/bin/bash", "-c"]
WORKDIR /workspace/GPT-SoVITS

# 1. 克隆 GPT-SoVITS 引擎
# 锁定到补丁对应的 commit（d523079），避免上游更新导致 git apply 失败
RUN git clone https://github.com/RVC-Boss/GPT-SoVITS.git /tmp/gs \
    && cd /tmp/gs \
    && git checkout d523079fc05d9a8028d6085bffe4a2757c32abb6 \
    && cd /workspace/GPT-SoVITS \
    && cp -a /tmp/gs/. . \
    && rm -rf /tmp/gs

# 2. 应用广普发音词典补丁
COPY patches/guangpu_pinyin.patch /tmp/guangpu_pinyin.patch
RUN git apply /tmp/guangpu_pinyin.patch \
    && rm /tmp/guangpu_pinyin.patch

# 3. 构建工具 + ffmpeg（opencc/pyopenjtalk 等需要编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
        cmake build-essential ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 4. 依赖（requirements.txt 由克隆的仓库提供）
RUN pip install -r extra-req.txt --no-deps \
    && pip install -r requirements.txt \
    && pip install faster-whisper noisereduce

# 5. 拷贝本仓库工具与脚本
COPY tools/guangpu_local_tts.py /workspace/tools/guangpu_local_tts.py
COPY scripts/run_whisper.py scripts/fix_transcript.py scripts/build_train_configs.py /workspace/scripts/

ENV PYTHONPATH="/workspace/GPT-SoVITS"
ENV GPT_SOVITS_ROOT="/workspace/GPT-SoVITS"

EXPOSE 9874

CMD ["/bin/bash"]
