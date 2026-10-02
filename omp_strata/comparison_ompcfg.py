"""Comparison-only stock OMP routes; neither adapter owns an installed engine.

NInfer Status captures are normalized by the operator to release_id,
endpoint_state, runtime_identity_sha256 (served identity.binary_sha256),
config_identity_sha256 (identity.config_sha256), and model_identity_sha256
(identity.model_artifact_sha256). Raw controller/status output stays private.
This module only reads that capture; it never invokes the NInfer controller.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace

from .common import atomic_write_bytes, canonical_json, is_sha256, sha256_bytes, sha256_file
from .comparison import ArmLaunch, ComparisonError
from .layout import Layout, host_platform
from .lifecycle import verify_install_fast
from .ompcfg import (CHAT_ROLES, CONTEXT_SAFETY_TOKENS, LauncherError, OMP_PROFILE,
                     install_profile_config, isolated_env, omp_argv, render_config_yml)
from .profile import load as load_profile

NATIVE_LANES = {
    "rtx3090-native": ("ninfer-native-3090", "q38-ninfer"),
    "rtx4090-native": ("ninfer-native-4090", "qwen3.8-27b"),
}
STATUS_IDENTITIES = ("runtime_identity_sha256", "config_identity_sha256", "model_identity_sha256")


def _windows_private_key(path: Path) -> bool:
    # Mode bits do not describe a Windows DACL. Read it without changing the
    # installation; only the current account and privileged OS principals may
    # have Allow entries. The path is data, never interpolated PowerShell code.
    script = ("$ErrorActionPreference='Stop'; "
              "$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
              "$known={param($t) ([Security.Principal.SecurityIdentifier]::new([Security.Principal.WellKnownSidType]::$t,$null)).Value}; "
              "$allowed=@($sid,(& $known 'LocalSystemSid'),(& $known 'BuiltinAdministratorsSid')); "
              "$acl=Get-Acl -LiteralPath $env:OMP_G25_KEY_PATH; "
              "$rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])); "
              "if($rules.Count -eq 0){exit 1}; "
              "foreach($rule in $rules){if($rule.AccessControlType -eq 'Allow' -and "
              "$allowed -notcontains $rule.IdentityReference.Value){exit 1}}; exit 0")
    env = {name: value for name, value in os.environ.items() if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR"}}
    env["OMP_G25_KEY_PATH"] = str(path.resolve())
    try:
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _http_json(url: str, *, key: str | None = None) -> tuple[int, object]:
    # Match the launcher's local identity policy without inheriting SSH-route
    # ownership assumptions. Redirects must never forward the bearer credential.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None

    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + key} if key else {})
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=5) as response:
            code, raw = response.status, response.read(1 << 20)
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, b""
        exc.close()
    except (OSError, urllib.error.URLError):
        return 0, None
    try:
        return code, json.loads(raw)
    except (ValueError, UnicodeError):
        return code, None


class _Arm:
    arm: str
    api: str

    def __init__(self, plan: Mapping, bindings: Mapping, *,
                 base_env: Mapping[str, str] | None = None, extra: Sequence[str] = ()):
        self.plan = plan.as_dict() if hasattr(plan, "as_dict") else copy.deepcopy(dict(plan))
        self.bindings = copy.deepcopy(dict(bindings))
        self.base_env = None if base_env is None else dict(base_env)
        self.extra = tuple(extra)
        try:
            self.root = Path(bindings["comparison_root"]).resolve()
            self.binary = Path(bindings["omp_binary"]).resolve()
            self.binding = self.bindings[self.arm]
            self.key_file = Path(self.binding["key_file"])
            self.port = self.binding["port"]
            self.profile = load_profile(Path(bindings["strata"]["profile"]))
            if (type(self.port) is not int or not 1 <= self.port <= 65535
                    or self.profile.id != plan["strata"]["profile_id"]
                    or self.profile.fingerprint != plan["strata"]["profile_fingerprint"]):
                raise ComparisonError("comparison profile identity or loopback port mismatch")
            for protected in (Path.home() / ".omp", Path(bindings["strata"]["root"]),
                              Path(bindings["ninfer"]["root"])):
                protected = protected.resolve()
                if self.root.is_relative_to(protected) or protected.is_relative_to(self.root):
                    raise ComparisonError("comparison root must be separate from installed engine and default OMP roots")
            self.provider = plan[self.arm]["provider"]
            self.model = plan[self.arm]["model_id"]
            if plan[self.arm]["api"] != self.api:
                raise ComparisonError("comparison API does not match the selected arm")
        except (KeyError, TypeError, OSError, ValueError) as exc:
            if isinstance(exc, ComparisonError):
                raise
            raise ComparisonError("invalid comparison route bindings or Strata profile") from None
        self.base_url = f"http://127.0.0.1:{self.port}/v1"

    def _pin(self) -> dict:
        """Rehash each invocation, without writing a verification marker next to OMP."""
        try:
            pin = self.plan["omp"]
            expected = self.profile.omp_artifact(pin["platform"])
            if (pin["platform"] != host_platform() or pin["version"] != self.profile.data["omp"]["version"]
                    or type(pin["bytes"]) is not int or pin["bytes"] <= 0 or not is_sha256(pin["sha256"])
                    or any(pin[name] != expected[name] for name in ("bytes", "sha256"))):
                raise ComparisonError("both arms require the same profile-bound stock OMP pin")
            if (not self.binary.is_file() or self.binary.stat().st_size != pin["bytes"]
                    or sha256_file(self.binary) != pin["sha256"]):
                raise ComparisonError("stock OMP binary size or SHA-256 differs from the comparison pin")
        except (KeyError, TypeError, OSError):
            raise ComparisonError("missing or unreadable pinned stock OMP binary") from None
        return dict(pin)

    def _key(self) -> str:
        try:
            if self.key_file.is_symlink() or (os.name != "nt" and self.key_file.stat().st_mode & 0o077):
                raise ValueError
            key = self.key_file.read_text(encoding="ascii").strip()
            if not 32 <= len(key) <= 512 or not all(33 <= ord(ch) <= 126 for ch in key):
                raise ValueError
            if os.name == "nt" and not _windows_private_key(self.key_file):
                raise ValueError
        except (OSError, ValueError):
            raise ComparisonError("comparison API key must be a readable, user-only file with nonblank valid key material") from None
        return key

    def _argv(self, layout) -> list[str]:
        try:
            # The production builder is the sole authority for forbidden overrides
            # and discovery flags. Only the selected fixed model is changed below.
            argv = omp_argv(layout, binary=self.binary, extra=self.extra)
        except LauncherError:
            raise ComparisonError("OMP argument may override the isolated route or discovery policy") from None
        if self.arm == "ninfer":
            argv[argv.index("--model") + 1] = self.provider + "/" + self.model
        return argv

    def _endpoint(self) -> dict:
        return {"arm": self.arm, "api": self.api, "provider": self.provider,
                "model": self.model, "port": self.port}

    def _manifest(self) -> dict:
        name = "release_manifest_sha256" if self.arm == "strata" else "manifest_sha256"
        try:
            path = Path(self.binding["manifest"])
            raw = path.read_bytes()
            expected = self.plan[self.arm][name]
            if not is_sha256(expected) or sha256_bytes(raw) != expected:
                raise ValueError
            manifest = json.loads(raw)
            if not isinstance(manifest, dict):
                raise ValueError
        except (KeyError, OSError, TypeError, ValueError):
            raise ComparisonError("comparison release manifest is absent or differs from the pinned bytes") from None
        return manifest

    def prepare(self, attempt_root: Path) -> ArmLaunch:
        key = self._key()
        self._pin()
        attempt = Path(attempt_root).resolve()
        if attempt == self.root or not attempt.is_relative_to(self.root):
            raise ComparisonError("attempt must be a fresh child of the comparison root")
        home = attempt / "omp-home"
        layout = SimpleNamespace(profile=self.profile, omp_home=home)
        argv = self._argv(layout)
        # Exclusive creation also refuses symlinks, stale sessions and config reuse.
        try:
            home.mkdir(parents=True, exist_ok=False)
        except OSError:
            raise ComparisonError("comparison OMP HOME is not fresh or cannot be created") from None
        env = isolated_env(layout, api_key=key, base_env=self.base_env)
        if self.arm == "strata":
            installed = install_profile_config(layout, base_url=self.base_url)
        else:
            env.pop("STRATA_API_KEY")
            env.update(NINFER_NATIVE_API_KEY=key, PI_OPENAI_STATEFUL="1")
            settings = json.loads(render_config_yml(self.profile))
            route = self.provider + "/" + self.model
            settings["modelRoles"] = {role: route for role in CHAT_ROLES}
            settings["providers"]["maxInFlightRequests"] = {self.provider: 1}
            model = {
                "id": self.model, "name": "Qwen3.8 27B NInfer native", "api": self.api,
                "reasoning": True, "thinking": {"mode": "effort", "efforts": ["low", "medium", "xhigh"]},
                "input": ["text"], "supportsTools": True,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                # Same client budget boundary as Strata; do not claim equal tokenizers.
                "contextWindow": self.profile.data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS,
                "maxTokens": self.profile.data["omp"]["max_tokens"],
                "compat": {"includeEncryptedReasoning": False, "supportsReasoningSummary": False},
            }
            models = {"providers": {self.provider: {
                "baseUrl": self.base_url, "api": self.api, "apiKey": "NINFER_NATIVE_API_KEY",
                "authHeader": True, "models": [model],
            }}}
            directory = home / ".omp" / "profiles" / OMP_PROFILE / "agent"
            installed = {}
            for name, value in (("config", settings), ("models", models)):
                data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
                atomic_write_bytes(directory / (name + ".yml"), data)
                installed[name + "_sha256"] = sha256_bytes(data)
        return ArmLaunch(argv=argv, env=env, home=home,
                         config_sha256=installed["config_sha256"], models_sha256=installed["models_sha256"],
                         endpoint=self._endpoint())


class StrataArm(_Arm):
    arm = "strata"
    api = "openai-completions"

    def __init__(self, plan: Mapping, bindings: Mapping, **kwargs):
        super().__init__(plan, bindings, **kwargs)
        if self.provider != "strata-local" or self.model != self.profile.data["strata"]["model_name"]:
            raise ComparisonError("Strata comparison route differs from the restricted launcher")

    def preflight(self) -> dict:
        key = self._key()
        pin = self._pin()
        manifest = self._manifest()
        planned = self.plan["strata"]
        try:
            installed = verify_install_fast(Layout(Path(self.binding["root"]), self.profile))
            runtime_hash = sha256_bytes(canonical_json(installed["identity"]))
            model_hash = sha256_bytes(canonical_json(self.profile.data["model"]))
            if (runtime_hash != planned["runtime_identity_sha256"]
                    or runtime_hash != installed["runtime_identity_sha256"]
                    or model_hash != planned["model_identity_sha256"]
                    or manifest["profile"]["fingerprint"] != self.profile.fingerprint
                    or manifest["install"]["runtime_identity_sha256"] != runtime_hash):
                raise ValueError
        except (OSError, KeyError, TypeError, ValueError, RuntimeError):
            raise ComparisonError("Strata installed runtime/model/manifest identity differs from the comparison plan") from None
        expected = self.profile.data["strata"]
        origin = self.base_url.removesuffix("/v1")
        code, health = _http_json(origin + "/health")
        if (code != 200 or not isinstance(health, dict) or health.get("api_key") is not True
                or health.get("loaded") is False or health.get("model") != self.model
                or health.get("max_context") != expected["setup_args"]["context"]):
            raise ComparisonError("Strata authenticated model/build/context/settings identity check failed")
        anonymous, _ = _http_json(self.base_url + "/models")
        authenticated, models = _http_json(self.base_url + "/models", key=key)
        rows = models.get("data") if isinstance(models, dict) else None
        if (anonymous != 401 or authenticated != 200 or not isinstance(rows, list) or len(rows) != 1
                or not isinstance(rows[0], dict) or rows[0].get("id") != self.model):
            raise ComparisonError("Strata authenticated model/build/context/settings identity check failed")
        code, props = _http_json(origin + "/props", key=key)
        generation = props.get("default_generation_settings") if isinstance(props, dict) else None
        context = generation.get("n_ctx") if isinstance(generation, dict) else None
        if (code != 200 or not isinstance(props, dict) or props.get("build_info") != "Strata " + expected["engine_version"]
                or context != expected["setup_args"]["context"]):
            raise ComparisonError("Strata authenticated model/build/context/settings identity check failed")
        code, settings = _http_json(origin + "/settings", key=key)
        if code != 200 or settings != {"shared": False, "defaults": {}}:
            raise ComparisonError("Strata authenticated model/build/context/settings identity check failed") from None
        return {**self._endpoint(), "engine_version": expected["engine_version"], "context": context,
                "profile_fingerprint": self.profile.fingerprint, "runtime_identity_sha256": runtime_hash,
                "model_identity_sha256": model_hash, "release_manifest_sha256": planned["release_manifest_sha256"],
                "omp": pin}


class NInferArm(_Arm):
    arm = "ninfer"
    api = "openai-responses"

    def __init__(self, plan: Mapping, bindings: Mapping, **kwargs):
        super().__init__(plan, bindings, **kwargs)
        if NATIVE_LANES.get(plan["ninfer"].get("lane")) != (self.provider, self.model):
            raise ComparisonError("NInfer requires the documented provider and model for its native lane")

    def preflight(self) -> dict:
        key = self._key()
        pin = self._pin()
        manifest = self._manifest()
        expected = self.plan["ninfer"]
        try:
            variant, = [item for item in manifest["components"]["ninfer_variants"]
                        if item["id"] == expected["lane"].replace("-native", "-windows-native")]
            if any(variant[wire] != expected[normalized] for wire, normalized in (
                ("server_binary_sha256", "runtime_identity_sha256"),
                ("configuration_sha256", "config_identity_sha256"),
                ("model_artifact_sha256", "model_identity_sha256"))):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise ComparisonError("NInfer manifest does not bind the selected native runtime/config/model") from None
        try:
            status = json.loads(Path(self.binding["status_file"]).read_text(encoding="utf-8"))
        except (KeyError, OSError, ValueError):
            raise ComparisonError("NInfer requires a normalized private controller Status capture") from None
        if (not isinstance(status, dict) or status.get("endpoint_state") != "ready"
                or not expected.get("release_id") or status.get("release_id") != expected["release_id"]
                or any(not is_sha256(expected.get(name)) or status.get(name) != expected[name]
                       for name in STATUS_IDENTITIES)):
            raise ComparisonError("NInfer controller Status identity is absent, unresolved or differs from the plan")
        anonymous, _ = _http_json(self.base_url + "/models")
        authenticated, models = _http_json(self.base_url + "/models", key=key)
        rows = models.get("data") if isinstance(models, dict) else None
        if (anonymous != 401 or authenticated != 200 or not isinstance(rows, list) or len(rows) != 1
                or not isinstance(rows[0], dict) or rows[0].get("id") != self.model):
            raise ComparisonError("NInfer authenticated native model identity check failed")
        code, live = _http_json(self.base_url + "/ninfer/status", key=key)
        identity = live.get("identity") if isinstance(live, dict) else None
        fields = {"runtime_identity_sha256": "binary_sha256", "config_identity_sha256": "config_sha256",
                  "model_identity_sha256": "model_artifact_sha256"}
        if (code != 200 or not isinstance(identity, dict) or live.get("status") != "ok"
                or identity.get("source_dirty") is not False
                or any(identity.get(wire) != expected[normalized] for normalized, wire in fields.items())):
            raise ComparisonError("NInfer authenticated served runtime/config/model identity differs from the plan")
        return {**self._endpoint(), "release_id": expected["release_id"],
                "manifest_sha256": expected["manifest_sha256"],
                **{name: status[name] for name in STATUS_IDENTITIES}, "omp": pin}
