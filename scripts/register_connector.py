from __future__ import annotations

"""Registra ou atualiza o conector Debezium de forma idempotente.

AVISO: no ambiente local os valores podem vir de connector.env; no deploy
Azure, as variáveis OLTP_* são recebidas diretamente pelo container.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
CONNECT_URL = os.getenv("KAFKA_CONNECT_URL", "http://localhost:8083").rstrip("/")
CONFIG_PATH = Path(
    os.getenv(
        "DEBEZIUM_CONNECTOR_CONFIG",
        str(ROOT_DIR / "infra" / "debezium" / "postgres-connector.json"),
    )
)
ENV_PATH = Path(
    os.getenv(
        "DEBEZIUM_CONNECTOR_ENV",
        str(ROOT_DIR / "infra" / "debezium" / "connector.env"),
    )
)

FILE_PROVIDER_PATTERN = re.compile(
    r"\$\{file:/config/connector\.env:([A-Z0-9_]+)\}"
)


def carregar_env(path: Path) -> dict[str, str]:
    """Carrega connector.env quando existir e o combina com os.getenv()."""
    values: dict[str, str] = {}

    if path.exists():
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"Linha inválida em {path.name}: {raw_line!r}")
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    # Variáveis do container têm prioridade sobre o arquivo local.
    for key in (
        "OLTP_HOST",
        "OLTP_PORT",
        "OLTP_USER",
        "OLTP_PASSWORD",
        "OLTP_DATABASE",
    ):
        env_value = os.getenv(key)
        if env_value:
            values[key] = env_value

    return values


def resolver_valor(value: Any, env_values: dict[str, str]) -> Any:
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        resolved = env_values.get(key)
        if not resolved:
            raise ValueError(
                f"A variável {key} não foi definida nem no ambiente "
                f"nem em {ENV_PATH}."
            )
        return resolved

    return FILE_PROVIDER_PATTERN.sub(replace, value)


def carregar_payload() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"JSON do conector não encontrado: {CONFIG_PATH}")

    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    config = payload.get("config")
    if not isinstance(config, dict):
        raise ValueError("postgres-connector.json não possui o objeto 'config'.")

    env_values = carregar_env(ENV_PATH)
    payload["config"] = {
        key: resolver_valor(value, env_values)
        for key, value in config.items()
    }
    return payload


def aguardar_connect() -> None:
    last_error: Exception | None = None
    for _ in range(60):
        try:
            response = requests.get(f"{CONNECT_URL}/connector-plugins", timeout=3)
            if response.ok:
                classes = {plugin.get("class") for plugin in response.json()}
                expected = "io.debezium.connector.postgresql.PostgresConnector"
                if expected not in classes:
                    raise RuntimeError("Plugin PostgreSQL do Debezium não encontrado.")
                return
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
        time.sleep(2)

    raise RuntimeError(
        f"Kafka Connect não ficou disponível corretamente: {last_error}"
    )


def erro_connect(response: requests.Response) -> RuntimeError:
    try:
        detail = json.dumps(response.json(), ensure_ascii=False, indent=2)
    except ValueError:
        detail = response.text or "Resposta sem corpo."
    return RuntimeError(
        f"Kafka Connect recusou a configuração (HTTP {response.status_code}).\n"
        f"{detail}"
    )


def main() -> None:
    aguardar_connect()
    payload = carregar_payload()
    name = str(payload["name"])

    existing = requests.get(f"{CONNECT_URL}/connectors/{name}", timeout=5)
    if existing.status_code == 200:
        response = requests.put(
            f"{CONNECT_URL}/connectors/{name}/config",
            json=payload["config"],
            timeout=30,
        )
        action = "atualizado"
    elif existing.status_code == 404:
        response = requests.post(
            f"{CONNECT_URL}/connectors", json=payload, timeout=30
        )
        action = "registrado"
    else:
        raise erro_connect(existing)

    if not response.ok:
        raise erro_connect(response)

    print(f"Conector {name} {action} com sucesso.")


if __name__ == "__main__":
    main()
