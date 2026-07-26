from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
LOG_DIR = RUNTIME_DIR / "logs"
PID_FILE = RUNTIME_DIR / "processes.json"


def print_step(message: str) -> None:
    print(message, flush=True)


def run(command: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        check=check,
        text=True,
    )


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def ensure_prerequisites() -> None:
    if not command_exists("docker"):
        raise RuntimeError("Docker não foi encontrado no PATH.")

    result = subprocess.run(
        ["docker", "compose", "version"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError("Docker Compose v2 não está disponível. Use 'docker compose'.")

    result = subprocess.run(
        ["docker", "info"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError("O Docker Desktop/daemon não está em execução.")


def copy_if_missing(target: Path, example: Path) -> None:
    if target.exists():
        return
    if not example.exists():
        raise FileNotFoundError(f"Arquivo de exemplo ausente: {example}")
    shutil.copyfile(example, target)
    print_step(f"📝 Criado {target.relative_to(PROJECT_ROOT)} a partir do exemplo.")


def ensure_configuration() -> None:
    copy_if_missing(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.example")
    copy_if_missing(
        PROJECT_ROOT / "infra" / "debezium" / "connector.env",
        PROJECT_ROOT / "infra" / "debezium" / "connector.env.example",
    )


def read_simple_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def wait_for_port(host: str, port: int, description: str, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"{description} não respondeu em {host}:{port} após {timeout}s.")


def validate_oltp_connection() -> None:
    connector_env = read_simple_env(PROJECT_ROOT / "infra" / "debezium" / "connector.env")
    configured_host = connector_env.get("OLTP_HOST", "host.docker.internal")
    host_for_host_os = "127.0.0.1" if configured_host == "host.docker.internal" else configured_host
    port = int(connector_env.get("OLTP_PORT", "5434"))
    print_step(f"🔎 Verificando PostgreSQL OLTP em {host_for_host_os}:{port}...")
    wait_for_port(host_for_host_os, port, "PostgreSQL OLTP", timeout=10)


def start_background(name: str, command: Sequence[str]) -> dict[str, object]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{name}.log"
    log_handle = log_path.open("a", encoding="utf-8")

    kwargs: dict[str, object] = {
        "cwd": PROJECT_ROOT,
        "stdin": subprocess.DEVNULL,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "text": True,
    }

    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True

    process = subprocess.Popen(list(command), **kwargs)
    log_handle.close()
    time.sleep(1)

    if process.poll() is not None:
        tail = ""
        try:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        except OSError:
            pass
        raise RuntimeError(f"{name} encerrou durante a inicialização.\n{tail}")

    return {
        "pid": process.pid,
        "command": list(command),
        "log": str(log_path.relative_to(PROJECT_ROOT)),
    }


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


def load_existing_processes() -> dict[str, dict[str, object]]:
    if not PID_FILE.exists():
        return {}
    try:
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {
        name: info
        for name, info in data.items()
        if isinstance(info, dict) and process_is_running(int(info.get("pid", 0)))
    }


def start_application_processes() -> dict[str, dict[str, object]]:
    existing = load_existing_processes()
    processes: dict[str, dict[str, object]] = dict(existing)

    commands = {
        "consumer": [sys.executable, "-m", "app.consumers.analytics_consumer"],
        "dashboard": [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/dashboard/dashboard.py",
            "--server.address=0.0.0.0",
            "--server.port=8501",
            "--server.headless=true",
        ],
    }

    for name, command in commands.items():
        if name in existing:
            print_step(f"ℹ️  {name} já está em execução (PID {existing[name]['pid']}).")
            continue
        print_step(f"▶️  Iniciando {name}...")
        processes[name] = start_background(name, command)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(json.dumps(processes, indent=2), encoding="utf-8")
    return processes


def main() -> None:
    os_name = platform.system() or os.name
    print_step(f"🚀 Iniciando estoque-medicamento-cdc em {os_name}...")

    try:
        ensure_prerequisites()
        ensure_configuration()
        validate_oltp_connection()

        print_step("🐳 Subindo cluster Kafka KRaft, Kafka Connect e Redis...")
        try:
            run(["docker", "compose", "up", "-d", "--wait"])
        except subprocess.CalledProcessError:
            print_step("\n📋 Estado dos containers após a falha:")
            run(["docker", "compose", "ps"], check=False)
            print_step("\n📋 Últimos logs do Zookeeper:")
            run(["docker", "compose", "logs", "--tail=120", "zookeeper"], check=False)
            raise

        print_step("🔌 Registrando/atualizando o conector Debezium...")
        run([sys.executable, "-m", "scripts.register_connector"])

        processes = start_application_processes()
        wait_for_port("127.0.0.1", 8501, "Dashboard Streamlit", timeout=30)

        print_step("\n✅ Pipeline CDC com Redis iniciado com sucesso.")
        print_step("🌐 Dashboard: http://localhost:8501")
        print_step("🔌 Kafka Connect: http://localhost:8083")
        for name, info in processes.items():
            print_step(f"📄 Log de {name}: {info['log']} (PID {info['pid']})")
    except Exception as exc:
        print_step(f"\n❌ Falha na inicialização: {exc}")
        print_step("Use 'make logs' para consultar os containers e '.runtime/logs/' para os processos Python.")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
