# 六张表的字段 Schema

> Source of truth：`lark-cli skills read lark-base/references/lark-base-field-schema.md`（CLI 内置）。本文件提供各表字段 JSON（建表前不要自创字段属性）；**含 `--fields` 的完整可执行命令在 [SKILL.md](../SKILL.md) Step 1**。
> 实测版本：lark-cli 1.0.96。

## 类型速查（本 skill 用到的 5 种）

| 语义 | 机器类型 | 注意 |
|---|---|---|
| 文本/链接样式/长文 | `text` | 超链接是 `style:{"type":"url"}`，**没有** `type:"url"` |
| 数字/评分/金额 | `number` | `style.type` 默认 `plain`，可设 `precision` |
| 单选 | `select` | `multiple:false`，`options:[{name},...]` 一次建全 |
| 日期 | `datetime` | `style.format` 如 `yyyy/MM/dd`；**没有** `type:"date"` |
| 关联记录 | `link` | 必填 `link_table`（目标表名） |

## 建表顺序（必须遵守）

1. **投递记录**（用 `+base-create --table-name --fields` 随 base 一起建）
2. 简历库 / 个人信息 / 评分规则 / Offer评估（任意顺序）
3. **面试记录**（最后建——它的「关联投递」link 指向投递记录）

## 表 1「投递记录」（base 的第一张表）

> **完整可执行命令（含 `--fields`）见 [SKILL.md](../SKILL.md) Step 1**——本文件只维护字段 schema，避免两处命令漂移。下述 JSON 数组即 Step 1 命令 `--fields` 的值。

```json
[
  {"name":"公司","type":"text"},
  {"name":"岗位","type":"text"},
  {"name":"投递日期","type":"datetime","style":{"format":"yyyy/MM/dd"}},
  {"name":"最近更新","type":"datetime","style":{"format":"yyyy/MM/dd"}},
  {"name":"进度查询链接","type":"text","style":{"type":"url"}},
  {"name":"状态","type":"select","multiple":false,"options":[{"name":"待投递"},{"name":"已投递"},{"name":"筛选中"},{"name":"笔试"},{"name":"一面"},{"name":"二面"},{"name":"三面"},{"name":"HR面"},{"name":"Offer"},{"name":"已挂"},{"name":"放弃"}]},
  {"name":"评分","type":"number","style":{"type":"plain","precision":1}},
  {"name":"评分拆解","type":"text"},
  {"name":"优先级","type":"select","multiple":false,"options":[{"name":"P0"},{"name":"P1"},{"name":"P2"}]},
  {"name":"JD核心拆解","type":"text"},
  {"name":"JD原文","type":"text"},
  {"name":"备注","type":"text"},
  {"name":"DDL日期","type":"datetime","style":{"format":"yyyy/MM/dd"}},
  {"name":"DDL事项","type":"text"}
]
```

> 若 base 已存在（降级路径/续跑），用 `+table-create --base-token <token> --name "投递记录" --fields '<上述 JSON 数组>'` 建表。

## 表 2「简历库」

```json
[
  {"name":"版本","type":"text"},
  {"name":"日期","type":"datetime","style":{"format":"yyyy/MM/dd"}},
  {"name":"简历全文","type":"text"}
]
```

## 表 3「个人信息」

```json
[
  {"name":"项","type":"text"},
  {"name":"值","type":"text"}
]
```

## 表 4「评分规则」

```json
[
  {"name":"模块","type":"text"},
  {"name":"维度","type":"text"},
  {"name":"权重","type":"number","style":{"type":"plain","precision":0}},
  {"name":"档位规则","type":"text"}
]
```

## 表 5「Offer评估」

```json
[
  {"name":"公司","type":"text"},
  {"name":"岗位","type":"text"},
  {"name":"城市","type":"text"},
  {"name":"评估分","type":"number","style":{"type":"plain","precision":1}},
  {"name":"评估拆解","type":"text"},
  {"name":"总包(万/年)","type":"number","style":{"type":"plain","precision":1}},
  {"name":"Base月薪(元)","type":"number","style":{"type":"plain","precision":0}},
  {"name":"团队/氛围分","type":"number","style":{"type":"plain","precision":1}},
  {"name":"备注","type":"text"}
]
```

## 表 6「面试记录」（最后建）

```json
[
  {"name":"公司","type":"text"},
  {"name":"岗位","type":"text"},
  {"name":"关联投递","type":"link","link_table":"投递记录"},
  {"name":"面试日期","type":"datetime","style":{"format":"yyyy/MM/dd"}},
  {"name":"面试轮次","type":"select","multiple":false,"options":[{"name":"一面"},{"name":"二面"},{"name":"三面"},{"name":"HR面"}]},
  {"name":"面试时长","type":"number","style":{"type":"plain","precision":0}},
  {"name":"面试评分","type":"number","style":{"type":"plain","precision":1}},
  {"name":"评分拆解","type":"text"},
  {"name":"面试总结","type":"text"},
  {"name":"关键问题","type":"text"},
  {"name":"改进清单","type":"text"},
  {"name":"待办","type":"text"}
]
```

> link 字段默认 `bidirectional:false`（单向），**不会**在投递记录生成反向字段；若发现投递记录出现反向 link 字段，说明创建时用了 `bidirectional:true`，按需保留或删除，不是重复建字段。

## 写入规范（CellValue 形态，写记录前必读）

| 字段类型 | CellValue 写法 |
|---|---|
| text | `"字符串"` |
| number | `12.5`（裸数字） |
| select（单选） | `["已投递"]`——**也是数组**，单选数组里只能有一个选项 |
| select（多选） | `["标签A","标签B"]` |
| datetime | `"2026-03-24 10:00"` 字符串 |
| link | `[{"id":"rec_xxx"}]`；写入前先用 `+record-list --filter-json` 定位到目标 record_id |

示例（录入一条投递记录的完整字段；示例数字与 40/40/20 与 45/35/20 权重自洽）：

```bash
lark-cli base +record-upsert --base-token <token> --table-id 投递记录 --as user --json '{
  "公司":"示例公司",
  "岗位":"产品经理",
  "投递日期":"2026-03-24 10:00",
  "最近更新":"2026-03-24 10:00",
  "状态":["已投递"],
  "评分":7.6,
  "评分拆解":"匹配7.6（硬性8/经验8/技能6）/策略8.1（方向10/平台7/城市5.6）",
  "优先级":["P1"],
  "DDL日期":"2026-04-02 19:30",
  "DDL事项":"4.2 19:30 一面"
}'
```

**更新示例**（完整更新语义见 SKILL「记录更新」——更新 ≠ 新建，须先定位 record_id）：

```bash
# 定位（--filter-json 双条件；record_id 在 data.record_id_list）
lark-cli base +record-list --base-token <token> --table-id 投递记录 --as user --format json \
  --filter-json '{"logic":"and","conditions":[["公司","==","示例公司"],["岗位","==","产品经理"]]}'
# 更新时同步写「最近更新」
lark-cli base +record-upsert --base-token <token> --table-id 投递记录 --record-id <id> --as user \
  --json '{"状态":["笔试"],"最近更新":"2026-03-28 14:00"}'
```

**含换行/引号的长 JSON**（如 JD核心拆解多行文本）：先写入临时文件再传，避免 shell 转义出错：

```bash
# macOS / Linux
cat > /tmp/record.json <<'EOF'
{"公司":"示例公司","JD核心拆解":"【岗位方向】支付\n【核心职责】……"}
EOF
lark-cli base +record-upsert ... --json "$(cat /tmp/record.json)"
```

```powershell
# Windows（PowerShell）：用编辑器或 Python 写文件，再以子表达式传参（--json 需要参数值，管道是 stdin 不行）
lark-cli base +record-upsert ... --json (Get-Content record.json -Raw)
```
