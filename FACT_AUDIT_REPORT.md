# 事实审计报告（截至 2026-02-07）

## 1. 架构一致性结论

1. `tmux` 形态与目标“2 window”基本一致。`scripts/swarm_layout_5.sh` 明确是 `codex-master` + `workers` 两窗布局（`scripts/swarm_layout_5.sh:6`），现场也确有 `swarm-claude-default` 的 `%1/%2/%3/%4` Claude pane。  
2. 但“可验证闭环”与目标不一致。当前没有常驻 `swarm.cli master/worker` 或 `swarm.claude_bridge` 进程（现场 `ps` 结果为空），`/tmp/ai_swarm/tasks.json` 全部 `pending`（27 条）。  
3. 结论：拓扑一致，闭环不成立。当前更像“bridge 扫描 + pane 注入尝试”，不是稳定的 `captured -> dispatched -> acked -> done` 生产闭环。

## 2. 宣称修复 vs 代码状态 vs 运行证据（三方对照）

1. Master 派发竞态/原子更新/回滚  
- 宣称：已修复  
- 代码：存在（`swarm/master_dispatcher.py:278`, `swarm/master_dispatcher.py:453`, `swarm/master_dispatcher.py:379`）  
- 运行证据：当前主链路未见 `master/worker` 常驻进程，无法证明这条修复在用户实际路径生效  
- 标签：未证实（代码已实现）

2. mailbox 写入顺序与 ASSIGNED 回滚  
- 宣称：已修复  
- 代码：存在（同文件 `swarm/master_dispatcher.py`）  
- 运行证据：`tasks.json` 全 `pending`，`instructions/` 空，当前场景未走该链路  
- 标签：未证实（代码已实现）

3. worker mailbox offset 持久化  
- 宣称：已修复  
- 代码：存在（`swarm/worker_smart.py:88`, `swarm/worker_smart.py:106`, `swarm/worker_smart.py:464`）  
- 运行证据：相关单测通过；但当前主问题链路不是 mailbox 闭环  
- 标签：已证实（局部）

4. FIFO ACK 语义增强（非写入即 ACK）  
- 宣称：已修复  
- 代码：存在（`swarm/claude_bridge.py:1000`, `swarm/claude_bridge.py:1066`, `swarm/fifo_input.py:216`）  
- 运行证据：现场 `bridge.log` 仅 `CAPTURED/PARSED`，无 `DISPATCHED/ACKED`；未看到该语义在用户路径完成闭环  
- 标签：未证实（代码已实现）

5. tmux scan 兼容（`send_enter`）  
- 宣称：已修复  
- 代码：存在（`swarm/master.py:218`）  
- 运行证据：与当前 bridge 主阻塞无直接闭环证据  
- 标签：未证实（与当前问题弱相关）

6. “v1.93 E2E A/B/C VERIFIED / Phase4 COMPLETE”  
- 宣称：已完成（`.planning/STATE.md:17`, `.planning/milestones/v1.93/04-E2E_ACCEPTANCE-SUMMARY.md:196`）  
- 代码/脚本：`scripts/swarm_e2e_v193.sh` 存在  
- 运行证据：现场重跑 A/B 均失败；A 显示 `Result: FAIL`（`/tmp/ai_swarm_e2e_v193/evidence/scenario_a_evidence.txt:724`）；B 终端失败且 evidence 缺失结果段（脚本在 `set -euo pipefail` 下有提前退出风险，见 `scripts/swarm_e2e_v193.sh:2`, `scripts/swarm_e2e_v193.sh:345`, `scripts/swarm_e2e_v193.sh:358`）  
- 标签：与证据冲突

7. “bridge/status 与窗口行为一致可追踪”  
- 脚本统计依赖无空格 JSON 模式（`"phase":"CAPTURED"`），见 `scripts/swarm_e2e_v193.sh:140`, `scripts/swarm_e2e_v193.sh:309`, `scripts/swarm_e2e_v193.sh:345`  
- 实际日志是 `json.dumps` 默认带空格（如 `{"phase": "CAPTURED"}`，见 `/tmp/ai_swarm_e2e_v193/evidence/scenario_a_evidence.txt:7`）  
- 导致脚本报“not found/0”，但日志实际有大量 BRIDGE 行（`/tmp/ai_swarm/status.log:1`）  
- 标签：已证实（观测链路失真）

## 3. 当前主阻塞问题（按严重度）

1. `S0` 验收与观测失真：E2E 脚本统计规则与实际 JSON 格式不匹配，导致“全 0/未找到”假结论。  
2. `S0` 闭环核心缺失：当前运行证据中 `bridge.log` 只有 `CAPTURED/PARSED`（1766 行中 `CAPTURED=1, PARSED=1765`），无 `DISPATCHED/ACKED`。  
3. `S1` 重复解析/噪声风暴：`PARSED` 大量重复，说明扫描与去重链路未形成可验证闭环（见 `swarm/claude_bridge.py:1219` 起）。  
4. `S1` 任务可追踪性不足：`status.log` 中 BRIDGE 条目的 `bridge_task_id` 全为 `null`（1766 条），不满足链路追踪要求。  
5. `S1` 重复派发迹象：同一 `bridge_task_id` 出现在多个 worker pane，见 `/tmp/ai_swarm_e2e_v193/evidence/pane_dup_report.txt:3`。  
6. `S2` 运行路径漂移：文档大量以 `master/worker` 闭环描述，但现场主要是 bridge+pane 行为，造成“报告通过/现场异常”长期不一致。

## 4. 明确标签汇总

1. 已证实  
- E2E 统计与真实日志不一致  
- A/B 现场复现失败  
- 重复 PARSED、无 ACKED  
- 跨 worker 重复 ID 现象

2. 未证实  
- 竞态修复、回滚、mailbox 顺序等在“当前用户链路”是否真正生效  
- FIFO ACK 语义是否在当前链路端到端成立

3. 与证据冲突  
- “Phase4 COMPLETE / A/B/C VERIFIED” 与当前现场复现结果冲突

## 5. 证据不足（不下结论）

1. `Unknown skill: task`：本次在仓库、`/tmp/ai_swarm`、`/tmp/ai_swarm_e2e_v193` 未检出该字符串；当前仅能标记为证据不足。  
2. “bridge/status 与窗口行为不一致”的历史发生频次：已复现该类冲突，但频次与分布证据不足。

---

## What changed

1. 未改动仓库代码。  
2. 将审计报告落地到项目根目录：`FACT_AUDIT_REPORT.md`。

## Why this is correct

1. 结论均绑定了代码行或证据文件行。  
2. 不把“单测通过”替代为“现场闭环成立”。

## Tests run

1. `python3 -m pytest tests/test_master_dispatcher.py -q` -> `27 passed`  
2. `python3 -m pytest tests/test_worker_smart.py::TestMailboxOffsetPersistence -q` -> `7 passed`  
3. `python3 -m pytest tests/test_claude_bridge.py -q` -> `96 passed`  
4. `python3 -m pytest --tb=no -q` -> `375 passed`  
5. `AI_SWARM_BRIDGE_PANE=%1 ./scripts/swarm_e2e_v193.sh A` -> `FAIL`  
6. `AI_SWARM_BRIDGE_PANE=%1 ./scripts/swarm_e2e_v193.sh B` -> `FAIL`

## Risks / residual gaps

1. 现场会话是动态系统，pane 缓冲会变化；审计结论基于当前时点快照（2026-02-07）。  
2. 历史证据文件可能被后续脚本覆盖，需保留只读快照策略才可长期比对。

## Rollback or recovery note

1. 本次无仓库代码修改，无需回滚。
