# Phase 3: 共享状态系统 - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

实现状态广播协议、任务锁机制，让多个 Worker 之间协调状态、避免重复执行。

**交付物：**
- `status_broadcaster.py` — 状态日志写入模块
- `task_lock.py` — 任务锁机制（基于原子文件创建 + 心跳）
- 集成到现有 `task_queue.py`

**不在本阶段：**
- 广播通知机制（轮询/监听）- Claude 决定
- 复杂分布式事务 - 超出范围

</domain>

<decisions>
## Implementation Decisions

### 状态协议格式

- **格式：** JSON Lines（每行一个 JSON 对象）
- **字段：**
  - `state` (string, required) — 状态码：START/DONE/WAIT/ERROR/HELP/SKIP
  - `task_id` (string, required) — 任务唯一标识符
  - `timestamp` (string, required) — ISO 8601 格式时间戳（精确到毫秒）
  - `message` (string, optional) — 人类可读描述
  - `meta` (object, optional) — 扩展字段（如 error_type, retry_count, timeout_sec）

- **状态码固定：** START/DONE/WAIT/ERROR/HELP/SKIP — 不再细分
- **扩展方式：** 通过 `meta` 字段扩展，不改变基础格式

**示例：**
```jsonl
{"state": "START", "task_id": "task-123", "timestamp": "2026-01-31T12:00:00.000Z", "message": "开始执行"}
{"state": "DONE", "task_id": "task-123", "timestamp": "2026-01-31T12:00:05.000Z", "message": "执行完成"}
```

- **状态日志路径：** `/tmp/ai_swarm/status.log`（AI_SWARM_DIR 可覆盖）

### 锁粒度控制

- **锁粒度：** 每个任务独立锁（不是全局锁）
- **锁文件路径：** `/tmp/ai_swarm/locks/{task_id}.lock`
- **锁实现：** 原子文件创建（`open(..., O_CREAT|O_EXCL)`），不用 fcntl.flock 或 portalocker（避免环境差异）

**锁文件内容：**
```json
{
  "worker_id": "worker-1",
  "task_id": "task-123",
  "acquired_at": "2026-01-31T12:00:00.000Z",
  "heartbeat_at": "2026-01-31T12:00:10.000Z",
  "ttl": 300
}
```

- **锁竞争策略：**
  - 检查锁是否过期（基于 heartbeat_at + ttl）
  - 已过期：允许抢占（删除旧锁，创建新锁）
  - 未过期：快速失败返回 False，不阻塞等待

### 故障恢复机制

- **心跳机制：** Worker 持锁期间每 10 秒更新 `heartbeat_at`（原子写/rename）
- **TTL 配置：**
  - 默认：300 秒（5 分钟）
  - 可通过环境变量 `AI_SWARM_LOCK_TTL` 覆盖
- **过期检测：** `heartbeat_at + ttl < now()` 则认为锁已过期

- **锁清理策略：** 懒清理
  - 尝试获取锁时，发现过期就删除锁文件
  - 任何 Worker/Master 都可以清理过期锁并抢占
  - 系统自动恢复，不依赖原 Worker 复活

**锁获取伪代码：**
```python
def acquire_lock(task_id):
    lock_path = f"{LOCKS_DIR}/{task_id}.lock"
    if exists(lock_path):
        lock = read_json(lock_path)
        if is_expired(lock):
            delete(lock_path)  # 懒清理
        else:
            return False  # 锁被占用，未过期
    # 原子创建
    write_atomically(lock_path, new_lock_json)
    return True
```

</decisions>

<specifics>
## Specific Ideas

- "用 O_CREAT|O_EXCL 实现原子锁，避免 flock 环境差异"
- "TTL 过期后任何 Worker/Master 都可以抢占，系统自动恢复"
- "保留 meta 字段用于未来扩展，不破坏兼容"

</specifics>

<deferred>
## Deferred Ideas

- **广播通知机制** — Worker 如何感知状态变化（轮询/文件监听/事件）- Claude 决定实现方式
- **状态聚合视图** — Master 显示所有 Worker 状态汇总 — Phase 4 及以后

</deferred>

---

*Phase: 03-shared-state-system*
*Context gathered: 2026-01-31*
