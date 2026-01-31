# Phase 4: Master 实现 - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

实现 Master 扫描、自动救援、任务分配，让 Master 能够监控 Worker 状态、检测卡点并安全处理。

**交付物：**
- `swarm/master_scanner.py` — 定期扫描 worker 状态和任务锁
- `swarm/auto_rescuer.py` — 检测 WAIT 模式，保守处理自动确认
- `swarm/master_dispatcher.py` — 任务分配给空闲 worker
- 集成测试覆盖

**不在本阶段：**
- 复杂负载均衡策略
- 自动 yes 模式（AI_SWARM_AUTO_YES）
- 跨网络分布式协作

</domain>

<decisions>
## Implementation Decisions

### 1. 扫描策略

- **扫描频率：** 主循环 1 秒一次
  - 可配置：`AI_SWARM_POLL_INTERVAL`（默认 1.0）
  - Master 主循环使用 1s 间隔

- **数据来源优先级：**
  1. `status.log`（JSONL）— 权威状态来源
     - 记录任务开始/完成/等待/错误等状态变更
  2. `tmux capture-pane` — 仅用于 WAIT 交互卡点检测
     - status.log 可能没及时写入，所以需要实时捕获

- **扫描内容：**
  1. 每个 Worker 的最新状态（status.log 最后一条）
  2. 每个 Task 的锁状态（是否过期/是否完成）
  3. 每个 Pane 最近 N 行输出（N=50）— 用于检测 WAIT 模式

### 2. 等待模式检测（WAIT Detection）

**只检测"明显在等待输入"的模式，按优先级：**

**交互确认类（优先级 1）：**
- `[y/n]`, `[Y/n]`, `(y/n)`, `y or n`（大小写都匹配）

**回车继续类（优先级 2）：**
- `Press ENTER`
- `Press Return`
- `hit enter`
- `按回车`
- `回车继续`
- `Press any key to continue`

**确认提示类（优先级 3）：**
- `confirm`
- `are you sure`
- `确认`
- `确定吗`

**检测逻辑：**
- 只看 **最新输出的末尾 20 行**
- 必须在 **最近 30 秒内出现**（避免历史残留误判）

### 3. 自动确认策略（保守原则）

**默认行为：不自动确认**
- Master 只记录 WAIT 状态
- 写入 status.log: `{"state": "HELP", "task_id": "...", "message": "Waiting for user input"}`
- 通知/报警给用户

**安全白名单（可自动确认）：**
- 场景：纯交互继续提示（如 "Press ENTER to continue"）
- 输入：直接发送回车（Enter）

**永不自动输入：**
- `y` / `yes` / `Y` / `YES`
- 只有显式配置 `AI_SWARM_AUTO_YES=1` 才支持（MVP 不支持此配置）

**黑名单关键词（出现即禁止自动操作，只上报 HELP）：**
- `delete`, `remove`, `rm -rf`, `format`, `overwrite`
- `drop database`, `drop table`
- `kill`, `terminate`
- `sudo`, `password`, `token`, `ssh`, `key`
- `生产`, `prod`

### 4. 任务分配机制

**Worker 空闲判定：**
- 状态为 `DONE` / `SKIP` / `ERROR` **且** 无持有锁
- 或心跳存在但无 active task

**分配算法（最简单 FIFO）：**
1. 从 `tasks.json` 队列头部开始
2. 取第一个未锁定的任务
3. 尝试抢占 `locks/{task_id}.lock`
4. 抢到锁 → 分配成功，更新任务状态为 `ASSIGNED`
5. 抢不到锁 → 跳下一个任务

**避免重复分配：**
- 必须先抢到锁才算分配成功
- 锁机制确保同一任务只被一个 Worker 执行

**负载均衡：**
- MVP 不做复杂策略
- 3 个 Worker 足够并行
- 后续可加"按耗时/队列长度"策略

### 配置项（环境变量）

所有配置通过环境变量，默认值安全优先：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `AI_SWARM_POLL_INTERVAL` | 1.0 | Master 扫描频率（秒） |
| `AI_SWARM_AUTO_YES` | （不支持） | MVP 不支持自动 yes |
| `AI_SWARM_LOCK_TTL` | 300 | 锁超时（秒），复用在 Phase 3 |
| `AI_SWARM_DIR` | /tmp/ai_swarm | 数据目录，复用在 Phase 1 |

</decisions>

<specifics>
## Specific Ideas

- "主脑=Master，3 个 worker"
- "status.log 作为权威状态，tmux capture 仅用于 WAIT 检测"
- "只检测末尾 20 行，最近 30s 内出现"
- "默认不自动确认，只记录 HELP 并通知用户"
- "最简单 FIFO 分配，抢锁成功才算"
- "黑名单关键词出现即禁止自动操作"

</specifics>

<deferred>
## Deferred Ideas

- **AI_SWARM_AUTO_YES 模式** — 后续 Phase 再支持
- **复杂负载均衡** — 按耗时/队列长度分配，MVP 不做
- **Web 状态面板** — Phase 2 增强功能
- **跨机 SSH 扩展** — 预留接口，Phase 2 增强

</deferred>

---

*Phase: 04-master-implementation*
*Context gathered: 2026-01-31*
