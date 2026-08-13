# -*- coding: utf-8 -*-
"""生成 s1/s2 训练配置（v2Pro）。

用法：
    python build_train_configs.py --dataset 数据集目录 --exp 实验名 \
        --s1-epochs 15 --s2-epochs 12 --root GPT-SoVITS根目录
输出：<root>/TEMP/tmp_s1.yaml 与 tmp_s2.json
"""

import argparse
import json
import os
import shutil

import yaml


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"..\GPT-SoVITS", help="GPT-SoVITS 根目录")
    p.add_argument("--dataset", required=True, help="数据集目录（含 2-name2text / 3-bert / 6-name2semantic 等）")
    p.add_argument("--exp", default="guangpu07", help="实验名")
    p.add_argument("--s1-epochs", type=int, default=15)
    p.add_argument("--s2-epochs", type=int, default=12)
    p.add_argument("--version", default="v2Pro")
    args = p.parse_args()

    root = os.path.abspath(args.root)
    ds = os.path.abspath(args.dataset)
    tmp = os.path.join(root, "TEMP")
    os.makedirs(tmp, exist_ok=True)

    shutil.copyfile(os.path.join(ds, "2-name2text-0.txt"), os.path.join(ds, "2-name2text.txt"))
    shutil.copyfile(os.path.join(ds, "6-name2semantic-0.tsv"), os.path.join(ds, "6-name2semantic.tsv"))

    with open(os.path.join(root, "GPT_SoVITS", "configs", "s1longer-v2.yaml"), encoding="utf-8") as f:
        s1 = yaml.safe_load(f)
    s1["train"]["batch_size"] = 8
    s1["train"]["epochs"] = args.s1_epochs
    s1["train"]["save_every_n_epoch"] = 2
    s1["train"]["if_save_every_weights"] = True
    s1["train"]["if_save_latest"] = True
    s1["train"]["if_dpo"] = False
    s1["train"]["half_weights_save_dir"] = os.path.join(root, "GPT_weights_v2Pro")
    s1["train"]["exp_name"] = args.exp
    s1["pretrained_s1"] = os.path.join(root, "GPT_SoVITS", "pretrained_models", "s1v3.ckpt")
    s1["train_semantic_path"] = os.path.join(ds, "6-name2semantic.tsv")
    s1["train_phoneme_path"] = os.path.join(ds, "2-name2text.txt")
    s1["output_dir"] = os.path.join(ds, "logs_s1_v2Pro")
    with open(os.path.join(tmp, "tmp_s1.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(s1, f, default_flow_style=False, allow_unicode=True)
    print("tmp_s1.yaml OK")

    with open(os.path.join(root, "GPT_SoVITS", "configs", "s2v2Pro.json"), encoding="utf-8") as f:
        s2 = json.load(f)
    s2["train"]["batch_size"] = 4
    s2["train"]["epochs"] = args.s2_epochs
    s2["train"]["text_low_lr_rate"] = 0.4
    s2["train"]["pretrained_s2G"] = os.path.join(root, "GPT_SoVITS", "pretrained_models", "v2Pro", "s2Gv2Pro.pth")
    s2["train"]["pretrained_s2D"] = os.path.join(root, "GPT_SoVITS", "pretrained_models", "v2Pro", "s2Dv2Pro.pth")
    s2["train"]["if_save_latest"] = True
    s2["train"]["if_save_every_weights"] = True
    s2["train"]["save_every_epoch"] = 2
    s2["train"]["gpu_numbers"] = "0"
    s2["train"]["grad_ckpt"] = True
    s2["train"]["lora_rank"] = 0
    s2["model"]["version"] = args.version
    s2["data"]["exp_dir"] = s2["s2_ckpt_dir"] = ds
    s2["save_weight_dir"] = os.path.join(root, "SoVITS_weights_v2Pro")
    s2["name"] = args.exp
    s2["version"] = args.version
    with open(os.path.join(tmp, "tmp_s2.json"), "w", encoding="utf-8") as f:
        json.dump(s2, f, ensure_ascii=False, indent=2)
    print("tmp_s2.json OK")


if __name__ == "__main__":
    main()
