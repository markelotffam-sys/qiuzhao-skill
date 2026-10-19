#!/usr/bin/env python3
"""schema 一致性校验（CI）：

1. references/table-schema.md 的 6 张表 JSON 可解析（单一来源，脚本运行时解析它）
2. references/dashboard-blocks.md 的 7 个 data_config 可解析
3. scoring_rows 生成 13 行；dashboard_templates 返回 7 个组件
exit 0 = 通过。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qz_lib as qz

WANT_TABLES = ["投递记录", "简历库", "个人信息", "评分规则", "Offer评估", "面试记录"]


def main() -> int:
    errors = []

    # 1. 六表 schema
    for name in WANT_TABLES:
        try:
            fields = qz.table_fields(name)
            if not fields:
                errors.append(f"表「{name}」schema 为空")
            elif not any(f.get("name") for f in fields):
                errors.append(f"表「{name}」字段缺 name")
        except SystemExit as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"表「{name}」JSON 解析失败：{e}")

    # 2. 看板模板
    try:
        tpls = qz.dashboard_templates()
        if len(tpls) != 7:
            errors.append(f"看板模板 {len(tpls)} 个 ≠ 7")
    except Exception as e:
        errors.append(f"看板模板解析失败：{e}")

    # 3. 业务生成器
    rows = qz.scoring_rows(["支付", "金融科技", "风控"], ["北京", "杭州"])
    if len(rows) != 13:
        errors.append(f"评分规则 {len(rows)} 行 ≠ 13")

    for e in errors:
        print(f"✗ {e}")
    if errors:
        return 1
    print("OK: 6 表 schema / 7 看板模板 / 13 评分行 全部可解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
