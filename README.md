# 秋招助理（qiuzhao） Skill

> v1.0.1 · 实测于 lark-cli 1.0.96

一个通用的校招投递管理助手：录入 JD、评估岗位契合度、跟踪投递进度、评估 Offer、面试复盘。
首次使用自动初始化（创建飞书表格结构、引导设置偏好），数据全部存在你自己的飞书账号下，本地只存指针。

## 安装

### 1. 准备 Claude Code 与 lark-cli

- 装好 [Claude Code](https://claude.com/claude-code)
- 装飞书命令行工具 lark-cli（公开 npm 包 [@larksuite/cli](https://www.npmjs.com/package/@larksuite/cli)，需 Node.js ≥ 16，建议 18+）：

```bash
npm install -g @larksuite/cli@1.0.96   # 本文实测版本；更新版本理论兼容、未复测
lark-cli config init --new      # 首次：初始化配置（会引导你在浏览器完成）
lark-cli auth login --domain base,docs,drive   # 用你自己的飞书账号授权；不确定范围可 --domain all
lark-cli auth status            # 确认通过
```

> `--domain base,docs,drive` 是推荐范围：base 域负责建表读写与 wiki 链接解析；docs/drive 提供「贴链接/搜标题定位表格」的文档搜索能力。只授权 base 也可用，但贴链接解析可能受限。

### 2. 把本仓库装进技能目录

```bash
git clone https://github.com/markelotffam-sys/qiuzhao-skill.git ~/.claude/skills/qiuzhao
```

> 没装 git 也可以：仓库页面 Code → Download ZIP，解压后把里面的文件夹改名为 `qiuzhao`，整个移到 `~/.claude/skills/` 下。

### 3. 开始使用

重启 Claude Code，输入 `/qiuzhao`——首次使用会自动进入初始化引导。

## 使用

```
/qiuzhao                    # 总览：状态计数 / P0 待办 / 7天 DDL / 停滞提醒（首次自动进初始化）
/qiuzhao 初始化             # 手动触发配置；换电脑时用它接入已有表格
/qiuzhao 录入 [JD原文]      # 录入新岗位：拆解 + 匹配分/策略分 + 优先级
/qiuzhao 更新 [公司+岗位]   # 更新投递状态/备注
/qiuzhao offer [公司+岗位]  # 记录 offer 薪资 + 评估分
/qiuzhao 简历 [粘贴全文]    # 录入/更新简历
/qiuzhao 面试 [录音/转写]   # 面试复盘：评分 + 关键问题 + 改进清单 + 待办
```

## 初始化后会发生什么

- 自动在飞书创建「秋招投递管理」多维表格（失败则引导你手动建表贴链接）
- 自动建 **6 张表** + 字段：投递记录（含「最近更新」「DDL日期」机器字段）/ 简历库 / 个人信息 / 评分规则 / Offer评估 / 面试记录
- 交互式询问你的**方向偏好**和**城市偏好**（一次一问），生成具体评分档位后写入 **13 行**评分规则
- 可选收集画像（基本画像/经历/投递策略/故事线/短板应对，各自用途会说明）
- 创建「投递进度看板」7 个组件：总投递岗位数（指标卡）/ 各状态分布（柱状图）/ 优先级分布（环形图）/ 各优先级平均评分（柱状图）/ 投递日期趋势（折线图）/ DDL 提醒（柱状图，按 DDL日期）/ 面试评分走势（面积图）
- 把 base_token、table_id 等存到 `~/.config/qiuzhao/config.json`，最后逐项校验（6 表 / 13 行规则 / 7 组件 / 关联字段）

之后随时改「评分规则」表即可调整权重和档位——改表不改代码。

## 数据归属与隐私

- **业务数据**（投递记录/简历/画像/评分规则）全部在你自己的飞书账号下，本仓库不含也不会收集任何个人数据
- **本地 config**（`~/.config/qiuzhao/config.json`）存的是 base_token / table_id 等指针——它属于你的账号信息，**不要提交到任何 git 仓库**（本仓库已 .gitignore 覆盖常见误提交路径）
- 手机装飞书 App 可随时查看投递表和看板
- 分发给别人的只有 skill 逻辑本身，任何人的数据都不会随仓库带走

## 核心设计决策

- **评分双轨**：匹配分（够不够格，客观对照简历）+ 策略分（值不值得，按你的偏好）
- **不设"别投"挡**：评分只用于排序 P0 主攻 / P1 重点 / P2 广撒，Offer 阶段再权衡薪资城市
- **权重放数据里**：评分规则存飞书表，改权重 = 改一条记录
- **硬卡一票否决**：学历/届数/专业等不可逾越项不满足 → 匹配分压至 4 以下
- **数据与认证解耦**：数据归个人账号，每台电脑用自己的授权——换设备不换数据
- **面试复盘闭环**：录音/转写 → 评分 + 改进清单 + 待办，写入面试记录表并关联投递

## 常见问题

**初始化时自动创建失败怎么办？**
在飞书手动创建一个多维表格（空表即可），把链接发给 AI，skill 会解析链接继续。

**想改评分权重/偏好？**
直接改飞书「评分规则」表对应行（「权重」列或「档位规则」列），不用动 skill。

**换电脑了？**
重新安装 skill，`/qiuzhao 初始化` 时把原来的表格链接发过来即可接入，数据不丢。

**配置文件丢了？**
config.json 只是指针，丢了重新初始化、贴原表格链接即可恢复。

**建表/看板命令报错？**
`--fields` 和 `--data-config` 是严格的 JSON schema，本仓库 `references/` 下有可直接复制的模板；也可以先 `lark-cli skills read lark-base` 查看 CLI 内置文档。

## License

[MIT](LICENSE) — 自由使用、修改、分发，保留出处即可。
