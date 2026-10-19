#!/usr/bin/env python3
"""qiuzhao 一键初始化：建 base + 6 表 + 13 行评分规则 + 7 组件看板 + config。

用法：
  python3 scripts/setup.py --direction "支付>金融科技>风控" --city "北京>杭州"
  python3 scripts/setup.py --base-url "<已有表格链接>" --direction "..." --city "..."   # 接入已有 base

幂等：已有 config 且 base 可达时只补缺失（表/字段/规则行/组件），不重复创建。
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz


def parse_order(s: str) -> list:
    return [x.strip() for x in s.replace("＞", ">").split(">") if x.strip()]


def ensure_base(args) -> tuple:
    """返回 (base_token, created_first_table: bool)。"""
    if args.base_url:
        d = qz.lark("base", "+url-resolve", "--url", args.base_url)
        token = (d.get("data") or {}).get("base_token") or (d.get("data") or {}).get("baseToken")
        if not token:
            sys.exit(f"url-resolve 未返回 base_token：{json.dumps(d.get('data'), ensure_ascii=False)[:300]}")
        return token, False
    d = qz.lark("base", "+base-create", "--name", args.name, "--time-zone", args.time_zone,
                "--table-name", "投递记录",
                "--fields", json.dumps(qz.table_fields("投递记录"), ensure_ascii=False))
    base = (d.get("data") or {}).get("base") or {}
    token = base.get("base_token")
    if not token:
        sys.exit(f"base-create 未返回 base_token：{json.dumps(d.get('data'), ensure_ascii=False)[:300]}")
    print(f"✓ base 已创建：{base.get('url', token)}")
    return token, True


def table_map(base_token: str) -> dict:
    d = qz.lark("base", "+table-list", "--base-token", base_token)
    return {t["name"]: t["id"] for t in (d.get("data") or {}).get("tables") or []}


def ensure_tables(base_token: str, first_created: bool) -> dict:
    want = ["投递记录", "简历库", "个人信息", "评分规则", "Offer评估", "面试记录"]
    have = table_map(base_token)
    for name in want:
        if name in have:
            continue
        d = qz.lark("base", "+table-create", "--base-token", base_token, "--name", name,
                    "--fields", json.dumps(qz.table_fields(name), ensure_ascii=False))
        print(f"✓ 表已创建：{name}")
    have = table_map(base_token)
    missing = [n for n in want if n not in have]
    if missing:
        sys.exit(f"表创建后仍缺失：{missing}")
    return have


def ensure_scoring_rows(base_token: str, table_id: str, direction: list, city: list) -> None:
    existing = qz.records("评分规则", {"base_token": base_token, "tables": {"评分规则": table_id}})
    if len(existing) >= 13:
        print(f"✓ 评分规则已有 {len(existing)} 行，跳过")
        return
    rows = qz.scoring_rows(direction, city)
    # create_records 是裸字段 map 数组（无 fields 包装），单次上限 200
    payload = {"create_records": rows}
    qz.lark("base", "+record-batch-create", "--base-token", base_token,
            "--table-id", table_id, "--json", json.dumps(payload, ensure_ascii=False))
    print(f"✓ 评分规则写入 {len(rows)} 行")


def ensure_dashboard(base_token: str, cfg_tables: dict) -> str:
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
    ap.add_argument("--direction", required=True, help='方向偏好排序，如 "支付>金融科技>风控"')
    ap.add_argument("--city", required=True, help='城市偏好排序，如 "北京>杭州"')
    ap.add_argument("--name", default="秋招投递管理")
    ap.add_argument("--time-zone", default="Asia/Shanghai", help="非中国区用户改本地时区")
    ap.add_argument("--base-url", help="接入已有表格时传其链接（跳过创建 base）")
    args = ap.parse_args()

    direction, city = parse_order(args.direction), parse_order(args.city)
    if not direction or not city:
        sys.exit("--direction 与 --city 均不能为空")

    token, first_created = ensure_base(args)
    tables = ensure_tables(token, first_created)
    ensure_scoring_rows(token, tables["评分规则"], direction, city)
    dash_id = ensure_dashboard(token, tables)

    cfg = {
        "base_token": token,
        "tables": tables,
        "dashboard_id": dash_id,
        "preferences": {"direction_order": direction, "city_order": city},
    }
    qz.save_config(cfg)
    print(f"✓ 配置已写入 {qz.CONFIG_PATH}")
    print("\n初始化完成。正在自检……")
    import init_check
    sys.exit(init_check.run())


if __name__ == "__main__":
    main()
