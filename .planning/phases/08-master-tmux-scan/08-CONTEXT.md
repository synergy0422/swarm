# Phase 8: Master 集成 tmux 实时扫描 - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

在 Master 主循环中集成 pane 扫描能力：
- 使用 TmuxCollaboration.capture_all_windows() 捕获所有 worker 窗口内容
- 扩展 WaitDetector.detect_in_pane() 检测 "Press Enter" 模式
- 检测到模式后自动发送 Enter（30 秒冷却）
- tmux 不可用时静默跳过，不报错
- 保持现有 status.log 扫描逻辑不变

**不包括**：
- 扩展 AutoRescuer（保持独立，仅用于模式检测）
- 新增 [y/n] 自动确认（v1.1 仅 ENTER）
- Web 监控面板（后续版本）

</domain>

<decisions>
## Implementation Decisions

### 扫描频率
- **独立间隔策略**：Pane 扫描使用独立的 `pane_poll_interval`（默认 3 秒）
- **可配置性**：通过 Master 初始化参数或 CLI 参数配置
- **分离理由**：`capture-pane` 比 status.log 扫描更昂贵，独立间隔避免性能影响
- **默认行为**：status.log 仍使用 `poll_interval`（默认 1 秒），不改变

### 模式扩展
- **仅 ENTER 模式**：WaitDetector.detect_in_pane() 只检测「Press Enter」相关模式
- **检测模式列表**：
  - "press enter"
  - "press return"
  - "hit enter"
  - "回车继续"
  - "按回车"
- **不做**：[y/n] 确认模式、编辑器模式（vim/nano 等）
- **理由**：保持最保守策略，与 v1.0 AutoRescuer 原则一致

### 日志行为
- **最小日志原则**：每次 auto-enter 只打印一句话
- **日志格式**：`[Master] Auto-ENTER for {window_name}`
- **不做**：详细日志、时间戳、调试输出
- **理由**：减少 Master 日志噪音，保持简洁

### 动作节流
- **30 秒冷却机制**：同一窗口 30 秒内最多 auto-enter 1 次
- **实现方式**：WaitDetector 或 Master 维护窗口级别的 `last_auto_enter` 时间戳
- **理由**：避免重复操作可能带来的副作用，留出人工干预窗口

### tmux 不可用处理
- **静默降级**：捕获异常后跳过 pane 扫描，不报错
- **保持现有逻辑**：status.log 扫描继续工作，不受影响
- **异常类型**：libtmux 连接失败、session 不存在、窗口不存在等

</decisions>

<specifics>
## Specific Ideas

无特定引用或示例。采用标准实现方式：
- WaitDetector.detect_in_pane() 返回检测到的模式列表（目前只有 "enter"）
- Master._auto_enter() 执行实际发送 Enter 操作
- 冷却检查在 Master 主循环中实现

</specifics>

<deferred>
## Deferred Ideas

- [y/n] 自动确认模式 — Phase 待定（需要更安全的白名单机制）
- 编辑器自动补全（vim/nano/git commit）— 后续版本
- Web 实时监控面板 — v1.2 或后续版本
- SSH 跨机扫描 — 架构预留，暂不实现

</deferred>

---

*Phase: 08-master-tmux-scan*
*Context gathered: 2026-02-01*
