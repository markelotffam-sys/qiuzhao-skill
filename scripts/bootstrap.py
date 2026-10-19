#!/usr/bin/env python3
"""qiuzhao 一键初始化（幂等）：建/续 base + 6 表 + 13 行规则 + 7 组件看板 + config。

用法：
  python3 scripts/bootstrap.py --direction "支付>金融科技>风控" --city "北京>杭州"
  python3 scripts/bootstrap.py --direction "..." --city "..." --base-url "<已有表格链接>"
  python3 scripts/bootstrap.py ... --fix-fields    # 补缺失字段/选项（含 high-risk 选项更新）

幂等保证：
- 已有 config 且 base 可达 → 复用续跑（不会建第二个 base）
- 新建 base 后**立即**写 config（哪怕后续步骤失败，重跑也能找回）
- 表存在只补缺表；字段/选项缺 → 按需补（--fix-fields）；评分行按 (模块,维度) 只补缺失
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz

WANT_TABLES = ["投递记录", "简历库", "个人信息", "评分规则", "Offer评估", "面试记录"]


def parse_order(s: str) -> list:
    """支持 '支付>金融科技' / '支付,金融科技' / '支付|金融科技'（推荐逗号，避开 shell 重定向）。"""
    parts = re.split(r"[>＞,，|｜/]+", s)
    return [x.strip() for x in parts if x.strip()]


def resolve_base(args) -> tuple:
    """返回 (base_token, cfg)。cfg 可能是部分状态（新建时立即落盘）。"""
    # 1. 显式传链接
    if args.base_url:
        d = qz.lark("base", "+url-resolve", "--url", args.base_url)
        data = d.get("data") or {}
        token = data.get("base_token") or data.get("baseToken")
        if not token:
            sys.exit(f"url-resolve 未返回 base_token：{json.dumps(data, ensure_ascii=False)[:300]}")
        return token, {}
    # 2. 已有 config 且可达 → 续跑（幂等关键）
    cfg = qz.try_load_config()
    if cfg and cfg.get("base_token") and qz.base_reachable(cfg["base_token"]):
        print(f"✓ 检测到已有配置与可达 base（{cfg['base_token'][:8]}…），续跑模式（只补缺失）")
        return cfg["base_token"], cfg
    if cfg:
        print("⚠ 配置存在但 base 不可达，将新建（如想接入旧表请用 --base-url）")
    # 3. 新建 base，立即写 config（失败重跑可找回）
    d = qz.lark("base", "+base-create", "--name", args.name, "--time-zone", args.time_zone,
                "--table-name", "投递记录",
                "--fields", json.dumps(qz.table_fields("投递记录"), ensure_ascii=False))
    base = (d.get("data") or {}).get("base") or {}
    token = base.get("base_token")
    if not token:
        sys.exit(f"base-create 未返回 base_token：{json.dumps(d.get('data'), ensure_ascii=False)[:300]}")
    state = {"base_token": token, "tables": {}, "dashboard_id": None,
             "preferences": {"direction_order": parse_order(args.direction),
                             "city_order": parse_order(args.city)}}
    qz.save_config(state)  # 立即落盘：中途失败重跑可找回
    print(f"✓ base 已创建并写入配置：{base.get('url', token)}")
    return token, state


def table_map(base_token: str) -> dict:
    d = qz.lark("base", "+table-list", "--base-token", base_token)
    return {t["name"]: t["id"] for t in (d.get("data") or {}).get("tables") or []}


def ensure_tables(base_token: str) -> dict:
    have = table_map(base_token)
    for name in WANT_TABLES:
        if name in have:
            continue
        qz.lark("base", "+table-create", "--base-token", base_token, "--name", name,
                "--fields", json.dumps(qz.table_fields(name), ensure_ascii=False))
        print(f"✓ 表已创建：{name}")
    have = table_map(base_token)
    missing = [n for n in WANT_TABLES if n not in have]
    if missing:
        sys.exit(f"表创建后仍缺失：{missing}")
    return have


def ensure_fields(base_token: str, tables: dict, fix: bool) -> None:
    """逐字段逐选项对比；缺字段 → 补建；缺选项 → --fix-fields 时用 field-update 补全。"""
    for name in WANT_TABLES:
        d = qz.lark("base", "+field-list", "--base-token", base_token, "--table-id", tables[name])
        items = (d.get("data") or {}).get("items") or (d.get("data") or {}).get("fields") or []
        live = {f.get("field_name") or f.get("name"): f for f in items}
        for spec in qz.table_fields(name):
            fname = spec["name"]
            if fname not in live:
                if fix:
                    qz.lark("base", "+field-create", "--base-token", base_token,
                            "--table-id", tables[name], "--json", json.dumps(spec, ensure_ascii=False))
                    print(f"✓ [{name}] 缺字段已补：{fname}")
                else:
                    print(f"⚠ [{name}] 缺字段：{fname}（加 --fix-fields 自动补）")
                continue
            if spec["type"] == "select":
                want = {o["name"] for o in spec.get("options") or []}
                raw = live[fname].get("options") or (live[fname].get("property") or {}).get("options") or []
                missing = want - {o.get("name") for o in raw if isinstance(o, dict)}
                if missing:
                    if fix:
                        full = dict(spec)
                        qz.lark("base", "+field-update", "--base-token", base_token,
                                "--table-id", tables[name], "--field-id", live[fname].get("id") or fname,
                                "--json", json.dumps(full, ensure_ascii=False), "--yes")
                        print(f"✓ [{name}] {fname} 缺选项已补：{sorted(missing)}")
                    else:
                        print(f"⚠ [{name}] {fname} 缺选项 {sorted(missing)}（加 --fix-fields 补，属 high-risk 会请求确认）")


def ensure_scoring_rows(base_token: str, table_id: str, direction: list, city: list) -> None:
    """按 (模块, 维度) 只补缺失行；已有行不动（用户可能改过权重）。"""
    existing = qz.records("评分规则", {"base_token": base_token, "tables": {"评分规则": table_id}})
    have = set()
    for r in existing:
        f = r["fields"]
        mod = f.get("模块")
        dim = f.get("维度")
        if isinstance(mod, list):
            mod = mod[0] if mod else None
        if isinstance(dim, list):
            dim = dim[0] if dim else None
        have.add((mod, dim))
    want = qz.scoring_rows(direction, city)
    missing = [r for r in want if (r["模块"], r["维度"]) not in have]
    if not missing:
        print(f"✓ 评分规则 13 行已齐（不覆盖已有权重）")
        return
    payload = {"create_records": missing}  # 裸字段 map 数组
    qz.lark("base", "+record-batch-create", "--base-token", base_token,
            "--table-id", table_id, "--json", json.dumps(payload, ensure_ascii=False))
    print(f"✓ 评分规则补写 {len(missing)} 行（已存在 {len(have)} 行未动）")


def ensure_dashboard(base_token: str) -> str:
    d = qz.lark("base", "+dashboard-list", "--base-token", base_token)
    dashes = (d.get("data") or {}).get("items") or (d.get("data") or {}).get("dashboards") or []
    dash = next((x for x in dashes if x.get("name") == "投递进度看板"), None)
    if dash:
        dash_id = dash.get("dashboard_id") or dash.get("id")
        print(f"✓ 看板已存在：{dash_id}")
    else:
        d = qz.lark("base", "+dashboard-create", "--base-token", base_token, "--name", "投递进度看板")
        dash_id = ((d.get("data") or {}).get("dashboard") or {}).get("dashboard_id")
        print(f"✓ 看板已创建：{dash_id}")
    d = qz.lark("base", "+dashboard-block-list", "--base-token", base_token, "--dashboard-id", dash_id)
    have = {b.get("name") for b in (d.get("data") or {}).get("items") or []}
    for name, btype, cfg in qz.dashboard_templates():
        if name in have:
            continue
        qz.lark("base", "+dashboard-block-create", "--base-token", base_token,
                "--dashboard-id", dash_id, "--name", name, "--type", btype,
                "--data-config", json.dumps(cfg, ensure_ascii=False))
        print(f"✓ 组件已创建：{name}")
    qz.lark("base", "+dashboard-arrange", "--base-token", base_token, "--dashboard-id", dash_id)
    return dash_id


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", required=True, help='方向偏好排序（推荐逗号分隔），如 "支付,金融科技,风控"')
    ap.add_argument("--city", required=True, help='城市偏好排序（推荐逗号分隔），如 "北京,杭州"')
    ap.add_argument("--name", default="秋招投递管理")
    ap.add_argument("--time-zone", default="Asia/Shanghai", help="非中国区用户改本地时区")
    ap.add_argument("--base-url", help="接入已有表格时传其链接（跳过创建 base）")
    ap.add_argument("--fix-fields", action="store_true", help="自动补缺失字段/选项（选项更新属 high-risk）")
    args = ap.parse_args()

    direction, city = parse_order(args.direction), parse_order(args.city)
    if not direction or not city:
        sys.exit("--direction 与 --city 均不能为空")

    token, cfg = resolve_base(args)
    tables = ensure_tables(token)
    ensure_fields(token, tables, fix=args.fix_fields)
    ensure_scoring_rows(token, tables["评分规则"], direction, city)
    dash_id = ensure_dashboard(token)

    cfg.update({
        "base_token": token,
        "tables": tables,
        "dashboard_id": dash_id,
        "preferences": {"direction_order": direction, "city_order": city},
    })
    qz.save_config(cfg)
    print(f"✓ 配置已写入 {qz.CONFIG_PATH}")
    print("\n初始化完成。正在自检……")
    import init_check
    sys.exit(init_check.run())


if __name__ == "__main__":
    main()
