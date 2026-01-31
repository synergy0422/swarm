# Phase 5: CLI 与启动脚本 - Context

**Gathered:** 2026-01-31
**Status:** Ready for implementation

<domain>
## Phase Boundary

实现 CLI 命令和启动脚本，为现有 swarm 组件（Phase 1-4）提供统一入口和一键启动能力。

**包含：**
- CLI 入口点（swarm 命令及其子命令）
- 启动编排逻辑（tmux session 创建、组件启动顺序）
- 配置管理（flags、环境变量、默认值）

**不包含：**
- 新的 swarm 协调逻辑（已在 Phase 1-4 完成）
- Worker 进程管理增强（每个 worker 独立进程即可）
- 集中式日志收集/旋转（后续阶段）
- Web 界面

</domain>

<decisions>
## Implementation Decisions

### 1. CLI 入口设计

**单一命令：`swarm`**
- Python package entry point
- 仓库内也可直接调用：`python -m swarm.cli ...`

**子命令：**
- `swarm init` - 检查依赖（tmux、libtmux）、打印环境变量提示、创建 AI_SWARM_DIR 目录结构
- `swarm up` - 一键启动 tmux 集群（master + N workers）
- `swarm master` - 仅启动 master（调试用）
- `swarm worker --id <n>` - 仅启动单个 worker（调试用）
- `swarm down` - 关闭 tmux session（按 cluster_id）
- `swarm status` - 打印当前 session/agents 状态（读 tmux + status.log）

**调用方式：**
- 主入口：swarm.cli 模块
- 仓库内：`python -m swarm.cli ...`
- 后续可加 console_scripts（setup.py/pyproject.toml）

**使用 argparse**（轻依赖，避免 typer）

### 2. 启动编排

**`swarm up` 启动顺序：**
1. **preflight** - 检查 tmux/libtmux、检查 API key 环境变量存在（只提示，不阻塞）
2. **创建/复用 tmux session** - `swarm-<cluster_id>`
3. **启动 master pane** - 先启动 master
4. **启动 N 个 worker panes** - 默认 3 个
5. **输出 attach 提示** - `tmux attach -t swarm-<cluster_id>`

**失败处理：**
- 任何步骤失败，打印清晰错误
- 尝试 `swarm down` 清理本次 session（best-effort）
- 不留下僵尸 session

### 3. 配置方式与优先级

**优先级：** CLI flags > 环境变量 > 默认值

**必需配置：**
- `--cluster-id`（默认 `default`）
- `--workers`（默认 `3`）

**目录：**
- `AI_SWARM_DIR` env（默认 `/tmp/ai_swarm`）

**API key：**
- 只读环境变量（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`）
- CLI 不接收 key 参数（避免泄露到 shell history）

**可选配置：**
- `--auto-enter`（仅允许 Press ENTER 自动回车，默认 `false`）
- **永不默认 yes**（安全原则）

### 4. Worker 隔离与可见性

**进程隔离：**
- 每个 worker 一个 tmux pane + 一个 Python 进程

**日志可见性：**
- pane 里直接输出（用户可看到实时日志）
- status.log 作为机器状态（供 master 读取）

**不做：**
- 集中式 log 收集/旋转（后续阶段）

### 5. 交付物

**代码：**
- `swarm/cli.py` - CLI 入口（argparse，轻依赖）

**脚本：**
- `scripts/swarm_up.sh` - 可选 shell 辅助（主入口仍是 `swarm up`）

**文档：**
- README 增加 5 行 usage：
  - `swarm init` - 初始化环境
  - `swarm up` - 启动集群
  - `tmux attach -t swarm-<cluster_id>` - 连接到集群
  - `swarm status` - 查看状态
  - `swarm down` - 关闭集群

### 6. 技术约束

**依赖最小化：**
- 使用 argparse（避免 typer/_click 等重量级依赖）
- 复用 Phase 1-4 已有模块
- 不引入新的运行时依赖

**不新增 swarm 逻辑：**
- 只做包装与启动脚本
- 协调逻辑已在 Phase 4 完成
- Worker 逻辑已在 Phase 3 完成

</decisions>

<specifics>
## Specific Ideas

- "保持简单，就像 docker-compose 或 kubectl 的感觉"
- "swarm up 应该是一条命令解决所有问题"
- "调试命令 master/worker 是为了开发方便，生产主要用 up"
- "README 要 5 行搞定，让用户 10 秒内会跑"

</specifics>

<deferred>
## Deferred Ideas

- 集中式日志收集与旋转 — 后续阶段
- Web 状态面板 — 后续阶段
- 跨机 SSH 支持 — 后续阶段
- 进程守护与自动重启 — 后续阶段
- 配置文件支持（~/.swarmrc） — 后续阶段

</deferred>

---
*Phase: 05-cli-startup*
*Context gathered: 2026-01-31*
