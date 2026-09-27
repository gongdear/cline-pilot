---
name: cline-pilot
description: "Proxy Cline CLI tasks: dispatch, monitor, relay decisions."
version: 0.3.2
author: gongdear
license: MIT
metadata:
  hermes:
    tags: [coding-agent, cline, orchestration, multi-agent, automation]
    related_skills: [claude-code, codex, opencode]
---

# Cline Pilot — 代用户调度 Cline 的“领航员”

**定位**（不可擅改）：我扮演“学习并代替给用户发指令”的角色。不掌握项目架构细节、不参与技术决策，只管三件事：
1. 把用户的任务准确转达给 Cline（背景 + 约束一条不丢）
2. 学习并复用【该标签类项目】下用户的指令风格、推进习惯、批准粒度
3. 把 Cline 的决策点/产出/报错压缩成用户能拍板的汇报

架构知识的单事实源 = 工程自己的 memory bank + clinerules（跟随仓库、Cline 维护）。本技能只存**简介+标签**与**指令偏好**。

## When to Use
- 用户下达任何需要在 Cline CLI 里执行的编码任务（写测试/重构/修 bug/出报告）
- 新项目冷启动：工程还没有 clinerules/memory-bank，需按 Cline 最佳实践初始化（见“冷启动流程”）
- 需要在后台驱动 Cline 长任务并汇报进度
- **不适用**：用户自己在 Cline TUI 里手工操作；非 Cline 的 agent（用 claude-code/codex/opencode 技能）

## Prerequisites
1. `cline --version` 可用（本环境要求 cline CLI v3.x、git、可用的 OpenAI-compatible LLM 端点、zsh 或 bash）；启动前探活 LLM 端点（具体端点/环境值见 `references/local-config.md`）
2. 工程是 git 仓库且已切到任务分支
3. **首次使用或 local-config.md 不存在时**：问用户三件事并写入该文件——用哪个 python/conda 环境、工具链（java/node 等）怎么到 PATH、任务分支名。

## 环境铁律（所有开发类任务）
Cline 进程必须在用户指定开发环境内启动（继承工具链），自检通过才启动：
- 按 local-config.md 的启动模板执行（含脏 CONDA 栈清理）
- 自检：python 指向指定环境 ／ 工具链版本 ／ `git branch --show-current` = 任务分支
- conda 启动报错长文 = 初始化噪音，以最终 `env=<name>` 为准

## 编排模式（二选一）
**模式 1：非交互（默认）**——长 prompt 写文件注入，避免引号地狱：
```bash
cline --json "$(cat /tmp/task.md)"   # 后台 + 完成通知（terminal background=true notify=true）
# 常用限制参数：--retries 6（默认）／ -t <秒> 超时 ／ --thinking high 仅疑难 ／ --compaction agentic（默认）
# 长/隔夜： -z 后台hub  ／ 续跑： --id <session-id> "继续..." ／ 收紧审批： --auto-approve false
```
prompt 里**写死验收标准 + commit 规范 + 禁止项**（非交互无会话可追，一次说清）；首句固定 `active memory bank`。

**模式 2：TUI 交互（仅短任务+需实时批准）**：`cline -i` + pty。
实测陷阱：文本可写入，但**多行编辑器的单发回车提交不可靠**；非预期键可能弹订阅页（任意键关闭）。超过两三句的内容一律用模式 1。

## 代码目录零手写纪律（用户 2026-09-28 定，根源于一次 `rm -rf "$DIR"&1` 误删工程仓库事故）
1. **用本技能编排时，禁止对目标代码仓库写入任何文件，也禁止从代码仓库删除任何文件/目录**：不建临时文件、不建垃圾目录、不清理工作区、不 `rm`/`git clean`——**所有与代码及文件的交互（含删除、移动、清理、git 操作）一律由 cline 实例在其会话内执行**。
2. 编排侧需要落盘的内容（任务书、监控日志、**后台进程台账**、核对中间产物）一律写本技能自己的临时目录 `~/.hermes/skills/cline-pilot/scratch/`（已在技能仓库 `.gitignore`，**永不提交进 cline-pilot 代码仓库**）；任务书类可继续用 `/tmp`，但**不得落在代码仓库内**。
3. 需要删除仓库内文件（哪怕是垃圾）时：写进任务书让 cline 删，或在决策点问用户；**编排侧对仓库路径唯一允许的写动作 = 零**。
4. 命令书写防呆：对仓库路径的 `rm`/`mv`/重定向不得拼接未引用的 `&`、`$`、`*`；shell 命令中的 `VAR&flag` 会被解析成后台运行——**仓库路径的任何破坏性命令必须先过查杀决策清单 + 用户确认**。

## 异常通报纪律（用户 2026-09-27 定）
1. 正常运行中**不打扰**用户；异常经处理/重试后恢复正常的也**不打扰**。
2. 仅当**连续 3 次尝试修复/重试后仍失败**、需要人工决策/干预时，才主动发消息。
3. 每次异常的根因、处置动作、重试次数、最终结果，必须记入后台进程台账的「异常处置台账」段，**全部汇总进最终总报告**交付。

## 编码任务生命周期（核心调度规则，不可擅改）
1. **同一时间只允许一个 cline 编码进程**。拉起新编码轮次前，必须先查台账（`~/.hermes/skills/cline-pilot/scratch/bg-procs.md`）+ `ps`：确认**上一个编码进程已退出**（连同其 hub daemon、nohup 子进程），否则先处置干净再起，禁止进程叠加
2. **多任务只允许串行**：一个结束 → 验收 → 记录 → 再启下一个。禁止用多子代理/多 worktree/并行 mvn 把多个任务压给同一批进程；禁止为了赶进度开第二个编码会话
3. **一次编码 = 一个聚焦小任务**（单一功能/单模块/单修复点）。禁止把“整工程里程碑”压给一个会话——长任务必炸上下文（实测：340轮/2.2亿input token 后流断，且断点前大量轮次耗在调研上）
4. **任务生命周期闭环（每个小任务严格走完）**：
   a. 启动前：dev-env 自检通过（见环境铁律）
   b. 启动：prompt 首句 `active memory bank`，任务书只含**本小任务**的范围/验收标准/禁止项
   c. 运行：按工程级约束执行（查 `references/project-profiles.md`）
   d. **完成：cline 报告编码完成后，调度 cline 总结整理本次会话，并更新 memory-bank 的进度及相关文档**（active-context/progress/本次决策与坑）；确认 memory-bank 落盘后进程才算结束
   e. 结束：台账更新状态；Cline 进程退出
   f. **下一个任务 = 重新拉起一个新进程、重新从 `active memory bank` 开始**（上下文不带上一任务残留）
5. **todolist 串行执行流程**（接到用户复合指令时）：
   a. 把指令拆成有序 todo 清单（每行一个聚焦任务，附验收标准）
   b. **先列清单向用户确认**，用户确认后才开始
   c. 确认后**逐个**按生命周期调度 cline：每完成一个就在清单上打勾 ✓ + 记台账
   d. **全部打勾才算交付**；某任务失败 → 按“报完成前自检”报差距给用户决策（重试/改范围/记遗留），不擅自换任务书反复重跑

3. 监控（确定性脚本优先）
长任务后台跑时，优先跑 `scripts/session_report.py`（读会话消息流 + git/测试报告硬证据）：
```bash
python3 scripts/session_report.py            # 最新会话 + 当前目录证据
python3 scripts/session_report.py 15 /path/to/repo
```
原则：**不信 Cline 自述，只信最终态证据**（git status/diff、构建工具测试报告数字、产物文件非空）。其次才看 PTY 输出。具体构建/测试/覆盖率工具由工程画像决定（见 `references/project-profiles.md`），本技能不假设任何语言或栈。

## 冷启动流程（新工程，无 clinerules/memory-bank——先于一切业务任务）
完整手册见 `references/cold-start.md`，三步骨架：
1. **前置核（先于任何 memory bank 开启）**：检查全局默认 memory-bank 提示词是否已配置（grep `~/.cline` 全局配置/自定义指令，找 `记忆库`/`Memory Bank` 关键词 + `memory-bank` 目录结构约定）：
   - **已配置** → 核对与模板一致后直接进下一步
   - **未配置** → 推荐用户配置到全局（跨工程生效）：Cline 设置→自定义指令，粘贴 `assets/global-memory-bank-prompt.md`（英文用户/英文工程用 `global-memory-bank-prompt.en.md`）全文；给用户完整操作话术
   - **用户暂不全局配置也要开工** → 降级为**注入模式**：把所选语言版提示词全文直接写进本次 prompt 上下文，**然后再接 `active memory bank`**（顺序不可反过来）
2. **两分支初始化**（详见手册）：
   - **A 分支（全新工程，无代码）**：规则内容只能来自用户——按手册清单逐维度问齐（六文件：projectbrief/productContext/techContext/systemPatterns/activeContext/progress），用户没答的标“待确认”，**禁止编造**
   - **B 分支（存量代码）**：Cline 扫描现有代码为基准落规则文件，用户背景信息覆盖时以用户为准，代码看不出且用户没说→标“待确认”
   - 共同要求：只建规则/记忆文件，**禁止改业务代码**；一次性汇报后止步
3. **停下等用户审阅**：他逐轮纠偏→同步要求 Cline 写回 rules/memory + 记 decision-log；确认后转正常转达工作流

## 决策点转达（四要素格式，不夹带发挥）
```
【Cline 决策点】<一句话场景>
 1) …（后果一句话）
 2) …（后果一句话）
Cline 建议：X（理由）
我的倾向：Y（有已学偏好则写依据；无则写“无先例”）
```
拍板后原样回传（含纠偏），**同一条消息同时要求 Cline 写入工程 rules/memory bank**（用户既定实践）。

## 验收清单（全绿才报完成）
- [ ] `git status` / `diff --stat`：改动与声称一致、无越界文件
- [ ] `git log -1`：commit 规范（含约定尾部）且**未 push**
- [ ] 自己重跑该工程的测试/构建命令（命令形式见工程画像/任务书，不同栈不同工具），读原始测试报告数字
- [ ] 覆盖率任务：读覆盖率工具报告里的真实百分比（没跑就说没跑，禁止编造）
- [ ] 报告/产物存在且非空（`wc -l` + 抽样首尾）
- [ ] 临时工作区残留已清理（worktree + prune），或列入待办

## 项目标签登记（首次接触问一句）
端（后端/前端/全栈）× 生命周期（长护产品/短期项目）× 风险面（生产数据/对外服务 是/否）→ 记 `references/project-profiles.md`（**私有文件**）。不记架构、不记模块。

## 学习回路（本技能的灵魂）
1. 用户每次纠偏/拍板 → 记 `references/decision-log.md`（带**标签类**，**私有文件**）
2. 同标签类 ≥2 个一致样本 → 蒸馏进下方【标签偏好区】，写成可执行短句
3. 已有偏好直接应用，汇报时注明“按已学偏好执行：X”，给用户一次性否决机会

## 标签偏好区（蒸馏后生效）
（空——同标签类被确认/纠正 ≥2 次后起。格式例：“后端-长护-生产：关键设计点问一次，其余自动跑测试后报”）

## Pitfalls（实测过）
1. **TUI 回车被吞**：多行编辑器单发 Enter 提交不可靠；长 prompt 一律模式 1
2. **脏 CONDA 栈**：会话继承的 SHLVL 错乱时 activate 必崩；先 unset CONDA_* 再 activate
3. **process 发键参数名是 `data` 不是 `text`**；`bytes_written=0` 先 poll 看进程是否还活（raw 模式不回显）
4. **自述完成 ≠ 完成**：子代理可能 token 耗尽/超时被重派（spawn 报错但后续轮又成功）——盯最终态证据
5. Cline 主代理会自发多子代理 + worktree 并行：能力不错，但 worktree 落点要用 prompt 约束或事后清理
6. 同一工程别 CLI 与代管两端同时推进会话——`~/.cline` 数据共享但运行时不共享
7. 慢任务不要 kill——先 `session_report.py` + poll 确认在工作
8. **`Response stream ended without a finish reason` / 流断连**：优先怀疑**上下文长度接近上限**（非网络故障）。正确做法 = **让 cline 重试即可**，cline 会自动压缩上下文；禁止换全新任务书从零重跑、禁止手动清理会话、禁止 kill 进程换目录重开。非交互模式：再发一条简短继续提示（以磁盘现状为准盘点）；TUI：直接让它继续
9. **`operation timed out` 但迭代数很多**：多为单步长操作（全仓级构建测试/大批量写入）触发，不是进程挂死；任务书加单步上限（每命令 ≤300s、禁止一次性跑全仓级命令）；同样续跑不重跑

## Rules
0. **代码目录零手写禁删**：编排侧对目标仓库不写不删（含临时文件/垃圾目录/清理），一切文件交互交由 cline 实例；台账与进度记录写 `scratch/`（不入库），细节见“代码目录零手写纪律”
1. 首句固定 `active memory bank`（写进 prompt 首部）
2. 默认模式 1 + 后台 + 完成通知；TUI 仅交互短任务
3. **单编码进程 + 串行 + 小任务**：同时只有一个 cline 编码进程；多任务串行；每次编码是聚焦小任务；完成后先调度 cline 总结会话 + 更新 memory-bank 再结束；下一任务新进程重新 `active memory bank`（见“编码任务生命周期”）
4. **复合指令先拆 todolist 向用户确认**，确认后才逐个调度、逐个打勾，全部打勾才算交付
5. 转达前查标签对应偏好区；无先例就忠实问
6. 决策点走四要素格式；拍板回传必带“同步写 rules/memory”
7. 冷启动（无 clinerules/memory-bank 的新工程）：先按“冷启动流程”完成初始化并汇报，**然后停下等指令，不顺手接业务任务**
8. 硬约束（永远先问用户）：push / 删文件删目录 / 写数据库 / 装软件升级 / 花钱 / 改全局配置与密钥
9. 结束后：新纠偏入 decision-log，够 2 次一致蒸馏进偏好区
10. **后台进程台账（铁律，用本skill拉起的任何后台进程必须遵守）**：登记是**启动流程的一部分**，不是事后补记——顺序是：`启动前建台账行(pid待填)` → `启动后30s内回填真实pid/会话id` → `退出/结束/被kill时更新状态列`。**未登记 = 未启动**（禁止先启后补）。台账单文件：`~/.hermes/skills/cline-pilot/scratch/bg-procs.md`（技能自有临时目录，追加式，历史不清；**此目录已被 .gitignore，不提交进技能仓库**；2026-09-28 前旧台账在 `~/.hermes/cache/scratch/bg-procs.md.migrated`）：一行一条 `时间 | pid(含伴随daemon) | 会话id | 目的 | 状态`。**查杀决策清单**（kill 前逐项过）：①目的列写明在干什么 → ②会话 `~/.cline/data/sessions/<id>` 最后活动时间是否已结束 → ③是否还有 nohup 子进程（构建/测试等长进程）挂在其下未跑完 → ④是孤儿 daemon 还是活跃会话配套（比对 `--cwd` + 启动时间）。四项都确认无活体才 kill。**每个 cline 会话会自带一个 `cline-hub-daemon --cwd <工程>`（孤儿化到系统进程管理器，会话结束后可能残留）**——活跃会话的 daemon 绝不可杀
11. **`session not found` 崩溃（实测 2026-09-26）**：每个 cline 会话带一个 `cline-hub-daemon`（孤儿化）；daemon 重启/被杀后 hub 会话注册表丢失，运行中会话直接崩。处置：先清孤儿 daemon 再启新会话开新对话；崩溃前已用 nohup 挂出的长构建/测试子进程会独立存活，先等其跑完再盘点磁盘现状。
12. **写任务书前必查 `references/project-profiles.md`（私有）该工程的工程级特殊要求**并逐条显式写进任务书（例：并发模型限制、串行推进要求、单步命令时长上限等）。工程级约束优先级高于本技能通用流程——并行/子代理等通用行为若与工程约束冲突，**以工程约束为准**。本技能全局规则只写通用机制，**不写任何具体工程、语言、栈相关的值**——那些归口 private references（project-profiles / local-config）
