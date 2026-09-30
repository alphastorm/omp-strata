"""Pinned stock OMP configuration and the deliberately restricted launcher boundary.

JSON is a YAML 1.2 subset; writing it avoids a runtime YAML dependency. Keys are
verified against OMP 18.4.0's domain settings registry and models schema bundle.
"""
from __future__ import annotations

import copy
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import urlsplit

from .common import atomic_write_bytes, sha256_bytes

OMP_PROFILE = "omp-strata"
CHAT_ROLES = ("default", "smol", "slow", "vision", "plan", "commit", "tiny", "memory", "task", "advisor", "judge")
FOREIGN_PROVIDERS = (
    "agent-plugins", "agents", "agents-md", "claude", "claude-md", "claude-plugins",
    "cline", "codex", "cursor", "gemini", "github", "mcp-json", "omp-plugins",
    "opencode", "skillshare", "ssh", "vscode", "windsurf",
)
DISCOVERY_OFF = ("--no-extensions", "--no-skills", "--no-rules",
                 "--no-lsp", "--no-title", "--no-prewalk", "--no-pty")


class LauncherError(ValueError):
    """Launching would violate the isolated local-provider contract."""


def _yaml(value: dict) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def render_models_yml(profile, *, base_url: str) -> str:
    url = urlsplit(base_url)
    if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1")
            or url.username is not None or url.password is not None
            or url.query or url.fragment or url.path.rstrip("/") != "/v1"):
        raise LauncherError("Strata base URL must be an authenticated loopback HTTP /v1 endpoint")
    model = profile.data["strata"]["model_name"]
    return _yaml({"providers": {"strata-local": {
        "baseUrl": base_url.rstrip("/"), "api": "openai-completions",
        "apiKey": "STRATA_API_KEY", "authHeader": True,
        "models": [{
            "id": model, "name": model, "reasoning": True,
            "thinking": {"mode": "effort", "efforts": ["low", "medium", "high"]},
            "input": ["text"], "supportsTools": True,
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": profile.data["omp"]["context_window"],
            "maxTokens": profile.data["omp"]["max_tokens"],
            "compat": {
                "supportsStore": False, "supportsDeveloperRole": False,
                "supportsMultipleSystemMessages": False, "maxTokensField": "max_tokens",
                "supportsUsageInStreaming": True, "supportsReasoningEffort": True,
                "thinkingFormat": "openai", "supportsStrictMode": False,
            },
        }],
    }}})


def _merge(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def render_config_yml(profile, *, overrides: dict | None = None) -> str:
    model = "strata-local/" + profile.data["strata"]["model_name"]
    settings = {
        "retry": {"enabled": False, "modelFallback": False, "fallbackRevertPolicy": "never"},
        "startup": {"checkUpdate": False},
        "providers": {"maxInFlightRequests": {"strata-local": 1}},
        # Strata rejects prompt + max_tokens beyond its context. Compact before
        # the full declared output budget no longer fits, with room for growth.
        "compaction": {"reserveTokens": profile.data["omp"]["max_tokens"] + 4096},
        "modelRoles": {role: model for role in CHAT_ROLES},
        "enabledProviders": ["native"], "disabledProviders": list(FOREIGN_PROVIDERS),
        "mcp": {"enableProjectConfig": False},
        "telemetry": {"otlpExportEnabled": False},
        "dev": {"autoqa": False, "autoqaConsent": "denied"},
    }
    if overrides is not None:
        _merge(settings, overrides)
    return _yaml(settings)


def install_profile_config(layout, *, base_url: str | None = None, overrides: dict | None = None) -> dict:
    if base_url is None:
        base_url = f"http://127.0.0.1:{layout.profile.data['server']['port']}/v1"
    directory = layout.omp_home / ".omp" / "profiles" / OMP_PROFILE / "agent"
    config = render_config_yml(layout.profile, overrides=overrides).encode("utf-8")
    models = render_models_yml(layout.profile, base_url=base_url).encode("utf-8")
    paths = {"config": directory / "config.yml", "models": directory / "models.yml"}
    atomic_write_bytes(paths["config"], config)
    atomic_write_bytes(paths["models"], models)
    return {**paths, "config_sha256": sha256_bytes(config), "models_sha256": sha256_bytes(models)}


def isolated_env(layout, *, api_key: str | None, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    if api_key is None or not api_key.strip():
        raise LauncherError("STRATA_API_KEY must be present and nonblank before starting OMP")
    base = os.environ if base_env is None else base_env
    # An allowlist also excludes proxies, OTEL exporters, shell startup injection,
    # NODE_OPTIONS, credential sockets and future provider environment variables.
    essentials = {"PATH", "SYSTEMROOT", "COMSPEC", "PATHEXT", "WINDIR", "LANG", "LANGUAGE", "TZ",
                  "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"}
    env = {key: value for key, value in base.items()
           if (key.upper() in essentials or key.upper().startswith("LC_"))
           and not key.upper().endswith(("_API_KEY", "_TOKEN", "_SECRET"))}
    home = layout.omp_home.resolve()
    directories = {
        "HOME": home, "USERPROFILE": home,
        "APPDATA": home / "appdata" / "roaming", "LOCALAPPDATA": home / "appdata" / "local",
        "TEMP": home / "tmp", "TMP": home / "tmp",
        "XDG_CONFIG_HOME": home / ".config", "XDG_DATA_HOME": home / ".local" / "share",
        "XDG_CACHE_HOME": home / ".cache", "XDG_STATE_HOME": home / ".local" / "state",
    }
    for key, directory in directories.items():
        directory.mkdir(parents=True, exist_ok=True)
        env[key] = str(directory)
    env.update(NO_COLOR="1", STRATA_API_KEY=api_key)
    return env


def omp_argv(layout, *, extra: Sequence[str], platform: str | None = None,
             binary: Path | None = None) -> list[str]:
    forbidden = {
        "--model", "--models", "--profile", "--alias", "--provider", "--api-key", "--base-url",
        "--config", "--config-file", "--config-dir", "--models-file", "--models-config",
        "--smol", "--slow", "--plan", "--prewalk-into", "--plan-yolo-into",
        "--extension", "-e", "--extensions", "--trusted-extension",
        "--hook", "--plugin-dir", "--plugins", "--skills", "--from-claude", "--from-codex",
    }
    for token in extra:
        if token == "--":
            break  # Stock OMP treats the remainder as literal prompt text.
        if token.split("=", 1)[0] in forbidden:
            raise LauncherError("OMP argument may override the isolated route or discovery policy")
    executable = binary if binary is not None else layout.omp_binary(platform)
    return [str(executable), "--profile", OMP_PROFILE, "--model",
            "strata-local/" + layout.profile.data["strata"]["model_name"], *DISCOVERY_OFF, *extra]
