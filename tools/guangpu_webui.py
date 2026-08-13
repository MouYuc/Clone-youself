# -*- coding: utf-8 -*-
"""广普配音 WebUI（基于 GPT-SoVITS v2Pro）

启动：
    set GPT_SOVITS_ROOT=D:\\AIVoice\\GPT-SoVITS   （如未设置默认 ../GPT-SoVITS）
    python tools/guangpu_webui.py

页面：合成 / 批量合成 / 环境检测 / 训练引导 / 历史记录 / 设置。
配置持久化：<仓库>/.guangpu_webui/config.json（不入库）。
历史记录：<仓库>/.guangpu_webui/history.json（不入库）。
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

import gradio as gr
import soundfile as sf

from guangpu_rules import safe_name, to_lightmid

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / ".guangpu_webui"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
OUTPUT_DIR = REPO_ROOT / "output"


# ================= 配置 =================
def _default_cfg():
    root = os.environ.get("GPT_SOVITS_ROOT") or str(REPO_ROOT.parent / "GPT-SoVITS")

    def p(*parts):
        return os.path.join(root, *parts)

    return {
        "gpt_sovits_root": root,
        "gpt_model": os.environ.get("GPT_MODEL", p("GPT_weights_v2Pro", "guangpu07-e14.ckpt")),
        "sovits_model": os.environ.get("SOVITS_MODEL", p("SoVITS_weights_v2Pro", "guangpu07_e12_s396.pth")),
        "ref_audio": os.environ.get("REF_AUDIO", p("custom_data", "sliced", "训练.wav_0000191040_0000343680.wav")),
        "ref_text": os.environ.get("REF_TEXT", "这条路走到头，左转就到了。"),
        "top_k": int(os.environ.get("TOP_K", "30")),
        "top_p": float(os.environ.get("TOP_P", "0.88")),
        "temperature": float(os.environ.get("TEMPERATURE", "0.95")),
        "sample_steps": int(os.environ.get("SAMPLE_STEPS", "64")),
        "speed": float(os.environ.get("SPEED", "1.0")),
        "pause_second": float(os.environ.get("PAUSE_SECOND", "0.15")),
        "auto_lightmid": os.environ.get("AUTO_LIGHTMID", "1") == "1",
    }


def load_config():
    cfg = _default_cfg()
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    return cfg


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ================= 历史记录 =================
def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def append_history(entries):
    hist = load_history()
    hist = entries + hist
    hist = hist[:200]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_history():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text("[]", encoding="utf-8")


# ================= 环境检测 =================
def env_check(cfg):
    rows = []

    def add(name, status, detail, fix=""):
        rows.append({"name": name, "status": status, "detail": detail, "fix": fix})

    try:
        v = sys.version_info
        add(
            "Python 版本",
            "ok" if (v.major, v.minor) >= (3, 10) else "bad",
            f"{v.major}.{v.minor}.{v.micro}",
            "请安装 Python 3.10+",
        )
    except Exception as e:
        add("Python 版本", "bad", str(e), "请安装 Python 3.10+")

    try:
        import torch

        ver = torch.__version__.split("+")[0]
        major, minor = (int(x) for x in ver.split(".")[:2])
        cuda = torch.cuda.is_available()
        detail = torch.__version__ + (" · CUDA 可用" if cuda else " · CUDA 不可用")
        add(
            "PyTorch + CUDA",
            "ok" if (major, minor) >= (2, 6) and cuda else "bad",
            detail,
            "请按 GPT-SoVITS 环境说明安装 torch==2.6.0+cu126（2.13 在 Windows 会崩溃）",
        )
    except Exception as e:
        add("PyTorch + CUDA", "bad", str(e), "pip install torch==2.6.0+cu126 torchaudio -i https://download.pytorch.org/whl/cu126")

    missing = [m for m in ("gradio", "soundfile", "numpy") if importlib.util.find_spec(m) is None]
    add(
        "依赖包 gradio / soundfile / numpy",
        "ok" if not missing else "bad",
        "已安装" if not missing else "缺少：" + ", ".join(missing),
        "pip install gradio soundfile numpy" if missing else "",
    )

    ff = shutil.which("ffmpeg")
    add(
        "ffmpeg",
        "ok" if ff else "bad",
        os.path.basename(ff) if ff else "未找到（可先用 wav 输出）",
        "winget install Gyan.FFmpeg" if not ff else "",
    )

    root = cfg.get("gpt_sovits_root", "")
    root_ok = os.path.isdir(root) and os.path.isdir(os.path.join(root, "GPT_SoVITS"))
    add(
        "GPT-SoVITS 根目录",
        "ok" if root_ok else "bad",
        root or "未配置",
        "运行 setup 脚本，或在「设置」页配置 GPT_SOVITS_ROOT" if not root_ok else "",
    )

    if root_ok:
        patched = all(
            _file_contains(os.path.join(root, "GPT_SoVITS", "text", f), "GP_PINYIN")
            for f in ("chinese.py", "chinese2.py")
        )
        add(
            "广普发音补丁",
            "ok" if patched else "bad",
            "已应用" if patched else "未应用",
            "git apply patches/guangpu_pinyin.patch" if not patched else "",
        )
    else:
        add("广普发音补丁", "warn", "跳过（根目录不可用）", "")

    gpt_ok = os.path.isfile(cfg.get("gpt_model", ""))
    sovits_ok = os.path.isfile(cfg.get("sovits_model", ""))
    add(
        "GPT / SoVITS 模型",
        "ok" if gpt_ok and sovits_ok else "bad",
        "已找到" if gpt_ok and sovits_ok else "缺少模型文件",
        "训练完成后在「设置」页配置模型路径" if not (gpt_ok and sovits_ok) else "",
    )

    ref_ok = os.path.isfile(cfg.get("ref_audio", ""))
    add(
        "参考音频",
        "ok" if ref_ok else "warn",
        "已找到" if ref_ok else "未找到，可在合成页手动指定",
        "",
    )
    return rows


def _file_contains(path, needle):
    try:
        return needle in Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def env_check_html(cfg):
    rows = env_check(cfg)
    colors = {"ok": "#4f7a58", "bad": "#c2564c", "warn": "#b26a3b"}
    dots = "".join(
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;'
        'padding:8px 0;border-bottom:1px solid #ece3d2;">'
        f'<span style="color:#3d352c;">{r["name"]}</span>'
        f'<span style="color:{colors[r["status"]]};font-size:12.5px;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        f'background:{colors[r["status"]]};margin-right:6px;"></span>{r["detail"]}</span></div>'
        for r in rows
    )
    fixes = [r["fix"] for r in rows if r["fix"] and r["status"] != "ok"]
    if fixes:
        code = "".join(f'<div style="padding:3px 0;">{f}</div>' for f in fixes)
        fix_html = (
            '<div style="background:#efe8da;border:1px solid #e2d7c2;border-radius:10px;'
            f'padding:10px 12px;margin-top:14px;font-family:Consolas,monospace;font-size:12px;color:#244a36;">{code}</div>'
        )
    else:
        fix_html = '<div style="color:#4f7a58;margin-top:14px;font-family:KaiTi;font-size:13px;">全部通过，可以开始合成。</div>'
    return dots + fix_html


# ================= 合成后端（懒加载） =================
_BACKEND = {"get_tts_wav": None, "change_gpt": None, "change_sovits": None, "root": None, "loaded": (None, None)}


def ensure_backend(cfg):
    root = os.path.abspath(cfg["gpt_sovits_root"])
    if _BACKEND["get_tts_wav"] is None or _BACKEND["root"] != root:
        sys.path.insert(0, root)
        sys.path.insert(0, os.path.join(root, "GPT_SoVITS"))
        try:
            os.chdir(root)
        except OSError:
            pass
        try:
            import sitecustomize  # noqa: F401  Windows torchaudio 修复
        except Exception:
            pass
        from GPT_SoVITS.inference_webui import (  # noqa: PLC0415
            change_gpt_weights,
            change_sovits_weights,
            get_tts_wav,
        )

        _BACKEND.update(
            get_tts_wav=get_tts_wav,
            change_gpt=change_gpt_weights,
            change_sovits=change_sovits_weights,
            root=root,
            loaded=(None, None),
        )
    gpt, sovits = cfg["gpt_model"], cfg["sovits_model"]
    if _BACKEND["loaded"] != (gpt, sovits):
        _BACKEND["change_gpt"](gpt_path=gpt)
        _BACKEND["change_sovits"](sovits_path=sovits)
        _BACKEND["loaded"] = (gpt, sovits)


def synth_one(cfg, text):
    get_tts_wav = _BACKEND["get_tts_wav"]
    res = get_tts_wav(
        ref_wav_path=cfg["ref_audio"],
        prompt_text=cfg["ref_text"],
        prompt_language="中文",
        text=text,
        text_language="中文",
        how_to_cut="不切",
        top_k=int(cfg["top_k"]),
        top_p=float(cfg["top_p"]),
        temperature=float(cfg["temperature"]),
        speed=float(cfg["speed"]),
        pause_second=float(cfg["pause_second"]),
        sample_steps=int(cfg["sample_steps"]),
    )
    last = list(res)[-1]
    return last[1], last[0]  # audio, sr


def save_audio(audio, sr, out_dir, base):
    os.makedirs(out_dir, exist_ok=True)
    wav = os.path.join(out_dir, base + ".wav")
    sf.write(wav, audio, sr)
    ff = shutil.which("ffmpeg")
    if ff:
        mp3 = os.path.join(out_dir, base + ".mp3")
        try:
            subprocess.run([ff, "-y", "-i", wav, "-b:a", "192k", mp3], capture_output=True, check=True)
            os.remove(wav)
            return mp3
        except Exception:
            return wav
    return wav


def parse_lines(text):
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip() and not ln.strip().startswith("#")]


def file_url(path):
    # 服务进程可能因预加载被 os.chdir 到 GPT-SoVITS 根目录，
    # Gradio 的 /file= 按相对路径+当前目录解析，因此这里一律输出绝对路径。
    return "/file=" + urllib.parse.quote(os.path.abspath(path))


# ================= 训练数据统计 =================
def training_stats(cfg):
    data = Path(cfg.get("gpt_sovits_root", "")) / "custom_data"
    stats = {"sliced": None, "lines": None, "duration": None}
    try:
        stats["sliced"] = len(list((data / "sliced").glob("*.wav")))
    except OSError:
        pass
    try:
        lst = data / "sliced_corrected.list"
        stats["lines"] = len([ln for ln in lst.read_text(encoding="utf-8").splitlines() if ln.strip()])
    except OSError:
        pass
    try:
        stats["duration"] = sf.info(str(data / "训练.wav")).duration
    except (OSError, RuntimeError):
        pass
    return stats


def guide_html(cfg):
    stats = training_stats(cfg)
    fmt_dur = f"{stats['duration']:.1f} 分钟" if stats["duration"] else "—"
    stat_cards = "".join(
        f'<div style="background:#fffdf7;border:1px solid #e2d7c2;border-radius:10px;padding:10px 12px;">'
        f'<div style="color:#8a7a63;font-family:KaiTi;font-size:12px;">{label}</div>'
        f'<div style="color:#2f5d43;font-size:18px;font-weight:700;margin-top:2px;">{value}</div></div>'
        for label, value in (
            ("切片数", stats["sliced"] if stats["sliced"] is not None else "—"),
            ("标注行数", stats["lines"] if stats["lines"] is not None else "—"),
            ("录音总时长", fmt_dur),
        )
    )
    steps = [
        ("壹", "录音", "用台词本录 10~15 分钟，自然随意、带情绪起伏"),
        ("贰", "切片 + 识别", "Whisper 自动标注，逐句切片"),
        ("叁", "人工校对", "广普错字多，必须逐句过一遍"),
        ("肆", "特征提取", "BERT / HuBERT / 声纹 / 语义"),
        ("伍", "训练", "s1 约 15 epoch + s2 约 12 epoch"),
    ]
    cards = "".join(
        f'<div style="background:#fffdf7;border:1px solid #e2d7c2;border-radius:11px;padding:12px;">'
        f'<div style="color:#2f5d43;font-family:KaiTi;font-size:17px;font-weight:700;">{no}</div>'
        f'<div style="font-weight:700;margin:6px 0 4px;font-family:serif;">{title}</div>'
        f'<div style="color:#8a7a63;font-size:12px;line-height:1.6;">{desc}</div></div>'
        for no, title, desc in steps
    )
    return (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;">{stat_cards}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:14px;">{cards}</div>'
        '<div style="margin-top:14px;background:#fffdf7;border:1px solid #e2d7c2;border-radius:11px;padding:12px;">'
        '训练相关脚本仍走命令行，WebUI 只做流程引导。完整教程见 '
        '<a href="https://github.com/MouYuc/Clone-youself/blob/main/docs/TRAINING_GUIDE.md" '
        'style="color:#2f5d43;">docs/TRAINING_GUIDE.md</a>。</div>'
    )


def history_html():
    hist = load_history()
    if not hist:
        return '<div style="color:#8a7a63;font-family:KaiTi;font-size:13px;padding:8px 0;">还没有合成记录。</div>'
    rows = []
    for h in hist:
        path = h.get("file") or ""
        if path and os.path.isfile(path):
            url = file_url(path)
            play = f'<audio controls preload="none" style="height:28px;width:160px;" src="{url}"></audio>'
            dl = f'<a href="{url}" download style="color:#2f5d43;text-decoration:none;">下载</a>'
        else:
            play, dl = '<span style="color:#ab9d86;">—</span>', "—"
        rows.append(
            f"<tr><td style='white-space:nowrap;'>{h.get('time', '')}</td>"
            f"<td>{h.get('text', '')}</td>"
            f"<td style='white-space:nowrap;'>{h.get('params', '')}</td>"
            f"<td>{h.get('name', '')}</td><td>{play}</td><td>{dl}</td></tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
        "<thead><tr style='color:#8a7a63;font-family:KaiTi;font-size:12.5px;text-align:left;'>"
        "<th style='padding:8px 6px;border-bottom:1px solid #e2d7c2;'>时间</th>"
        "<th style='padding:8px 6px;border-bottom:1px solid #e2d7c2;'>台词</th>"
        "<th style='padding:8px 6px;border-bottom:1px solid #e2d7c2;'>参数</th>"
        "<th style='padding:8px 6px;border-bottom:1px solid #e2d7c2;'>文件</th>"
        "<th style='padding:8px 6px;border-bottom:1px solid #e2d7c2;'>试听</th>"
        "<th style='padding:8px 6px;border-bottom:1px solid #e2d7c2;'></th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


# ================= 页面切换 =================
NAV_ORDER = ["synth", "batch", "env", "guide", "history", "settings"]
PAGE_TITLES = {
    "synth": ("合成", "写台词，一键生成带广味的配音"),
    "batch": ("批量合成", "上传台词文件，整批产出并打包"),
    "env": ("环境检测", "缺什么依赖，一眼看清并给出修复命令"),
    "guide": ("训练引导", "从录音到专属音色的五步流程"),
    "history": ("历史记录", "最近的合成记录，可回听与下载"),
    "settings": ("设置", "模型与路径配置，保存为本机默认"),
}


# ================= 样式（V1 纸感墨绿 + T4 字体） =================
CSS = """
:root {
  --gp-bg:#f6f1e7; --gp-side:#efe8da; --gp-panel:#fffdf7; --gp-border:#e2d7c2; --gp-bsoft:#ece3d2;
  --gp-ink:#3d352c; --gp-ink2:#8a7a63; --gp-ink3:#ab9d86;
  --gp-grn:#2f5d43; --gp-grn2:#244a36; --gp-grnsoft:#eef3ea; --gp-grnline:#c8d8c5;
  --gp-serif:"Noto Serif SC","Source Han Serif SC","Songti SC","SimSun",serif;
  --gp-kai:"KaiTi","STKaiti","Kaiti SC",serif;
}
.gp-root { background:var(--gp-bg); color:var(--gp-ink); min-height:100vh; }
.gradio-container { max-width:none !important; width:100% !important; }
.gp-side { background:var(--gp-side); border-right:1px solid var(--gp-border); padding:18px 12px; }
.gp-side button { width:100%; justify-content:flex-start; margin-bottom:4px; border-radius:9px;
  background:transparent; border:1px solid transparent; color:var(--gp-ink2); }
.gp-side button:hover { background:rgba(47,93,67,.08); color:var(--gp-ink); }
.gp-side button.primary { background:var(--gp-grnsoft); border-color:var(--gp-grnline); color:var(--gp-grn); font-weight:600; }
.gp-main { background:var(--gp-bg); padding:22px 24px 30px; }
.gp-head h1 { font-family:var(--gp-serif); color:var(--gp-grn); font-size:22px; margin:0 0 4px; }
.gp-head p { color:var(--gp-ink2); font-size:13px; margin:0; font-family:var(--gp-kai); }
.gp-card { background:var(--gp-panel); border:1px solid var(--gp-border); border-radius:12px; padding:16px; }
.gp-lbl { font-family:var(--gp-kai); color:var(--gp-ink2); font-size:13px; margin-bottom:4px; }
.gp-ta textarea { background:var(--gp-panel); border:1px solid var(--gp-border); border-radius:10px;
  font-family:var(--gp-serif); font-size:14px; line-height:1.8; color:var(--gp-ink); }
.gp-ta textarea:focus { border-color:var(--gp-grn); box-shadow:0 0 0 1px var(--gp-grn); }
.gp-param input[type=range] { accent-color:var(--gp-grn); }
.gp-param label { font-family:var(--gp-kai); color:var(--gp-ink2); font-size:13px; }
.gp-val { font-family:ui-monospace,Consolas,monospace; color:var(--gp-grn); font-size:13px; text-align:right; min-width:44px; }
.gp-check input[type=checkbox] { accent-color:var(--gp-grn); }
.gp-check label { color:var(--gp-ink); font-size:13px; }
.gp-collapse { border:1px solid var(--gp-border); border-radius:10px; overflow:hidden; }
.gp-collapse summary { font-family:var(--gp-kai); color:var(--gp-ink2); padding:9px 12px; background:var(--gp-side); }
.gp-primary button { background:var(--gp-grn) !important; border-color:var(--gp-grn) !important; color:var(--gp-panel) !important; border-radius:9px; }
.gp-primary button:hover { background:var(--gp-grn2) !important; }
.gp-ghost button { background:var(--gp-panel); border:1px solid var(--gp-border); color:var(--gp-ink2); border-radius:9px; }
.gp-ghost button:hover { color:var(--gp-grn); border-color:var(--gp-grnline); }
.gp-outrow { background:var(--gp-panel); border:1px solid var(--gp-bsoft); border-radius:10px; padding:6px 10px; }
.gp-note { color:var(--gp-ink3); font-size:12.5px; font-family:var(--gp-kai); }
.gp-err { color:#c2564c; font-size:13px; font-family:var(--gp-kai); background:#fbf1ef; border:1px solid #ecd3cf; border-radius:8px; padding:8px 10px; }
.gp-drop { background:var(--gp-grnsoft); border:1.5px dashed var(--gp-grnline); border-radius:12px; }
.gp-audio audio { border-radius:8px; }
"""


# ================= 构建界面 =================
def fmt_num(v):
    if isinstance(v, float):
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return s if s else "0"
    return str(v)


try:
    theme = gr.themes.Soft(primary_hue=gr.themes.colors.green, neutral_hue=gr.themes.colors.stone)
except Exception:
    theme = gr.themes.Soft()

cfg0 = load_config()

with gr.Blocks(css=CSS, theme=theme, title="广普配音") as demo:
    cfg_state = gr.State(cfg0)

    with gr.Row(elem_classes="gp-root", equal_height=False):
        # ---------- 侧边栏 ----------
        with gr.Column(scale=0, min_width=214, elem_classes="gp-side"):
            gr.HTML(
                '<div style="display:flex;align-items:center;gap:10px;padding:2px 8px 16px;">'
                '<div style="width:32px;height:32px;border-radius:9px;background:#2f5d43;color:#fffdf7;'
                'font-family:serif;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;">广</div>'
                '<b style="font-family:serif;font-size:16px;color:#3d352c;">广普配音</b></div>'
            )
            b_synth = gr.Button("合成", variant="primary")
            b_batch = gr.Button("批量合成", variant="secondary")
            b_env = gr.Button("环境检测", variant="secondary")
            b_guide = gr.Button("训练引导", variant="secondary")
            b_history = gr.Button("历史记录", variant="secondary")
            b_settings = gr.Button("设置", variant="secondary")
            gr.HTML(
                '<div style="border-top:1px solid #e2d7c2;margin-top:10px;padding-top:12px;color:#8a7a63;'
                'font-family:KaiTi;font-size:12.5px;">'
                '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4f7a58;margin-right:6px;"></span>'
                '本机模式 · 环境检测见对应页</div>'
            )

        # ---------- 主区 ----------
        with gr.Column(scale=1, elem_classes="gp-main"):
            head = gr.Markdown(
                f"<h1>{PAGE_TITLES['synth'][0]}</h1><p>{PAGE_TITLES['synth'][1]}</p>",
                elem_classes="gp-head",
            )

            # ===== 合成页 =====
            with gr.Column(visible=True) as p_synth:
                with gr.Row():
                    with gr.Column(scale=3):
                        with gr.Column(elem_classes="gp-card"):
                            gr.Markdown("台词（一行一句）", elem_classes="gp-lbl")
                            ta = gr.Textbox(lines=6, placeholder="最重要的系，心态要放轻松。", elem_classes="gp-ta", show_label=False)
                            auto_cb = gr.Checkbox(value=bool(cfg0["auto_lightmid"]), label="自动转轻中广普（是→系 · 的→嘅 · 没有→冇）", elem_classes="gp-check")
                        with gr.Column(elem_classes="gp-card"):
                            gr.Markdown("参数（默认 H4 定稿配方）", elem_classes="gp-lbl")
                            with gr.Row():
                                sl_tk = gr.Slider(minimum=1, maximum=100, value=cfg0["top_k"], step=1, label="top_k", elem_classes="gp-param", scale=4)
                                with gr.Column(scale=1, min_width=52):
                                    val_tk = gr.Markdown(f"**{fmt_num(cfg0['top_k'])}**", elem_classes="gp-val")
                            with gr.Row():
                                sl_tp = gr.Slider(minimum=0.01, maximum=1, value=cfg0["top_p"], step=0.01, label="top_p", elem_classes="gp-param", scale=4)
                                with gr.Column(scale=1, min_width=52):
                                    val_tp = gr.Markdown(f"**{fmt_num(cfg0['top_p'])}**", elem_classes="gp-val")
                            with gr.Row():
                                sl_temp = gr.Slider(minimum=0.1, maximum=1.5, value=cfg0["temperature"], step=0.01, label="temperature", elem_classes="gp-param", scale=4)
                                with gr.Column(scale=1, min_width=52):
                                    val_temp = gr.Markdown(f"**{fmt_num(cfg0['temperature'])}**", elem_classes="gp-val")
                            with gr.Row():
                                sl_steps = gr.Slider(minimum=8, maximum=128, value=cfg0["sample_steps"], step=1, label="sample_steps", elem_classes="gp-param", scale=4)
                                with gr.Column(scale=1, min_width=52):
                                    val_steps = gr.Markdown(f"**{fmt_num(cfg0['sample_steps'])}**", elem_classes="gp-val")
                            with gr.Row():
                                sl_speed = gr.Slider(minimum=0.5, maximum=2.0, value=cfg0["speed"], step=0.05, label="speed", elem_classes="gp-param", scale=4)
                                with gr.Column(scale=1, min_width=52):
                                    val_speed = gr.Markdown(f"**{fmt_num(cfg0['speed'])}**", elem_classes="gp-val")
                            with gr.Row():
                                sl_pause = gr.Slider(minimum=0, maximum=1, value=cfg0["pause_second"], step=0.01, label="pause_second", elem_classes="gp-param", scale=4)
                                with gr.Column(scale=1, min_width=52):
                                    val_pause = gr.Markdown(f"**{fmt_num(cfg0['pause_second'])}**", elem_classes="gp-val")
                        with gr.Accordion("模型与参考音频", open=True, elem_classes="gp-collapse"):
                            tb_gpt = gr.Textbox(value=cfg0["gpt_model"], label="GPT 模型")
                            tb_sovits = gr.Textbox(value=cfg0["sovits_model"], label="SoVITS 模型")
                            tb_ref = gr.Textbox(value=cfg0["ref_audio"], label="参考音频")
                            tb_reftext = gr.Textbox(value=cfg0["ref_text"], label="参考文本")
                        with gr.Row():
                            btn_clear = gr.Button("清空", elem_classes="gp-ghost")
                            btn_savedef = gr.Button("存为默认", elem_classes="gp-ghost")
                            btn_synth = gr.Button("开始合成", elem_classes="gp-primary")
                        save_note = gr.Markdown("", elem_classes="gp-note")
                    with gr.Column(scale=2):
                        with gr.Column(elem_classes="gp-card"):
                            with gr.Row():
                                gr.Markdown("输出", elem_classes="gp-lbl")
                                out_summary = gr.Markdown("", elem_classes="gp-note")
                            out_rows = []
                            out_audios = []
                            for _ in range(12):
                                with gr.Row(visible=False, elem_classes="gp-outrow") as r:
                                    a = gr.Audio(type="filepath", show_download_button=True, elem_classes="gp-audio")
                                out_rows.append(r)
                                out_audios.append(a)

            # ===== 批量页 =====
            with gr.Column(visible=False) as p_batch:
                with gr.Row():
                    with gr.Column(scale=3):
                        with gr.Column(elem_classes="gp-card"):
                            gr.Markdown("台词文件（.txt · UTF-8 · 一行一句，支持 # 注释）", elem_classes="gp-lbl")
                            batch_file = gr.File(file_types=[".txt"], elem_classes="gp-drop")
                        with gr.Column(elem_classes="gp-card"):
                            tb_outdir = gr.Textbox(value=str(OUTPUT_DIR), label="输出目录（建议留在仓库 output/ 内，便于试听）")
                            zip_cb = gr.Checkbox(value=True, label="完成后打包 zip 下载", elem_classes="gp-check")
                        with gr.Row():
                            btn_batch = gr.Button("开始批量合成", elem_classes="gp-primary")
                    with gr.Column(scale=2):
                        with gr.Column(elem_classes="gp-card"):
                            gr.Markdown("进度与结果", elem_classes="gp-lbl")
                            batch_status = gr.Markdown("", elem_classes="gp-note")
                            batch_zip = gr.File(label="zip 下载", visible=True)

            # ===== 环境页 =====
            with gr.Column(visible=False) as p_env:
                with gr.Row():
                    with gr.Column(scale=3):
                        with gr.Column(elem_classes="gp-card"):
                            with gr.Row():
                                gr.Markdown("环境检查", elem_classes="gp-lbl")
                                btn_env = gr.Button("重新检测", elem_classes="gp-ghost")
                            env_out = gr.HTML(env_check_html(cfg0))
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<div style="background:#fffdf7;border:1px solid #e2d7c2;border-radius:12px;padding:14px;color:#8a7a63;font-family:KaiTi;font-size:13px;">'
                            "环境就绪前，「合成」会引导你先补全依赖；补丁相关问题见训练引导页。<br><br>"
                            "提示：torch 必须用 2.6.0+cu126（2.13 在 Windows 上会崩溃）。</div>"
                        )

            # ===== 引导页 =====
            with gr.Column(visible=False) as p_guide:
                guide_out = gr.HTML(guide_html(cfg0))

            # ===== 历史页 =====
            with gr.Column(visible=False) as p_history:
                with gr.Row():
                    btn_hrefresh = gr.Button("刷新", elem_classes="gp-ghost")
                    btn_hclear = gr.Button("清空历史", elem_classes="gp-ghost")
                history_out = gr.HTML(history_html())

            # ===== 设置页 =====
            with gr.Column(visible=False) as p_settings:
                with gr.Column(elem_classes="gp-card"):
                    gr.Markdown("路径与模型配置（保存为本机默认，写入 .guangpu_webui/config.json）", elem_classes="gp-lbl")
                    st_root = gr.Textbox(value=cfg0["gpt_sovits_root"], label="GPT-SoVITS 根目录")
                    st_gpt = gr.Textbox(value=cfg0["gpt_model"], label="GPT 模型")
                    st_sovits = gr.Textbox(value=cfg0["sovits_model"], label="SoVITS 模型")
                    st_ref = gr.Textbox(value=cfg0["ref_audio"], label="参考音频")
                    st_reftext = gr.Textbox(value=cfg0["ref_text"], label="参考文本")
                    with gr.Row():
                        btn_saveset = gr.Button("保存设置", elem_classes="gp-primary")
                    set_note = gr.Markdown("", elem_classes="gp-note")

    # ---------- 事件 ----------
    _out_switch = [
        p_synth, p_batch, p_env, p_guide, p_history, p_settings,
        head,
        b_synth, b_batch, b_env, b_guide, b_history, b_settings,
        guide_out, history_out,
    ]

    def switch(page, cfg):
        vis = {name: gr.update(visible=(name == page)) for name in NAV_ORDER}
        title, sub = PAGE_TITLES[page]
        variants = [gr.update(variant="primary" if n == page else "secondary") for n in NAV_ORDER]
        return (
            [vis[n] for n in NAV_ORDER]
            + [f"<h1>{title}</h1><p>{sub}</p>"]
            + variants
            + [guide_html(cfg), history_html()]
        )

    for name, btn in zip(NAV_ORDER, [b_synth, b_batch, b_env, b_guide, b_history, b_settings]):
        btn.click(fn=lambda s, p=name: switch(p, s), inputs=[cfg_state], outputs=_out_switch)

    for sl, val in [(sl_tk, val_tk), (sl_tp, val_tp), (sl_temp, val_temp), (sl_steps, val_steps), (sl_speed, val_speed), (sl_pause, val_pause)]:
        sl.change(fn=lambda v: f"**{fmt_num(v)}**", inputs=sl, outputs=val)

    _out_synth = [out_summary] + [u for pair in zip(out_rows, out_audios) for u in pair]

    def do_synth(text, auto, tk, tp, temp, steps, speed, pause, gpt, sovits, ref_audio, ref_text, cfg_state, progress=gr.Progress()):
        cfg = dict(cfg_state)
        cfg.update(
            gpt_model=gpt, sovits_model=sovits, ref_audio=ref_audio, ref_text=ref_text,
            top_k=int(tk), top_p=float(tp), temperature=float(temp), sample_steps=int(steps),
            speed=float(speed), pause_second=float(pause), auto_lightmid=bool(auto),
        )
        lines = parse_lines(text)
        empty = [gr.update(visible=False), gr.update(value=None)] * 12
        if not lines:
            yield "台词为空，请先输入内容。", *empty
            return
        try:
            progress(0, desc="加载模型…")
            ensure_backend(cfg)
        except Exception as exc:
            yield f"后端初始化失败：{exc}。请到「环境检测」页排查。", *empty
            return
        out_dir = os.path.join(OUTPUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out_dir, exist_ok=True)
        total = len(lines)
        rows = [gr.update(visible=False), gr.update(value=None)] * 12
        ok = 0
        done = []
        for i, line in enumerate(lines):
            progress((i + 1) / total, desc=f"合成第 {i + 1}/{total} 句")
            use = to_lightmid(line) if auto else line
            base = f"{i + 1:03d}_{safe_name(line)}"
            try:
                audio, sr = synth_one(cfg, use)
                path = save_audio(audio, sr, out_dir, base)
                ok += 1
                done.append({"text": line, "path": path})
                if i < 12:
                    rows[i * 2] = gr.update(visible=True)
                    rows[i * 2 + 1] = gr.update(value=path, label=os.path.basename(path))
            except Exception as exc:
                if i < 12:
                    rows[i * 2] = gr.update(visible=True)
                    rows[i * 2 + 1] = gr.update(value=None, label=f"{base} · 失败")
                done.append({"text": line, "path": ""})
            yield f"进度 {i + 1}/{total} · 成功 {ok} · {out_dir}", *rows
        params = f"t{cfg['temperature']}/s{cfg['sample_steps']}"
        append_history(
            [
                {
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "text": d["text"],
                    "params": params,
                    "name": os.path.basename(d["path"]) if d["path"] else "",
                    "file": d["path"],
                }
                for d in done
                if d["path"]
            ]
        )
        yield f"完成 {ok}/{total} · 输出目录：{out_dir}", *rows

    btn_synth.click(
        do_synth,
        inputs=[ta, auto_cb, sl_tk, sl_tp, sl_temp, sl_steps, sl_speed, sl_pause, tb_gpt, tb_sovits, tb_ref, tb_reftext, cfg_state],
        outputs=_out_synth,
    )

    def clear_synth():
        return "", "", *([gr.update(visible=False), gr.update(value=None)] * 12)

    btn_clear.click(fn=clear_synth, inputs=[], outputs=[ta, out_summary] + [u for pair in zip(out_rows, out_audios) for u in pair])

    def save_default(text, auto, tk, tp, temp, steps, speed, pause, gpt, sovits, ref_audio, ref_text, cfg_state):
        cfg = dict(cfg_state)
        cfg.update(
            gpt_model=gpt, sovits_model=sovits, ref_audio=ref_audio, ref_text=ref_text,
            top_k=int(tk), top_p=float(tp), temperature=float(temp), sample_steps=int(steps),
            speed=float(speed), pause_second=float(pause), auto_lightmid=bool(auto),
        )
        save_config(cfg)
        return cfg, "已保存为默认配置（.guangpu_webui/config.json）。"

    btn_savedef.click(
        save_default,
        inputs=[ta, auto_cb, sl_tk, sl_tp, sl_temp, sl_steps, sl_speed, sl_pause, tb_gpt, tb_sovits, tb_ref, tb_reftext, cfg_state],
        outputs=[cfg_state, save_note],
    )

    def do_batch(file_obj, outdir, zip_on, cfg_state, progress=gr.Progress()):
        cfg = dict(cfg_state)
        if file_obj is None:
            return "请先上传台词文件。", None
        try:
            raw = Path(file_obj).read_text(encoding="utf-8-sig")
        except Exception as exc:
            return f"读取文件失败：{exc}（请确认 UTF-8 编码）", None
        lines = parse_lines(raw)
        if not lines:
            return "文件里没有有效台词（空行或 # 注释会被忽略）。", None
        try:
            progress(0, desc="加载模型…")
            ensure_backend(cfg)
        except Exception as exc:
            return f"后端初始化失败：{exc}。请到「环境检测」页排查。", None
        out_dir = os.path.abspath(outdir.strip() or os.path.join(OUTPUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S")))
        os.makedirs(out_dir, exist_ok=True)
        total = len(lines)
        ok = 0
        fails = []
        done = []
        for i, line in enumerate(lines):
            progress((i + 1) / total, desc=f"合成第 {i + 1}/{total} 句")
            use = to_lightmid(line) if cfg["auto_lightmid"] else line
            try:
                audio, sr = synth_one(cfg, use)
                path = save_audio(audio, sr, out_dir, f"{i + 1:03d}_{safe_name(line)}")
                ok += 1
                done.append({"text": line, "path": path})
            except Exception as exc:
                fails.append(f"第 {i + 1} 句：{exc}")
        zip_path = None
        if zip_on and ok:
            base = os.path.join(OUTPUT_DIR, f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(os.path.dirname(base), exist_ok=True)
            try:
                zip_path = shutil.make_archive(base, "zip", out_dir)
            except Exception:
                zip_path = None
        params = f"t{cfg['temperature']}/s{cfg['sample_steps']}"
        append_history(
            [
                {
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "text": d["text"],
                    "params": params,
                    "name": os.path.basename(d["path"]),
                    "file": d["path"],
                }
                for d in done
            ]
        )
        msg = f"完成 {ok}/{total} · 输出目录：{out_dir}"
        if fails:
            msg += "；失败：" + "；".join(fails[:5]) + ("…" if len(fails) > 5 else "")
        return msg, zip_path

    btn_batch.click(do_batch, inputs=[batch_file, tb_outdir, zip_cb, cfg_state], outputs=[batch_status, batch_zip])

    btn_env.click(fn=lambda s: env_check_html(s), inputs=cfg_state, outputs=env_out)
    btn_hrefresh.click(fn=history_html, inputs=[], outputs=history_out)

    def do_clear_history():
        clear_history()
        return history_html()

    btn_hclear.click(fn=do_clear_history, inputs=[], outputs=history_out)

    def save_settings(root, gpt, sovits, ref_audio, ref_text, cfg_state):
        cfg = dict(cfg_state)
        cfg.update(gpt_sovits_root=root.strip(), gpt_model=gpt.strip(), sovits_model=sovits.strip(), ref_audio=ref_audio.strip(), ref_text=ref_text.strip())
        save_config(cfg)
        return cfg, "已保存（.guangpu_webui/config.json）。重启后仍生效。"

    btn_saveset.click(
        save_settings,
        inputs=[st_root, st_gpt, st_sovits, st_ref, st_reftext, cfg_state],
        outputs=[cfg_state, set_note],
    )


if __name__ == "__main__":
    # GPT-SoVITS 的 inference_webui 在模块级自建 Gradio 应用并注册事件，
    # 只能在我们的应用启动前导入，否则组件注册会崩溃；因此这里先预加载后端。
    _boot_cfg = load_config()
    try:
        ensure_backend(_boot_cfg)
        print("后端模型已加载，正在启动 WebUI ...")
    except Exception as exc:
        print(f"后端预加载失败（可到环境检测页排查）：{exc}")
    demo.queue().launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        allowed_paths=[str(REPO_ROOT)],
        blocked_paths=[str(CONFIG_DIR)],
        show_error=True,
        show_api=False,
        inbrowser=True,
    )
