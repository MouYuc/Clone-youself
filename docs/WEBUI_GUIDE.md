# WebUI 使用说明

本地图形界面，打开浏览器即可完成：写台词 → 合成 → 试听 → 下载。
页面：**合成 / 批量合成 / 环境检测 / 训练引导 / 历史记录 / 设置**。

## 启动

```powershell
# Windows
$env:GPT_SOVITS_ROOT = 'D:\AIVoice\GPT-SoVITS'   # 换成你的 GPT-SoVITS 路径
python tools\guangpu_webui.py
```

```bash
# Linux / macOS
export GPT_SOVITS_ROOT=/path/to/GPT-SoVITS
python tools/guangpu_webui.py
```

浏览器打开 <http://127.0.0.1:7860>。

> 如果 `GPT_SOVITS_ROOT` 不设置，默认按"本仓库与 GPT-SoVITS 平级"查找。
> 也可以在 WebUI 的「设置」页填写路径并保存，写入 `.guangpu_webui/config.json`（不会入库）。

## 页面说明

- **合成**：多行台词（一行一句）+ 自动转轻中广普开关 + 六个参数滑块（默认 H4 定稿配方）+ 模型/参考音频（可改）+ 逐句输出（试听 + 下载）。
- **批量合成**：上传 `.txt` 台词文件，整批合成，完成后打包 zip 下载。
- **环境检测**：检查 Python / PyTorch+CUDA / 依赖包 / ffmpeg / GPT-SoVITS 根目录 / 广普补丁 / 模型 / 参考音频，缺什么直接给修复命令。
- **训练引导**：五步流程（录音 → 切片+识别 → 人工校对 → 特征提取 → 训练）+ 训练数据统计。
- **历史记录**：最近 200 条合成记录，可回听、下载、清空。
- **设置**：GPT-SoVITS 根目录与模型/参考音频路径，保存为本机默认。

## 配置优先级

内置默认值 < 环境变量 < `.guangpu_webui/config.json` < 界面手动修改（当次会话）。

常用环境变量：

| 变量 | 作用 |
|---|---|
| `GPT_SOVITS_ROOT` | GPT-SoVITS 根目录 |
| `GPT_MODEL` / `SOVITS_MODEL` | 模型路径 |
| `REF_AUDIO` / `REF_TEXT` | 参考音频与文本 |
| `TOP_K` / `TOP_P` / `TEMPERATURE` / `SAMPLE_STEPS` / `SPEED` / `PAUSE_SECOND` | 合成参数 |
| `AUTO_LIGHTMID` | `0` 关闭自动转广普 |
| `GRADIO_SERVER_NAME` / `GRADIO_SERVER_PORT` | 监听地址 / 端口（默认 127.0.0.1:7860） |

## 常见问题

**启动很慢？**
启动时会预加载模型，需要 10~30 秒，属于正常现象；启动后合成立即开始，无需再等模型加载。

**试听按钮没有声音 / 文件下载不了？**
输出目录建议保持在仓库 `output/` 内（默认如此）。自定义目录请放在仓库内，否则浏览器无法访问。

**ffmpeg 缺失？**
合成会降级输出 wav；环境检测页会给出安装命令（Windows：`winget install Gyan.FFmpeg`）。

**粤字还是按普通话念？**
说明广普补丁未应用：在 GPT-SoVITS 里执行 `git apply patches/guangpu_pinyin.patch`，并重新跑训练的特征提取；已训练模型不受影响。

**端口被占用？**
设置 `GRADIO_SERVER_PORT=7861` 后重启。

## 安全说明

- WebUI 默认只监听本机回环地址（127.0.0.1），不对外网开放。
- 本仓库与 WebUI 不含任何人的声音克隆模型、录音或声纹特征；请使用自己的声音训练。
