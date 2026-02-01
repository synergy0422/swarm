def cmd_up(args):
    """
    Launch tmux session with master + N workers.

    Uses subprocess to call tmux directly, avoiding libtmux API issues.
    """
    import subprocess

    cluster_id = args.cluster_id
    workers = args.workers
    session_name = f"swarm-{cluster_id}"

    # Check if session already exists
    result = subprocess.run(
        ['tmux', 'has-session', '-t', session_name],
        capture_output=True
    )
    if result.returncode == 0:
        print(f"[ERROR] Swarm session already exists: {session_name}", file=sys.stderr)
        print(f"[ERROR] Run 'swarm down --cluster-id {cluster_id}' first", file=sys.stderr)
        return 1

    # Ensure directory exists
    ai_swarm_dir = os.environ.get('AI_SWARM_DIR', '/tmp/ai_swarm')
    os.makedirs(ai_swarm_dir, exist_ok=True)

    print(f"[SWARM] Creating tmux session: {session_name}")

    try:
        # Create master window with master command
        master_cmd = f'python3 -m swarm.cli --cluster-id {cluster_id} master'
        subprocess.run([
            'tmux', 'new-session', '-d', '-s', session_name,
            '-n', 'master', '-x', '80', '-y', '24',
            master_cmd
        ], check=True)

        # Create worker windows
        for i in range(workers):
            worker_cmd = f'python3 -m swarm.cli --cluster-id {cluster_id} worker --id {i}'
            subprocess.run([
                'tmux', 'new-window', '-t', session_name,
                '-n', f'worker-{i}', worker_cmd
            ], check=True)

        print(f"\n[SWARM] Swarm session created: {session_name}")
        print(f"[SWARM] Master + {workers} workers launched")
        print(f"\n[SWARM] Attach to session:")
        print(f"[SWARM]   tmux attach -t {session_name}")
        print(f"\n[SWARM] Check status:")
        print(f"[SWARM]   python3 -m swarm.cli --cluster-id {cluster_id} status")
        print(f"\n[SWARM] Stop swarm:")
        print(f"[SWARM]   python3 -m swarm.cli --cluster-id {cluster_id} down")

        return 0

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to create tmux session: {e}", file=sys.stderr)
        print("[SWARM] Attempting cleanup...")
        cmd_down(args)
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to create session: {e}", file=sys.stderr)
        print("[SWARM] Attempting cleanup...")
        cmd_down(args)
        return 1
