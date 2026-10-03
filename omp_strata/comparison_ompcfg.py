"""Comparison-only stock OMP routes; neither adapter owns an installed engine.

NInfer Status captures are normalized by the operator to release_id,
endpoint_state, runtime_identity_sha256 (served identity.binary_sha256),
config_identity_sha256 (identity.config_sha256), and model_identity_sha256
(identity.model_artifact_sha256). Raw controller/status output stays private.
Docker identity comes from a fresh private read-only argv probe and the selected
release manifest, not a native controller capture. Neither path controls an engine.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from eval.support import run_bounded

from .common import atomic_write_bytes, canonical_json, is_sha256, sha256_bytes, sha256_file
from .comparison import (DOCKER_LANE, NINFER_LANES, ArmLaunch, ComparisonError,
                         validate_docker_probe_argv)
from .layout import Layout, host_platform
from .lifecycle import verify_install_fast
from .ompcfg import (CHAT_ROLES, CONTEXT_SAFETY_TOKENS, LauncherError, OMP_PROFILE,
                     install_profile_config, isolated_env, omp_argv, render_config_yml)
from .profile import load as load_profile

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
            env.update({self.key_env: key, "PI_OPENAI_STATEFUL": "1"})
            settings = json.loads(render_config_yml(self.profile))
            route = self.provider + "/" + self.model
            settings["modelRoles"] = {role: route for role in CHAT_ROLES}
            settings["providers"]["maxInFlightRequests"] = {self.provider: 1}
            model = {
                "id": self.model, "name": "Qwen3.8 27B NInfer", "api": self.api,
                "reasoning": True, "thinking": {"mode": "effort", "efforts": ["low", "medium", "xhigh"]},
                "input": ["text"], "supportsTools": True,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                # Same client budget boundary as Strata; do not claim equal tokenizers.
                "contextWindow": self.profile.data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS,
                "maxTokens": self.profile.data["omp"]["max_tokens"],
                "compat": {"includeEncryptedReasoning": False, "supportsReasoningSummary": False},
            }
            if self.docker:
                model["compat"]["supportsImageDetailOriginal"] = False
            models = {"providers": {self.provider: {
                "baseUrl": self.base_url, "api": self.api, "apiKey": self.key_env,
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
        if NINFER_LANES.get(plan["ninfer"].get("lane")) != (self.provider, self.model):
            raise ComparisonError("NInfer requires the documented provider and model for its lane")
        self.docker = plan["ninfer"]["lane"] == DOCKER_LANE
        self.key_env = "NINFER_BETA_API_KEY" if self.docker else "NINFER_NATIVE_API_KEY"

    def _docker_status(self, manifest: dict, key: str) -> dict:
        expected = self.plan["ninfer"]
        try:
            runtime = manifest["components"]["ninfer"]
            config = manifest["runtime_identity"]
            digest = expected["image_digest"]
            if (not isinstance(digest, str) or not digest.startswith("sha256:") or not is_sha256(digest[7:])
                    or runtime["oci_manifest_digest"] != digest
                    or runtime["server_binary_sha256"] != expected["runtime_identity_sha256"]
                    or config["configuration_sha256"] != expected["config_identity_sha256"]
                    or manifest["components"]["model"]["artifact_sha256"] != expected["model_identity_sha256"]
                    or config["public_model_id"] != self.model
                    or manifest["release"] != expected["release_id"]
                    or not isinstance(config["deployment_profile"], str) or not config["deployment_profile"]
                    or any(not is_sha256(expected.get(name)) for name in STATUS_IDENTITIES)):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise ComparisonError("NInfer manifest does not bind the selected Docker image/runtime/config/model") from None
        argv = self.binding.get("docker_identity_probe_argv")
        validate_docker_probe_argv(argv, key=key)
        started = datetime.now(timezone.utc)
        try:
            result = run_bounded(argv, cwd=Path(self.binding["root"]), timeout=10, limit=65536)
            if result["returncode"] != 0 or result["timed_out"] or result["output_limited"]:
                raise ValueError
            status = json.loads(result["stdout"])
            if not isinstance(status, dict):
                raise ValueError
            observed = datetime.fromisoformat(status["observed_at"].replace("Z", "+00:00"))
            container_start = datetime.fromisoformat(status["started_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if (observed.tzinfo is None or container_start.tzinfo is None
                    or not -2 <= (observed - started).total_seconds() <= (now - started).total_seconds() + 2
                    or container_start > observed or container_start.year < 2020
                    or not is_sha256(status.get("container_id"))
                    or status.get("running") is not True or status.get("endpoint_state") != "ready"
                    or status.get("release_id") != expected["release_id"]
                    or status.get("image_digest") != digest
                    or status.get("deployment_profile") != config["deployment_profile"]
                    or any(status.get(name) != expected[name] for name in STATUS_IDENTITIES)):
                raise ValueError
            publications = status["publications"]
            if (not isinstance(publications, list) or not publications
                    or any(not isinstance(row, dict) or set(row) != {"host_ip", "host_port", "container_port", "protocol"}
                           or row["host_ip"] not in {"127.0.0.1", "0.0.0.0", "::", "::1"}
                           or type(row["host_port"]) is not int or row["host_port"] != self.port
                           or type(row["container_port"]) is not int or row["container_port"] != 8080
                           or row["protocol"] != "tcp" for row in publications)
                    or not any(row["host_ip"] in {"127.0.0.1", "0.0.0.0"} for row in publications)):
                raise ValueError
        except (KeyError, OSError, TypeError, ValueError, AttributeError):
            raise ComparisonError("NInfer Docker identity probe is absent, stale, unsafe or differs from the plan") from None
        return status

    def preflight(self) -> dict:
        key = self._key()
        pin = self._pin()
        manifest = self._manifest()
        expected = self.plan["ninfer"]
        if self.docker:
            status = self._docker_status(manifest, key)
        else:
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
        if (anonymous not in ({401, 403} if self.docker else {401})
                or authenticated != 200 or not isinstance(rows, list) or len(rows) != 1
                or not isinstance(rows[0], dict) or rows[0].get("id") != self.model):
            raise ComparisonError("NInfer authenticated model identity check failed")
        code, live = _http_json(self.base_url + "/ninfer/status", key=key)
        identity = live.get("identity") if isinstance(live, dict) else None
        fields = {"runtime_identity_sha256": "binary_sha256", "config_identity_sha256": "config_sha256",
                  "model_identity_sha256": "model_artifact_sha256"}
        if (code != 200 or not isinstance(identity, dict) or live.get("status") != "ok"
                or identity.get("source_dirty") is not False
                or (self.docker and identity.get("deployment_profile") != status["deployment_profile"])
                or any(identity.get(wire) != expected[normalized] for normalized, wire in fields.items())):
            raise ComparisonError("NInfer authenticated served runtime/config/model identity differs from the plan")
        docker_identity = ({name: status[name] for name in
                           ("image_digest", "container_id", "started_at", "observed_at", "deployment_profile")}
                          if self.docker else {})
        if self.docker:
            docker_identity["internal_model_id"] = identity.get("model_id")
            # Public-capable endpoint evidence records observed publication scope,
            # not IP literals. The unmodified probe output remains private.
            scopes = {"127.0.0.1": "ipv4-loopback", "0.0.0.0": "ipv4-wildcard",
                      "::1": "ipv6-loopback", "::": "ipv6-wildcard"}
            docker_identity["publications"] = [
                {"address_scope": scopes[row["host_ip"]],
                 **{name: row[name] for name in ("host_port", "container_port", "protocol")}}
                for row in status["publications"]]
        return {**self._endpoint(), **docker_identity, "release_id": expected["release_id"],
                "manifest_sha256": expected["manifest_sha256"],
                **{name: status[name] for name in STATUS_IDENTITIES}, "omp": pin}
