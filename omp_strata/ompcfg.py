"""Pinned stock OMP configuration and the deliberately restricted launcher boundary.

JSON is a YAML 1.2 subset; writing it avoids a runtime YAML dependency. Local keys
are verified against stock OMP's settings registry and models schema bundle.
The 19.0.0 admission leaves earlier profiles' rendered config and environment unchanged.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import urlsplit

from .common import atomic_write_bytes, release_version, sha256_bytes

OMP_PROFILE = "omp-strata"
CHAT_ROLES = ("default", "smol", "slow", "vision", "plan", "commit", "tiny", "memory", "task", "advisor", "judge")
FOREIGN_PROVIDERS = (
    "agent-plugins", "agents", "agents-md", "claude", "claude-md", "claude-plugins",
    "cline", "codex", "cursor", "gemini", "github", "mcp-json", "omp-plugins",
    "opencode", "skillshare", "vscode", "windsurf",
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


def omp_version(profile) -> tuple[int, ...]:
    version = release_version(profile.data["omp"]["version"])
    if version is None:
        raise LauncherError("a pinned OMP release version is required")
    return version


PROVIDER_SLOT_SINCE = (19, 2, 0)
# Stock's idle grace is 3 s. On Darwin kill_tree reached the daemon and stock spawned its replacement
# before the client exited; the last worker exited 8.032 s after the client. Never kill a survivor.
PROVIDER_SLOT_EXIT_S = 10


def direct_daemon_socket(directory: Path) -> Path | None:
    """Stock ipc/endpoint.rs: direct UTF-8 pathname + NUL must fit sun_path; Windows uses a named pipe."""
    path = directory / "daemon.sock"
    if os.name == "nt" or len(os.fsencode(path)) >= (108 if sys.platform.startswith("linux") else 104):
        return None
    return path


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


def inflight_limit(profile) -> int:
    """Requests OMP may send one Strata server at once: its batch slots (stock setup `--parallel`), else one."""
    return profile.data["strata"]["setup_args"].get("parallel") or 1


def render_config_yml(profile, *, overrides: dict | None = None) -> str:
    model = "strata-local/" + profile.data["strata"]["model_name"]
    v19 = omp_version(profile) >= (19, 0, 0)
    discovery = ("custom-context", "ssh-config", "ssh-json") if v19 else ("ssh",)
    settings = {
        "retry": {"enabled": False, "modelFallback": False, "fallbackRevertPolicy": "never"},
        "update": {"auto": False},
        "startup": {"checkUpdate": False, "setupWizard": False},
        "providers": {"maxInFlightRequests": {"strata-local": inflight_limit(profile)}},
        # Speculative compaction off. Near its threshold stock OMP sends the same model a background summary request;
        # with one sequence and one in-flight request that request delays the agent's next turn and replaces the live
        # prefix the turn would reuse (G17 on 18.8.0: 17 s, then all 105,748 tokens re-read).
        # Compaction itself stays stock and runs when the threshold is reached. No threshold override: stock OMP
        # already fits each request's max_tokens to the remaining window (401778d packages/agent/src/output-budget.ts
        # fitOutputTokensToContextWindow; observed in G17), so the default reserve keeps its full usable context.
        # Tests pass reduced thresholds as explicit overrides.
        "compaction": {"asyncEnabled": False},
        "modelRoles": {role: model for role in CHAT_ROLES},
        "enabledProviders": ["native"], "disabledProviders": sorted((*FOREIGN_PROVIDERS, *discovery)),
        "mcp": {"enableProjectConfig": False},
        "telemetry": {"otlpExportEnabled": False},
        "dev": {"autoqa": False, "autoqaConsent": "denied"},
    }
    if v19:
        settings.update(
            composer={"predictions": False},  # no auxiliary model turn after interactive answers
            launch={"enabled": False},  # print/RPC force persist on; disallow named services, not foreground bash
            spelling={"autocomplete": "off"},  # interactive typing must not open a daemon prediction unit
        )
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


# Stock OMP refreshes its public model catalog in the background at startup with a fresh cache
# (model-registry refreshInBackground; no setting disables it), and the tools it spawns inherit its environment.
# Non-loopback HTTP(S) from the client and those tools is therefore pointed at a closed loopback port, while
# loopback (the Strata route) stays direct. No proxy process exists; this is defense in depth, not enforcement:
# the qualification evidence is the per-process network observation, not this setting. The v19 Codex npm
# refresh has its own off switch (below); disabledProviders does not stop that model-cache lookup.
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
    if omp_version(layout.profile) >= (19, 0, 0):
        env["PI_AI_CODEX_CLIENT_VERSION"] = "0.169.0"  # v19's built-in floor, packages/catalog/src/wire/codex.ts
    return env


def _native_cache_busy(binary: Path, addons: list[Path]) -> bool:
    if sys.platform == "darwin":
        # Concurrent taskset attempts share an executable, never an addon. Darwin maps it until exit.
        users = subprocess.run(["lsof", "-nP", "-t", "--", *map(str, addons)], stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=5)
        if users.returncode == 1 and not users.stdout and not users.stderr:
            return False
        if users.returncode:
            raise RuntimeError("native cache retained: addon census unavailable")
        return True
    if os.name == "nt":
        # G24/G25 use a dedicated executable. Conservatively wait for every user of that binary,
        # even if Windows has not mapped the DLL (or does not expose its module list).
        script = """$ErrorActionPreference = 'Stop'
foreach ($p in (Get-CimInstance Win32_Process -Property Name,ExecutablePath | Where-Object Name -eq $env:OMP_GATE_NAME)) {
    if (!$p.ExecutablePath) {throw 'image identity unavailable'}
    if ($p.ExecutablePath -eq $env:OMP_GATE_EXE) { 'busy'; break }
}"""
        users = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                               env={**os.environ, "OMP_GATE_EXE": str(binary.resolve()), "OMP_GATE_NAME": binary.name},
                               stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=PROVIDER_SLOT_EXIT_S, check=True)
        return bool(users.stdout.strip())
    from . import procs
    if not sys.platform.startswith("linux") or not Path("/proc/self/maps").is_file():
        raise RuntimeError("native cache retained: addon census unavailable")
    exe = binary.resolve()
    # Distinct attempts can share an executable. Compare mapped files by device and inode,
    # not the display pathname (which can contain escapes, aliases or a deletion suffix).
    targets = {(os.major(st.st_dev), os.minor(st.st_dev), st.st_ino) for st in (addon.stat() for addon in addons)}
    for row in procs.table().identified.values():
        if Path(row.exe) != exe:
            continue
        try:
            with Path(f"/proc/{row.pid}/maps").open("rb") as mappings:
                for line in mappings:
                    _, _, _, dev, inode, *_ = line.split(None, 5)
                    major, minor = dev.split(b":")
                    if (int(major, 16), int(minor, 16), int(inode)) in targets:
                        return True
        except (FileNotFoundError, ProcessLookupError):
            continue  # Process exited between the table snapshot and the maps read.
        except (OSError, ValueError) as exc:
            raise RuntimeError("native cache retained: addon census unavailable") from exc
    return False


def drop_native_cache(omp_home: Path, *, version: str, binary: Path | None = None) -> None:
    """Delete the native addon a compiled stock OMP extracted into an isolated HOME, once its process has exited.

    OMP writes its embedded ~175 MB addon to `$HOME/.omp/natives/<version>/` (or `$XDG_DATA_HOME/omp/natives` when
    that `omp` directory exists) whenever it is missing, so a fresh HOME per attempt kept one copy per attempt: 572
    copies, ~100 GB, by 2026-10-06. OMP re-extracts it on its next start; sessions and config are untouched.
    Before provider slots this is best effort. From 19.2.0 an uncertain/held cache is a reported failure;
    don't remove files while a worker can still be using them.
    """
    locations = (omp_home / ".omp/natives", omp_home / ".local/share/omp/natives")
    modern = release_version(version) >= PROVIDER_SLOT_SINCE
    if modern:
        addons = [p for directory in locations if directory.resolve().is_relative_to(omp_home.resolve())
                  for p in directory.glob("*/*.node")]
        if addons:
            if binary is None:
                raise RuntimeError("native cache retained: missing pinned binary for census")
            deadline = time.monotonic() + PROVIDER_SLOT_EXIT_S
            while _native_cache_busy(binary, addons):
                if time.monotonic() >= deadline:
                    raise RuntimeError("native cache retained: provider-slot worker survived")
                time.sleep(.1)
    for natives in locations:
        if modern and natives.exists():
            if natives.is_symlink() or not natives.resolve().is_relative_to(omp_home.resolve()):
                raise RuntimeError("native cache retained: path outside attempt")
            shutil.rmtree(natives)
        else:
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
    settings["providers"]["maxInFlightRequests"] = {"strata-" + m["label"]: inflight_limit(route.servers[m["label"]])
                                                    for m in route.data["members"]}
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
                      + "\n---\nInspect the assigned scope without modifying files. Return the requested result with"
                      + " yield if you have that tool, otherwise as your final message.\n")
        atomic_write_bytes(directory / "agents" / (name + ".md"), definition.encode())
    return {**paths, "config_sha256": sha256_bytes(config), "models_sha256": sha256_bytes(models)}


def route_argv(layout, route, *, extra: Sequence[str], binary: Path | None = None) -> list[str]:
    if omp_version(route.main) >= (19, 0, 0):
        for token in extra:
            if token == "--":
                break
            if token.split("=", 1)[0] == "--offline":
                raise LauncherError("--offline would restrict subagents to the active provider on a client route")
    argv = omp_argv(layout, extra=extra, binary=binary)
    argv[argv.index("--model") + 1] = route_model(route, route.data["roles"]["default"])
    return argv
