#!/usr/bin/env python3
"""
AI Swarm 启动脚本 - WSL 兼容版本

在 WSL2 环境中，tmux 服务器无法在后台持久运行。
此脚本使用替代方案来运行 swarm。

用法:
    ./run_swarm.sh start     # 启动集群（前台运行）
    ./run_swarm.sh status    # 查看状态
    ./run_swarm.sh stop      # 停止集群
"""

import argparse
import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# 默认配置
DEFAULT_CLUSTER = "default"
DEFAULT_WORKERS = 3

# cc-switch 代理配置
CC_SWITCH_URL = "http://127.0.0.1:15721"


def ensure_dir():
    """确保数据目录存在"""
    swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
    os.makedirs(swarm_dir, exist_ok=True)
    return swarm_dir


def cmd_start(args):
    """启动集群（在前台运行 master，workers 在后台）"""
    cluster = args.cluster or DEFAULT_CLUSTER
    workers = args.workers
    swarm_dir = ensure_dir()

    print(f"[SWARM] 启动集群: {cluster}, workers: {workers}")
    print(f"[SWARM] 数据目录: {swarm_dir}")

    # 检查 cc-switch 代理
    llm_base_url = os.environ.get('LLM_BASE_URL', '')
    if llm_base_url:
        print(f"[SWARM] cc-switch 代理: {llm_base_url}")
    else:
        print(f"[SWARM] 注意: 未检测到 LLM_BASE_URL")
        print(f"[SWARM]       如需使用 cc-switch，请设置: export LLM_BASE_URL={CC_SWITCH_URL}")

    print()
    print("[提示] 按 Ctrl+C 停止集群")
    print()

    # 启动 master
    from swarm.master import Master

    master = Master()

    # 启动 workers（后台进程）
    worker_procs = []
    for i in range(workers):
        print(f"[SWARM] 启动 worker-{i}...")
        env = os.environ.copy()
        env['AI_SWARM_DIR'] = swarm_dir
        env['SWARM_CLUSTER_ID'] = cluster

        # 如果设置了 LLM_BASE_URL，转发给 worker
        if llm_base_url:
            env['LLM_BASE_URL'] = llm_base_url

        proc = subprocess.Popen(
            [sys.executable, '-m', 'swarm.cli', 'worker', '--id', str(i)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        worker_procs.append(proc)
        time.sleep(0.5)

    print()
    print(f"[SWARM] Master 和 {workers} workers 已启动")
    print()

    try:
        # 运行 master（这会阻塞）
        print("[SWARM] Master 运行中...")
        master.run()
    except KeyboardInterrupt:
        print("\n[SWARM] 正在停止集群...")
    finally:
        # 停止 workers
        for proc in worker_procs:
            proc.terminate()
            proc.wait(timeout=5)

        print("[SWARM] 集群已停止")


def cmd_status(args):
    """查看状态"""
    cluster = args.cluster or DEFAULT_CLUSTER
    swarm_dir = ensure_dir()

    print(f"[SWARM] 集群: {cluster}")
    print(f"[SWARM] 数据目录: {swarm_dir}")

    # 检查状态日志
    status_log = f"{swarm_dir}/status.log"
    if os.path.exists(status_log):
        print("\n[状态日志]")
        with open(status_log, 'r') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line.strip())
    else:
        print("\n[状态] 暂无状态日志")


def cmd_stop(args):
    """停止集群"""
    cluster = args.cluster or DEFAULT_CLUSTER
    print(f"[SWARM] 停止集群: {cluster}")
    print("[提示] 在 WSL 环境中，需要手动停止进程")
    print("       使用: pkill -f 'swarm.cli'")


def main():
    parser = argparse.ArgumentParser(
        description='AI Swarm 控制脚本 (WSL 兼容版)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    sub = parser.add_subparsers(dest='command', help='可用命令')

    # start 命令
    p_start = sub.add_parser('start', help='启动集群')
    p_start.add_argument('--cluster', '-c', help='集群 ID (默认: default)')
    p_start.add_argument('--workers', '-w', type=int, default=DEFAULT_WORKERS,
                         help=f'worker 数量 (默认: {DEFAULT_WORKERS})')

    # status 命令
    p_status = sub.add_parser('status', help='查看状态')
    p_status.add_argument('--cluster', '-c', help='集群 ID (默认: default)')

    # stop 命令
    p_stop = sub.add_parser('stop', help='停止集群')
    p_stop.add_argument('--cluster', '-c', help='集群 ID (默认: default)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print()
        print("示例:")
        print("  ./run_swarm.sh start           # 启动集群 (3 workers)")
        print("  ./run_swarm.sh start -w 5      # 启动 5 workers")
        print("  ./run_swarm.sh status          # 查看状态")
        print("  ./run_swarm.sh stop            # 停止集群")
        return 0

    commands = {
        'start': cmd_start,
        'status': cmd_status,
        'stop': cmd_stop,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
