"""Pinned stock OMP configuration and the deliberately restricted launcher boundary.

JSON is a YAML 1.2 subset; writing it avoids a runtime YAML dependency. Local keys
are verified against OMP 18.4.0's settings registry and models schema bundle;
remote agent-model overrides are exercised on OMP 18.4.6, .8, .10 and .12.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
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
FORBIDDEN_OMP_OPTIONS = frozenset({
    "--model", "--models", "--profile", "--alias", "--provider", "--api-key", "--base-url",
    "--config", "--config-file", "--config-dir", "--models-file", "--models-config",
    "--smol", "--slow", "--plan", "--prewalk-into", "--plan-yolo-into",
    "--extension", "-e", "--extensions", "--trusted-extension",
    "--hook", "--plugin-dir", "--plugins", "--skills", "--from-claude", "--from-codex",
})


class LauncherError(ValueError):
    """Launching would violate the isolated local-provider contract."""


def _yaml(value: dict) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


# Stock OMP fits each request's max_tokens to (declared window - its prompt estimate); stock Strata refuses any
# request with prompt + max_tokens + 8 > n_ctx. OMP counts appended messages locally, so its estimate can fall a
# few tokens short (G17, 2026-09-30: prompt 105,522 + fitted cap 25,563 = 131,085 > 131,064 -> HTTP 400 on the
# closing turn). Declaring the window this much below the engine's absorbs that error and the server slack.
CONTEXT_SAFETY_TOKENS = 1024


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
            "contextWindow": profile.data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS,
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
        # No compaction override: stock OMP already fits each request's max_tokens to the remaining window
        # (401778d packages/agent/src/output-budget.ts fitOutputTokensToContextWindow; observed in G17), so the
        # default reserve keeps its full usable context. Tests pass reduced thresholds as explicit overrides.
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


# Stock OMP 18.4.0 refreshes its public model catalog in the background at every startup with a fresh cache
# (model-registry refreshInBackground; no setting disables it), and the tools it spawns inherit its environment.
# Non-loopback HTTP(S) from the client and those tools is therefore pointed at a closed loopback port, while
# loopback (the Strata route) stays direct. No proxy process exists; this is defense in depth, not enforcement:
# the qualification evidence is the per-process network observation, not this setting.
EGRESS_GUARD_PROXY = "http://127.0.0.1:9"
EGRESS_GUARD_NO_PROXY = "127.0.0.1,localhost,::1"


def isolated_env(layout, *, api_key: str | None, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    if api_key is None or not api_key.strip():
        raise LauncherError("STRATA_API_KEY must be present and nonblank before starting OMP")
    base = os.environ if base_env is None else base_env
    # An allowlist also excludes inherited proxies, OTEL exporters, shell startup injection,
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
    # Windows environment names are case-insensitive: one spelling each there, both spellings on POSIX.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        for spelling in ((name,) if os.name == "nt" else (name, name.lower())):
            env[spelling] = EGRESS_GUARD_PROXY
    for spelling in (("NO_PROXY",) if os.name == "nt" else ("NO_PROXY", "no_proxy")):
        env[spelling] = EGRESS_GUARD_NO_PROXY
    env.update(NO_COLOR="1", STRATA_API_KEY=api_key)
    return env


def drop_native_cache(omp_home: Path) -> None:
    """Delete the native addon a compiled stock OMP extracted into an isolated HOME, once its process has exited.

    OMP writes its embedded ~175 MB addon to `$HOME/.omp/natives/<version>/` (or `$XDG_DATA_HOME/omp/natives` when
    that `omp` directory exists) whenever it is missing, so a fresh HOME per attempt kept one copy per attempt: 572
    copies, ~100 GB, by 2026-10-06. OMP re-extracts it on its next start; sessions and config are untouched.
    Best effort: a held file (e.g. a scanner on Windows) leaves the old state rather than failing the attempt, and
    `rmtree` never follows a symlinked directory out of the HOME.
    """
    for natives in (omp_home / ".omp" / "natives", omp_home / ".local" / "share" / "omp" / "natives"):
        shutil.rmtree(natives, ignore_errors=True)


def omp_argv(layout, *, extra: Sequence[str], platform: str | None = None,
             binary: Path | None = None) -> list[str]:
    for token in extra:
        if token == "--":
            break  # Stock OMP treats the remainder as literal prompt text.
        if token.split("=", 1)[0] in FORBIDDEN_OMP_OPTIONS:
            raise LauncherError("OMP argument may override the isolated route or discovery policy")
    executable = binary if binary is not None else layout.omp_binary(platform)
    return [str(executable), "--profile", OMP_PROFILE, "--model",
            "strata-local/" + layout.profile.data["strata"]["model_name"], *DISCOVERY_OFF, *extra]


def route_key_env(label: str) -> str:
    return "STRATA_ROUTE_" + label.upper().replace("-", "_") + "_KEY"


def route_model(route, label: str) -> str:
    return "strata-" + label + "/" + route.servers[label].data["strata"]["model_name"]


def install_route_config(layout, route) -> dict:
    """Render only the public route. Existing local rendering remains unchanged."""
    providers = {}
    for member in route.data["members"]:
        label = member["label"]
        template = json.loads(render_models_yml(route.servers[label], base_url=f"http://127.0.0.1:{member['local_port']}/v1"))
        provider = template["providers"]["strata-local"]
        provider["apiKey"] = route_key_env(label)
        providers["strata-" + label] = provider
    settings = json.loads(render_config_yml(route.main))
    settings["modelRoles"] = {role: route_model(route, label) for role, label in route.data["roles"].items()}
    settings["providers"]["maxInFlightRequests"] = {name: 1 for name in providers}
    # Override only model selection; keep the stock prompts, tools, schema and thinking level.
    worker = route_model(route, route.data["roles"]["task"])
    settings["task"] = {"agentModelOverrides": {"task": worker, "scout": worker}}
    directory = layout.omp_home / ".omp" / "profiles" / OMP_PROFILE / "agent"
    config, models = _yaml(settings).encode(), _yaml({"providers": providers}).encode()
    paths = {"config": directory / "config.yml", "models": directory / "models.yml"}
    atomic_write_bytes(paths["config"], config)
    atomic_write_bytes(paths["models"], models)
    # Stock native user agents are discovered even with extension/skill/rule discovery off.
    for name, label in route.data["agents"].items():
        definition = ("---\nname: " + name + "\ndescription: Strata fleet read-only scout"
                      + "\ntools: read, find, grep, glob\nmodel: " + route_model(route, label)
                      + "\n---\nInspect the assigned scope without modifying files. Submit the requested result with yield.\n")
        atomic_write_bytes(directory / "agents" / (name + ".md"), definition.encode())
    return {**paths, "config_sha256": sha256_bytes(config), "models_sha256": sha256_bytes(models)}


def route_argv(layout, route, *, extra: Sequence[str], binary: Path | None = None) -> list[str]:
    argv = omp_argv(layout, extra=extra, binary=binary)
    argv[argv.index("--model") + 1] = route_model(route, route.data["roles"]["default"])
    return argv
