from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PID_FILE = PROJECT_ROOT / ".runtime" / "processes.json"


def running(pid: int) -> bool:
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


def connector_status() -> None:
    print("\nConector Debezium:")
    try:
        response = requests.get(
            "http://localhost:8083/connectors/estoque-postgres-connector/status",
            timeout=3,
        )
        response.raise_for_status()
        data = response.json()
        connector = data.get("connector", {}).get("state", "DESCONHECIDO")
        tasks = ", ".join(
            str(task.get("state", "DESCONHECIDO"))
            for task in data.get("tasks", [])
        ) or "sem tasks"
        print(f"  connector: {connector}")
        print(f"  tasks: {tasks}")
    except Exception as exc:
        print(f"  indisponível: {exc}")


def main() -> None:
    subprocess.run(
        ["docker", "compose", "ps"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    connector_status()

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
