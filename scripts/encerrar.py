from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
PID_FILE = RUNTIME_DIR / "processes.json"


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_process(name: str, pid: int) -> None:
    if not process_is_running(pid):
        print(f"ℹ️  {name} já estava encerrado.")
        return

    print(f"⏹️  Encerrando {name} (PID {pid})...")
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and process_is_running(pid):
        time.sleep(0.25)
    if process_is_running(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def stop_python_processes() -> None:
    if not PID_FILE.exists():
        print("ℹ️  Nenhum arquivo de processos encontrado.")
        return

    try:
        processes = json.loads(PID_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        processes = {}

    for name, info in processes.items():
        try:
            pid = int(info.get("pid", 0))
        except (AttributeError, TypeError, ValueError):
            continue
        stop_process(name, pid)

    PID_FILE.unlink(missing_ok=True)


def main() -> None:
    print("🛑 Encerrando estoque-medicamento-cdc...")
    stop_python_processes()

    result = subprocess.run(
        ["docker", "compose", "down", "--remove-orphans"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("Não foi possível encerrar os containers Docker.")
    print("✅ Sistema encerrado. Os volumes do Kafka e do Redis foram preservados.")


if __name__ == "__main__":
    main()
