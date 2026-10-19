# 投递进度看板：7 个组件的 data_config 模板

> Source of truth：`lark-cli skills read lark-base/references/lark-base-dashboard-block-config.md`（CLI 内置）。**data_config 不要从自然语言臆造**，按下文模板复制，只替换表名/字段名时必须先 `+table-list`/`+field-list` 确认真实名称。
> 实测版本：lark-cli 1.0.96。

## 创建顺序（严格串行）

```bash
# 1. 建仪表盘，拿 dashboard_id
lark-cli base +dashboard-create --base-token <token> --name "投递进度看板" --as user

# 2. 逐个创建 7 个组件（禁止并行！每次创建后记录返回的 block_id）
lark-cli base +dashboard-block-create --base-token <token> --dashboard-id <did> \
  --name "总投递岗位数" --type statistics --data-config '<见下>' --as user

# 3. 全部建完后整理布局
lark-cli base +dashboard-arrange --base-token <token> --dashboard-id <did> --as user
```

- `--position` 可省（服务端自动排布）；需要精确布局时传 `'{"x":0,"y":0,"w":6,"h":4}'`（x/y/w/h 四键齐全）
- 创建后可用 `+dashboard-block-get-data --block-id <bid>` 验证有数

## 7 个组件模板

### 1. 总投递岗位数（statistics 指标卡）

```json
{"table_name":"投递记录","count_all":true}
```

### 2. 各状态分布（column 柱状图）

```json
{
  "table_name": "投递记录",
  "count_all": true,
  "group_by": [{ "field_name": "状态", "mode": "integrated", "sort": {"type":"value","order":"desc"} }]
}
```

### 3. 优先级分布（ring 环形图）

```json
{
  "table_name": "投递记录",
  "count_all": true,
  "group_by": [{ "field_name": "优先级", "mode": "integrated", "sort": {"type":"group","order":"asc"} }]
}
```

### 4. 各优先级平均评分（column 柱状图）

```json
{
  "table_name": "投递记录",
  "series": [{ "field_name": "评分", "rollup": "AVERAGE" }],
  "group_by": [{ "field_name": "优先级", "mode": "integrated", "sort": {"type":"group","order":"asc"} }]
}
```

### 5. 投递日期趋势（line 折线图）

```json
{
  "table_name": "投递记录",
  "count_all": true,
  "group_by": [{ "field_name": "投递日期", "mode": "integrated", "sort": {"type":"group","order":"asc"} }]
}
```

### 6. DDL 提醒（column 柱状图，按 DDL日期 取数 + 过滤非空）

```json
{
  "table_name": "投递记录",
  "count_all": true,
  "group_by": [{ "field_name": "DDL日期", "mode": "integrated", "sort": {"type":"group","order":"asc"} }],
  "filter": { "conjunction": "and", "conditions": [{ "field_name": "DDL日期", "operator": "isNotEmpty" }] }
}
```

> 以「DDL日期」（datetime）为机器判定字段——自由文本「DDL事项」不可靠且无法稳定过滤。柱状图展示"哪天有几个 DDL"；文案看「DDL事项」字段。

### 7. 面试评分走势（area 面积图，数据源=面试记录）

```json
{
  "table_name": "面试记录",
  "series": [{ "field_name": "面试评分", "rollup": "AVERAGE" }],
  "group_by": [{ "field_name": "面试日期", "mode": "integrated", "sort": {"type":"group","order":"asc"} }]
}
```

## 关键约束（违反会创建失败）

- 图表类型必带 `table_name`；`series` 与 `count_all` 二选一，至少一个
- `group_by` 最多 2 个；写了 `sort` 就必须带 `order`（`value` 排序不会自动补方向）
- `filter` 的日期条件只能 `is/isGreater/isLess`，value 用 `["ExactDate", 毫秒时间戳]`；`isNotEmpty` 不传 value（模板 6 即按 DDL日期 过滤非空）
- 同一 dashboard 的组件**必须串行创建**，并记录每个 `block_id`
- 已知坑：`text` 类型组件经 CLI 更新时文本会被包一层 JSON 引号（1.0.96 实测），且 `--data-config` 会吞换行——本看板不使用 text 组件，DDL 展示用模板 6 的数据驱动柱状图替代
