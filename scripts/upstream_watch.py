#!/usr/bin/env python3
"""Read-only upstream news and append-only, unqualified tuple drafts.

report writes JSON to stdout and a short summary to stderr: 0 = no news, 3 = news,
4 = incomplete (including partial API results). draft: 0 = created, 2 = refused.
Only GitHub/Hugging Face metadata is fetched; installers and locks are never written.
"""
from __future__ import annotations

import argparse
import ast
import copy
import datetime as dt
import http.client
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omp_strata.common import flag_pairs, prerelease_tag, read_json, release_version, sha256_bytes
from omp_strata.engine_component import inspect_archive
from omp_strata.install import GENERATED_CONFIG_KEYS, generated_config_keys
from omp_strata.ompcfg import CONTEXT_SAFETY_TOKENS
from omp_strata.profile import CALIBRATION_DEFAULTS, Profile, gpu_requirements, load, validate
from omp_strata.receipts import schema_errors
from scripts import realhost_gates
from tests.unit.test_strata_surface import routes

ROOT = Path(__file__).resolve().parents[1]
GITHUB = "https://api.github.com"
HF = "https://huggingface.co"
REPOS = {"strata": "Niko1221/Strata", "omp": "can1357/oh-my-pi"}
CONSTANTS = ("MIN_ENGINE", "MIN_DRIVER", "CUDA_WHEELS", "PY_PACKAGES", "LLAMA_CPP_COMMIT", "HF_REVISIONS")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")

# Exact v0.1.39 AST branches outside this Windows, text-only lane.
# Their guards must be false; changed branches get the normal fail-closed pure_exec review.
NON_PLANNING_BRANCHES_0_1_39 = {
    "9fb87c80079cfecb09d86ad1baa5ee0c28912f18c365a2abedb4e26175dbfd19",  # Linux rotational PLE IO
    "a08debe9f17b323faa3f63f098bb63e35f7471f5b86ef9b37524acf76dcca13d",  # vision VRAM tip
    "cdaf5f8f1b9b04a523c6945e47d6f401dea5ab5496435105d7c2a3ef7e16a72a",  # vision config-file reads
}
# v0.1.39+ `setup --parallel N` (#465): this branch writes cfg["parallel"] = N and prints parallel_note, which warns when
# N exceeds stock's recommendation for the card. Skipped unless a profile asks for N; then run with its helpers.
OPT_IN_PARALLEL_0_1_39 = "6d789cd7488f160093167c544558c9d609c3a67793ff8d1218d2023fe01b05b7"
# v0.1.40.2+ helpers run as written (they loop): the batch-slot recommendation, the host recommendations setup
# prints (bench_tips), and v0.1.41's pure remote-cache argv helper. Any other loop body needs review.
REVIEWED_HELPERS_0_1_40_2 = {
    "83d3be46740af7da81d5970eaf49f18cd6a0d7af216842a559522a365e2508e4": "parallel_slot_gb",
    "bd6464642b3d20c90163b62c31bce5db6ca111e08239e45159aa2ba6c29d9d4a": "parallel_recommend",
    "052170339e9d51a2bddab62c6e20971dfcf333d26efd65dd7e97a0774c58a14e": "parallel_note",
    "86c45949c37a778c3178a4b30ff9d38e90295ab5591fe9c468f83841c7d42a46": "arg_after",
    "0e6beeb447ed6cf8769b27897cc0b4ba7bc9ec5195cb754f9b3d5a7f42d4a672": "bench_tips",
    "e80eccadcb01a1ab2ef3c5ea7f11b7a78dddc38f80b9acf361d37b9b97ba9af5": "recommend_remote_expert_opt",
}

# v0.1.40.1 hardware probes only gate advisory text at these exact AST statements.
# Admit the fixed probe values there only: changed callers (including new args/config work) must be reviewed.
FIXED_ADVISORY_PROBES_0_1_40_1 = {
    "db734fd045c027dd76ab2e3d5dc88f4edf2137a550713409b43d457e5ea20444",  # NVIDIA display tip
    "c8af7e748d5ff4796367e59127a73e674efa645c7c6a1dbd8422ccb88da68850",  # two-socket CPU tip
}

# v0.1.41's compute-mode warning only prints advice. The exact block includes a GPU loop/comprehension; its
# nvidia-smi input is fixed to Default, never probed. Changed callers or config/argv work must be reviewed.
FIXED_ADVISORY_PROBES_0_1_41 = {
    "a8e3adc24adae21c4d9d894aa2946bf91b4ac709e69ca384ca7ad137e3233c0c",
}

# Calculated from stock v0.1.42 setup.py. Only these exact GPU-selection bodies and default-choice
# statements may use sorting/comprehensions; pure_exec's general vocabulary stays unchanged.
REVIEWED_HELPERS_0_1_42 = {
    "68de8b17af7d72acb3260cdb8e70ebf4b5f23d09fc3e3abecb7606341087bab9": "gpu_rank",
    "9a78218294d52eb4c7267d50d6a02b749e1c33b0c0a3005c683c5f7d73940be8": "gpu_problem",
    "0280b65dc632a00d2b468cee8038ac5192a5e175d8a0e31f3170355c79f01b12": "together_ok",
    "fcfa532fd9740bee74e874564bb74b5bb835a035baf09ff9ad55c1d99cfc1a9d": "ram_ctx",
}
NON_PLANNING_BRANCHES_0_1_42 = {
    "7e62c49f55a04d5f8f5166816ddaa2813f3951e04c0d1355a191dc671f49912a",  # budget/UMA cache
    "c3ab07cc6573542ca2ab2c5bc8c695ed3d4b433f7b2c4647d243574e25b7aa82",  # opt-in replicas
}
DEFAULT_RECOMMENDATION_0_1_42 = "75fc9ff7085dea1e76e7117a7ecb020e0031d84269ee2ae356fe1ee53d8145fa"

# v0.1.44.1's fresh native NVIDIA GSQ-RCO lane only. New families remain unreviewed planning choices.
LITERAL_ALIASES_0_1_44 = frozenset({"NVFP4_GPTQ_REPO", "NVFP4_NVIDIA_REPO", "NVFP4_ENGINE"})
REVIEWED_HELPERS_0_1_44 = {
    "99dfd16d7a1dd0e422937d2cc39672a4dd306abd200916a2203fc7e14330f42c": "menu_families",
    "7a4b3888290f6d48182077e576268e917de118a2013c9af51f8eaec0405695f5": "recommended_size",
    "4d458b460202b78075f65ceb27c54e97915c900454684646f2438a47c33361f7": "unsloth_default_env",
}
NON_PLANNING_BRANCHES_0_1_44 = {
    "641e2ed7e15d487bc62521d721249ef69fcd0f064f0abcfbb30c8ee2a6e57c45",  # Windows has no rotational PLE probe
    "ae2070346ba43fbc5ef19da544091eae0bdc8967d80807b0c3b58ac0f960634d",  # Unsloth small-card adjustments
    "f2d7eae39c8fd58054a7ef4b0f76e532f015399e8382e41465c1be88027ee52f",  # opt-in image generation
    "3f076786963aadc1082582b2854a688a239f88eb89fe938a994649e47f79e827",  # opt-in image encoder config reads
}
DEFAULT_RECOMMENDATION_0_1_44 = "0bf50970e8ac2a274d3c383151ba4c3afc9193e03e15ee9e770a435ce9645a90"
INSTALLED_SIZE_0_1_44_1 = "4617c3c1d892d4d821704f5598fe8fe948b50cdf6c3a85ff4156cfc0a4158b70"
INSTALLED_CHOICE_0_1_44_1 = "266017f4d237909f12544749bdb6cb49c26a0159316c2562c95af6ddca35dc5c"
MODEL_ARGS_0_1_44 = "114b39b35e9831de7bbf86e245e3fa38473ad7dff3771927811e3c330e9093de"

# v0.2.1 (90767252): aliases must themselves be literal, never executable expressions.
LITERAL_ALIASES_0_2_1 = frozenset({"GYRO_ENGINE", "FP4LOCAL_ENGINE", "NVFP4_FP4LOCAL_REPO"})
# v0.2.1: pure planning arithmetic and informational defaults; no probes, IO or new model lanes.
REVIEWED_HELPERS_0_2_1 = {
    "6f6bac81a839e0ff0e636054c16f048598663333ac46726727beafa093dd6792": "recommend_pool_workers",  # cap 32
    "99150f1129d9c7158ec4b19b8490a0995f89f6cc484a2ce5cbddd7fef9f0770f": "low_ram_gpu_gb",  # MTP reserve
    "7ff4dd53d9a16b28961b91db83b5d2608957d5050c19ad8e3212fec6347c4d74": "low_ram_resident",
    "7da744402ac7c3994d19e240bdd5e281280c284701c4afa72bbb73efb00f884e": "recommended_size",
    "2b1f2cca41fcd31bef072318b43fffd7a7c06c158ec60060cfd74ac4757fedb0": "tier_pick",
    "13af7ed5d68db25191660cbde09dc0e22921275e5fab9c49f81652acea92eb73": "low_ram_vram",
    "99cd2a689047c6ef55cf67442a28387e774ca6a36d60324e702ceb94ec03fe60": "mem_have",
    # Fixed native-mode selection: CONTROL=False, _CONTROL_HOME=None, WIN=True; never ambient probes.
    "cbfc662321930eff04bd8da6f4562f709260d3b7834ce366ef0b10b357ca1b02": "home",
    "427d6d949caa5627c9004d6360996e4af17bbfdaf544c4791a3f10840ee67dab": "engine_exe",
    "a74279cda5834968e151a05a091eb45de1d3e3e5ac65f8c95ad3058f59ea81ff": "ple_ram_platform_ok",
}
# v0.2.1 unreachable IO/opt-ins: their entire guards must stay false in the native text-only fresh root.
NON_PLANNING_BRANCHES_0_2_1 = {
    "7fde91d2d79db871240a3619ad7c0c353df7daf4234eae537cf49d7410e61962",  # vision argv/advice
    "97790878814d4a015f347dd200e547f0070f54498654efd76775ccc5c3ceb22e",  # HIP tuning directory IO
    "cb66727ec1b2a04989af14de85d683415e39b4b7d0bc220da5b8cd59c9da793c",  # explicit MTP opt-in/out
    "9499c8eff6209e1c93a0a7589c89a0db3c3daba285840af46c12f79a063bb8c1",  # vision config IO
}
DEFAULT_RECOMMENDATION_0_2_1 = "ca0dbfc6feb30ed72337ab4af81268f15c5c9dd706511846070be360209ebe52"
TIER_CHOICE_0_2_1 = "d31a8ddf4b3440eef6170191a7ce79c4a6bd929361f7e73fd348a380579e92a7"
CONFIG_0_2_1 = "0f11dbb087a3a533d2ddcb23bb12cd845d8214ac5fede1a7dc2d448fb412ac80"  # fixed native paths
PLE_DISK_0_2_1 = "8d67ae066a0689bee978ed6cfb88b8ed272742820ed1794a796377a3557a3887"  # both IO guards false
PREP_DISK_0_2_1 = "8fefc825ebd599703c976feebf90874800c5f2902b0881a641076a3dd3a08d00"  # ready=False, no IO
DISK_0_2_1 = "fe5a78a38d49d0ac5023889f0d2d5adbfbc0e52ceaf219718b38497a9038bdc6"  # pure byte arithmetic
CPU_RECOMMENDATION_0_2_1 = "858a850c5ae584523738295e6d88b725df5031f1cbbb21204f921eefe3174436"
# v0.2.1 advisory-only: pool_workers_note reads CPU layout just for text. Never execute that probe.
POOL_NOTE_0_2_1 = "eb7b4089ef70723df2ac5bd9c0da02621ac87ffa0d1ccd5991ce61f0f59314bc"
# v0.2.1 fresh-root write projection: no earlier config, no explicit reserve, no user_args; stamp copies args.
# These IO helpers are checked, NEVER executed. Changed bodies require another review, not a guessed projection.
FRESH_WRITE_0_2_1 = {
    "write_setup_config": "c7a21347e0566ec6e13ebb82293991f94c46cba50ed1abed7d178a4d6e2f35d2",
    "carry_user_args": "e5590cc9119f0959f0736051784ee8c454b7509d27c99c3bc7f440eba2a8abfc",
    "explicit_args": "3741fe9aa1d10b8f5c3f08f6ce1e0cf6812f1e47bf3e2220d00d368a240ca4d2",
}
WRITE_CALL_0_2_1 = "8e63dba773ae3d32c9049449b6c4cf096c5f7d00fe7ba0e52684550bd6daec36"
# v0.2.1 adds the ready-pack embedding GGUF; that arm and tensor-file IO stay unreachable.
# Only its unchanged GSQ argv assignment is evaluated, exactly as for v0.1.44.1.
MODEL_ARGS_0_2_1 = "761d638da675088223e4501b3d319de8585925b7c4aa0cb53a579d07e7671b36"
# v0.2.1 user_args module: pure argv grouping/capture/stamp; fresh capture({}, ...) is empty and stamp copies args.
# Draft checks the complete module AST before relying on the fresh-write projection (no module code is executed).
USER_ARGS_0_2_1 = "e1f02bc46dfc4edd0c16a82300c327ff9e7d964a084bcc0e3bafd8f2d5e68efa"

# v0.2.2 (011c9e60), reviewed in docs/UPSTREAM.md: gpu_sel normalizes our scalar/list inputs;
# remote-cache advice remains unchanged for plain layer splits. No general pure_exec vocabulary is widened.
REVIEWED_HELPERS_0_2_2 = {
    "bbf4d50f7683de5f42d446b0d0802982f9d60c44a0a204392bfffa4d48906646": "gpu_sel",
    "6bfb60fef7092efb584a2fc052f25f8b84d3863debe02040004d5f041ce9b672": "recommend_remote_expert_opt",
    "5d41bbc51e005e058d63fce392b97711180d75409745ac6adde4fbe93306ee91": "tier_pick",
}
# Both role guards must be false: explicit --gpus returns before interactive Main/Helper/Off selection.
MULTI_CONFIG_0_2_2 = "360bbac44ee628d2e82295b28dc2d9fd9418fc4f37d7bcd3a995922fbf3d5e9c"
ROLES_CONFIG_0_2_2 = "5ec2fe77b9c37e2282f3e716df9f4f8373fa705e25051f0f2b5b1f60b3d96f84"
# Exact margin, real, need assignments as one module: retain need (real + margin), never run free_gb.
DISK_0_2_2 = "73b0a4fd10c9cfb5ad90e732694f5bbbb275f963f9724db13211d51b6ee43312"
# Only set_flag's multi-value editing changed; fresh capture/stamp is unchanged. Never execute this module.
USER_ARGS_0_2_2 = "625e4282ba491b97cd8073a9c687acc90023ecb115233cd123eb6a36b7b717ae"


def reviewed_hash(node) -> str:
    """SHA-256 of a statement's full AST dump, the same on every supported Python.

    Python 3.13 made `ast.dump` omit None and empty-list fields unless `show_empty=True`; 3.12 always prints them.
    The reviewed hashes above are of the full form, so CI (3.12) and dev-env (3.13) admit the same statements.
    """
    full = {"show_empty": True} if sys.version_info >= (3, 13) else {}
    return sha256_bytes(ast.dump(node, include_attributes=False, **full).encode())


def run_reviewed(tree, names, ns) -> None:
    """Define stock helpers whose loops pure_exec refuses, each only as its reviewed body."""
    for name in names:
        node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), None)
        helpers = (REVIEWED_HELPERS_0_1_40_2 | REVIEWED_HELPERS_0_1_42 | REVIEWED_HELPERS_0_1_44
                   | REVIEWED_HELPERS_0_2_1 | REVIEWED_HELPERS_0_2_2)
        if node is None or helpers.get(reviewed_hash(node)) != name:
            raise Incomplete(f"stock {name} is missing or changed; review required")
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<stock-setup-helper>", "exec",
                     flags=__import__("__future__").annotations.compiler_flag), ns)


class Incomplete(ValueError):
    """Metadata cannot establish a complete answer or an immutable pin."""


def version(tag):
    parsed = release_version(tag)
    if parsed is None:
        raise Incomplete(f"not a supported release tag: {tag}")
    return (*parsed[:3], parsed[3] if len(parsed) == 4 else -1, 0 if prerelease_tag(tag) else 1)


def auth_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=10)
            token = result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            pass
    return token


def urllib_transport(url, headers):
    """Transport contract: return (decoded JSON, lower-case response headers), or raise."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
        size = response.headers.get("Content-Length")
        if len(raw) > 16 * 1024 * 1024 or (size is not None and len(raw) != int(size)):
            raise Incomplete("truncated API response")
        return json.loads(raw), {k.lower(): v for k, v in response.headers.items()}


class API:
    def __init__(self, transport=urllib_transport, token=None):
        self.transport, self.token = transport, token

    def get(self, url):
        if not url.startswith((GITHUB + "/", HF + "/api/")):
            raise Incomplete("unexpected metadata origin")
        headers = {"Accept": "application/json", "User-Agent": "omp-strata-upstream-watch"}
        if url.startswith(GITHUB + "/"):
            headers["X-GitHub-Api-Version"] = "2022-11-28"
            if self.token:
                headers["Authorization"] = "Bearer " + self.token
        try:
            return self.transport(url, headers)
        except (OSError, ValueError, TimeoutError, http.client.HTTPException) as exc:
            raise Incomplete(f"API response unavailable or incomplete ({type(exc).__name__})") from None

    def pages(self, url):
        rows, seen = [], set()
        origin = urllib.parse.urlsplit(url).netloc
        for _ in range(50):
            if url in seen or urllib.parse.urlsplit(url).netloc != origin:
                raise Incomplete("invalid API pagination")
            seen.add(url)
            data, headers = self.get(url)
            if not isinstance(data, list):
                raise Incomplete("API list missing")
            rows.extend(data)
            links = re.findall(r'<([^>]+)>;\s*rel="next"', headers.get("link", ""))
            if not links:
                # A full requested page without pagination metadata is not evidence of the end.
                if len(data) >= 100:
                    raise Incomplete("full API page without a next/end boundary")
                return rows
            if len(links) != 1 or not data:
                raise Incomplete("inconsistent API pagination")
            url = links[0]
        raise Incomplete("API pagination limit reached")

    def commit(self, repo, tag):
        version(tag)
        data, _ = self.get(f"{GITHUB}/repos/{repo}/git/ref/tags/{tag}")
        obj = data.get("object", {}) if isinstance(data, dict) else {}
        if not isinstance(obj, dict) or not SHA40.fullmatch(str(obj.get("sha", ""))):
            raise Incomplete(f"{repo} {tag}: tag ref has no immutable object SHA")
        if obj.get("type") == "commit":
            return obj["sha"], None
        if obj.get("type") != "tag":
            raise Incomplete(f"{repo} {tag}: tag must point to a commit or an annotated tag")
        annotated, _ = self.get(f"{GITHUB}/repos/{repo}/git/tags/{obj['sha']}")
        peeled = annotated.get("object", {}) if isinstance(annotated, dict) else {}
        if (not isinstance(annotated, dict) or annotated.get("sha") != obj["sha"]
                or annotated.get("tag") != tag or not isinstance(peeled, dict)
                or peeled.get("type") != "commit" or not SHA40.fullmatch(str(peeled.get("sha", "")))):
            raise Incomplete(f"{repo} {tag}: annotated tag identity or commit target is invalid")
        return peeled["sha"], obj["sha"]

    def assets(self, repo, tag, names):
        release, _ = self.get(f"{GITHUB}/repos/{repo}/releases/tags/{tag}")
        if (not isinstance(release, dict) or release.get("tag_name") != tag or release.get("draft") is not False
                or release.get("prerelease") is not False or prerelease_tag(tag)
                or not isinstance(release.get("id"), int)):
            raise Incomplete(f"{repo} {tag}: stable published release missing")
        assets = self.pages(f"{GITHUB}/repos/{repo}/releases/{release['id']}/assets?per_page=100")
        out = {}
        for name in names:
            hits = [a for a in assets if isinstance(a, dict) and a.get("name") == name]
            if len(hits) != 1:
                raise Incomplete(f"{repo} {tag}: asset {name} missing or duplicated")
            a = hits[0]
            digest = str(a.get("digest", ""))
            url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
            if (not digest.startswith("sha256:") or not SHA256.fullmatch(digest[7:])
                    or type(a.get("size")) is not int or a["size"] <= 0 or a.get("browser_download_url") != url):
                raise Incomplete(f"{repo} {tag}: asset {name} has no complete immutable pin")
            out[name] = {"url": url, "file": name, "bytes": a["size"], "sha256": digest[7:],
                         "sha256_source": f"GitHub release asset digest for {repo} {tag}"}
        return out


SOURCE_IDENTITY = ("repository", "release_id", "tag", "peeled_commit", "tag_object_sha", "assets", "published_at",
                   "prerelease", "github_prerelease", "github_immutable")


def frozen_inventory(rows, repo, tag):
    """Freeze every asset, including publisher-unhashed objects which are not installable pins."""
    if not isinstance(rows, list) or not rows:
        raise Incomplete("release assets unavailable")
    assets, names, identifiers = [], set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise Incomplete("release asset identity unavailable")
        name, identifier, size, digest = (row.get(key) for key in ("name", "id", "size", "digest"))
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
                or name in names or type(identifier) is not int or identifier <= 0 or identifier in identifiers
                or type(size) is not int or size <= 0 or row.get("state") != "uploaded"):
            raise Incomplete("release asset identity/size unavailable or duplicated")
        if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)):
            raise Incomplete("release asset publisher digest is invalid")
        url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
        if row.get("browser_download_url") != url:
            raise Incomplete("release asset download URL does not match its source identity")
        names.add(name)
        identifiers.add(identifier)
        assets.append({"id": identifier, "name": name, "bytes": size,
                       "sha256": digest[7:] if digest is not None else None, "url": url})
    return sorted(assets, key=lambda asset: asset["name"])


def discover_release(api, repo, tag, *, allow_prerelease=False):
    """Cross-check both release identities, all asset pages and the tag before/after discovery."""
    version(tag)
    base = f"{GITHUB}/repos/{repo}"
    release, _ = api.get(f"{base}/releases/tags/{urllib.parse.quote(tag, safe='')}")
    if (not isinstance(release, dict) or release.get("tag_name") != tag
            or type(release.get("id")) is not int or release["id"] <= 0
            or type(release.get("draft")) is not bool or type(release.get("prerelease")) is not bool):
        raise Incomplete("release identity/flags unavailable")
    if release["draft"]:
        return {"state": "skipped", "tag": tag, "reason": "draft"}
    prerelease = release["prerelease"] or prerelease_tag(tag)
    if prerelease and not allow_prerelease:
        return {"state": "skipped", "tag": tag, "reason": "prerelease"}
    if (type(release.get("immutable")) is not bool
            or schema_errors(release.get("published_at"), {"type": "string", "format": "date-time"})):
        raise Incomplete("release publication time/immutability flag unavailable")
    commit, tag_object = api.commit(repo, tag)
    assets = frozen_inventory(api.pages(f"{base}/releases/{release['id']}/assets?per_page=100"), repo, tag)
    if frozen_inventory(release.get("assets"), repo, tag) != assets:
        raise Incomplete("release asset listing is incomplete or changed during discovery")
    by_id, _ = api.get(f"{base}/releases/{release['id']}")
    fields = ("id", "tag_name", "published_at", "draft", "prerelease", "immutable")
    if (not isinstance(by_id, dict)
            or any(type(by_id.get(key)) is not type(release[key]) or by_id.get(key) != release[key] for key in fields)
            or frozen_inventory(by_id.get("assets"), repo, tag) != assets
            or api.commit(repo, tag) != (commit, tag_object)):
        raise Incomplete("release identity or tag changed during discovery")
    return {"repository": repo, "release_id": release["id"], "tag": tag, "peeled_commit": commit,
            "tag_object_sha": tag_object, "assets": assets, "published_at": release["published_at"],
            "prerelease": prerelease, "github_prerelease": release["prerelease"],
            "github_immutable": release["immutable"]}


def assert_same_release(frozen, snapshot):
    """Historical schema-1 evidence stays byte-for-byte intact; new records bind asset IDs too."""
    if frozen.get("schema_version") == 1:
        expected = {key: snapshot[key] for key in SOURCE_IDENTITY[:7]}
        expected["assets"] = [{"name": asset["name"], "size": asset["bytes"],
                               "digest": "sha256:" + asset["sha256"] if asset["sha256"] else None}
                              for asset in snapshot["assets"]]
        keys = SOURCE_IDENTITY[:7]
    else:
        expected, keys = snapshot, SOURCE_IDENTITY
    if any(frozen.get(key) != expected[key] for key in keys):
        raise Incomplete("moved tag or changed release/assets: frozen evidence was not modified")


def check_frozen_release(root, snapshot):
    path = root / "releases/campaigns" / (snapshot["tag"] + ".json")
    if path.exists():
        assert_same_release(read_json(path), snapshot)


def select_strata_assets(snapshot, *, platform="windows-x86_64", backend="cuda", variant=None):
    """Select package names, not a runnable profile or a claim about an unobserved host's driver."""
    assets = snapshot["assets"]
    legacy = [a for a in assets if a["name"] == "strata-windows-x64.zip"]
    if legacy:
        if len(legacy) != 1 or platform != "windows-x86_64" or backend != "cuda" or variant not in (None, "cuda13"):
            raise Incomplete("legacy single-zip lane is Windows x86_64 CUDA 13 only")
        return {"layout": "single-zip", "engine": legacy[0]}
    if platform != "windows-x86_64" or backend != "cuda" or variant not in ("cuda12", "cuda13"):
        raise Incomplete("component selection requires Windows x86_64, cuda and an explicit cuda12/cuda13 variant")
    engines = []
    for asset in assets:
        engine = re.fullmatch(r"strata-engine-([0-9]+[.][0-9]+[.][0-9]+(?:[.][0-9]+)?)-"
                              + re.escape(f"{platform}-{backend}-{variant}") + r"\.tar\.gz", asset["name"])
        if engine:
            engines.append((engine[1], asset))
    if len(engines) != 1:
        raise Incomplete("engine component tarball is missing or ambiguous")
    component_version, engine = engines[0]
    return {"layout": "components", "component_version": component_version, "platform": platform,
            "backend": backend, "variant": variant, "engine": engine}


def artifact_pin(snapshot, asset):
    if asset["sha256"] is None:
        raise Incomplete(f"{asset['name']}: no complete immutable pin for installation")
    return {"url": asset["url"], "file": asset["name"], "bytes": asset["bytes"], "sha256": asset["sha256"],
            "sha256_source": f"GitHub release asset digest for {snapshot['repository']} {snapshot['tag']}"}


def git(src, *args):
    result = subprocess.run(["git", "-C", str(src), *args], capture_output=True, text=True,
                            stdin=subprocess.DEVNULL, timeout=30)
    if result.returncode:
        raise Incomplete("local Strata revision or source file unavailable")
    return result.stdout


def literal_constants(source, names):
    assignments = {node.targets[0].id: node.value for node in ast.parse(source).body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name)}
    class LiteralAliases(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id not in LITERAL_ALIASES_0_1_44 | LITERAL_ALIASES_0_2_1:
                return node
            return ast.parse(repr(ast.literal_eval(assignments[node.id])), mode="eval").body
    out = {}
    for name in names:
        if name in assignments:
            try:
                out[name] = ast.literal_eval(LiteralAliases().visit(copy.deepcopy(assignments[name])))
            except (ValueError, TypeError, KeyError):
                raise Incomplete(f"setup constant {name} is no longer literal") from None
    missing = set(names) - out.keys()
    if missing:
        raise Incomplete("missing setup constants: " + ", ".join(sorted(missing)))
    return out


def assigned(node, name):
    return (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name)


def pure_exec(nodes, namespace):
    """Fail closed before executing only setup's arithmetic/config assembly, never its main or imports.

    This intentionally small vocabulary needs review when stock setup changes. There is no filesystem,
    network, subprocess or import primitive in the resulting namespace.
    """
    # v0.1.40.2: gfx_arch_is is a pure arch-string comparison reached only on the HIP lane, like hipblaslt_table; this
    # planner fixes hip=False, so neither is loaded or executed.
    named_calls = {"str", "float", "int", "round", "len", "max", "min", "ValueError", "ok", "warn", "is_wsl", "hf",
                   "low_ram_gpu_gb", "low_ram_needed", "low_ram_resident", "ctx_ram_need", "resolve_rope",
                   "derived_factor", "resident_budget_gib", "budget_choice", "hipblaslt_table", "gfx_arch_is",
                   "small_card_note", "desktop_reserve_note", "linux_desktop", "say", "cpu_cores",
                   "hybrid_pool_workers", "recommend_pool_workers", "model_file", "model_shards",
                   "recommend_remote_expert_opt", "isinstance", "rotational_disk", "kv_streaming_ram_gb",
                   "two_socket_note", "compute_mode_warning", "unsloth_default_env"}
    for node in nodes:
        digest = reviewed_hash(node)
        fixed_advisory_probe = digest in FIXED_ADVISORY_PROBES_0_1_40_1
        fixed_compute_mode_probe = digest in FIXED_ADVISORY_PROBES_0_1_41
        for sub in ast.walk(node):
            if isinstance(sub, (ast.For, ast.comprehension)) and not (
                    fixed_compute_mode_probe or (isinstance(sub, ast.For) and isinstance(sub.iter, ast.Call)
                    and isinstance(sub.iter.func, ast.Name)
                    and sub.iter.func.id in {"small_card_note", "desktop_reserve_note", "two_socket_note"})):
                raise Incomplete("stock setup planning loop is unreviewed; review required")
            if isinstance(sub, (ast.Import, ast.ImportFrom, ast.With, ast.While, ast.Try, ast.Global,
                                ast.Nonlocal, ast.Delete, ast.Lambda)):
                raise Incomplete("stock setup planning block now performs non-planning work; review required")
            if isinstance(sub, ast.Attribute) and sub.attr.startswith("_"):
                raise Incomplete("unsupported private attribute in stock planning")
            if isinstance(sub, ast.Attribute) and sub.attr == "environ":
                raise Incomplete("stock setup planning reads the ambient environment; review required")
            if isinstance(sub, ast.Call):
                safe = ((isinstance(sub.func, ast.Name) and (sub.func.id in named_calls
                         or (fixed_advisory_probe and sub.func.id in {"gpu_drives_display", "cpu_sockets"})
                         or (fixed_compute_mode_probe and sub.func.id == "gpu_compute_mode")))
                        or (isinstance(sub.func, ast.Attribute) and sub.func.attr in
                            ("get", "lower", "setdefault", "cpu_count", "ceil", "index", "append", "join",
                             "format", "remove", "startswith")))
                if not safe:
                    raise Incomplete("new call in stock setup planning; review required")
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, "<stock-setup-planning>", "exec", flags=__import__("__future__").annotations.compiler_flag),
         namespace)


def planning_cards(tree, ns, inventory, selection):
    """Validate sanitized facts and execute only stock's reviewed NVIDIA split selection."""
    if not isinstance(inventory, list) or len(inventory) < 2:
        raise Incomplete("multi-GPU planning requires an inventory of at least two cards")
    fields = {"index", "name", "arch", "vram_mib", "pci_bus_id", "display_attached"}
    indices, buses, cards = set(), set(), []
    for card in inventory:
        if (not isinstance(card, dict) or set(card) != fields
                or type(card.get("index")) is not int or card["index"] < 0
                or not isinstance(card.get("name"), str)
                or not re.fullmatch(r"NVIDIA [ -~]+", card["name"])
                or not isinstance(card.get("arch"), str) or not re.fullmatch(r"[1-9][0-9]{1,2}", card["arch"])
                or int(card["arch"]) < 75
                or type(card.get("vram_mib")) is not int or card["vram_mib"] <= 0
                or not isinstance(card.get("pci_bus_id"), str)
                or not re.fullmatch(r"[0-9a-f]{8}:[0-9a-f]{2}:[0-1][0-9a-f]\.[0-7]", card["pci_bus_id"])
                or type(card.get("display_attached")) is not bool):
            raise Incomplete("invalid or unsupported sanitized GPU inventory card")
        if card["index"] in indices or card["pci_bus_id"] in buses:
            raise Incomplete("GPU inventory indices and PCI bus ids must be unique")
        indices.add(card["index"])
        buses.add(card["pci_bus_id"])
        cards.append({**card, "vram_gb": card["vram_mib"] / 1024, "count": len(inventory)})
    run_reviewed(tree, ("gpu_rank", "gpu_problem", "together_ok"), ns)
    if selection == "all":
        chosen = ns["together_ok"](cards)
    else:
        if (not isinstance(selection, list) or len(selection) < 2
                or any(type(i) is not int or i < 0 for i in selection)
                or len(set(selection)) != len(selection) or not set(selection) <= indices):
            raise Incomplete("--gpus must name at least two distinct inventory indices")
        selected = [card for card in cards if card["index"] in selection]
        problems = [ns["gpu_problem"](card, together=True) for card in selected]
        if any(problems):
            raise Incomplete("stock setup refuses the selected cards: " + next(p for p in problems if p))
        chosen = ns["together_ok"](selected)
        order = [card["index"] for card in chosen]
        if selection != order:
            raise Incomplete(f"explicit GPU order is not stock gpu_rank order; stock order: {order}")
    if len(chosen) < 2 or any(card["vram_gb"] < 20 for card in chosen):
        raise Incomplete("multi-GPU variant needs at least two >=20 GiB cards; small-card planning is unreviewed")
    return chosen


def stock_default_recommendation(tree, ns):
    """Expose v0.1.42's native NVIDIA defaults as data, never as draft model choices."""
    body = next(n.body for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    nodes = [n for n in body if any(assigned(n, name) for name in ("fams", "names", "rec", "small", "rec_ctx"))
             or (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name)
                 and n.value.func.value.id == "names" and n.value.func.attr == "sort")]
    families = [n for n in ast.walk(tree) if assigned(n, "rec_fam")]
    if len(families) != 1:
        raise Incomplete("stock default recommendation moved; review required")
    nodes.insert(1, families[0])
    digest = reviewed_hash(ast.Module(body=nodes, type_ignores=[]))
    if digest not in {DEFAULT_RECOMMENDATION_0_1_42, DEFAULT_RECOMMENDATION_0_1_44, DEFAULT_RECOMMENDATION_0_2_1}:
        raise Incomplete("stock default recommendation changed; review required")
    defaults = dict(ns)
    if digest in {DEFAULT_RECOMMENDATION_0_1_44, DEFAULT_RECOMMENDATION_0_2_1}:
        installed = [n for n in body if assigned(n, "installed")]
        helper = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "installed_size"), None)
        if (len(installed) != 1 or reviewed_hash(installed[0]) != INSTALLED_CHOICE_0_1_44_1
                or helper is None or reviewed_hash(helper) != INSTALLED_SIZE_0_1_44_1):
            raise Incomplete("stock installed-size default changed; review required")
        # A fresh isolated root has no installed configs. Never execute installed_size's config-file reads.
        defaults["installed"] = None
        run_reviewed(tree, ("menu_families", "recommended_size"), defaults)
    if digest == DEFAULT_RECOMMENDATION_0_2_1:
        tier = [n for statement in body for n in ast.walk(statement) if assigned(n, "tier")]
        if len(tier) != 1 or reviewed_hash(tier[0]) != TIER_CHOICE_0_2_1:
            raise Incomplete("stock tier default changed; review required")
        run_reviewed(tree, ("tier_pick", "low_ram_vram", "mem_have"), defaults)
        exec(compile(ast.Module(body=tier, type_ignores=[]), "<stock-tier>", "exec"), defaults)
    run_reviewed(tree, ("ram_ctx",), defaults)
    def execute(statements):
        exec(compile(ast.Module(body=statements, type_ignores=[]), "<stock-defaults>", "exec"), defaults)
    execute(nodes[:1])
    # The reviewed family expression's else arm: native NVIDIA is never Strix Halo. No hardware helper runs.
    defaults["family"] = eval(compile(ast.Expression(families[0].value.orelse),
                                      "<stock-default-family>", "eval"), defaults)
    execute(nodes[2:5])
    defaults["model"] = defaults["names"][int(defaults["rec"]) - 1]
    defaults["low_ram"] = defaults["low_ram_needed"](defaults["model"], defaults["ram"])
    execute(nodes[5:])
    return {"family": defaults["family"], "model": defaults["model"], "context": defaults["rec_ctx"],
            "source": "stock setup default questions (native NVIDIA); informational, not selected"}


def stock_plan(source, *, family, model, context, ram, vram=None, kv="int8", gpu=None, port=18090, reviewed=True,
               cpu_cores=None, parallel=None, tips=False, gpu_inventory=None, gpus=None, engine_version=None):
    """Evaluate stock pure choices and config assembly for Windows NVIDIA single-card or layer-split plans.

    No setup main/import is executed. A context past the trained 262144 gets stock resolve_rope's default (yarn,
    factor context / 262144, experimental upstream). Other backends, calibration measurements, vision and low-RAM
    need their own reviewed planner; this draft lane refuses them instead of silently degrading a variant.
    `parallel` plans stock `--parallel N` (refused where stock warns about N for this card); `tips` also returns the
    engine flags stock setup's printed host recommendations name for this host (`stock_tips`) and the RAM they need.
    True selects every printed tip; a mapping selects only its flag keys, for inherited profile decisions.
    """
    tree = ast.parse(source)
    multi_input = gpu_inventory is not None or gpus is not None
    if multi_input and (gpu is not None or vram is not None):
        raise Incomplete("cannot mix scalar gpu/vram with multi-GPU inventory/gpus inputs")
    if multi_input and (gpu_inventory is None or gpus is None):
        raise Incomplete("multi-GPU planning requires both gpu_inventory and gpus")
    if not multi_input:
        gpu = 0 if gpu is None else gpu
        if type(gpu) is not int or gpu < 0 or not isinstance(vram, (int, float)) or isinstance(vram, bool):
            raise Incomplete("single-GPU planning requires a nonnegative index and scalar VRAM")
    constants = literal_constants(source, ("MODELS", "HF_REVISIONS", "LOW_RAM_HEADROOM_GB", "MIN_DRIVER",
                                          "MIN_ENGINE", "RESIDENT_ENGINE", "CONTEXTS"))
    ns = dict(constants, math=SimpleNamespace(ceil=math.ceil),
              __builtins__={"str": str, "float": float, "int": int, "round": round, "len": len,
                            "max": max, "min": min, "ValueError": ValueError, "isinstance": isinstance, "list": list,
                            "sum": sum, "any": any, "enumerate": enumerate, "dict": dict,
                            "sorted": sorted, "bool": bool, "tuple": tuple})
    current_lane = tuple(constants["MIN_ENGINE"]) >= (0, 1, 42)
    gsq_lane = tuple(constants["MIN_ENGINE"]) >= (0, 1, 44)
    component_lane = tuple(constants["MIN_ENGINE"]) >= (0, 1, 45)
    if component_lane:
        coder = (family, model) == ("coder", "IQ1_M") and context in (131072, 262144)
        qwen = (family, model, context) == ("qwen", "IQ3_S", 262144)
        if (kv != "int8" or not (
                coder and not multi_input and 30 <= vram <= 33 and parallel is None and cpu_cores is None
                or qwen and not multi_input and 90 <= vram <= 100 and parallel == 4 and cpu_cores == (8, 16)
                or qwen and multi_input and parallel is None and cpu_cores is None)):
            raise Incomplete("v0.2.1 planning is reviewed only for the 5090 coder, PRO slots4 and 4090+3090 lanes")
    if engine_version is not None and (not isinstance(engine_version, tuple) or not engine_version
                                      or any(type(n) is not int or n < 0 for n in engine_version)
                                      or engine_version < tuple(constants["MIN_ENGINE"])):
        raise Incomplete("component engine version is below MIN_ENGINE or invalid")
    if gsq_lane and (family, model) not in {("qwen", "IQ3_S"), ("coder", "IQ1_M")}:
        raise Incomplete("v0.1.44 planning is reviewed only for qwen IQ3_S and coder IQ1_M")
    if multi_input and not current_lane:
        raise Incomplete("multi-GPU planning requires the reviewed stock v0.1.42 lane")
    if current_lane and constants["MODELS"].get(model, {}).get("budget"):
        raise Incomplete("v0.1.42 budget planning is unreviewed")
    # v0.1.40.1: literal KV byte counts feed arithmetic; the display reserve is advisory text only.
    optional_constants = {"UNSLOTH_SHARDS", "UNSLOTH_IQ4_XS_SHARDS", "UNSLOTH_RAM_LEFT_GB", "SMALL_CARD_GB",
                          "DRAFT_VOCAB_MIB", "DESKTOP_RESERVE_MIB", "REMOTE_EXPERT_OPT", "KV_CELL_BYTES",
                          "DISPLAY_RESERVE_MIB", "HELPER_CACHE_FLAGS", "SPLIT_MIN_VRAM_GB",
                          "UNSLOTH_BIG_SHARDS", "RECOMMENDED_SIZES", "MEMORY_TIERS", "MTP_VRAM_GB",
                          "POOL_WORKERS_CAP", "GYRO_FILES", "TIER_SYSTEM_RESERVE_GB"}
    ns.update(literal_constants(source, {name for name in optional_constants
                                         if any(assigned(node, name) for node in tree.body)}))
    if "TIER_SYSTEM_RESERVE_GB" in ns and (
            type(ns["TIER_SYSTEM_RESERVE_GB"]) is not float or ns["TIER_SYSTEM_RESERVE_GB"] != 5.0):
        raise Incomplete("stock informational tier reserve changed; review required")
    selected = planning_cards(tree, ns, gpu_inventory, gpus) if multi_input else []
    if component_lane and selected and [card["name"] for card in selected] != [
            "NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 3090"]:
        raise Incomplete("v0.2.1 layer split is reviewed only for the RTX 4090 + RTX 3090 pair")
    if selected:
        gpu, vram = selected[0]["index"], selected[0]["vram_gb"]
    ns["hf"] = lambda repo: f"{HF}/{repo}/resolve/{constants['HF_REVISIONS'][repo]}/"
    families = next((n for n in tree.body if assigned(n, "FAMILIES")), None)
    pure_names = {"low_ram_needed", "low_ram_gpu_gb", "low_ram_resident", "ctx_ram_need", "resolve_rope",
                  "derived_factor"}
    # Reviewed advisory/argv and per-model shard arithmetic only; never load the hardware or IO helpers.
    pure_names |= {n.name for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name in {"small_card_note", "desktop_reserve_note", "hybrid_pool_workers",
                                  "recommend_pool_workers", "model_file", "model_shards",
                                  "recommend_remote_expert_opt"}}
    # kv_streaming_ram_gb is byte-count arithmetic; two_socket_note and v0.1.41's compute_mode_warning only build text.
    pure_names |= {n.name for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name in {"kv_streaming_ram_gb", "two_socket_note", "compute_mode_warning"}}
    if constants["MODELS"].get(model, {}).get("budget"):
        pure_names |= {"resident_budget_gib", "budget_choice"}
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in pure_names]
    if families is None or {f.name for f in funcs} != pure_names:
        raise Incomplete("stock pure planning functions missing")
    # v0.1.41 adds any(a.split(...) for a in args) to this pure helper. Admit that exact body through the existing
    # reviewed-helper mechanism, not any/split/comprehensions in pure_exec's general vocabulary.
    remote_opt = next((f for f in funcs if f.name == "recommend_remote_expert_opt"), None)
    if remote_opt is not None and (REVIEWED_HELPERS_0_1_40_2 | REVIEWED_HELPERS_0_2_2).get(
            reviewed_hash(remote_opt)) == remote_opt.name:
        funcs.remove(remote_opt)
        if reviewed_hash(remote_opt) in REVIEWED_HELPERS_0_2_2:
            if "TIER_SYSTEM_RESERVE_GB" not in ns:
                raise Incomplete("stock informational tier reserve missing; review required")
            run_reviewed(tree, ("gpu_sel",), ns)
        run_reviewed(tree, (remote_opt.name,), ns)
    if gsq_lane:
        run_reviewed(tree, ("unsloth_default_env",), ns)
    if component_lane:
        changed = {"recommend_pool_workers", "low_ram_gpu_gb", "low_ram_resident"}
        run_reviewed(tree, changed | {"home", "engine_exe", "ple_ram_platform_ok"}, ns)
        funcs = [f for f in funcs if f.name not in changed]
    pure_exec([families, *funcs], ns)
    if (model not in ns["MODELS"] or family not in ns["FAMILIES"] or context not in ns["CONTEXTS"]
            or context <= 8192 or kv not in ("int8", "q4_0")):
        raise Incomplete("variant outside the reviewed text-only planning surface")
    spec, fam = ns["MODELS"][model], ns["FAMILIES"][family]
    budget_model = bool(spec.get("budget"))
    if family not in spec.get("families", ("qwen", "swift")):
        raise Incomplete("model/family unsupported by stock setup")
    if (not math.isfinite(ram) or not math.isfinite(vram) or vram < 20
            or (ns["low_ram_needed"](model, ram) if not budget_model else ram < spec["ram_gb"])):
        raise Incomplete("variant requires low-RAM mode or a smaller GPU; not silently degraded")
    need = ns["ctx_ram_need"](model, context, False)
    if need is not None and need > ram:
        raise Incomplete("variant exceeds stock setup's RAM recommendation")
    scaling, scale = ns["resolve_rope"](context, None, None)
    shard_count = ns["model_shards"](fam, model) if "model_shards" in ns else fam.get("shards", 2)
    model_files = [ns["model_file"](fam, model, i) if "model_file" in ns else fam["file"].format(q=model, i=i)
                   for i in range(1, shard_count + 1)]
    body = next(n.body for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    starts = [i for i, n in enumerate(body) if assigned(n, "args")]
    ends = [i for i, n in enumerate(body) if assigned(n, "cfg_path")]
    if len(starts) != 1 or not any(i > starts[0] for i in ends):
        raise Incomplete("stock config assembly moved; review required")
    end = next(i for i in ends if i > starts[0])
    notes, warnings = [], []
    scratch = Path("/tmp/omp-strata-plan")  # Paths are assembled, never created or opened.
    ns.update(family=family, model=model, fam=fam, ctx=context, ram=ram, kv=kv, low_ram=False,
              resident=False, budget=None, q4_split=False, vision="none", esp=None, hip=False,
              ready=False, in_budget=False,
              multi=[card["index"] for card in selected], draft_vocab=None,
              scaling=scaling, rope_scale=scale, eng=scratch / "engine", EXE="strata.exe", ROOT=scratch,
              pack=scratch / "pack", shards=[scratch / f"shard{i}" for i in range(1, shard_count + 1)],
              ple=scratch / "shard2",
              rt=scratch / "mtp", tag=fam["tag"] + model, lib_dirs=[], port=port,
              gpu=selected[0] if selected else {"index": gpu, "count": 1, "vram_gb": vram},
              engine_ver=engine_version or tuple(constants["MIN_ENGINE"]),
              CONTROL=False, _CONTROL_HOME=None,
              a=SimpleNamespace(low_ram="off", kv_streaming="auto", resident_budget_gib=None, gpu=gpu,
                                vram_reserve_mib=None, browser=None, parallel=parallel, vision_tokens=None,
                                host="127.0.0.1", api_key=None, layer_split="auto",
                                no_remote_expert_opt=False, replicas=None, images=None, mtp=None, _roles=None),
              ok=notes.append, say=notes.append, warn=warnings.append, is_wsl=lambda: False,
              WIN=True, linux_desktop=lambda: False)  # Fixed native Windows lane; no ambient environment reads.
    # The host's (performance, efficiency) physical cores as stock cpu_cores() counts them: a planning input like RAM
    # and VRAM, never read from the planning machine. None: cores all alike. Install refuses a host whose stock
    # setup plans another --pool-workers.
    ns["cpu_cores"] = lambda: cpu_cores
    ns["cuda_tk"] = 13  # CUDA-12 hosts are outside this RTX 30/40/50, driver >= 580 lane; install refuses their config.
    ns["rotational_disk"] = lambda path: None  # Stock returns None on Windows; never probe the planning host's disk.
    # v0.1.40.1: these probes only gate tips, never args/config. Suppress the display tip and use unknown sockets;
    # never run nvidia-smi or the planning machine's CPU topology probe. Exact callsites above enforce that boundary.
    ns["gpu_drives_display"] = lambda gpu: False
    ns["cpu_sockets"] = lambda: None
    ns["gpu_compute_mode"] = lambda index: "Default"  # Exact v0.1.41 advisory block only; never run nvidia-smi.
    ns["chosen"] = selected or [ns["gpu"]]
    default_recommendation = stock_default_recommendation(tree, ns) if current_lane else None
    if default_recommendation:
        notes.append("Stock host default (informational, draft choices unchanged): "
                     f"{default_recommendation['family']} {default_recommendation['model']}, "
                     f"{default_recommendation['context']} tokens.")
    if budget_model:
        choices = [n for n in ast.walk(tree) if assigned(n, "budget") and isinstance(n.value, ast.Call)
                   and isinstance(n.value.func, ast.Name) and n.value.func.id == "budget_choice"]
        if len(choices) != 1 or "UNSLOTH_RAM_LEFT_GB" not in ns:
            raise Incomplete("stock RAM budget choice moved; review required")
        pure_exec(choices, ns)
    if gsq_lane:
        model_args = [n for n in body[:starts[0]] if isinstance(n, ast.If)
                      and any(assigned(branch, "model_args") for branch in n.orelse)]
        if len(model_args) != 1 or reviewed_hash(model_args[0]) != (MODEL_ARGS_0_2_1 if component_lane else MODEL_ARGS_0_1_44):
            raise Incomplete("stock GSQ-RCO model arguments changed; review required")
        # Evaluate only the reviewed GGUF argv expression, not its tensor-file lookup or the ready-pack arm.
        pure_exec([n for n in model_args[0].orelse if assigned(n, "model_args")], ns)
    parallel_planned = False
    for node in body[starts[0]:end]:
        digest = reviewed_hash(node)
        if digest == OPT_IN_PARALLEL_0_1_39:
            if parallel is not None:
                ns.update(literal_constants(source, ("PARALLEL_MAX", "PARALLEL_SHARE", "PARALLEL_HELD",
                                                     "PARALLEL_COST_NOTE")))
                run_reviewed(tree, ("parallel_slot_gb", "parallel_recommend", "parallel_note"), ns)
                exec(compile(ast.Module(body=[node], type_ignores=[]), "<stock-setup-parallel>", "exec"), ns)
                parallel_planned = True
        elif digest == PLE_DISK_0_2_1 and component_lane:
            # v0.2.1 disk and SSD/PLE IO are unreachable on Windows; check BOTH guards, not just `disk`.
            if ns["disk"] or ns["ple_ram_platform_ok"]():
                raise Incomplete("stock PLE planning requires an unreviewed platform")
        elif digest == CONFIG_0_2_1 and component_lane:
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<stock-native-config>", "exec"), ns)
        elif digest in {MULTI_CONFIG_0_2_2, ROLES_CONFIG_0_2_2} and component_lane:
            role = node.body[2] if digest == MULTI_CONFIG_0_2_2 else node
            # getattr is permitted only for this exact false guard, never in the general planner namespace.
            if eval(compile(ast.Expression(role.test), "<stock-no-roles>", "eval"),
                    {"__builtins__": {"getattr": getattr}, "a": ns["a"]}):
                raise Incomplete("stock setup requires unreviewed GPU roles; review required")
            if digest == MULTI_CONFIG_0_2_2 and ns["multi"]:
                pure_exec(node.body[:2] + node.body[3:], ns)
        elif digest in (NON_PLANNING_BRANCHES_0_1_39 | NON_PLANNING_BRANCHES_0_1_42 |
                        NON_PLANNING_BRANCHES_0_1_44 | NON_PLANNING_BRANCHES_0_2_1):
            # Only these exact reviewed guards can bypass validation of their unreachable IO/opt-in bodies.
            if eval(compile(ast.Expression(node.test), "<stock-setup-lane>", "eval"), ns):
                raise Incomplete("stock setup requires an unreviewed planning lane")
            pure_exec(node.orelse, ns)
        else:
            pure_exec([node], ns)
    if parallel is not None and not parallel_planned:
        raise Incomplete("stock setup --parallel branch is missing or changed; review required")
    if "recommend_pool_workers" in pure_names:
        recommendations = [n for n in body[end + 1:] if isinstance(n, ast.If)
                           and any(isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                                   and sub.func.id == "recommend_pool_workers"
                                   for branch in n.orelse for sub in ast.walk(branch))]
        if (len(recommendations) != 1
                or ast.dump(recommendations[0].test) != ast.dump(ast.parse("cal is not None", mode="eval").body)):
            raise Incomplete("stock CPU worker recommendation moved; review required")
        # A fresh isolated install has no saved calibration. Evaluate its whole default branch, never its IO sibling.
        if component_lane:
            note = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "pool_workers_note"), None)
            if (reviewed_hash(recommendations[0]) != CPU_RECOMMENDATION_0_2_1
                    or note is None or reviewed_hash(note) != POOL_NOTE_0_2_1):
                raise Incomplete("stock CPU advice changed; review required")
            # Only the first assignment changes cfg; the two loops are advisory CPU topology probes.
            pure_exec(recommendations[0].orelse[:1], ns)
        else:
            pure_exec(recommendations[0].orelse, ns)
    cfg = ns["cfg"]
    if component_lane:
        for name, expected in FRESH_WRITE_0_2_1.items():
            node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), None)
            if node is None or reviewed_hash(node) != expected:
                raise Incomplete(f"stock fresh-config {name} changed; review required")
        writes = [n for n in body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                  and isinstance(n.value.func, ast.Name) and n.value.func.id == "write_setup_config"]
        if len(writes) != 1 or reviewed_hash(writes[0]) != WRITE_CALL_0_2_1:
            raise Incomplete("stock fresh-config write call changed; review required")
        cfg["args_written"] = list(cfg["args"])
    if warnings:
        raise Incomplete("stock setup warns about the requested variant: " + warnings[0])
    setup_args = {"family": family, "model": model, "context": context, "kv": kv, "vision": "no",
                  "experimental_speed_projection": "off", "low_ram": "off",
                  **({"gpus": ns["multi"], "layer_split": "auto"} if selected else {"gpu": gpu}),
                  **({"parallel": parallel} if parallel else {})}
    if (cfg.get("gpu") != (ns["multi"] if selected else gpu) or cfg.get("gpus_asked") is not True
            or (cfg.get("layer_split") != "auto" if selected else "layer_split" in cfg)):
        raise Incomplete("stock setup GPU selection or layer split changed; review required")
    if reviewed and set(cfg) != generated_config_keys(setup_args, args_written=component_lane):
        raise Incomplete("stock setup writes unreviewed config keys")
    if selected and "--remote-expert-opt" in cfg["args"]:
        raise Incomplete("plain stock layer split unexpectedly enables a helper-cache flag; review required")
    stock_tips, tips_ram = None, None
    if tips:
        # The host recommendations stock setup prints after writing this config (text only; nothing changes unless
        # the user adds the named flags to the config's args). Pinned tips are the engine flags they name.
        names = ("PREFILL_BIG_RAM_GB", "PREFILL_RISK_RAM_GB", "HEADROOM_RAM_GB", "AGENT_CACHE_FREE_GB",
                 "AGENT_CACHE_MIB", "SMALL_VISION_VRAM_GB")
        ns.update(literal_constants(source, names))
        run_reviewed(tree, ("arg_after", "bench_tips"), ns)
        printed = ns["bench_tips"](cfg["args"], cfg.get("env"), ram, spec["ram_gb"], vram, "none", True)
        cache = f"tip: for several agents or clients at once, --conversation-cache-mib {ns['AGENT_CACHE_MIB']} in"
        stock_tips = {}
        if any(t.startswith(cache) for t in printed):
            stock_tips["--conversation-cache-mib"] = str(ns["AGENT_CACHE_MIB"])
        if any(t.startswith("tip: with ") and "--prefill auto:32768 in the config's args" in t for t in printed):
            stock_tips["--prefill"] = "auto:32768"
        if tips is not True:
            stock_tips = {flag: value for flag, value in stock_tips.items() if flag in tips}
        # The RAM each printed tip assumes: its own threshold on the PC's RAM, and the cache's budget free at start.
        tips_ram = {"min_total_ram_gib": max([math.ceil(ns["PREFILL_BIG_RAM_GB"])] * ("--prefill" in stock_tips)
                                             + [math.ceil(spec["ram_gb"] + ns["AGENT_CACHE_FREE_GB"])]
                                             * ("--conversation-cache-mib" in stock_tips), default=0),
                    "extra_available_ram_gib": math.ceil(ns["AGENT_CACHE_MIB"] / 1024)
                    * ("--conversation-cache-mib" in stock_tips)}
    # Evaluate setup's own fresh-install disk formula, reserving the larger CPU-pack branch on either CPU.
    disk_nodes = [n for n in body if assigned(n, "need")
                  and any(isinstance(x, ast.Name) and x.id == "to_fetch" for x in ast.walk(n.value))]
    split_disk = [body[i:i + 3] for i, node in enumerate(body) if assigned(node, "margin")]
    if component_lane and split_disk:
        if len(split_disk) != 1 or reviewed_hash(ast.Module(body=split_disk[0], type_ignores=[])) != DISK_0_2_2:
            raise Incomplete("stock split disk estimate changed; review required")
        disk_nodes = split_disk[0]
    elif len(disk_nodes) != 1:
        raise Incomplete("stock disk estimate moved; review required")
    if component_lane:
        prep = [n for n in body if assigned(n, "prep_gb")]
        if (len(prep) != 1 or reviewed_hash(prep[0]) != PREP_DISK_0_2_1
                or (not split_disk and reviewed_hash(disk_nodes[0]) != DISK_0_2_1)):
            raise Incomplete("stock component disk estimate changed; review required")
        # The reviewed ready-pack condition is false in both GSQ lanes, so prepared_done never runs.
        exec(compile(ast.Module(body=prep, type_ignores=[]), "<stock-disk-choice>", "exec"), ns)
    # v0.1.40.1 counts existing pack/MTP files: a new profile has a fresh root, so both are absent; never probe disk.
    ns.update(to_fetch=spec["download_gb"], avx512=True, pack_bin=False, mtp_have=False)
    disk_choices = []
    if any(isinstance(n, ast.Name) and n.id == "q2_avx" for node in disk_nodes for n in ast.walk(node)):
        disk_choices = [n for n in body[:starts[0]] if assigned(n, "q2_avx")]
        if len(disk_choices) != 1:
            raise Incomplete("stock Q2 disk choice moved; review required")
        # Stock q2_avx combines model/family with the reviewed worst-case avx512=True; no ambient CPU flags or IO.
    pure_exec([*disk_choices, *disk_nodes], ns)
    path_flags = {"--pack", "--native", "--ple-gguf", "--expert-profile", "--mtp"}
    flags, args = [], iter(cfg["args"])
    for arg in args:
        if arg in path_flags:
            next(args)
        else:
            flags.append(arg)
    streaming = "--kv-resident" in cfg["args"]
    kv_ram = ns["kv_ram_gb"] if streaming else 0
    if streaming:
        total = max(spec["arena_gb"] + constants["LOW_RAM_HEADROOM_GB"],
                    spec["ram_gb"] + kv_ram + 1, need or 0)
        available = spec["ram_gb"] + kv_ram
    else:
        # Stock leaves KV in VRAM when its RAM test fails; that is not a degraded expert mode.
        # Keep the no-low-RAM and no-paging-warning boundaries, with the same headroom free at start.
        total = max(spec["arena_gb"] + constants["LOW_RAM_HEADROOM_GB"], spec["ram_gb"] - 4, need or 0)
        available = total
    budget_plan = None
    if budget_model:
        # Setup subtracts the streamed KV and its OS/engine/file-cache reserve before rounding the budget.
        # Preserve that reserve at start too; counting only MODELS.ram_gb would understate a large budget.
        total = max(spec["ram_gb"] + kv_ram + (1 if streaming else 0),
                    ns["budget"] + ns["UNSLOTH_RAM_LEFT_GB"] + math.ceil(kv_ram))
        available = ns["budget"] + kv_ram + ns["UNSLOTH_RAM_LEFT_GB"]
        budget_plan = {"ram_gib": ram, "vram_gib": vram, "resident_budget_gib": ns["budget"],
                       "kv_ram_gb": kv_ram, "ram_headroom_gib": ns["UNSLOTH_RAM_LEFT_GB"],
                       "arena_gb": spec["arena_gb"]}
    extra_streamed_ram = (len(selected) * (parallel or 1) - 1) * kv_ram if selected and streaming else 0
    total += extra_streamed_ram
    available += extra_streamed_ram
    if selected:
        notes.append(f"Calculated conservative streamed-session RAM reservation: {extra_streamed_ram:g} GiB "
                     f"extra for {len(selected)} cards x {parallel or 1} slot(s); shared expert arena counted once. "
                     "Not measured; qualify against G21 observations.")
        if total > ram:
            raise Incomplete("planning RAM is below the calculated conservative multi-GPU requirement")
    requirements = [{"gpu_index": card["index"], "gpu_model": card["name"], "arch": card["arch"],
                     "pci_bus_id": card["pci_bus_id"], "min_gpu_vram_mib": card["vram_mib"],
                     "display_attached": card["display_attached"]} for card in selected]
    return {"setup_args": setup_args,
            "expected_engine_flags": flags, "model_name": cfg["model_name"], "config_keys": sorted(cfg),
            "stock_tips": stock_tips, "tips_ram": tips_ram,
            "host": {"min_total_ram_gib": math.ceil(total),
                     "min_available_ram_gib_at_start": math.ceil(available),
                     "min_free_disk_gib": math.ceil(ns["need"] * 1e9 / 2**30),
                     "min_driver_major": constants["MIN_DRIVER"], **({"gpus": requirements} if selected else {})},
            "model_url": fam["hf"].format(q=model),
            "model_files": model_files,
            "model_hashes": fam.get("sha256", {}), "budget_plan": budget_plan,
            "thresholds": {"low_ram_below": spec["arena_gb"] + constants["LOW_RAM_HEADROOM_GB"],
                           "kv_streaming_from": spec["ram_gb"] + ns["kv_ram_gb"] + 1,
                           "arena_gb": spec["arena_gb"], "fresh_disk_gb": ns["need"],
                           **({"extra_streamed_session_ram_gib": extra_streamed_ram,
                               "streamed_session_count": len(selected) * (parallel or 1)} if selected else {})},
            **({"stock_default_recommendation": default_recommendation} if default_recommendation else {}),
            "notes": notes}


def env_names(src, tag):
    """Inventory tracked text, using only read-only git show (not the checkout's working files)."""
    pending, files = [""], []
    while pending:
        folder = pending.pop()
        listing = git(src, "show", f"{tag}:{folder}").split("\n\n", 1)
        if len(listing) != 2:
            raise Incomplete("cannot inventory Strata tree")
        for name in listing[1].splitlines():
            path = folder + name
            if name.endswith("/"):
                pending.append(path)
            elif Path(name).suffix in (".py", ".cpp", ".cu", ".h", ".hpp", ".cuh", ".sh", ".bat"):
                files.append(f"{tag}:{path}")
    found = set()
    for start in range(0, len(files), 80):
        found.update(re.findall(r'["\'](STRATA_[A-Z][A-Z0-9_]*)["\']',
                                git(src, "show", *files[start:start + 80])))
    return found


def classified_routes():
    g = realhost_gates
    return {"GET": set(g.G13_PROTECTED_GET) | set(g.G13_PUBLIC_GET) | set(g.G13_PUBLIC_STATIC)
                   | set(g.G13_ABSENT_GET), "POST": set(g.G13_PROTECTED_POST) | set(g.G13_KEY_ONLY_POST),
            "OPTIONS": set()}


def checklist(src, old, new):
    version(old)
    version(new)
    snapshots = []
    for tag in (old, new):
        source = git(src, "show", f"{tag}:setup.py")
        raw_routes = routes(git(src, "show", f"{tag}:serve/server.py"))
        classified = classified_routes()
        route_set = {m: sorted({p or "/" for p in ps}) for m, ps in raw_routes.items()}
        # Optional writes stay visible as well as the exact keys for our text-only NVIDIA configuration.
        optional = set()
        for node in ast.walk(ast.parse(source)):
            if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store)
                    and isinstance(node.value, ast.Name) and node.value.id == "cfg"
                    and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
                optional.add(node.slice.value)
        component_lane = tuple(literal_constants(source, ("MIN_ENGINE",))["MIN_ENGINE"]) >= (0, 1, 45)
        plan = stock_plan(source, family="coder", model="IQ1_M", context=131072,
                          ram=45 if component_lane else 64, vram=32000 / 1024 if component_lane else 24,
                          reviewed=False)
        snapshots.append({"tag": tag, "constants": literal_constants(source, CONSTANTS),
                          "requirements_blob": git(src, "rev-parse", f"{tag}:requirements.txt").strip(),
                          "generated_config_keys": plan["config_keys"],
                          "conditional_generated_config_keys": sorted(optional & {"layer_split", "parallel"}),
                          "other_config_writes": sorted(optional - GENERATED_CONFIG_KEYS - {"layer_split", "parallel"}),
                          "routes": route_set,
                          "unclassified_routes": {m: sorted(set(ps) - classified.get(m, set()))
                                                  for m, ps in route_set.items()
                                                  if m not in classified or set(ps) - classified[m]},
                          "env_names": sorted(env_names(src, tag))})
    before, after = snapshots
    changes = {key: {"before": before["constants"][key], "after": after["constants"][key]}
               for key in CONSTANTS if before["constants"][key] != after["constants"][key]}
    return {"pinned": before, "candidate": after, "changed_constants": changes,
            "requirements_unchanged": before["requirements_blob"] == after["requirements_blob"],
            "config_keys_changed": before["generated_config_keys"] != after["generated_config_keys"],
            "routes_changed": before["routes"] != after["routes"],
            # A route the pinned release serves that the candidate's census no longer finds: removed upstream, or
            # moved where the census cannot see it (v0.1.40.2's POST dispatch, until `routes` followed delegation).
            "lost_routes": {m: sorted(set(ps) - set(after["routes"].get(m, ())))
                            for m, ps in before["routes"].items() if set(ps) - set(after["routes"].get(m, ()))},
            "new_env_names": sorted(set(after["env_names"]) - set(before["env_names"])),
            "removed_env_names": sorted(set(before["env_names"]) - set(after["env_names"]))}


def item_state(item, kind):
    if not isinstance(item, dict) or item.get("state") not in ("open", "closed"):
        raise Incomplete("tracked item state missing")
    if kind == "pulls":
        if type(item.get("merged")) is not bool:
            raise Incomplete("tracked PR merge status missing")
        if item["merged"]:
            return "merged"
        if item["state"] == "closed":
            return "closed-unmerged (check maintainer commit)"
    return item["state"]


def report(api, root, watch, *, strata_src=None, pinned_tag=None, strata_tag=None):
    result = {"schema_version": 1, "complete": True, "news": False, "releases": {}, "tracked": [], "errors": []}
    def incomplete(where, exc):
        result["complete"] = False
        result["errors"].append(f"{where}: {exc}")
        if where in REPOS:
            result["releases"][where] = {"state": "unavailable", "reason": str(exc)}
    pins = {}
    try:
        profiles = []
        for path in sorted((root / "profiles").glob("*.json")):
            # Profile status is an immutable draft identity even after qualification.
            # Only the release manifest establishes qualification; a newer draft is not a baseline.
            try:
                manifest_text = (root / "releases" / path.stem / "manifest.json").read_text()
            except FileNotFoundError:
                continue
            manifest = json.loads(manifest_text)
            if not isinstance(manifest, dict):
                raise Incomplete("release manifest unavailable")
            if manifest.get("status") == "qualified":
                profiles.append(json.loads(path.read_text()))
        if not profiles:
            raise Incomplete("no qualified release manifests")
        for component in REPOS:
            pins[component] = max((p[component]["tag"] for p in profiles
                                   if not prerelease_tag(p[component]["tag"])), key=version)
    except (OSError, ValueError, KeyError) as exc:
        incomplete("profiles", type(exc).__name__)
    for component, repo in REPOS.items():
        try:
            if component not in pins:
                raise Incomplete("no pinned tag")
            rows = api.pages(f"{GITHUB}/repos/{repo}/releases?per_page=100")
            newer, skipped = [], []
            for row in rows:
                if (not isinstance(row, dict) or not isinstance(row.get("tag_name"), str)
                        or type(row.get("draft")) is not bool or type(row.get("prerelease")) is not bool):
                    raise Incomplete("release metadata missing")
                if row["draft"] or row["prerelease"] or prerelease_tag(row["tag_name"]):
                    skipped.append({"tag": row["tag_name"], "reason": "draft" if row["draft"] else "prerelease"})
                    continue
                if (not isinstance(row.get("published_at"), str) or not row["published_at"]
                        or not isinstance(row.get("html_url"), str) or not row["html_url"]):
                    raise Incomplete("release publication metadata missing")
                if version(row["tag_name"]) > version(pins[component]):
                    newer.append({"tag": row["tag_name"], "url": row.get("html_url"),
                                  "published_at": row.get("published_at")})
            result["releases"][component] = {
                "state": "update" if newer else "no_update", "pinned": pins[component],
                "newer": sorted(newer, key=lambda r: version(r["tag"])), "skipped": skipped,
            }
            result["news"] |= bool(newer)
        except (Incomplete, KeyError, TypeError) as exc:
            incomplete(component, exc)
    for entry in watch["tracked"]:
        try:
            repo, kind, number = entry["repository"], entry["kind"], entry["number"]
            if repo not in REPOS.values() or kind not in ("issues", "pulls") or type(number) is not int:
                raise Incomplete("invalid tracked item")
            item, _ = api.get(f"{GITHUB}/repos/{repo}/{kind}/{number}")
            state = item_state(item, kind)
            changed = state != entry["state"]
            result["tracked"].append({**entry, "state": state, "changed": changed,
                                      "url": f"https://github.com/{repo}/{kind.replace('pulls', 'pull')}/{number}"})
            result["news"] |= changed
        except (Incomplete, KeyError, TypeError) as exc:
            incomplete("tracked item", exc)
    if strata_src:
        try:
            old = pinned_tag or pins["strata"]
            newer = result["releases"].get("strata", {}).get("newer", [])
            new = strata_tag or (newer[-1]["tag"] if newer else old)
            result["checklist"] = checklist(strata_src, old, new)
            if result["checklist"]["lost_routes"]:
                raise Incomplete("route census lost routes the pinned release serves; review required")
        except (Incomplete, KeyError, ValueError, TypeError, NameError, StopIteration) as exc:
            incomplete("checklist", exc)
    result["exit_code"] = 4 if not result["complete"] else 3 if result["news"] else 0
    result["state"] = "unavailable" if not result["complete"] else "update" if result["news"] else "no_update"
    return result


def hf_files(api, plan):
    match = re.fullmatch(r"https://huggingface.co/(.+)/resolve/([0-9a-f]{40})/(.*)", plan["model_url"])
    if not match:
        raise Incomplete("stock model URL is not pinned")
    repo, revision, folder = match.groups()
    rows = api.pages(f"{HF}/api/models/{repo}/tree/{revision}/{folder.rstrip('/')}?limit=100")
    files = []
    for name in plan["model_files"]:
        path = folder + name
        matches = [r for r in rows if r.get("path") == path]
        if len(matches) != 1:
            raise Incomplete("pinned model shard missing or duplicated")
        row = matches[0]
        lfs = row.get("lfs", {})
        if (not SHA256.fullmatch(str(lfs.get("oid", ""))) or type(row.get("size")) is not int
                or row["size"] <= 0 or lfs.get("size") != row["size"]):
            raise Incomplete("pinned model shard has no complete LFS pin")
        provenance = "Hugging Face LFS object id at the pinned revision"
        if plan.get("model_hashes"):
            if plan["model_hashes"].get(name) != (row["size"], lfs["oid"]):
                raise Incomplete("stock setup shard size/SHA-256 differs from pinned Hugging Face LFS metadata")
            provenance = "Stock setup.py UNSLOTH_SHARDS, cross-checked against " + provenance
        files.append({"path": path, "bytes": row["size"], "sha256": lfs["oid"], "sha256_source": provenance})
    return repo, revision, files


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def mtp_pin(source):
    """Read both stock layouts: the earlier literal fallback and the later named pin/hash table."""
    assignments = {n.targets[0].id: n.value for n in ast.parse(source).body
                   if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    pin = assignments.get("PINNED_REVISION")
    if pin is None:
        revision = assignments.get("REVISION")
        if not isinstance(revision, ast.BoolOp) or not isinstance(revision.op, ast.Or):
            raise Incomplete("stock MTP revision is not pinned")
        pin = revision.values[-1]
    revision = ast.literal_eval(pin)
    if not isinstance(revision, str) or not SHA40.fullmatch(revision):
        raise Incomplete("stock MTP revision is not immutable")
    return revision, ast.literal_eval(assignments["SHA256"]) if "SHA256" in assignments else None


def calibrated_flags(flags, settings):
    """Stock calibrate.apply on an engine argv: each DEFAULTS flag removed, then appended with its kept or default
    value (None: no flag)."""
    out = list(flags)
    for flag, default in CALIBRATION_DEFAULTS.items():
        if flag in out:
            i = out.index(flag)
            del out[i:i + 2]
        value = settings.get(flag, default)
        if value is not None:
            out += [flag, value]
    return out


def tipped_flags(flags, tips):
    """The engine argv with stock setup's printed recommendations added as its tips say: a flag's value replaced, or the
    flag appended."""
    out = list(flags)
    for flag, value in tips.items():
        if flag in out[:-1]:
            out[out.index(flag) + 1] = value
        else:
            out += [flag, value]
    return out


def dependency_review(src, old, candidate, constants, prior):
    """v0.2.1 moved only cmake/ninja to build requirements; the unchanged lock remains a verified superset."""
    for key in ("CUDA_WHEELS", "LLAMA_CPP_COMMIT"):
        if constants[key] != prior[key]:
            raise Incomplete(f"{key} changed: cannot reuse predecessor dependency pins")
    before = git(src, "show", f"{old}:requirements.txt")
    after = git(src, "show", f"{candidate}:requirements.txt")
    if constants["PY_PACKAGES"] == prior["PY_PACKAGES"] and before == after:
        return {"status": "unchanged", "lock": "unchanged predecessor bytes and sha256"}
    if constants["PY_PACKAGES"] == prior["PY_PACKAGES"]:
        raise Incomplete("requirements.txt changed: resolve a new lock separately")
    removed = {"cmake", "ninja"}
    if (any(prior["PY_PACKAGES"].count(name) != 1 for name in removed)
            or constants["PY_PACKAGES"] != [name for name in prior["PY_PACKAGES"] if name not in removed]):
        raise Incomplete("PY_PACKAGES changed beyond removal of exactly cmake and ninja")
    def requirements(text):
        return [line.split("#", 1)[0].strip() for line in text.splitlines() if line.split("#", 1)[0].strip()]
    old_lines, new_lines = requirements(before), requirements(after)
    build_lines = [line for line in old_lines if re.fullmatch(r"(?:cmake|ninja)==[0-9][A-Za-z0-9.+-]*", line)]
    if ({line.split("==")[0] for line in build_lines} != removed or len(build_lines) != 2
            or new_lines != [line for line in old_lines if line not in build_lines]
            or sorted(requirements(git(src, "show", f"{candidate}:requirements-build.txt"))) != sorted(build_lines)):
        raise Incomplete("requirements changed beyond moving the same cmake/ninja pins to requirements-build.txt")
    return {"status": "verified-superset", "removed_runtime_packages": sorted(removed),
            "build_requirements": build_lines, "lock": "unchanged predecessor bytes and sha256",
            "note": "CUDA_WHEELS and LLAMA_CPP_COMMIT unchanged; only cmake/ninja moved to build requirements."}


def draft(api, root, predecessor, *, strata_tag, omp_tag, profile_id, strata_src,
          family=None, model=None, context=None, ram=None, vram=None, cpu_cores=None,
          calibration=None, calibration_host=None, calibration_date=None, parallel=None, stock_tips=False,
          gpu_inventory=None, gpus=None, pipeline_windows=None, allow_prerelease=False, check=False,
          platform="windows-x86_64", backend="cuda", variant=None, engine_archive=None):
    if check:
        if not strata_tag:
            raise Incomplete("--release or --strata-tag is required")
        snapshot = discover_release(api, REPOS["strata"], strata_tag, allow_prerelease=allow_prerelease)
        if snapshot.get("state") == "skipped":
            raise Incomplete("release skipped: " + snapshot["reason"] + "; prereleases require --allow-prerelease")
        check_frozen_release(root, snapshot)
        selected = select_strata_assets(snapshot, platform=platform, backend=backend, variant=variant)
        supported = selected["layout"] == "single-zip" or (
            not snapshot["prerelease"] and not prerelease_tag(strata_tag) and variant == "cuda13")
        return {"check": True, "source_release": snapshot, "assets": selected,
                "install_supported": supported,
                "install_note": ("Legacy profile planning still checks source and dependency compatibility."
                                 if selected["layout"] == "single-zip" else
                                 "Stable cuda13 component drafting requires --engine-archive; archive, source and "
                                 "dependency review still applies." if supported else
                                 "Component drafting is supported only for stable cuda13 releases; beta and cuda12 refused.")}
    if not all((predecessor, strata_tag, omp_tag, profile_id, strata_src)):
        raise Incomplete("--from, --release/--strata-tag, --omp-tag, --id and --strata-src are required without --check")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,80}", profile_id):
        raise Incomplete("invalid profile id")
    profile_path, release_dir = root / "profiles" / f"{profile_id}.json", root / "releases" / profile_id
    if profile_path.exists() or release_dir.exists():
        raise Incomplete("profile or release ledger already exists; nothing overwritten")
    snapshot = discover_release(api, REPOS["strata"], strata_tag, allow_prerelease=allow_prerelease)
    if snapshot.get("state") == "skipped":
        raise Incomplete("release skipped: " + snapshot["reason"] + "; prereleases require --allow-prerelease")
    check_frozen_release(root, snapshot)
    selected = select_strata_assets(snapshot, platform=platform, backend=backend, variant=variant)
    component = None
    engine = artifact_pin(snapshot, selected["engine"])
    if selected["layout"] == "components":
        if snapshot["prerelease"] or prerelease_tag(strata_tag):
            raise Incomplete("beta component drafting is refused even with --allow-prerelease; use --check")
        if variant != "cuda13" or engine_archive is None:
            raise Incomplete("stable component drafting requires --variant cuda13 and --engine-archive PATH")
        component = inspect_archive(Path(engine_archive), engine)
        if component["engine_version"] != selected["component_version"]:
            raise Incomplete("component manifest version differs from the selected asset")
    elif engine_archive is not None:
        raise Incomplete("--engine-archive is only for component releases")
    original = load(predecessor)
    data = copy.deepcopy(original.data)
    multi_input = gpu_inventory is not None or gpus is not None
    if multi_input and (gpu_inventory is None or gpus is None or vram is not None):
        raise Incomplete("--gpu-inventory and --gpus must be paired, without scalar --vram-gib")
    if original.multi_gpu and not multi_input:
        raise Incomplete("a multi-GPU predecessor requires fresh --gpu-inventory and --gpus planning inputs")
    if isinstance(gpu_inventory, (str, Path)):
        gpu_inventory = inventory_cards(json.loads(Path(gpu_inventory).read_text(encoding="utf-8")))
    elif isinstance(gpu_inventory, dict):
        gpu_inventory = inventory_cards(gpu_inventory)
    measured = None
    if calibration is not None:
        # Stock tools/calibrate.py's printed result for the install of exactly this predecessor profile.
        measured = json.loads(Path(calibration).read_text(encoding="utf-8"))
        if not isinstance(measured, dict) or set(measured) != {"settings", "report"}:
            raise Incomplete("calibration input is not stock calibrate.py's printed result")
        if not measured["settings"]:
            raise Incomplete("stock calibration kept every default: the predecessor already is the calibrated profile")
        if "calibration" in data["strata"] or (strata_tag, omp_tag) != (data["strata"]["tag"], data["omp"]["tag"]):
            raise Incomplete("a calibration applies only to the uncalibrated profile and tuple it was measured on")
    if data["host"]["os"] != "windows":
        raise Incomplete("only the reviewed native Windows planning lane is supported")
    strata_commit, strata_tag_object = snapshot["peeled_commit"], snapshot["tag_object_sha"]
    omp_commit, omp_tag_object = api.commit(REPOS["omp"], omp_tag)
    if git(strata_src, "rev-parse", f"{strata_tag}^{{commit}}").strip() != strata_commit:
        raise Incomplete("local candidate tag differs from live GitHub commit")
    old = data["strata"]["commit"]
    source = git(strata_src, "show", f"{strata_commit}:setup.py")
    if component and reviewed_hash(ast.parse(git(strata_src, "show", f"{strata_commit}:strata_control/user_args.py"))) not in {
            USER_ARGS_0_2_1, USER_ARGS_0_2_2}:
        raise Incomplete("stock user-args stamping changed; review required")
    if measured is not None:
        stock = literal_constants(git(strata_src, "show", f"{strata_commit}:tools/calibrate.py"), ("DEFAULTS",))
        older_defaults = {k: v for k, v in CALIBRATION_DEFAULTS.items() if not k.startswith("--adapt-")}
        if stock["DEFAULTS"] not in (older_defaults, CALIBRATION_DEFAULTS):
            raise Incomplete("stock calibration DEFAULTS changed; review required")
        if set(measured["settings"]) - set(stock["DEFAULTS"]):
            raise Incomplete("calibration settings are not supported by this stock release")
    old_source = git(strata_src, "show", f"{old}:setup.py")
    constants, prior = literal_constants(source, CONSTANTS), literal_constants(old_source, CONSTANTS)
    dependencies = dependency_review(strata_src, old, strata_commit, constants, prior)
    lock = data["strata"]["python_lock"]
    if sha256_bytes((root / lock["path"]).read_bytes()) != lock["sha256"]:
        raise Incomplete("predecessor Python lock is missing or changed")
    if constants["LLAMA_CPP_COMMIT"] not in data["strata"]["artifacts"]["llama_cpp_archive"]["url"]:
        raise Incomplete("predecessor llama.cpp archive does not pin stock setup's commit")
    setup = data["strata"]["setup_args"]
    # A host fact like the GPU model: given here, else kept from the predecessor; None for cores all alike.
    cores = tuple(cpu_cores) if cpu_cores is not None else tuple(data["host"].get("cpu_cores") or ()) or None
    if cores is not None and measured is not None:
        raise Incomplete("a calibration on a hybrid CPU is unreviewed: stock setup and calibrate both set --pool-workers")
    # Stock setup's opt-ins carry forward like the GPU: batch slots (`--parallel N`; 1 = one at a time) and the engine
    # flags its printed host recommendations name. Both are planned again from this release's setup.
    parallel = setup.get("parallel") if parallel is None else (parallel if parallel >= 2 else None)
    pinned_tips = data["strata"].get("stock_tips") or {}
    want_tips = stock_tips or bool(pinned_tips)
    pinned_pipeline = data["strata"].get("pipeline_windows")
    pipeline_windows = pinned_pipeline if pipeline_windows is None else pipeline_windows
    if pipeline_windows is not None:
        if type(pipeline_windows) is not int or pipeline_windows != 2:
            raise Incomplete("strata.pipeline_windows: exactly the integer 2 required")
        if not multi_input:
            raise Incomplete("strata.pipeline_windows: requires a multi-card layer-split plan")
        if parallel is not None and parallel >= 2:
            raise Incomplete("strata.pipeline_windows: incompatible with --parallel >= 2 (batch slots)")
    plan = stock_plan(source, family=family or setup["family"], model=model or setup["model"],
                      context=context or setup["context"], ram=ram if ram is not None else data["host"]["min_total_ram_gib"],
                      vram=None if multi_input else vram if vram is not None else data["host"]["min_gpu_vram_mib"] / 1024,
                      kv=setup["kv"], gpu=None if multi_input else setup["gpu"],
                      gpu_inventory=gpu_inventory, gpus=gpus, port=data["server"]["port"], cpu_cores=cores,
                      parallel=parallel, tips=pinned_tips or want_tips,
                      engine_version=tuple(int(n) for n in component["engine_version"].split(".")) if component else None)
    if measured is not None:
        # Bind calibration to the measured model/context/topology before composing the explicit stock opt-ins.
        # Slots are a server config key; tips are appended after calibrate.apply, as during install.
        measured_setup = {k: v for k, v in setup.items() if k != "parallel"}
        planned_setup = {k: v for k, v in plan["setup_args"].items() if k != "parallel"}
        measured_flags = tipped_flags(plan["expected_engine_flags"], pinned_tips)
        if pinned_pipeline is not None:
            measured_flags = tipped_flags(measured_flags, {"--pipeline-windows": str(pinned_pipeline)})
        if (planned_setup != measured_setup
                or measured_flags != data["strata"]["expected_engine_flags"]):
            raise Incomplete("stock setup plans a different install than the measured one: recalibrate")
        if original.multi_gpu:
            identity = ("gpu_index", "gpu_model", "arch", "pci_bus_id", "display_attached")
            if ([tuple(card[k] for k in identity) for card in plan["host"]["gpus"]]
                    != [tuple(card[k] for k in identity) for card in original.gpu_requirements]):
                raise Incomplete("stock setup plans different cards than the measured install: recalibrate")
        plan["expected_engine_flags"] = calibrated_flags(plan["expected_engine_flags"], measured["settings"])
    dropped = sorted(set(pinned_tips) - set(plan["stock_tips"] or {}))
    if want_tips:
        if not pinned_tips and not plan["stock_tips"]:
            raise Incomplete("stock setup does not recommend any engine flag for this planning host")
        plan["expected_engine_flags"] = tipped_flags(plan["expected_engine_flags"], plan["stock_tips"])
        host = plan["host"]
        host["min_total_ram_gib"] = max(host["min_total_ram_gib"], plan["tips_ram"]["min_total_ram_gib"])
        host["min_available_ram_gib_at_start"] += plan["tips_ram"]["extra_available_ram_gib"]
    if pipeline_windows is not None:
        plan["expected_engine_flags"] = tipped_flags(plan["expected_engine_flags"],
                                                   {"--pipeline-windows": str(pipeline_windows)})
    platforms = ("windows-x64", "darwin-arm64", "linux-x64")
    names = ["omp-" + p + (".exe" if p == "windows-x64" else "") for p in platforms]
    omp_assets = api.assets(REPOS["omp"], omp_tag, names)
    repo, revision, files = hf_files(api, plan)
    mtp_source = git(strata_src, "show", f"{strata_commit}:tools/mtp_fetch.py")
    mtp_old = git(strata_src, "show", f"{old}:tools/mtp_fetch.py")
    mtp_revision, tensor_hashes = mtp_pin(mtp_source)
    old_revision, old_hashes = mtp_pin(mtp_old)
    if mtp_revision != old_revision or (old_hashes is not None and tensor_hashes != old_hashes):
        raise Incomplete("stock MTP tensors changed: predecessor tensor manifest cannot be reused")
    mtp = data["model"]["mtp_source"]
    if mtp["revision"] != mtp_revision or not SHA256.fullmatch(str(mtp.get("tensor_manifest_sha256", ""))):
        raise Incomplete("MTP tensor manifest does not match stock pinned revision")
    hf_mtp, _ = api.get(f"{HF}/api/models/{mtp['repository']}/revision/{mtp['revision']}")
    if not isinstance(hf_mtp, dict) or hf_mtp.get("sha") != mtp["revision"]:
        raise Incomplete("MTP revision cannot be resolved")
    data.update(profile_id=profile_id, status="draft")
    gpu_description = (" + ".join(card["gpu_model"] for card in plan["host"]["gpus"]) if multi_input
                       else data["host"]["gpu_model"])
    data["description"] = (f"Stock Strata {strata_tag} with stock OMP {omp_tag.removeprefix('v')}; "
                           f"{plan['model_name']} on {gpu_description}, native Windows, text only, "
                           f"{plan['setup_args']['context']:,}-token context. Stock setup-derived thresholds and "
                           "flags; no hardware qualification or inherited receipts.")
    if measured is not None:
        data["description"] += (" Stock calibration pinned: " + " ".join(f"{k} {v}" for k, v in measured["settings"].items())
                                + f" (tools/calibrate.py on {calibration_host}).")
    if parallel or plan["stock_tips"]:
        chosen = ([f"--parallel {parallel}"] if parallel else []) + [f"{k} {v}" for k, v in (plan["stock_tips"] or {}).items()]
        data["description"] += " Stock setup recommendations pinned: " + ", ".join(chosen) + "."
    if pipeline_windows is not None:
        data["description"] += f" Stock pipeline windows pinned: --pipeline-windows {pipeline_windows}."
    if cores is not None:
        data["host"]["cpu_cores"] = list(cores)
        workers = flag_pairs(plan["expected_engine_flags"]).get("--pool-workers")
        data["description"] += (f" Hybrid CPU, {cores[0]} performance + {cores[1]} efficiency cores"
                                + (f": stock --pool-workers {workers}." if workers else
                                   ": no stock --pool-workers (not more efficiency than performance cores)."))
    else:
        data["host"].pop("cpu_cores", None)
    # Round model download estimates upward using the exact freshly resolved sizes.
    disk = plan["thresholds"]["fresh_disk_gb"] + max(0, sum(f["bytes"] for f in files) / 1e9
                                                        - literal_constants(source, ("MODELS",))["MODELS"][plan["setup_args"]["model"]]["download_gb"])
    setup_floors = {**{key: value for key, value in plan["host"].items() if key != "gpus"},
                    "min_free_disk_gib": math.ceil(disk * 1e9 / 2**30)}
    # Setup estimates omit observed integration-root and engine peaks. A tuple bump can raise
    # a predecessor floor, never lower a constraint established while operating that profile.
    host_floors = {key: {"predecessor": data["host"][key], "setup": value,
                         "selected": max(data["host"][key], value)} for key, value in setup_floors.items()}
    if plan["budget_plan"]:
        derivations = {
            "min_total_ram_gib": "ceil(budget + UNSLOTH_RAM_LEFT_GB + ceil(kv_ram_gb)); also at least the "
                                 "stock KV-streaming threshold. This floor preserves setup's planned budget.",
            "min_available_ram_gib_at_start": "ceil(budget + kv_ram_gb + UNSLOTH_RAM_LEFT_GB): the stock "
                                              "reserve covers the OS, engine and file cache beside experts and KV.",
            "min_free_disk_gib": "ceil((max(MODELS.download_gb, exact pinned shard bytes / 1e9) + 8) * 1e9 / "
                                 "2**30): stock fresh-install need, no low-RAM experts.bin or Q2_0 conversion.",
            "min_driver_major": "Stock setup.py MIN_DRIVER for its CUDA runtime."}
        for key, values in host_floors.items():
            values["derivation"] = derivations[key] + " Selected=max(predecessor, setup)."
        data["host_floors"] = host_floors
    else:
        data.pop("host_floors", None)
    data["host"].update({key: values["selected"] for key, values in host_floors.items()})
    if multi_input:
        # Preserve established capacity by exact model, not a potentially renumbered index.
        prior_cards = gpu_requirements(original.data["host"])
        new_cards = copy.deepcopy(plan["host"]["gpus"])
        for card in new_cards:
            card["min_gpu_vram_mib"] = max([card["min_gpu_vram_mib"]] + [old["min_gpu_vram_mib"]
                for old in prior_cards if old["gpu_model"] == card["gpu_model"]])
        for key in ("gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached"):
            data["host"].pop(key, None)
        data["host"]["gpus"] = new_cards
    strata = data["strata"]
    strata.update(tag=strata_tag, commit=strata_commit,
                  engine_version=component["engine_version"] if component else strata_tag.removeprefix("v"),
                  setup_args=plan["setup_args"], expected_engine_flags=plan["expected_engine_flags"], model_name=plan["model_name"])
    if component:
        strata["engine_component"] = component["pin"]
    else:
        strata.pop("engine_component", None)
    if plan["budget_plan"]:
        strata["budget_plan"] = plan["budget_plan"]
    else:
        strata.pop("budget_plan", None)
    if measured is not None:
        strata["calibration"] = {"settings": measured["settings"], "measured_on": calibration_host,
                                 "date": calibration_date, "source_profile": original.id,
                                 "source_fingerprint": original.fingerprint, "report": measured["report"]}
    if plan["stock_tips"]:
        strata["stock_tips"] = plan["stock_tips"]
    else:
        strata.pop("stock_tips", None)
    if pipeline_windows is not None:
        strata["pipeline_windows"] = pipeline_windows
    forbidden = set(strata["forbidden_engine_flags"]) | {"--mmap-experts", "--resident-experts", "--expert-profile-save",
                                                         "--resident-budget-gib", "--draft-vocab"}
    strata["forbidden_engine_flags"] = sorted(forbidden - set(plan["expected_engine_flags"]))
    strata["artifacts"]["engine_archive"] = engine
    data["model"].update(repository=repo, revision=revision, variant=plan["setup_args"]["family"],
                         quantization=plan["setup_args"]["model"], files=files)
    data["omp"].update(tag=omp_tag, version=omp_tag.removeprefix("v"), source_commit=omp_commit,
                       artifacts={p: omp_assets[n] for p, n in zip(platforms, names)},
                       context_window=plan["setup_args"]["context"])
    problems = validate(data)
    if problems:
        raise Incomplete("draft profile rejected: " + "; ".join(problems))
    profile = Profile(path=profile_path, data=data)
    ledger = json.loads((root / "docs/handoff/2026-09-30/acceptance_matrix.json").read_text())
    ledger.update(prepared_date=dt.date.today().isoformat(), profile_id=profile.id,
                  profile_fingerprint=profile.fingerprint, execution_performed=False)
    for gate in ledger["gates"]:
        gate.update(status="not_run", receipts=[], receipt_paths=[], note=None)
    ledger_bytes = json_bytes(ledger)
    manifest = {"schema_version": 1, "candidate_id": profile.id, "status": "draft",
                "profile": {"path": f"../../profiles/{profile.id}.json", "fingerprint": profile.fingerprint},
                "qualification": {"ledger": "qualification.json", "ledger_sha256": sha256_bytes(ledger_bytes)},
                "capabilities": data["capabilities"], "claims": {"comparative_claims": False, "engine_only_comparison": False},
                "install": {"generated_files": [], "runtime_identity_sha256": None},
                "publication_authorized": False, "blockers": ["Draft: no gate has run on this tuple yet."]}
    # Recheck source identity before reserving an append-only result.
    assert_same_release(snapshot, discover_release(api, REPOS["strata"], strata_tag,
                                                  allow_prerelease=allow_prerelease))
    # Reserve both destinations before writing; never open an existing file for replacement.
    release_dir.mkdir()
    try:
        with profile_path.open("xb") as target:
            target.write(json_bytes(data))
    except BaseException:
        release_dir.rmdir()  # Only the empty directory just reserved by this invocation.
        raise
    for name, content in (("qualification.json", ledger_bytes), ("manifest.json", json_bytes(manifest)),
                          ("source-release.json", json_bytes(snapshot))):
        with (release_dir / name).open("xb") as target:
            target.write(content)
    return {"profile": f"profiles/{profile.id}.json", "fingerprint": profile.fingerprint,
            "manifest": f"releases/{profile.id}/manifest.json", "gates": {"not_run": len(ledger["gates"])},
            "planning": plan, "host_floors": host_floors, "dropped_stock_tips": dropped,
            "source_release": snapshot, "dependency_review": dependencies,
            "tag_object_shas": {name: sha for name, sha in (("strata", strata_tag_object), ("omp", omp_tag_object))
                                if sha is not None},
            "omp_declared_context": data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS}


def inventory_cards(document):
    """Read a sanitized list or the complete schema-1 inventory command's document."""
    if isinstance(document, list):
        return document
    # The producer's "complete" means every required identity and capacity fact is present; "missing" can then hold
    # only advisory gaps (PCIe link or compute-mode fields a driver does not report), which planning never reads.
    if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
            or document["schema_version"] != 1 or document.get("complete") is not True
            or not isinstance(document.get("gpus"), list)):
        raise Incomplete("GPU inventory document must be schema 1 and complete")
    cards = []
    for card in document["gpus"]:
        if not isinstance(card, dict):
            raise Incomplete("GPU inventory contains an invalid card")
        cards.append({key: card.get(key) for key in ("index", "name", "arch", "pci_bus_id", "display_attached")}
                     | {"vram_mib": card.get("memory_total_mib")})
    return cards


def gpus_arg(text):
    """argparse type for stock-ranked --gpus all or I,J,... selection."""
    if text == "all":
        return text
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:,(?:0|[1-9][0-9]*))+", text):
        raise argparse.ArgumentTypeError("all or two or more comma-separated nonnegative GPU indices")
    return [int(index) for index in text.split(",")]


def cpu_cores_arg(text):
    """argparse type for --cpu-cores P,E: a hybrid CPU's performance and efficiency physical core counts."""
    match = re.fullmatch(r"([1-9]\d{0,2}),([1-9]\d{0,2})", text)
    if not match:
        raise argparse.ArgumentTypeError("P,E: two positive core counts (omit the option when all cores are alike)")
    return int(match[1]), int(match[2])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    news = sub.add_parser("report", help="JSON stdout; human summary stderr; exit 0/3/4")
    news.add_argument("--strata-src", type=Path)
    news.add_argument("--pinned-strata-tag")
    news.add_argument("--strata-tag")
    create = sub.add_parser("draft", help="append-only unqualified profile and ledger; exit 0/2")
    create.add_argument("--from", dest="predecessor", type=Path)
    create.add_argument("--strata-tag", "--release", dest="strata_tag")
    create.add_argument("--omp-tag")
    create.add_argument("--id", dest="profile_id")
    create.add_argument("--strata-src", type=Path, help="read-only tagged Strata checkout")
    create.add_argument("--allow-prerelease", action="store_true", help="explicit owner-selected prerelease intake")
    create.add_argument("--check", action="store_true", help="print frozen metadata/asset selection; no writes or downloads")
    create.add_argument("--platform", default="windows-x86_64")
    create.add_argument("--backend", default="cuda")
    create.add_argument("--variant", choices=("cuda12", "cuda13"), help="explicit component variant, not host qualification")
    create.add_argument("--engine-archive", type=Path, help="local stable cuda13 component tarball; never downloaded here")
    create.add_argument("--family")
    create.add_argument("--model")
    create.add_argument("--context", type=int)
    create.add_argument("--ram-gib", dest="ram", type=float, help="planning RAM, not the profile's floor")
    create.add_argument("--vram-gib", dest="vram", type=float, help="single-GPU planning only")
    create.add_argument("--gpu-inventory", type=Path, help="sanitized GPU list or complete inventory JSON document")
    create.add_argument("--gpus", type=gpus_arg, help="all or I,J,... in stock gpu_rank order; requires --gpu-inventory")
    create.add_argument("--cpu-cores", type=cpu_cores_arg, metavar="P,E",
                        help="the host's performance and efficiency physical cores as stock setup's cpu_cores() "
                             "counts them (hybrid CPUs; omit when all cores are alike)")
    create.add_argument("--calibration", type=Path,
                        help="stock tools/calibrate.py's printed JSON for the --from profile's install")
    create.add_argument("--calibration-host", help="public label of the host it was measured on")
    create.add_argument("--calibration-date", help="measurement date, YYYY-MM-DD")
    create.add_argument("--parallel", type=int, metavar="N",
                        help="stock setup --parallel N batch slots (refused unless stock recommends N for the card; "
                             "1 = one at a time); default: the predecessor's")
    create.add_argument("--stock-tips", action="store_true",
                        help="pin the engine flags stock setup's printed host recommendations name for the planning "
                             "host (kept from a predecessor that pins them)")
    create.add_argument("--pipeline-windows", type=int, choices=(2,),
                        help="pin stock's decode-capable two-verifier pipeline on a multi-card layer split, without "
                             "batch slots (kept from a predecessor that pins it)")
    args = parser.parse_args(argv)
    api = API(token=auth_token())
    try:
        if args.command == "report":
            result = report(api, ROOT, json.loads((ROOT / "upstream-watch.json").read_text()),
                            strata_src=args.strata_src, pinned_tag=args.pinned_strata_tag, strata_tag=args.strata_tag)
            print(json.dumps(result, indent=2))
            count = sum(len(r["newer"]) for r in result["releases"].values())
            print(f"{'INCOMPLETE' if not result['complete'] else 'NEWS' if result['news'] else 'NO NEWS'}: "
                  f"{count} newer releases; {len(result['tracked'])} tracked items; {len(result['errors'])} errors", file=sys.stderr)
            return result["exit_code"]
        kwargs = vars(args).copy()
        kwargs.pop("command")
        result = draft(api, ROOT, **kwargs)
        print(json.dumps(result, indent=2))
        print("Metadata check only; no files or binaries written." if args.check else
              "Draft created; all gates not_run, no receipts inherited.", file=sys.stderr)
        return 0
    except (Incomplete, OSError, ValueError, KeyError, TypeError, StopIteration, NameError) as exc:
        # No raw OS paths, payloads, credentials or subprocess stderr in public output.
        message = str(exc) if isinstance(exc, Incomplete) else type(exc).__name__
        print(json.dumps({"complete": False, "error": message}))
        return 4 if args.command == "report" else 2


if __name__ == "__main__":
    raise SystemExit(main())
