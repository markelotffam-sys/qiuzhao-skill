# Changelog

## 1.1.2 — 2026-10-19

Windows 适配（macOS/Linux 之外把 Windows 提为一等公民）：

- subprocess 显式 UTF-8 读取（修中文乱码/UnicodeDecodeError）；输出流统一 UTF-8（修 ✓⚠✗ 在 GBK 控制台崩溃）
- `find_lark_cli` 回退 `%APPDATA%\npm\lark-cli.cmd`，`.cmd` 经 `cmd /c` 执行
- 偏好分隔符支持 `,` `|` `>`（推荐逗号，避开 cmd 重定向）；文档示例改逗号
- README 新增 Windows 段落（`py -3`、`%USERPROFILE%`、PowerShell 用法）；heredoc 示例补 PowerShell 变体
- CI 新增 windows-latest job（compileall + 测试 + schema 校验）；新增 2 组 Windows 用例（共 13 项）

## 1.1.1 — 2026-10-19

可靠性修复（初始化从"能跑"到"稳"）：

- `setup.py` 更名 `bootstrap.py`；**幂等成立**：已有 config 自动续跑、新建 base 后立即写 config（中途失败可找回）
- 接入已有表补齐字段/选项（`--fix-fields`）；评分规则按 (模块,维度) 只补缺失，不重复写入、不覆盖已改权重
- 转化率口径修正：进过面 = 有面试记录或状态到达一面+（"面完被拒"不再误算未进面）；分母排除待投递/放弃
- 导出收紧权限（目录 700/文件 600）并明确"导出≠恢复"；overview 同时刻排序修复 + 未填/其他状态行
- 新增单元测试（11 项，含上述 bug 回归）；CI 跑 compileall + unittest + schema 校验
- README 补 Python 3.9+ 依赖；默认表行为说明对齐

## 1.1.0 — 2026-10-19

架构升级：**脚本做确定性，LLM 做判断**。

- 新增 `scripts/` 七个脚本：一键初始化（setup）、自检（init_check）、总览（overview）、旧数据迁移（migrate_backfill，默认预览）、备份导出（export_backup）、转化率复盘（conversion_report）、schema 校验（check_schema_sync，CI）
- 初始化从 7 步命令流收敛为「问 2 个偏好 + 跑 1 条脚本」，幂等可续跑（`--base-url` 接入已有表）
- 字段 schema 真正单一来源：脚本运行时解析 references，CI 校验可解析性
- 写入前预览原则：批量写入/删除/迁移先列变化再执行
- 反馈闭环（轻量版）：各优先级进面率/Offer率复盘，只呈现事实、不自动调参

## 1.0.7 — 2026-10-19

- 「未来 7 天」明确为**含今天共 7 天**（今天起至今天+6 的 23:59）
- 加 schema 一致性 CI（`scripts/check_schema_sync.py`）：自动比对 SKILL Step 1 与 references 表 1 的字段 JSON
- CHANGELOG 1.0.6 措辞修正（"可执行命令唯一来源"）

## 1.0.6 — 2026-10-19

- 「未来 7 天」明确为自然日口径（到今天+7 的 23:59）
- 旧数据迁移补翻页说明（`--offset` / ndjson）
- 可执行命令唯一来源（完整命令只在 SKILL Step 1）；字段 JSON 两处保留但加 CI 自动比对防漂移
- README FAQ 合并、.gitignore 精简

## 1.0.5 — 2026-10-19

- 初始化 Step 1 内嵌完整可执行命令（14 字段 JSON）
- 旧数据迁移：批量回填「最近更新」（map 形状、200 条/批）
- 已有表升级：缺失字段与 select 选项（如「三面」）的补齐路径
- DDL 规则完善：只知日期时写当天 23:59；DDL边界互斥

## 1.0.1 – 1.0.4 — 2026-10-19

早期迭代修复（字段结构、初始化流程、总览输出、记录定位、文档一致性若干），细节已并入 1.0.5+。

## 1.0.0 — 2026-10-19

首个公开版（实测于 lark-cli 1.0.96）：

- 六表数据结构（投递记录/简历库/个人信息/评分规则/Offer评估/面试记录）+ 可执行字段 schema
- 自举初始化：自动建 base → 建表 → 收集偏好 → 生成评分档位（13 行规则）→ 7 组件看板 → 校验
- 评分双轨（匹配分/策略分）、P0/P1/P2 优先级排序、Offer 注水检测、面试复盘闭环
- 总览固定输出模板；配置外置 `~/.config/qiuzhao/config.json`；MIT License
