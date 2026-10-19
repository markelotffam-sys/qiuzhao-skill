#!/usr/bin/env python3
"""导出（不含自动恢复）：把 6 张表导出为本地 JSON（默认 ~/qiuzhao-backup/<日期>/；Unix 收紧为 700/600，Windows 另需手动 ACL）。

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
    try:
        out.chmod(0o700)  # 含简历/投递数据与 base_token，收紧目录权限
    except OSError:
        pass

    meta = {"base_token": cfg["base_token"], "tables": cfg["tables"],
            "preferences": cfg.get("preferences"), "exported_at": datetime.datetime.now().isoformat()}
    # base_token 属个人指针：备份文件是本地私有数据，正常保留以便恢复
    (out / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    total = 0
    for name in TABLES:
        rows = qz.records(name, cfg)
        total += len(rows)
        fp = out / f"{name}.json"
        fp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            fp.chmod(0o600)
        except OSError:
            pass
        print(f"✓ {name}: {len(rows)} 条")
    print(f"\n导出完成：{out}（共 {total} 条；Unix 权限 700/600，Windows 不适用 chmod——如需收紧请手动设 ACL）。含 base_token 与个人数据，勿分享该目录；此为导出（不含自动恢复），恢复需导入或人工回填。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
