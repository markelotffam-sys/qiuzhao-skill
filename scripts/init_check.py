#!/usr/bin/env python3
"""初始化完成校验（幂等自检）：6 表 / 字段 / 13 行规则 / 7 组件 / link 字段。

用法：python3 scripts/init_check.py
exit 0 = 全部通过（可修复项降级为警告）；1 = 有阻塞缺失。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz

WANT_TABLES = ["投递记录", "简历库", "个人信息", "评分规则", "Offer评估", "面试记录"]


def main() -> int:
    cfg = qz.load_config()
    base = cfg["base_token"]
    errors, warns = [], []

    # 1. 表
    d = qz.lark("base", "+table-list", "--base-token", base)
    tables = {t["name"]: t["id"] for t in (d.get("data") or {}).get("tables") or []}
    for name in WANT_TABLES:
        if name not in tables:
            errors.append(f"缺表：{name}")
    extra = set(tables) - set(WANT_TABLES)
    if extra:
        warns.append(f"多余表（仅提示）：{sorted(extra)}")

    # 2. 字段（逐字段逐选项）
    for name in WANT_TABLES:
        if name not in tables:
            continue
        d = qz.lark("base", "+field-list", "--base-token", base, "--table-id", tables[name])
        live = {}
        for f in (d.get("data") or {}).get("items") or (d.get("data") or {}).get("fields") or []:
            live[f.get("field_name") or f.get("name")] = f
        for spec in qz.table_fields(name):
            fname = spec["name"]
            if fname not in live:
                errors.append(f"[{name}] 缺字段：{fname}")
                continue
            lf = live[fname]
            ltype = lf.get("type") or lf.get("ui_type")
            if ltype and ltype != spec["type"]:
                warns.append(f"[{name}] {fname} 类型 {ltype} ≠ schema {spec['type']}")
            if spec["type"] == "select":
                want_opts = {o["name"] for o in spec.get("options") or []}
                raw_opts = lf.get("options") or (lf.get("property") or {}).get("options") or []
                live_opts = {o.get("name") for o in raw_opts if isinstance(o, dict)}
                missing = want_opts - live_opts
                if missing:
                    warns.append(f"[{name}] {fname} 缺选项 {sorted(missing)}（可修复项，用 +field-update 补）")

    # 3. 评分规则 13 行 + 档位非占位
    if "评分规则" in tables:
        rows = qz.records("评分规则", cfg)
        if len(rows) < 13:
            errors.append(f"评分规则 {len(rows)} 行 < 13")
        for r in rows:
            f = r["fields"]
            rule = str(f.get("档位规则") or "")
            if f.get("维度") in ("方向一致性", "城市") and ("由初始化" in rule or "生成档位" in rule):
                errors.append(f"档位仍为占位文案：{f.get('模块')}/{f.get('维度')}")

    # 4. 看板 7 组件
    if cfg.get("dashboard_id"):
        d = qz.lark("base", "+dashboard-block-list", "--base-token", base,
                    "--dashboard-id", cfg["dashboard_id"])
        blocks = {b.get("name") for b in (d.get("data") or {}).get("items") or []}
        for name, _t, _c in qz.dashboard_templates():
            if name not in blocks:
                errors.append(f"缺看板组件：{name}")
    else:
        errors.append("config 缺 dashboard_id")

    # 5. link 字段
    if "面试记录" in tables:
        d = qz.lark("base", "+field-list", "--base-token", base, "--table-id", tables["面试记录"])
        fields = (d.get("data") or {}).get("items") or (d.get("data") or {}).get("fields") or []
        if not any((f.get("field_name") or f.get("name")) == "关联投递" for f in fields):
            errors.append("面试记录缺「关联投递」link 字段")

    for w in warns:
        print(f"⚠ {w}")
    for e in errors:
        print(f"✗ {e}")
    if errors:
        print(f"\n校验未通过：{len(errors)} 项缺失（只补缺失，勿重建）")
        return 1
    print(f"✓ 校验通过：6 表 / 13 行评分规则 / 7 组件 / link 字段就绪" + (f"（{len(warns)} 条可修复警告）" if warns else ""))
    return 0


def run() -> int:
    return main()


if __name__ == "__main__":
    sys.exit(main())
