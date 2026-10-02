# cline-pilot

**Agent 技能：把 Cline CLI 当作用户的代理来调度编码任务。**

拆解任务下发 → 非交互/交互两种模式驱动 Cline → 读会话文件 + 硬证据（git/测试报告）监控进度 →
决策点按固定四要素格式转达用户拍板 → 验收清单全绿才报完成——同时在过程中
**按项目标签学习用户的指令偏好与推进习惯，逐渐代替用户做决策**。

遵循 [Agent Skills 开放规范](https://agentskills.io/specification)。
适用于任何支持该标准的 agent：Hermes、Cline、Claude Code、Codex、Cursor、OpenCode 等。
(English docs: [README.md](README.md))

## 它做什么 / 不做什么

| 做（本技能职责） | 不做 |
|---|---|
| 把用户任务准确转达给 Cline CLI（背景 + 约束一条不丢） | 掌握项目架构细节（那归工程自己的 memory bank + clinerules） |
| 在用户指定开发环境内启动 Cline（conda 环境、固定任务分支） | 擅自做技术决策——硬约束动作永远先回用户 |
| 用会话文件 + `git`/测试报告硬证据监控后台长任务，不信自述 | push、删文件、写库、花钱、改全局配置——一律先问 |
| 决策点按四要素格式转达，附已学偏好或注明"无先例" | |
| 按 6 项验收清单全绿才报"完成" | |
| 把每次纠偏/拍板**按项目标签类**记录，逐步蒸馏稳定偏好 | |

## 安装

```bash
# 方式一：npx skills CLI（通用）
npx skills add https://github.com/gongdear/cline-pilot

# 方式二：复制技能目录到对应 agent 的技能目录
#   Hermes:    ~/.hermes/skills/
#   Cline:     ~/.cline/skills/
#   Claude Code: ~/.claude/skills/
#   Codex:     ~/.codex/skills/
mkdir -p ~/.hermes/skills && cp -r cline-pilot ~/.hermes/skills/
```

## 快速开始

1. **首次使用**：agent 会问你要开发环境三件事（python/conda 环境名、工具链怎么到
   PATH、任务分支命名）并写入 `references/local-config.md`
   （模板见 `references/local-config.example.md`）。该文件**私有**，已被 git 忽略。
2. **下达编码任务**：针对 Cline CLI 的任何编码任务。技能自动激活，选模式、注入
   prompt（首句固定 `active memory bank`）、后台运行、用
   `scripts/session_report.py` 盯进度。
3. **验证**：
   ```bash
   python3 scripts/session_report.py 15 /path/to/repo
   ```

## 目录结构（渐进披露）

```
cline-pilot/
├── SKILL.md                          # 核心工作流（<150 行，激活时整体加载）
├── README.md / README.zh.md
├── LICENSE                           # MIT
├── scripts/
│   └── session_report.py             # 只读监控：会话消息 + git/surefire 硬证据（stdlib only，双语注释）
├── references/
│   ├── cold-start.md                 # 冷启动手册（新工程：无 clinerules/memory-bank 时）
│   ├── local-config.example.md       # 模板 → 私有的 local-config.md
│   ├── project-profiles.example.md   # 模板 → 私有的 project-profiles.md
│   └── decision-log.example.md       # 模板 → 私有的 decision-log.md
└── assets/
    └── global-memory-bank-prompt.md  # 全局 memory-bank 提示词（逐字模板，开启任何 memory bank 前的前置核）
```

`SKILL.md` 仅在激活时加载；`references/*` 按需读取；脚本是确定性代码——
agent 不必每次即兴发挥监控逻辑。

## 设计原则

- **冷启动前置核**——任何 memory bank 开启前，全局必须已有默认 memory-bank 提示词
  （`assets/global-memory-bank-prompt.md`，逐字模板）
- **新工程分两路**——无代码：规则逐维度问用户后落盘；有存量代码：以扫描代码为基准落文件
- **技能里不记架构**——项目技术事实归工程自己的 memory bank / clinerules；
  本技能只存简介 + 标签 + 已学偏好
- **确定性优先**——凡是"每次都必须对"的步骤，用脚本而非让模型每次现编
- **证据优先**——完成与否由 git status、测试报告数字、产物非空来证明，
  不由 agent 自述证明
- **学习回路**——纠偏 → `decision-log.md`（按标签类）→ 同标签类 ≥2 个一致样本
  → 蒸馏进 SKILL.md 的偏好区
- **隐私分层**——公开文件（SKILL.md、scripts、example 模板）零用户秘密；
  私有状态留在被 git 忽略的 `references/*.md`

## 最佳实践：双档模型策略

Cline 在**冷启动**和**常态执行**两个阶段的最优模型选择差异极大。推荐配置（维护者在生产级多模块后端上验证过）：

1. **初始化——用长上下文能力强的（付费）模型。**
   把重量级工作一次性做完：全工程代码扫描、基于代码实际行为撰写项目规则
   （`clinerules` / memory-bank 种子），并写出 1-2 个**模板级代码/测试**
   （断言风格、Mock 粒度、命名、边界覆盖的示范样板）。该阶段读多写少、
   长上下文档档密集——正是前沿模型的付费价值所在。一次高质量冷启动可以
   省掉后续大部分返工：之后每个批次都被它写下的规则约束着执行。

2. **常态执行——切换为本地小参数量模型逐任务循环。**
   规则与模板就位后，每个批次都是小粒度明确指令（目标类、测试文件路径、
   任务书含 Mock 清单、断言要求）的受限任务。这种任务形态对本地小模型
   极其友好（约 30B 量级的开源模型即可；维护者本地跑 Qwen 系构建 via Ollama）：
   粒度铁律 + 防幻觉协议 + 批次级核证承担纪律，模型质量即可与成本/隐私/吞吐做权衡。

经验法则：**前沿模型一次性买断规则，本地模型天天跑纪律。**
本地批次同一断言连续 3 次失败，说明模板/规则有缺口——把**该批次**
升级回强模型重做，不要继续烧本地重试。

## 校验

```bash
npx @anthropics/skills-ref validate .   # 或：skills-ref validate ./cline-pilot
python3 -m py_compile scripts/session_report.py
python3 scripts/session_report.py 5 /path/to/repo
```

## 贡献

- 新坑 / 新模式 → 直接提 PR 改 `SKILL.md`（保持 <500 行）
- 新脚本 → 放 `scripts/`，stdlib only，可独立运行
- 遵循规范：https://agentskills.io/specification

## 许可

MIT — 见 [LICENSE](LICENSE)
