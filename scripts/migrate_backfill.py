#!/usr/bin/env python3
"""旧数据迁移：批量回填「最近更新」；报告缺「DDL日期」的记录。

用法：python3 scripts/migrate_backfill.py --apply     # 实际写入
      python3 scripts/migrate_backfill.py            # 预览（写入前预览，不落盘）
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入（默认只预览）")
    args = ap.parse_args()

    cfg = qz.load_config()
    apps = qz.records("投递记录", cfg)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    def val(r, k):
        v = r["fields"].get(k)
        return v[0] if isinstance(v, list) and v and isinstance(v[0], str) else v

    need = [r["record_id"] for r in apps if not val(r, "最近更新")]
    ddl_miss = [f"{val(r,'公司')}/{val(r,'岗位')}（DDL事项：{val(r,'DDL事项')}）"
                for r in apps if val(r, "DDL事项") and not val(r, "DDL日期")]

    print(f"【预览】待回填「最近更新」= {len(need)} 条；有 DDL事项 缺 DDL日期 = {len(ddl_miss)} 条")
    for x in ddl_miss[:20]:
        print(f"  - {x}")
    if len(ddl_miss) > 20:
        print(f"  …共 {len(ddl_miss)} 条")

    if not args.apply:
        print("\n（预览模式，未写入。加 --apply 执行回填）")
        return 0

    for i in range(0, len(need), 200):
        chunk = need[i:i + 200]
        payload = {"update_records": {rid: {"最近更新": now} for rid in chunk}}
        qz.lark("base", "+record-batch-update", "--base-token", cfg["base_token"],
                "--table-id", cfg["tables"]["投递记录"], "--json", json.dumps(payload, ensure_ascii=False))
        print(f"✓ 已回填 {len(chunk)} 条（批次 {i // 200 + 1}）")
    print("完成。「DDL日期」需按「DDL事项」文案人工/半自动回填（只知日期时写当天 23:59）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
