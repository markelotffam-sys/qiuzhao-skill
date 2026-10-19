#!/usr/bin/env python3
"""导出备份：把 6 张表导出为本地 JSON（默认 ~/qiuzhao-backup/<日期>/）。

用法：python3 scripts/export_backup.py [--out DIR]
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz

TABLES = ["投递记录", "简历库", "个人信息", "评分规则", "Offer评估", "面试记录"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="导出目录（默认 ~/qiuzhao-backup/<日期>）")
    args = ap.parse_args()

    cfg = qz.load_config()
    out = Path(args.out) if args.out else Path.home() / "qiuzhao-backup" / datetime.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)

    meta = {"base_token": cfg["base_token"], "tables": cfg["tables"],
            "preferences": cfg.get("preferences"), "exported_at": datetime.datetime.now().isoformat()}
    # base_token 属个人指针：备份文件是本地私有数据，正常保留以便恢复
    (out / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    total = 0
    for name in TABLES:
        rows = qz.records(name, cfg)
        total += len(rows)
        (out / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ {name}: {len(rows)} 条")
    print(f"\n导出完成：{out}（共 {total} 条）。含 base_token，属私人备份，请勿分享该目录。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
