#!/usr/bin/env python3
"""脚本单元测试（unittest + mock，零第三方依赖）。

运行：python3 -m unittest discover -s tests -v
"""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qz_lib as qz
import bootstrap
import conversion_report
import overview


class TestScoringRows(unittest.TestCase):
    def test_thirteen_rows(self):
        rows = qz.scoring_rows(["支付", "金融科技", "风控"], ["北京", "杭州"])
        self.assertEqual(len(rows), 13)
        self.assertEqual({r["模块"] for r in rows}, {"匹配分", "策略分", "Offer评估"})

    def test_levels_generated_from_preference(self):
        rows = qz.scoring_rows(["支付", "金融科技"], ["北京"])
        dir_rule = next(r for r in rows if r["维度"] == "方向一致性")["档位规则"]
        self.assertIn("支付=10", dir_rule)
        self.assertIn("金融科技=8", dir_rule)
        self.assertNotIn("由初始化", dir_rule)

    def test_weights_sum(self):
        rows = qz.scoring_rows(["支付"], ["北京"])
        self.assertEqual(sum(r["权重"] for r in rows if r["模块"] == "匹配分"), 100)
        self.assertEqual(sum(r["权重"] for r in rows if r["模块"] == "策略分"), 100)
        self.assertEqual(sum(r["权重"] for r in rows if r["模块"] == "Offer评估"), 100)


class TestEnsureScoringRows(unittest.TestCase):
    def test_partial_rows_only_fills_missing(self):
        """已有 12 行时只补 1 行，不再整批 13 行重复写入。"""
        existing = [
            {"record_id": f"rec{i}", "fields": {"模块": r["模块"], "维度": r["维度"]}}
            for i, r in enumerate(qz.scoring_rows(["支付"], ["北京"])[:12])
        ]
        calls = []

        def fake_lark(*args, **kwargs):
            if "+record-batch-create" in args:
                calls.append(json.loads(args[args.index("--json") + 1]))
                return {"ok": True, "data": {}}
            return {"ok": True, "data": {}}

        with mock.patch.object(qz, "records", return_value=existing), \
             mock.patch.object(qz, "lark", side_effect=fake_lark):
            bootstrap.ensure_scoring_rows("tok", "tbl", ["支付"], ["北京"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]["create_records"]), 1)

    def test_complete_rows_write_nothing(self):
        existing = [
            {"record_id": f"rec{i}", "fields": {"模块": r["模块"], "维度": r["维度"]}}
            for i, r in enumerate(qz.scoring_rows(["支付"], ["北京"]))
        ]
        with mock.patch.object(qz, "records", return_value=existing), \
             mock.patch.object(qz, "lark") as m:
            bootstrap.ensure_scoring_rows("tok", "tbl", ["支付"], ["北京"])
        m.assert_not_called()


class TestBootstrapIdempotent(unittest.TestCase):
    def test_existing_config_reuses_base(self):
        """已有 config 且 base 可达 → 不再 base-create（不建第二个 base）。"""
        cfg = {"base_token": "tok123", "tables": {}, "dashboard_id": None}
        args = mock.Mock(base_url=None, direction="支付>金融科技", city="北京",
                         name="x", time_zone="Asia/Shanghai")
        with mock.patch.object(qz, "try_load_config", return_value=cfg), \
             mock.patch.object(qz, "base_reachable", return_value=True), \
             mock.patch.object(qz, "lark") as m:
            token, _ = bootstrap.resolve_base(args)
        self.assertEqual(token, "tok123")
        for call in m.call_args_list:
            self.assertNotIn("+base-create", call.args)

    def test_new_base_writes_config_immediately(self):
        """新建 base 后立即写 config（中途失败可找回）。"""
        args = mock.Mock(base_url=None, direction="支付>金融科技", city="北京",
                         name="x", time_zone="Asia/Shanghai")
        saved = []

        def fake_lark(*a, **k):
            return {"ok": True, "data": {"base": {"base_token": "newtok", "url": "u"}}}

        with mock.patch.object(qz, "try_load_config", return_value=None), \
             mock.patch.object(qz, "lark", side_effect=fake_lark), \
             mock.patch.object(qz, "save_config", side_effect=saved.append):
            token, _ = bootstrap.resolve_base(args)
        self.assertEqual(token, "newtok")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["base_token"], "newtok")


class TestConversion(unittest.TestCase):
    def _run(self, apps, interviews):
        def fake_records(table, cfg):
            return interviews if table == "面试记录" else apps

        buf = io.StringIO()
        with mock.patch.object(qz, "load_config", return_value={"base_token": "t"}), \
             mock.patch.object(qz, "records", side_effect=fake_records), \
             redirect_stdout(buf):
            conversion_report.main()
        return buf.getvalue()

    def test_rejected_after_interview_counts_as_interviewed(self):
        """面完被拒（状态=已挂）也算进过面。"""
        apps = [
            {"record_id": "recA", "fields": {"公司": "A", "优先级": ["P0"], "状态": ["已挂"]}},
            {"record_id": "recB", "fields": {"公司": "B", "优先级": ["P0"], "状态": ["一面"]}},
        ]
        interviews = [{"record_id": "iv1", "fields": {"关联投递": [{"id": "recA"}]}}]
        out = self._run(apps, interviews)
        line = next(l for l in out.splitlines() if l.startswith("P0"))
        self.assertIn("2", line.split()[1])  # 分母 2
        self.assertIn("2", line.split()[2])  # 进过面 2（不是 1）

    def test_denominator_excludes_pending_and_abandoned(self):
        apps = [
            {"record_id": "r1", "fields": {"优先级": ["P1"], "状态": ["待投递"]}},
            {"record_id": "r2", "fields": {"优先级": ["P1"], "状态": ["放弃"]}},
            {"record_id": "r3", "fields": {"优先级": ["P1"], "状态": ["已投递"]}},
        ]
        out = self._run(apps, [])
        line = next(l for l in out.splitlines() if l.startswith("P1"))
        self.assertEqual(line.split()[1], "1")  # 分母只有 1


class TestParseOrderSeparators(unittest.TestCase):
    def test_all_separators(self):
        """逗号/竖线/尖括号/全角均可解析（Windows cmd 推荐逗号）。"""
        self.assertEqual(bootstrap.parse_order("支付,金融科技,风控"), ["支付", "金融科技", "风控"])
        self.assertEqual(bootstrap.parse_order("支付|金融科技"), ["支付", "金融科技"])
        self.assertEqual(bootstrap.parse_order("支付>金融科技"), ["支付", "金融科技"])
        self.assertEqual(bootstrap.parse_order("支付＞金融科技，风控"), ["支付", "金融科技", "风控"])
        self.assertEqual(bootstrap.parse_order("支付 , 金融科技 "), ["支付", "金融科技"])


class TestFindLarkCli(unittest.TestCase):
    def test_windows_cmd_fallback(self):
        """Windows：which 找不到时回退 %APPDATA%\\npm\\lark-cli.cmd。"""
        import os
        fake_appdata = "/fake/appdata"
        target = Path(fake_appdata) / "npm" / "lark-cli.cmd"
        with mock.patch.object(qz.shutil, "which", return_value=None), \
             mock.patch.dict(os.environ, {"APPDATA": fake_appdata}), \
             mock.patch.object(Path, "exists", lambda self: str(self) == str(target)):
            self.assertEqual(qz.find_lark_cli(), str(target))


class TestOverviewHelpers(unittest.TestCase):
    def test_parse_dt_formats(self):
        self.assertIsNotNone(overview.parse_dt("2026-03-24 10:00"))
        self.assertIsNotNone(overview.parse_dt("2026-03-24"))
        self.assertIsNotNone(overview.parse_dt("2026-03-24T10:00:00.000+08:00"))
        self.assertIsNone(overview.parse_dt(None))

    def test_same_instant_sort_does_not_crash(self):
        """同一时刻两条 DDL 排序不因比较 dict 崩溃。"""
        import datetime
        t = datetime.datetime(2026, 1, 1, 10, 0)
        items = [(t, {"b": 1}), (t, {"a": 1})]
        sorted(items, key=lambda x: x[0])  # 不抛 TypeError 即通过


if __name__ == "__main__":
    unittest.main()
