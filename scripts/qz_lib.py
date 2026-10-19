#!/usr/bin/env python3
"""qiuzhao skill 脚本共享库：lark-cli 调用、config 读写、schema 单一来源。

字段 schema 一律从 references/table-schema.md 运行时解析（单一来源）；
看板 data_config 从 references/dashboard-blocks.md 解析。
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path.home() / ".config" / "qiuzhao" / "config.json"
LEGACY_CONFIG_PATH = Path.home() / ".claude" / "skills" / "qiuzhao" / "config.json"


def find_lark_cli() -> str:
    exe = shutil.which("lark-cli")
    if exe:
        return exe
    cand = Path.home() / ".npm-global" / "bin" / "lark-cli"
    if cand.exists():
        return str(cand)
    sys.exit("lark-cli 未找到；请先安装：npm install -g @larksuite/cli@1.0.96")


def lark(*args: str, check: bool = True) -> dict:
    """执行 lark-cli 子命令并解析 JSON 输出。"""
    cmd = [find_lark_cli(), *args, "--as", "user"]
    if "--format" not in args:
        cmd += ["--format", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        if check:
            sys.exit(f"lark-cli 输出无法解析：{args[0:3]}\n{proc.stdout[:300]}\n{proc.stderr[:300]}")
        return {"ok": False, "error": {"message": proc.stderr[:300] or proc.stdout[:300]}}
    if check and not data.get("ok"):
        sys.exit(f"lark-cli 失败：{args[0:4]}\n{json.dumps(data.get('error'), ensure_ascii=False)[:400]}")
    return data


def try_load_config() -> dict:
    """读 config，不存在返回 None（不退出）。"""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if LEGACY_CONFIG_PATH.exists():
        cfg = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
        save_config(cfg)
        LEGACY_CONFIG_PATH.unlink()
        return cfg
    return None


def base_reachable(base_token: str) -> bool:
    d = lark("base", "+table-list", "--base-token", base_token, check=False)
    return bool(d.get("ok"))


def load_config() -> dict:
    """读 config；新路径缺失时尝试旧路径一次性迁移。"""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if LEGACY_CONFIG_PATH.exists():
        cfg = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
        save_config(cfg)
        LEGACY_CONFIG_PATH.unlink()
        return cfg
    sys.exit(f"配置不存在：{CONFIG_PATH}\n请先运行 bootstrap.py 初始化（或提供已有表格链接）")


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- schema 单一来源：从 references 解析 ----------

def _ref_table_schema() -> dict:
    text = (ROOT / "references" / "table-schema.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    tables = {}
    for m in re.finditer(r"## 表 (\d)「([^」]+)」.*?```json\n(.*?)```", text, re.S):
        tables[m.group(2)] = json.loads(m.group(3))
    return tables


def table_fields(name: str) -> list:
    tables = _ref_table_schema()
    if name not in tables:
        sys.exit(f"references/table-schema.md 中未找到表「{name}」的 schema")
    return tables[name]


def dashboard_templates() -> list:
    """返回 [(block_name, type, data_config_dict), ...]，顺序即创建顺序。"""
    text = (ROOT / "references" / "dashboard-blocks.md").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"### \d+\. (.+?)（(\w+)[^）]*）\s*\n+```json\n(.*?)```", text, re.S):
        out.append((m.group(1).strip(), m.group(2).strip(), json.loads(m.group(3))))
    return out


# ---------- 业务规则 ----------

def scoring_rows(direction_order: list, city_order: list) -> list:
    """生成 13 行评分规则。direction_order/city_order 为偏好排序列表（最喜欢的在前）。"""
    def ladder(order, top, second, rest_floor):
        parts = []
        scores = [top, second] + [max(rest_floor, second - 2 * (i - 1)) for i in range(2, len(order))]
        for name, sc in zip(order, scores):
            parts.append(f"{name}={sc}")
        return "；".join(parts)

    dir_levels = ladder(direction_order, 10, 8, 4)
    dir_levels += "；其他产品=3-4；无关=1" if len(direction_order) else "按偏好逐级递减"
    city_levels = ladder(city_order, 10, 7, 3)
    city_levels += "；其他=3" if len(city_order) else "按偏好逐级递减"

    return [
        {"模块": "匹配分", "维度": "硬性要求达成度", "权重": 40, "档位规则": "全部满足=10；满足大半=7；缺关键项=4；明显不符=2"},
        {"模块": "匹配分", "维度": "经验相关度", "权重": 40, "档位规则": "做过同类=10；强相关=8；相关=6；无关=3"},
        {"模块": "匹配分", "维度": "技能匹配度", "权重": 20, "档位规则": "JD关键词命中率；核心技能全中=10"},
        {"模块": "策略分", "维度": "方向一致性", "权重": 45, "档位规则": dir_levels},
        {"模块": "策略分", "维度": "平台价值", "权重": 35, "档位规则": "按客观锚点查证（市值/营收/行业地位/校招品牌力）分档，不预设名单：TOP级=10；头部/大型上市=8；细分知名=6；中型=4；小厂=2"},
        {"模块": "策略分", "维度": "城市", "权重": 20, "档位规则": city_levels},
        {"模块": "策略分", "维度": "优先级", "权重": 0, "档位规则": "P0：匹配≥7且策略≥7；P1：一高一中；P2：其余（阈值说明行，权重不参与计算）"},
        {"模块": "Offer评估", "维度": "薪资总包", "权重": 35, "档位规则": "主评分；总包高但base低→注水检测下调"},
        {"模块": "Offer评估", "维度": "薪资规则", "权重": 0, "档位规则": "总包=base×12+年终+签字费+期权面值；期权按面值；城市不做成本调整（口径说明行）"},
        {"模块": "Offer评估", "维度": "方向一致性", "权重": 20, "档位规则": "同策略分「方向一致性」档位"},
        {"模块": "Offer评估", "维度": "平台价值", "权重": 20, "档位规则": "同策略分「平台价值」档位"},
        {"模块": "Offer评估", "维度": "城市", "权重": 15, "档位规则": "同策略分「城市」档位"},
        {"模块": "Offer评估", "维度": "团队/氛围", "权重": 10, "档位规则": "用户主观打分 0-10"},
    ]


def records(table: str, cfg: dict) -> list:
    """读取一张表全部记录，自动翻页；返回 [{record_id, fields}, ...]。"""
    out, offset = [], 0
    while True:
        d = lark("base", "+record-list", "--base-token", cfg["base_token"],
                 "--table-id", cfg["tables"][table], "--limit", "200", "--offset", str(offset))
        data = d.get("data") or {}
        ids = data.get("record_id_list") or []
        rows = data.get("data") or []
        fields = data.get("fields") or []
        for rid, row in zip(ids, rows):
            fmap = {f: v for f, v in zip(fields, row)} if fields else {}
            out.append({"record_id": rid, "fields": fmap})
        if not data.get("has_more") or not ids:
            break
        offset += 200
    return out
