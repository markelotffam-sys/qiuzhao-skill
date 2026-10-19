#!/usr/bin/env python3
"""转化率复盘：各优先级的实际进面率 / Offer 率（轻量反馈闭环，不做自动调参）。

用法：python3 scripts/conversion_report.py

口径：进面 = 状态到达 一面/二面/三面/HR面/Offer；Offer = 状态 Offer。
样本 <20 条的档位仅作参考——转化率差异很可能是随机波动，调权重请人工判断。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz

INTERVIEW_PLUS = {"一面", "二面", "三面", "HR面", "Offer"}
PRIO = ["P0", "P1", "P2"]


def main() -> int:
    cfg = qz.load_config()
    apps = qz.records("投递记录", cfg)

    def val(r, k):
        v = r["fields"].get(k)
        return v[0] if isinstance(v, list) and v and isinstance(v[0], str) else v

    print("【转化率复盘】（进面=状态到达一面及之后；Offer=终态 Offer）")
    print(f"{'优先级':<4} {'样本':>4} {'进面':>4} {'进面率':>7} {'Offer':>5} {'Offer率':>7}  提示")
    for p in PRIO:
        rows = [r for r in apps if val(r, "优先级") == p]
        n = len(rows)
        iv = sum(1 for r in rows if (val(r, "状态") or "") in INTERVIEW_PLUS)
        off = sum(1 for r in rows if val(r, "状态") == "Offer")
        note = "" if n >= 20 else "样本<20，仅供参考"
        if n:
            print(f"{p:<4} {n:>4} {iv:>4} {iv / n:>6.0%} {off:>5} {off / n:>6.0%}  {note}")
        else:
            print(f"{p:<4} {0:>4} {'-':>4} {'-':>7} {'-':>5} {'-':>7}")

    others = [r for r in apps if val(r, "优先级") not in PRIO]
    if others:
        print(f"\n（另有 {len(others)} 条未填优先级，未纳入统计）")
    print("\n说明：本视图只呈现事实，**不自动调权重**。样本充足时可参考进面率差异，")
    print("人工决定是否调整「评分规则」表的方向/平台/城市档位或权重。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
