# Plan: Phase 23 - 快照脚本实现

**Created:** 2026-02-03
**Wave:** 1
**Depends On:** None
**Files Modified:**
- `scripts/swarm_snapshot.sh`
- `README.md`
- `docs/SCRIPTS.md`

## Objective

实现 `scripts/swarm_snapshot.sh` 脚本，一键采集 tmux swarm 运行状态并输出到时间戳目录。脚本为只读操作，不创建/修改任何状态文件。

## Implementation Context

@.planning/PROJECT.md (core value, current milestone)
@.planning/REQUIREMENTS.md (SNAP-01 ~ SNAP-09, DOCS-01, DOCS-02)
@.planning/phases/23-snapshot-script/CONTEXT.md (implementation decisions)

**Reference pattern:** scripts/swarm_selfcheck.sh (set -euo pipefail, usage function, _common.sh sourcing)

## Output Directory Structure

```
<snapshot_dir>/
  tmux/
    structure.txt      # sessions, windows, panes info
  panes/
    <session>.<window>.<pane>.txt  # each pane output with prefix
  state/
    status.log         # copy of status.log (if exists)
  locks/
    list.txt           # lock directory listing (if exists)
  meta/
    git.txt            # git status, branch, dirty state
    summary.txt        # snapshot overview and error summary
```

**Critical Constraints (must_haves):**
- [ ] **只读操作**: 禁止对 `$SWARM_STATE_DIR` 执行任何写入（mkdir, cp, rm 等）
- [ ] 状态文件复制：从 `$SWARM_STATE_DIR/status.log` **只读复制**到快照目录的 `state/`
- [ ] 锁目录读取：仅执行 `ls -la` 读取列表，**禁止写操作**

## Output Directory Conflict Resolution

**策略：** 如果 `--out` 指定且目录存在，自动追加 `_YYYYmmdd_HHMMSS` 后缀

```bash
if [[ -d "$SNAPSHOT_DIR" ]]; then
    SNAPSHOT_DIR="${SNAPSHOT_DIR}_$(date +%Y%m%d_%H%M%S)"
fi
```

## Error Handling

- 部分失败继续执行（非阻塞）
- 所有错误收集到 ERRORS 数组
- **Summary 格式** (`meta/summary.txt`):
  ```text
  Snapshot: /path/to/snapshot_<timestamp>
  Session: swarm-claude-default
  Panes: 5
  Time: 2026-02-03 15:30:45

  Files:
  - tmux/structure.txt
  - panes/*.txt
  ...

  Errors:
  - [15:30:42] tmux: session 'invalid-session' not found
  ```

## Tasks

<task type="auto">
  <name>Create swarm_snapshot.sh with argument parsing</name>
  <files>scripts/swarm_snapshot.sh</files>
  <action>
    Create scripts/swarm_snapshot.sh with:

    1. **Shebang and error handling:** `#!/bin/bash` + `set -euo pipefail`

    2. **Source _common.sh:**
       ```bash
       SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
       source "$SCRIPT_DIR/_common.sh"
       ```

    3. **Argument parsing** (while loop with case):
       - `--session, -s`: Override SESSION_NAME (default from _common.sh)
       - `--lines, -n`: SNAPSHOT_LINES (default 50)
       - `--out, -o`: SNAPSHOT_DIR (default /tmp/ai_swarm_snapshot_<timestamp>)
       - `--help, -h`: Show usage and exit 0

    4. **Usage function** (cat <<EOF format):
       - Synopsis with examples
       - Options table
       - Output directory structure

    5. **Variable initialization:**
       - SNAPSHOT_LINES default 50
       - SNAPSHOT_DIR with auto-increment: if --out exists, append `_YYYYmmdd_HHMMSS`
       - ERRORS array for error collection
       - declare -a ERRORS=()

    6. **Skeleton functions** (to be filled):
       - `check_tmux_session()` - verify session exists (read-only)
       - `dump_tmux_structure()` - save structure.txt for specified session only
       - `dump_pane_output()` - save panes/*.txt
       - `dump_state_files()` - READ-ONLY copy status.log to snapshot
       - `dump_locks()` - READ-ONLY ls to list.txt
       - `dump_git_info()` - save meta/git.txt
       - `generate_summary()` - create meta/summary.txt with Errors section
       - `main()` - orchestrate all functions
  </action>
  <verify>File exists with correct structure: head -60 scripts/swarm_snapshot.sh</verify>
  <done>Script skeleton created with all functions stubbed and argument parsing working</done>
</task>

<task type="auto">
  <name>Implement core snapshot functions</name>
  <files>scripts/swarm_snapshot.sh</files>
  <action>
    Implement all snapshot functions in scripts/swarm_snapshot.sh:

    1. **check_tmux_session():**
       - Use `tmux list-sessions -F '#{session_name}'` to verify session exists
       - Return error if session not found (add to ERRORS array)
       - **只读操作**

    2. **dump_tmux_structure():**
       - 仅采集指定 session（`$SESSION_NAME`）的结构
       - `tmux list-windows -t "$SESSION_NAME" -F '#{window_index}: #{window_name}'`
       - For each window: `tmux list-panes -t "$SESSION_NAME:window_index" -F '#{pane_index}: #{pane_title}'`
       - Save to `$SNAPSHOT_DIR/tmux/structure.txt`
       - **只读操作**

    3. **dump_pane_output():**
       - Loop all panes in specified session using `tmux list-panes -t "$SESSION_NAME"`
       - For each pane: `tmux capture-pane -p -t "$SESSION_NAME:$win.$pane"`
       - Add prefix to each line: `[${SESSION_NAME}:${win}.${pane}] <content>`
       - Save to `$SNAPSHOT_DIR/panes/${SESSION_NAME}.${win}.${pane}.txt`
       - Limit to last N lines using `tail -n $SNAPSHOT_LINES`
       - **只读操作**

    4. **dump_state_files():**
       - Check if `$SWARM_STATE_DIR/status.log` exists
       - If exists: `cp "$SWARM_STATE_DIR/status.log" "$SNAPSHOT_DIR/state/status.log"`
       - If not: mark as "NOT FOUND" (will be in summary)
       - **只读复制到快照目录，禁止对 SWARM_STATE_DIR 写操作**

    5. **dump_locks():**
       - Check if `$SWARM_STATE_DIR/locks/` exists
       - If exists: `ls -la "$SWARM_STATE_DIR/locks/" > "$SNAPSHOT_DIR/locks/list.txt"`
       - If not: mark as "NOT FOUND" (will be in summary)
       - **只读列出，禁止写操作**

    6. **dump_git_info():**
       - `git rev-parse --short HEAD` (commit SHA)
       - `git rev-parse --abbrev-ref HEAD` (branch)
       - `git status --porcelain` (dirty state)
       - Save to `$SNAPSHOT_DIR/meta/git.txt`
       - **只读操作**

    7. **Error collection:**
       - Every function captures errors to ERRORS array
       - Continue on partial failure (non-blocking)
       - Pattern: `ERRORS+=("[$(date +%H:%M:%S)] Error description")`
  </action>
  <verify>All functions implemented, script runs without syntax errors</verify>
  <done>Core snapshot functions complete and functional</done>
</task>

<task type="auto">
  <name>Implement summary generation and main orchestration</name>
  <files>scripts/swarm_snapshot.sh</files>
  <action>
    Complete scripts/swarm_snapshot.sh:

    1. **generate_summary():**
       Create `$SNAPSHOT_DIR/meta/summary.txt` with format:
       ```
       Snapshot: /path/to/snapshot_<timestamp>
       Session: swarm-claude-default
       Panes: 5
       Time: 2026-02-03 15:30:45

       Files:
       - tmux/structure.txt
       - panes/*.txt
       - state/status.log (if exists)
       - locks/list.txt (if exists)
       - meta/git.txt
       - meta/summary.txt

       Errors:
       - [15:30:42] tmux: session 'xxx' not found
       - [15:30:43] status.log: NOT FOUND
       ```
       - If no errors: omit Errors section or show "Errors: none"

    2. **main() function:**
       - Parse arguments
       - Create output directory: `mkdir -p "$SNAPSHOT_DIR/{tmux,panes,state,locks,meta}"`
       - Check tmux session exists
       - Run all dump_* functions (collect errors, don't fail)
       - Generate summary
       - Print output directory path to stdout
       - Print error count: "Errors: N"

    3. **Execute main:**
       - `main "$@"` at end of script

    4. **Make executable:**
       - `chmod +x scripts/swarm_snapshot.sh`

    5. **must_haves validation:**
       - Verify no write operations to `$SWARM_STATE_DIR`
       - Verify errors are collected in ERRORS array
       - Verify summary.txt has proper format with Errors section
  </action>
  <verify>Script runs end-to-end, creates snapshot with all expected files</verify>
  <done>Summary generation and main orchestration complete</done>
</task>

<task type="auto">
  <name>Update README.md with diagnostic snapshot section</name>
  <files>README.md</files>
  <action>
    Add "诊断快照" (Diagnostic Snapshot) section to README.md in appropriate location:

    1. **Find insertion point:** Look for "使用说明" (Usage) or "脚本索引" (Script Index) sections
    2. **Insert before/after the most relevant section**

    ```markdown
    ## 诊断快照

    v1.8 引入了诊断快照功能，用于采集 tmux swarm 运行状态进行诊断分析。

    ### 使用方法

    ```bash
    # 基本用法（采集默认会话）
    ./scripts/swarm_snapshot.sh

    # 指定会话名称
    ./scripts/swarm_snapshot.sh --session my-session

    # 自定义输出行数（默认 50）
    ./scripts/swarm_snapshot.sh --lines 100

    # 自定义输出目录
    ./scripts/swarm_snapshot.sh --out /path/to/snapshot
    ```

    ### 参数说明

    | 参数 | 说明 |
    |------|------|
    | `--session, -s` | tmux 会话名称 |
    | `--lines, -n` | 每个窗格捕获的行数（默认 50） |
    | `--out, -o` | 输出目录（默认 /tmp/ai_swarm_snapshot_<timestamp>） |
    | `--help, -h` | 显示帮助信息 |

    ### 输出内容

    快照会创建以下目录结构：
    ```
    <snapshot_dir>/
      tmux/           # tmux 结构信息
      panes/          # 各窗格输出（带 session:window.pane 前缀）
      state/          # 状态文件
      locks/          # 锁目录列表
      meta/           # git 信息和摘要
    ```

    **注意：** 快照脚本为只读操作，不会修改任何状态文件。
    ```

    3. **Update Script Index section** to add swarm_snapshot.sh entry.
  </action>
  <verify>README.md contains new section, script index updated</verify>
  <done>README.md updated with diagnostic snapshot documentation</done>
</task>

<task type="auto">
  <name>Update docs/SCRIPTS.md with swarm_snapshot.sh documentation</name>
  <files>docs/SCRIPTS.md</files>
  <action>
    Add swarm_snapshot.sh documentation to docs/SCRIPTS.md:

    1. Add "诊断快照脚本" header after "系统工具脚本" section (before "实用脚本")

    2. Include documentation with:
       - **用途：** 一键采集 tmux swarm 运行状态用于诊断
       - **参数表格：** --session, --lines, --out, --help
       - **环境变量：** CLAUDE_SESSION, SNAPSHOT_LINES, SNAPSHOT_DIR
       - **示例：** Basic usage, custom session, custom lines, custom output
       - **高级用法：** Error handling notes, output structure explanation
       - **只读约束：** 不会修改 SWARM_STATE_DIR 中任何文件
       - **依赖：** _common.sh, tmux

    3. Update script dependency diagram to include swarm_snapshot.sh
  </action>
  <verify>docs/SCRIPTS.md contains swarm_snapshot.sh documentation</verify>
  <done>docs/SCRIPTS.md updated with complete swarm_snapshot.sh documentation</done>
</task>

## Verification

Run these commands to verify implementation:

```bash
# 1. Script is executable
test -x scripts/swarm_snapshot.sh

# 2. Help works
./scripts/swarm_snapshot.sh --help

# 3. Script runs without errors (create empty tmux session first if needed)
# tmux new-session -d -s test-session
# ./scripts/swarm_snapshot.sh --session test-session
# ls -la /tmp/ai_swarm_snapshot_*/

# 4. Verify output structure
# cat <snapshot_dir>/meta/summary.txt
# cat <snapshot_dir>/tmux/structure.txt
# ls <snapshot_dir>/panes/

# 5. README updated
# grep -c "诊断快照" README.md

# 6. SCRIPTS.md updated
# grep -c "swarm_snapshot.sh" docs/SCRIPTS.md

# 7. Verify read-only constraint (no writes to SWARM_STATE_DIR)
# strace -f -e trace=open,openat,mkdir,cp ./scripts/swarm_snapshot.sh 2>&1 | grep /tmp/ai_swarm
```

## Success Criteria

- [ ] `scripts/swarm_snapshot.sh` created with `--session`, `--lines`, `--out` arguments
- [ ] `tmux/` directory contains session/window/pane structure info (specified session only)
- [ ] `panes/` directory contains pane output with `[session:window.pane]` prefix
- [ ] `state/` directory contains status.log copy (if exists)
- [ ] `locks/` directory contains lock list (if exists)
- [ ] `meta/` directory contains git.txt and summary.txt
- [ ] **只读操作:** 禁止对 `$SWARM_STATE_DIR` 执行任何写操作
- [ ] **错误摘要:** summary.txt 包含 Errors: 段落
- [ ] **目录冲突:** 自动追加 `_YYYYmmdd_HHMMSS` 后缀
- [ ] README.md has new "诊断快照" section
- [ ] docs/SCRIPTS.md has swarm_snapshot.sh documentation

## Output

After completion, create `.planning/phases/23-snapshot-script/23-SUMMARY.md`
