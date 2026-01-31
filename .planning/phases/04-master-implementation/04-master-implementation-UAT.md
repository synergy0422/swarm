---
status: testing
phase: 04-master-implementation
source: 04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md
started: 2026-01-31T14:10:07Z
updated: 2026-01-31T14:15:00Z
---

## Current Test

number: 2
name: Worker mailbox isolation
expected: |
  Worker 只能消费自己的 {worker_id}.jsonl mailbox

  验证方式：
  - Worker 初始化时设置 self.mailbox_path = instructions/{worker_id}.jsonl
  - poll_for_instructions() 只读取自己的 mailbox 文件
  - poll_for_instructions() 记录 offset 避免重复执行
  - 收到指令后调用 _verify_task_lock() 验证锁所有权
  - 锁验证失败时 broadcast SKIP 并跳过执行

  测试场景：task 分配给 worker-1，worker-2 的 mailbox 应该为空或不存在
awaiting: user response

## Tests

### 1. Master uses MasterDispatcher with mailbox
expected: Master 主循环使用 MasterDispatcher（而不是旧 TaskDispatcher）dispatch_one() 成功后会：1. acquire_lock 成功后写入 mailbox (instructions/{worker_id}.jsonl) 2. 更新 tasks.json 为 ASSIGNED（带 assigned_worker_id） 3. 广播 ASSIGNED（meta 含 worker_id）检查方式：- swarm/master.py 中的 self.dispatcher 是 MasterDispatcher 实例- MasterDispatcher.dispatch_one() 包含 _write_to_mailbox() 调用- MasterDispatcher.dispatch_one() 包含 _update_task_status() 调用
result: pass
note: Fixed - Master now uses MasterDispatcher, old TaskDispatcher removed. Integration tests pass (4/4).

### 2. Worker mailbox isolation
expected: Worker 只能消费自己的 {worker_id}.jsonl mailbox验证方式：- Worker 初始化时设置 self.mailbox_path = instructions/{worker_id}.jsonl- poll_for_instructions() 只读取自己的 mailbox 文件- poll_for_instructions() 记录 offset 避免重复执行- 收到指令后调用 _verify_task_lock() 验证锁所有权- 锁验证失败时 broadcast SKIP 并跳过执行测试场景：task 分配给 worker-1，worker-2 的 mailbox 应该为空或不存在
result: pending

### 3. Integration smoke test
expected: 最小集成测试：启动 master，模拟 2 workers，投递 1 个 task，断言 instructions/{worker_id}.jsonl 被写入，另一个 worker mailbox 不会收到
result: pending

## Summary

total: 3
passed: 1
issues: 0
pending: 2
skipped: 0

## Gaps

[none yet]
