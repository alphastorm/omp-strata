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
from omp_strata.common import flag_pairs, release_version, sha256_bytes
from omp_strata.install import GENERATED_CONFIG_KEYS
from omp_strata.ompcfg import CONTEXT_SAFETY_TOKENS
from omp_strata.profile import CALIBRATION_DEFAULTS, Profile, load, validate
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
        if node is None or REVIEWED_HELPERS_0_1_40_2.get(reviewed_hash(node)) != name:
            raise Incomplete(f"stock {name} is missing or changed; review required")
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<stock-setup-helper>", "exec",
                     flags=__import__("__future__").annotations.compiler_flag), ns)


class Incomplete(ValueError):
    """Metadata cannot establish a complete answer or an immutable pin."""


def version(tag):
    parsed = release_version(tag)
    if parsed is None:
        raise Incomplete(f"not a stable release tag: {tag}")
    return parsed


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
        if obj.get("type") != "commit" or not SHA40.fullmatch(str(obj.get("sha", ""))):
            raise Incomplete(f"{repo} {tag}: tag must point directly to a commit (annotated tags refused)")
        return obj["sha"]

    def assets(self, repo, tag, names):
        release, _ = self.get(f"{GITHUB}/repos/{repo}/releases/tags/{tag}")
        if (not isinstance(release, dict) or release.get("tag_name") != tag or release.get("draft") is not False
                or release.get("prerelease") is not False or not isinstance(release.get("id"), int)):
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


def git(src, *args):
    result = subprocess.run(["git", "-C", str(src), *args], capture_output=True, text=True,
                            stdin=subprocess.DEVNULL, timeout=30)
    if result.returncode:
        raise Incomplete("local Strata revision or source file unavailable")
    return result.stdout


def literal_constants(source, names):
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in names:
                try:
                    out[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    raise Incomplete(f"setup constant {node.targets[0].id} is no longer literal") from None
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
                   "two_socket_note", "compute_mode_warning"}
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


def stock_plan(source, *, family, model, context, ram, vram, kv="int8", gpu=0, port=18090, reviewed=True,
               cpu_cores=None, parallel=None, tips=False):
    """Evaluate stock pure choices and its inline config assembly for one Windows NVIDIA GPU.

    No setup main/import is executed. A context past the trained 262144 gets stock resolve_rope's default (yarn,
    factor context / 262144, experimental upstream). Other backends, calibration measurements, vision and low-RAM
    need their own reviewed planner; this draft lane refuses them instead of silently degrading a variant.
    `parallel` plans stock `--parallel N` (refused where stock warns about N for this card); `tips` also returns the
    engine flags stock setup's printed host recommendations name for this host (`stock_tips`) and the RAM they need.
    """
    tree = ast.parse(source)
    constants = literal_constants(source, ("MODELS", "HF_REVISIONS", "LOW_RAM_HEADROOM_GB", "MIN_DRIVER",
                                          "MIN_ENGINE", "RESIDENT_ENGINE", "CONTEXTS"))
    ns = dict(constants, math=SimpleNamespace(ceil=math.ceil),
              __builtins__={"str": str, "float": float, "int": int, "round": round, "len": len,
                            "max": max, "min": min, "ValueError": ValueError, "isinstance": isinstance, "list": list,
                            "sum": sum, "any": any, "enumerate": enumerate, "dict": dict})
    # v0.1.40.1: literal KV byte counts feed arithmetic; the display reserve is advisory text only.
    optional_constants = {"UNSLOTH_SHARDS", "UNSLOTH_IQ4_XS_SHARDS", "UNSLOTH_RAM_LEFT_GB", "SMALL_CARD_GB",
                          "DRAFT_VOCAB_MIB", "DESKTOP_RESERVE_MIB", "REMOTE_EXPERT_OPT", "KV_CELL_BYTES",
                          "DISPLAY_RESERVE_MIB", "HELPER_CACHE_FLAGS"}
    ns.update(literal_constants(source, {name for name in optional_constants
                                         if any(assigned(node, name) for node in tree.body)}))
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
    if remote_opt is not None and REVIEWED_HELPERS_0_1_40_2.get(reviewed_hash(remote_opt)) == remote_opt.name:
        funcs.remove(remote_opt)
        run_reviewed(tree, (remote_opt.name,), ns)
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
              resident=False, budget=None, q4_split=False, vision="none", esp=None, hip=False, multi=[], draft_vocab=None,
              scaling=scaling, rope_scale=scale, eng=scratch / "engine", EXE="strata.exe", ROOT=scratch,
              pack=scratch / "pack", shards=[scratch / f"shard{i}" for i in range(1, shard_count + 1)],
              ple=scratch / "shard2",
              rt=scratch / "mtp", tag=fam["tag"] + model, lib_dirs=[], port=port,
              gpu={"index": gpu, "count": 1, "vram_gb": vram}, engine_ver=tuple(constants["MIN_ENGINE"]),
              a=SimpleNamespace(low_ram="off", kv_streaming="auto", resident_budget_gib=None, gpu=gpu,
                                vram_reserve_mib=None, browser=None, parallel=parallel, vision_tokens=None,
                                host="127.0.0.1", api_key=None),
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
    ns["chosen"] = [ns["gpu"]]  # stock's chosen GPUs: the one card of this lane
    if budget_model:
        choices = [n for n in ast.walk(tree) if assigned(n, "budget") and isinstance(n.value, ast.Call)
                   and isinstance(n.value.func, ast.Name) and n.value.func.id == "budget_choice"]
        if len(choices) != 1 or "UNSLOTH_RAM_LEFT_GB" not in ns:
            raise Incomplete("stock RAM budget choice moved; review required")
        pure_exec(choices, ns)
    parallel_planned = False
    for node in body[starts[0]:end]:
        digest = reviewed_hash(node) if isinstance(node, ast.If) else None
        if digest == OPT_IN_PARALLEL_0_1_39:
            if parallel is not None:
                ns.update(literal_constants(source, ("PARALLEL_MAX", "PARALLEL_SHARE", "PARALLEL_HELD",
                                                     "PARALLEL_COST_NOTE")))
                run_reviewed(tree, ("parallel_slot_gb", "parallel_recommend", "parallel_note"), ns)
                exec(compile(ast.Module(body=[node], type_ignores=[]), "<stock-setup-parallel>", "exec"), ns)
                parallel_planned = True
        elif digest in NON_PLANNING_BRANCHES_0_1_39:
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
        pure_exec(recommendations[0].orelse, ns)
    cfg = ns["cfg"]
    if warnings:
        raise Incomplete("stock setup warns about the requested variant: " + warnings[0])
    if reviewed and set(cfg) != GENERATED_CONFIG_KEYS | ({"parallel"} if parallel else set()):
        raise Incomplete("stock setup writes unreviewed config keys")
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
        # The RAM each printed tip assumes: its own threshold on the PC's RAM, and the cache's budget free at start.
        tips_ram = {"min_total_ram_gib": max([math.ceil(ns["PREFILL_BIG_RAM_GB"])] * ("--prefill" in stock_tips)
                                             + [math.ceil(spec["ram_gb"] + ns["AGENT_CACHE_FREE_GB"])]
                                             * ("--conversation-cache-mib" in stock_tips), default=0),
                    "extra_available_ram_gib": math.ceil(ns["AGENT_CACHE_MIB"] / 1024)
                    * ("--conversation-cache-mib" in stock_tips)}
    # Evaluate setup's own fresh-install disk formula, reserving the larger CPU-pack branch on either CPU.
    disk_nodes = [n for n in body if assigned(n, "need")
                  and any(isinstance(x, ast.Name) and x.id == "to_fetch" for x in ast.walk(n.value))]
    if len(disk_nodes) != 1:
        raise Incomplete("stock disk estimate moved; review required")
    # v0.1.40.1 counts existing pack/MTP files: a new profile has a fresh root, so both are absent; never probe disk.
    ns.update(to_fetch=spec["download_gb"], avx512=True, pack_bin=False, mtp_have=False)
    disk_choices = []
    if any(isinstance(n, ast.Name) and n.id == "q2_avx" for n in ast.walk(disk_nodes[0])):
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
    return {"setup_args": {"family": family, "model": model, "context": context, "kv": kv, "vision": "no",
                           "experimental_speed_projection": "off", "low_ram": "off", "gpu": gpu,
                           **({"parallel": parallel} if parallel else {})},
            "expected_engine_flags": flags, "model_name": cfg["model_name"], "config_keys": sorted(cfg),
            "stock_tips": stock_tips, "tips_ram": tips_ram,
            "host": {"min_total_ram_gib": math.ceil(total),
                     "min_available_ram_gib_at_start": math.ceil(available),
                     "min_free_disk_gib": math.ceil(ns["need"] * 1e9 / 2**30),
                     "min_driver_major": constants["MIN_DRIVER"]},
            "model_url": fam["hf"].format(q=model),
            "model_files": model_files,
            "model_hashes": fam.get("sha256", {}), "budget_plan": budget_plan,
            "thresholds": {"low_ram_below": spec["arena_gb"] + constants["LOW_RAM_HEADROOM_GB"],
                           "kv_streaming_from": spec["ram_gb"] + ns["kv_ram_gb"] + 1,
                           "arena_gb": spec["arena_gb"], "fresh_disk_gb": ns["need"]},
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
        plan = stock_plan(source, family="coder", model="IQ1_M", context=131072, ram=64, vram=24, reviewed=False)
        snapshots.append({"tag": tag, "constants": literal_constants(source, CONSTANTS),
                          "requirements_blob": git(src, "rev-parse", f"{tag}:requirements.txt").strip(),
                          "generated_config_keys": plan["config_keys"],
                          "other_config_writes": sorted(optional - GENERATED_CONFIG_KEYS), "routes": route_set,
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
    pins = {}
    try:
        profiles = [json.loads(p.read_text()) for p in sorted((root / "profiles").glob("*.json"))]
        for component in REPOS:
            pins[component] = max((p[component]["tag"] for p in profiles), key=version)
    except (OSError, ValueError, KeyError) as exc:
        incomplete("profiles", type(exc).__name__)
    for component, repo in REPOS.items():
        try:
            if component not in pins:
                raise Incomplete("no pinned tag")
            rows = api.pages(f"{GITHUB}/repos/{repo}/releases?per_page=100")
            newer = []
            for row in rows:
                if not isinstance(row, dict) or any(k not in row for k in ("draft", "prerelease", "tag_name")):
                    raise Incomplete("release metadata missing")
                if row["draft"] or row["prerelease"]:
                    continue
                if version(row["tag_name"]) > version(pins[component]):
                    newer.append({"tag": row["tag_name"], "url": row.get("html_url"),
                                  "published_at": row.get("published_at")})
            result["releases"][component] = {"pinned": pins[component], "newer": sorted(newer, key=lambda r: version(r["tag"]))}
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


def draft(api, root, predecessor, *, strata_tag, omp_tag, profile_id, strata_src,
          family=None, model=None, context=None, ram=None, vram=None, cpu_cores=None,
          calibration=None, calibration_host=None, calibration_date=None, parallel=None, stock_tips=False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,80}", profile_id):
        raise Incomplete("invalid profile id")
    profile_path, release_dir = root / "profiles" / f"{profile_id}.json", root / "releases" / profile_id
    if profile_path.exists() or release_dir.exists():
        raise Incomplete("profile or release ledger already exists; nothing overwritten")
    original = load(predecessor)
    data = copy.deepcopy(original.data)
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
    strata_commit = api.commit(REPOS["strata"], strata_tag)
    omp_commit = api.commit(REPOS["omp"], omp_tag)
    if git(strata_src, "rev-parse", f"{strata_tag}^{{commit}}").strip() != strata_commit:
        raise Incomplete("local candidate tag differs from live GitHub commit")
    old = data["strata"]["commit"]
    source = git(strata_src, "show", f"{strata_commit}:setup.py")
    if measured is not None:
        stock = literal_constants(git(strata_src, "show", f"{strata_commit}:tools/calibrate.py"), ("DEFAULTS",))
        if stock["DEFAULTS"] != CALIBRATION_DEFAULTS:
            raise Incomplete("stock calibration DEFAULTS changed; review required")
    old_source = git(strata_src, "show", f"{old}:setup.py")
    constants, prior = literal_constants(source, CONSTANTS), literal_constants(old_source, CONSTANTS)
    for key in ("CUDA_WHEELS", "PY_PACKAGES", "LLAMA_CPP_COMMIT"):
        if constants[key] != prior[key]:
            raise Incomplete(f"{key} changed: cannot reuse predecessor dependency pins")
    if git(strata_src, "rev-parse", f"{old}:requirements.txt") != git(strata_src, "rev-parse", f"{strata_commit}:requirements.txt"):
        raise Incomplete("requirements.txt changed: resolve a new lock separately")
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
    plan = stock_plan(source, family=family or setup["family"], model=model or setup["model"],
                      context=context or setup["context"], ram=ram if ram is not None else data["host"]["min_total_ram_gib"],
                      vram=vram if vram is not None else data["host"]["min_gpu_vram_mib"] / 1024,
                      kv=setup["kv"], gpu=setup["gpu"], port=data["server"]["port"], cpu_cores=cores,
                      parallel=parallel, tips=want_tips)
    if want_tips:
        dropped = sorted(set(pinned_tips) - set(plan["stock_tips"]))
        if not plan["stock_tips"] or dropped:
            raise Incomplete("stock setup does not recommend "
                             + (", ".join(dropped) if dropped else "any engine flag") + " for this planning host")
        plan["expected_engine_flags"] = tipped_flags(plan["expected_engine_flags"], plan["stock_tips"])
        host = plan["host"]
        host["min_total_ram_gib"] = max(host["min_total_ram_gib"], plan["tips_ram"]["min_total_ram_gib"])
        host["min_available_ram_gib_at_start"] += plan["tips_ram"]["extra_available_ram_gib"]
    if measured is not None:
        if (plan["setup_args"] != data["strata"]["setup_args"]
                or plan["expected_engine_flags"] != data["strata"]["expected_engine_flags"]):
            raise Incomplete("stock setup plans a different install than the measured one: recalibrate")
        plan["expected_engine_flags"] = calibrated_flags(plan["expected_engine_flags"], measured["settings"])
    engine_name = "strata-windows-x64.zip"
    engine = api.assets(REPOS["strata"], strata_tag, [engine_name])[engine_name]
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
    data["description"] = (f"Stock Strata {strata_tag} with stock OMP {omp_tag.removeprefix('v')}; "
                           f"{plan['model_name']} on {data['host']['gpu_model']}, native Windows, text only, "
                           f"{plan['setup_args']['context']:,}-token context. Stock setup-derived thresholds and "
                           "flags; no hardware qualification or inherited receipts.")
    if measured is not None:
        data["description"] += (" Stock calibration pinned: " + " ".join(f"{k} {v}" for k, v in measured["settings"].items())
                                + f" (tools/calibrate.py on {calibration_host}).")
    if parallel or want_tips:
        chosen = ([f"--parallel {parallel}"] if parallel else []) + [f"{k} {v}" for k, v in (plan["stock_tips"] or {}).items()]
        data["description"] += " Stock setup recommendations pinned: " + ", ".join(chosen) + "."
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
    setup_floors = {**plan["host"], "min_free_disk_gib": math.ceil(disk * 1e9 / 2**30)}
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
    strata = data["strata"]
    strata.update(tag=strata_tag, commit=strata_commit, engine_version=strata_tag.removeprefix("v"),
                  setup_args=plan["setup_args"], expected_engine_flags=plan["expected_engine_flags"], model_name=plan["model_name"])
    if plan["budget_plan"]:
        strata["budget_plan"] = plan["budget_plan"]
    else:
        strata.pop("budget_plan", None)
    if measured is not None:
        strata["calibration"] = {"settings": measured["settings"], "measured_on": calibration_host,
                                 "date": calibration_date, "source_profile": original.id,
                                 "source_fingerprint": original.fingerprint, "report": measured["report"]}
    if want_tips:
        strata["stock_tips"] = plan["stock_tips"]
    else:
        strata.pop("stock_tips", None)
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
    # Reserve both destinations before writing; never open an existing file for replacement.
    release_dir.mkdir()
    try:
        with profile_path.open("xb") as target:
            target.write(json_bytes(data))
    except BaseException:
        release_dir.rmdir()  # Only the empty directory just reserved by this invocation.
        raise
    for name, content in (("qualification.json", ledger_bytes), ("manifest.json", json_bytes(manifest))):
        with (release_dir / name).open("xb") as target:
            target.write(content)
    return {"profile": f"profiles/{profile.id}.json", "fingerprint": profile.fingerprint,
            "manifest": f"releases/{profile.id}/manifest.json", "gates": {"not_run": len(ledger["gates"])},
            "planning": plan, "host_floors": host_floors,
            "omp_declared_context": data["omp"]["context_window"] - CONTEXT_SAFETY_TOKENS}


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
    create.add_argument("--from", dest="predecessor", type=Path, required=True)
    create.add_argument("--strata-tag", required=True)
    create.add_argument("--omp-tag", required=True)
    create.add_argument("--id", dest="profile_id", required=True)
    create.add_argument("--strata-src", type=Path, required=True, help="read-only tagged Strata checkout")
    create.add_argument("--family")
    create.add_argument("--model")
    create.add_argument("--context", type=int)
    create.add_argument("--ram-gib", dest="ram", type=float, help="planning RAM, not the profile's floor")
    create.add_argument("--vram-gib", dest="vram", type=float)
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
        print("Draft created; all gates not_run, no receipts inherited.", file=sys.stderr)
        return 0
    except (Incomplete, OSError, ValueError, KeyError, TypeError, StopIteration, NameError) as exc:
        # No raw OS paths, payloads, credentials or subprocess stderr in public output.
        message = str(exc) if isinstance(exc, Incomplete) else type(exc).__name__
        print(json.dumps({"complete": False, "error": message}))
        return 4 if args.command == "report" else 2


if __name__ == "__main__":
    raise SystemExit(main())
