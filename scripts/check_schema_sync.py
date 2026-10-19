#!/usr/bin/env python3
"""校验 SKILL.md Step 1 的 --fields JSON 与 references/table-schema.md 表 1 的 JSON 一致。

防漂移：字段改动必须两处同步，本脚本在 CI 与本地均可运行。
exit 0 = 一致；exit 1 = 不一致（打印差异摘要）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REF = ROOT / "references" / "table-schema.md"


def extract_step1_fields(text: str):
    m = re.search(r"--fields '\s*(\[.*?\])'\s*--as user", text, re.S)
    return json.loads(m.group(1)) if m else None


def extract_ref_table1(text: str):
    # 表 1 小节内的第一个 json 代码块
    m = re.search(r"## 表 1.*?```json\n(.*?)```", text, re.S)
    return json.loads(m.group(1)) if m else None


def main():
    skill_fields = extract_step1_fields(SKILL.read_text(encoding="utf-8"))
    ref_fields = extract_ref_table1(REF.read_text(encoding="utf-8"))
    if skill_fields is None:
        print("FAIL: 未在 SKILL.md Step 1 中解析到 --fields JSON")
        return 1
    if ref_fields is None:
        print("FAIL: 未在 references/table-schema.md 表 1 中解析到 JSON 块")
        return 1
    if skill_fields == ref_fields:
        print(f"OK: 两处表 1 schema 一致（{len(skill_fields)} 个字段）")
        return 0
    sk = {f.get("name") for f in skill_fields}
    rf = {f.get("name") for f in ref_fields}
    print("FAIL: 两处表 1 schema 不一致")
    print("  仅在 SKILL:", sorted(sk - rf))
    print("  仅在 references:", sorted(rf - sk))
    return 1


if __name__ == "__main__":
    sys.exit(main())
