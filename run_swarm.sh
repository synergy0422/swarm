#!/usr/bin/env python3
"""
AI Swarm 启动脚本

环境要求:
    导出 LLM_BASE_URL (使用本地代理时):
        export LLM_BASE_URL="http://127.0.0.1:15721"
        export ANTHROPIC_API_KEY="dummy"  # 可选，占位即可

用法:
    ./run_swarm.sh up        # 启动集群 (默认 3 workers)
    ./run_swarm.sh up --workers 5  # 启动 5 workers
    ./run_swarm.sh status    # 查看状态
    ./run_swarm.sh down      # 停止集群
    ./run_swarm.sh attach    # 进入 tmux 会话
    ./run_swarm.sh logs      # 查看 master 日志
"""

import argparse
import subprocess
import sys
import os

# 默认配置
DEFAULT_CLUSTER = "default"
DEFAULT_WORKERS = 3


def get_cluster_id():
    """获取当前集群 ID（支持手动设置或自动检测）"""
    return os.environ.get('SWARM_CLUSTER_ID', DEFAULT_CLUSTER)


def cmd_up(args):
    """启动集群"""
    cluster = args.cluster or get_cluster_id()
    workers = args.workers

    print(f"[SWARM] 启动集群: {cluster}, workers: {workers}")

    # 检查是否已存在
    result = subprocess.run(
        ['tmux', 'has-session', '-t', f'swarm-{cluster}'],
        capture_output=True
    )
    if result.returncode == 0:
        print(f"[ERROR] 集群已存在: {cluster}")
        print(f"        使用: swarm down --cluster-id {cluster}")
        return 1

    # 确保目录存在
    swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
    os.makedirs(swarm_dir, exist_ok=True)

    # 启动
    cmd = ['python3', '-m', 'swarm.cli', 'up', '--cluster-id', cluster, '--workers', str(workers)]
    print(f"[RUN] {' '.join(cmd)}")
    os.execvp('python3', cmd)


def cmd_down(args):
    """停止集群"""
    cluster = args.cluster or get_cluster_id()
    cmd = ['python3', '-m', 'swarm.cli', 'down', '--cluster-id', cluster]
    print(f"[RUN] {' '.join(cmd)}")
    os.execvp('python3', cmd)


def cmd_status(args):
    """查看状态"""
    cluster = args.cluster or get_cluster_id()
    cmd = ['python3', '-m', 'swarm.cli', 'status', '--cluster-id', cluster]
    print(f"[RUN] {' '.join(cmd)}")
    os.execvp('python3', cmd)


def cmd_attach(args):
    """进入 tmux 会话"""
    cluster = args.cluster or get_cluster_id()
    session = f'swarm-{cluster}'

    # 检查会话是否存在
    result = subprocess.run(
        ['tmux', 'has-session', '-t', session],
        capture_output=True
    )
    if result.returncode != 0:
        print(f"[ERROR] 会话不存在: {session}")
        print(f"        先运行: ./run_swarm.sh up")
        return 1

    print(f"[SWARM] 进入 tmux 会话: {session}")
    print("[提示] 退出 tmux: Ctrl+b 然后按 d")
    print()
    os.execvp('tmux', ['tmux', 'attach-session', '-t', session])


def cmd_logs(args):
    """查看日志"""
    cluster = args.cluster or get_cluster_id()
    swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')

    # 尝试多种日志位置
    log_paths = [
        f'{swarm_dir}/{cluster}/status.log',
        f'{swarm_dir}/status.log',
        '/tmp/ai_swarm/status.log',
    ]

    log_found = False
    for log_path in log_paths:
        if os.path.exists(log_path):
            print(f"[日志] {log_path}")
            print("-" * 60)
            subprocess.run(['tail', '-n', '50', log_path])
            log_found = True
            break

    if not log_found:
        print("[INFO] 暂无日志文件")
        print(f"       AI_SWARM_DIR: {swarm_dir}")
        print(f"       集群目录: {swarm_dir}/{cluster}")


def cmd_clean():
    """清理 tmux 会话和临时文件"""
    cluster = get_cluster_id()
    session = f'swarm-{cluster}'

    # 杀掉 tmux 会话
    result = subprocess.run(
        ['tmux', 'kill-session', '-t', session],
        capture_output=True
    )
    if result.returncode == 0:
        print(f"[CLEAN] tmux 会话已清理: {session}")
    else:
        print(f"[INFO] 无需清理或会话不存在: {session}")

    # 清理目录
    swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
    cluster_dir = f'{swarm_dir}/{cluster}'
    if os.path.exists(cluster_dir):
        import shutil
        shutil.rmtree(cluster_dir)
        print(f"[CLEAN] 目录已清理: {cluster_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='AI Swarm 控制脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    sub = parser.add_subparsers(dest='command', help='可用命令')

    # up 命令
    p_up = sub.add_parser('up', help='启动集群')
    p_up.add_argument('--cluster', '-c', help='集群 ID (默认: default)')
    p_up.add_argument('--workers', '-w', type=int, default=DEFAULT_WORKERS,
                      help=f'worker 数量 (默认: {DEFAULT_WORKERS})')

    # down 命令
    p_down = sub.add_parser('down', help='停止集群')
    p_down.add_argument('--cluster', '-c', help='集群 ID (默认: default)')

    # status 命令
    p_status = sub.add_parser('status', help='查看状态')
    p_status.add_argument('--cluster', '-c', help='集群 ID (默认: default)')

    # attach 命令
    p_attach = sub.add_parser('attach', help='进入 tmux 会话')
    p_attach.add_argument('--cluster', '-c', help='集群 ID (默认: default)')

    # logs 命令
    p_logs = sub.add_parser('logs', help='查看日志')
    p_logs.add_argument('--cluster', '-c', help='集群 ID (默认: default)')

    # clean 命令
    sub.add_parser('clean', help='清理 tmux 会话和临时文件')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print()
        print("示例:")
        print("  ./run_swarm.sh up              # 启动默认集群 (3 workers)")
        print("  ./run_swarm.sh up -w 5         # 启动 5 workers")
        print("  ./run_swarm.sh up -c mycluster # 启动指定集群")
        print("  ./run_swarm.sh status          # 查看状态")
        print("  ./run_swarm.sh attach          # 进入 tmux 会话")
        print("  ./run_swarm.sh logs            # 查看日志")
        print("  ./run_swarm.sh down            # 停止集群")
        print("  ./run_swarm.sh clean           # 清理")
        return 0

    # 执行命令
    commands = {
        'up': cmd_up,
        'down': cmd_down,
        'status': cmd_status,
        'attach': cmd_attach,
        'logs': cmd_logs,
        'clean': cmd_clean,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
