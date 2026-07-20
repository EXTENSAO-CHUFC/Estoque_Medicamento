from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PID_FILE = PROJECT_ROOT / ".runtime" / "processes.json"


def running(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> None:
    subprocess.run(["docker", "compose", "ps"], cwd=PROJECT_ROOT, check=False)
    print("\nProcessos Python:")
    if not PID_FILE.exists():
        print("  nenhum registrado")
        return
    try:
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("  arquivo de PID inválido")
        return
    for name, info in data.items():
        pid = int(info.get("pid", 0))
        state = "rodando" if running(pid) else "parado"
        print(f"  {name}: {state} (PID {pid}) — {info.get('log', '')}")


if __name__ == "__main__":
    main()
