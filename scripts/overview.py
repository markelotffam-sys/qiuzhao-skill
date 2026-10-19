#!/usr/bin/env python3
"""总览：固定结构输出（状态计数 / P0 待办 / DDL 两段 / 停滞提醒 / 最近面试 / 看板提示）。

用法：python3 scripts/overview.py
"""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz

TERMINAL = {"Offer", "已挂", "放弃"}
ORDER = ["待投递", "已投递", "筛选中", "笔试", "一面", "二面", "三面", "HR面", "Offer", "已挂", "放弃"]


def parse_dt(v):
    if not v:
        return None
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v / 1000)
    s = str(v).replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def main() -> int:
    cfg = qz.load_config()
    now = datetime.datetime.now()
    apps = qz.records("投递记录", cfg)

    def f(rec, key):
        v = rec["fields"].get(key)
        return v[0] if isinstance(v, list) and v and isinstance(v[0], str) else v

    # 1. 状态计数
    counts = {}
    for r in apps:
        st = f(r, "状态") or "（未填）"
        counts[st] = counts.get(st, 0) + 1
    line = " · ".join(f"{st} {counts[st]}" for st in ORDER if st in counts)
    print(f"【各状态计数】{line or '暂无记录'}（共 {len(apps)}）")

    # 2. P0 待办（非终态，按评分降序）
    p0 = [r for r in apps if f(r, "优先级") == "P0" and (f(r, "状态") or "") not in TERMINAL]
    p0.sort(key=lambda r: -(f(r, "评分") or 0))
    print("\n【P0 待办】")
    print("\n".join(f"- {f(r,'公司')} / {f(r,'岗位')} · {f(r,'状态')} · 评分 {f(r,'评分')}" for r in p0) or "（无）")

    # 3. DDL 两段（互斥）
    win_end = (now + datetime.timedelta(days=6)).replace(hour=23, minute=59, second=0)
    upcoming, expired, no_date = [], [], 0
    for r in apps:
        ddl, item = parse_dt(f(r, "DDL日期")), f(r, "DDL事项")
        if item and not ddl:
            no_date += 1
            continue
        if not ddl:
            continue
        (expired if ddl <= now else upcoming if ddl <= win_end else []).append((ddl, r))
    print(f"\n【DDL · 未来 7 天（含今天）】")
    for ddl, r in sorted(upcoming):
        print(f"- {ddl:%m-%d %H:%M} {f(r,'DDL事项') or ''}（{f(r,'公司')}）")
    if not upcoming:
        print("（无）")
    print(f"【DDL · 已过期】")
    for ddl, r in sorted(expired):
        print(f"- {ddl:%m-%d %H:%M} {f(r,'DDL事项') or ''}（{f(r,'公司')}）— 建议清理")
    if not expired:
        print("（无）")
    if no_date:
        print(f"⚠ 另有 {no_date} 条有「DDL事项」但缺「DDL日期」（旧数据，建议回填，否则会漏显）")

    # 4. 停滞提醒（最近更新 >14 天；空值跳过并提示）
    stale, no_upd = [], 0
    for r in apps:
        if (f(r, "状态") or "") in TERMINAL:
            continue
        upd = parse_dt(f(r, "最近更新"))
        if not upd:
            no_upd += 1
            continue
        if (now - upd).days > 14:
            stale.append(r)
    print("\n【停滞提醒（>14 天未更新）】")
    print("\n".join(f"- {f(r,'公司')} / {f(r,'岗位')} · {f(r,'状态')}" for r in stale) or "（无）")
    if no_upd:
        print(f"⚠ 另有 {no_upd} 条缺「最近更新」未参与停滞判断（建议回填）")

    # 5. 最近面试复盘
    try:
        ivs = qz.records("面试记录", cfg)
        if ivs:
            ivs.sort(key=lambda r: parse_dt(f(r, "面试日期")) or datetime.datetime.min, reverse=True)
            top = ivs[0]
            improves = str(f(top, "改进清单") or "").split("；")[:3]
            print(f"\n【最近面试】{f(top,'公司')} / {f(top,'岗位')} · 评分 {f(top,'面试评分')}")
            for imp in improves:
                if imp.strip():
                    print(f"  改进：{imp.strip()}")
    except SystemExit:
        pass

    print(f"\n【看板】可在飞书打开「投递进度看板」查看图表")
    return 0


if __name__ == "__main__":
    sys.exit(main())
