"""Host-free admission of the single reviewed stock DeepSeek comparison family."""
import ast
from contextlib import ExitStack
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from omp_strata import dsv41, install, lifecycle
from omp_strata import fetch
from omp_strata.common import read_json
from omp_strata.layout import Layout
from omp_strata.profile import Profile, runtime_build_labels, validate
from tests.candidate import PROFILE, REPO
from scripts import upstream_watch, realhost_gates as gates, requalify, perf_probe, tracer


def profile_data():
    data = read_json(PROFILE)
    data["profile_id"] = "test-dsv41-262k"
    data["status"] = "draft"
    data["host"] = {"os": "windows", "route": "native-windows", "gpu_index": 0,
                    "gpu_model": "NVIDIA RTX PRO 6000 Blackwell Workstation Edition", "display_attached": True,
                    "min_gpu_vram_mib": 97000, "min_total_ram_gib": 192, "min_available_ram_gib_at_start": 80,
                    "min_driver_major": 580, "min_free_disk_gib": 262, "cpu_cores": [8, 16]}
    data["server"].update(port=18090, ready_timeout_s=3600)
    data["omp"].update(context_window=262144, max_tokens=32768)
    comp = dict(dsv41.COMPONENT)
    data["strata"] = {"repository": "https://github.com/Niko1221/Strata.git", "tag": dsv41.TAG,
                      "commit": dsv41.COMMIT, "engine_version": dsv41.ENGINE_VERSION,
                      "model_name": dsv41.MODEL_NAME, "artifacts": {"dsv41_package": dict(dsv41.PACKAGE)},
                      "dsv41_component": comp, "python_lock": {
                          "path": "locks/strata-python-cp313-win_amd64-strata0.2.11.txt", "python": "3.13",
                          "sha256": "0174631a131ad17525138ec35288107257bcfeadf64792f46a5ea1b58549363b"},
                      "setup_args": {"family": dsv41.FAMILY, "model": dsv41.MODEL, "context": 262144,
                                     "vision": "no", "gpu": 0},
                      "expected_engine_flags": dsv41.stock_flags(262144),
                      "forbidden_engine_flags": list(dsv41.FORBIDDEN_FLAGS),
                      "engine_env": dict(dsv41.ENGINE_ENV), "user_args": list(dsv41.USER_ARGS)}
    data["model"] = {"variant": dsv41.FAMILY, "quantization": "IQ2_XS", "license": "MIT", "files": dsv41.model_files()}
    return data


class Admission(unittest.TestCase):
    def test_checked_in_comparison_tuple_is_valid_but_never_ready(self):
        from omp_strata import ompcfg
        from omp_strata.profile import load
        from scripts.verify_release import verify
        pid = "win11-rtxpro6000-dsv41-iq2xs-262k-experts6-strata0.2.11-omp18.16.0"
        profile = load(REPO / "profiles" / (pid + ".json"))
        self.assertEqual(profile.data["status"], "draft")
        rendered = ompcfg.render_models_yml(profile, base_url="http://127.0.0.1:18090/v1")
        self.assertIn("261120", rendered)
        self.assertIn("32768", rendered)
        self.assertEqual(ompcfg.inflight_limit(profile), 1)
        release = REPO / "releases" / pid
        self.assertEqual(verify(release / "manifest.json")["errors"], [])
        self.assertTrue(verify(release / "manifest.json", require_ready=True)["errors"])
        ledger = read_json(release / "qualification.json")
        self.assertFalse(ledger["execution_performed"])
        self.assertTrue(all(g["status"] == "not_run" and not g["receipts"] for g in ledger["gates"]))

    def test_exact_family_and_both_reviewed_contexts_validate(self):
        for context in dsv41.CONTEXTS:
            data = profile_data()
            data["strata"]["setup_args"]["context"] = data["omp"]["context_window"] = context
            data["strata"]["expected_engine_flags"] = dsv41.stock_flags(context)
            self.assertEqual(validate(data), [])

    def test_forbidden_qwen_options_never_reach_the_qwen_checks(self):
        for key in ("kv", "low_ram", "parallel", "kv_streaming", "experimental_speed_projection", "layer_split"):
            data = profile_data()
            data["strata"]["setup_args"][key] = "off"
            with self.subTest(key):
                self.assertTrue(validate(data))
        for key in dsv41.FORBIDDEN_STRATA:
            data = profile_data()
            data["strata"][key] = {}
            with self.subTest(key):
                self.assertTrue(validate(data))

    def test_wrong_inputs_package_experts_vision_and_env_are_refused(self):
        mutations = [
            lambda p: p["model"]["files"][0].update(sha256="0" * 64),
            lambda p: p["model"]["files"][0].update(bytes=39535788064),
            lambda p: p["model"]["files"][0].update(revision="f" * 40),
            lambda p: p["model"]["files"][0].update(path=p["model"]["files"][0]["path"].replace("00004", "00006")),
            lambda p: p["strata"]["artifacts"].clear(),
            lambda p: p["strata"]["artifacts"]["dsv41_package"].update(sha256="0" * 64),
            lambda p: p["strata"]["dsv41_component"].update(version="0.1.52"),
            lambda p: p["strata"]["dsv41_component"].update(manifest_sha256="0" * 64),
            lambda p: p["strata"]["dsv41_component"].update(build_source="other"),
            lambda p: p["strata"].update(user_args=["--experts", "5"]),
            lambda p: p["strata"]["setup_args"].update(vision="none"),
            lambda p: p["strata"]["setup_args"].update(vision="yes"),
            lambda p: p["strata"]["engine_env"].pop("STRATA_DS4_AUTO_PIN"),
            lambda p: p["server"].update(ready_timeout_s=900),
            lambda p: p["model"].update(mtp_source={"revision": "a" * 40}),
            lambda p: p["host"].update(gpu_index=False),
            lambda p: p["server"].update(listen_host="::1"),
            lambda p: p["server"].update(port=18091),
        ]
        for i, mutate in enumerate(mutations):
            data = profile_data()
            mutate(data)
            with self.subTest(i):
                self.assertTrue(validate(data))

    def test_stock_fixture_supplies_every_byte_and_digest(self):
        tree = ast.parse((REPO / "tests/fixtures/strata_0_2_11_plan.py").read_text())
        pins = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id in
                                                   ("DSV41_FILES", "DSV41_ISTA_FILES") for n in node.targets):
                pins.update(ast.literal_eval(node.value))
        for _repo, _revision, path, size, digest in dsv41.FILES:
            self.assertEqual(pins[path.rsplit("/", 1)[-1]], (size, digest))

    def test_layout_and_conversation_claim_are_family_specific(self):
        profile = Profile(Path("profiles/test.json"), profile_data())
        layout = Layout(Path("root"), profile)
        self.assertEqual(layout.strata_config.name, "strata-deepseek-v4.1-flash-ist-das-2.25bpw.json")
        self.assertEqual(layout.dsv41_engine_dir.name, "0.1.57-windows-x86_64-cuda-cuda13")
        self.assertEqual(layout.dsv41_package.name, dsv41.PACKAGE_NAME)
        self.assertFalse(profile.parks_automatically)
        self.assertFalse(profile.keeps_conversations)

    def test_fetch_uses_per_file_revisions_and_no_qwen_artifacts_or_mmproj(self):
        layout = Layout(Path("root"), Profile(Path("profiles/test.json"), profile_data()))
        items = fetch.plan(layout, platform="windows-x64")
        self.assertEqual([i.name for i in items], ["omp", "dsv41"] + ["model"] * 7)
        self.assertEqual(len({i.dest for i in items}), len(items))
        self.assertEqual(items[1].sha256, dsv41.PACKAGE["sha256"])
        for item, row in zip(items[2:], dsv41.FILES):
            repo, revision, path, size, digest = row
            self.assertEqual(item.url, f"https://huggingface.co/{repo}/resolve/{revision}/{path}")
            self.assertEqual((item.bytes, item.sha256), (size, digest))
            self.assertNotIn("mmproj", item.url)
        self.assertEqual(len(fetch.plan(layout, platform="windows-x64", only={"dsv41"})), 1)
        self.assertEqual([i.name for i in fetch.plan(layout, platform="darwin-arm64")], ["omp"])


def generated_config(layout):
    pack, engine = dsv41.pack_dir(layout).resolve(), layout.dsv41_engine_dir.resolve()
    args = ["--pack", str(pack), *dsv41.stock_flags(262144)]
    return {"exe": str(engine / dsv41.ENTRYPOINT), "args": args, "args_written": list(args),
            "cwd": str(layout.strata.resolve()), "tokenizer": str(pack / "tokenizer"),
            "model_name": dsv41.MODEL_NAME, "arch": dsv41.FAMILY,
            "log": str(layout.strata_config.with_suffix(".log").resolve()), "lib_dirs": [str(engine)],
            "port": 18090, "engine_ready_s": 3600, "gpu": 0, "gpus_asked": True, "host": "127.0.0.1",
            "user_args": list(dsv41.USER_ARGS), "env": dict(dsv41.ENGINE_ENV)}


class Installation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.layout = Layout(Path(self.tmp.name).resolve(), Profile(Path("profiles/test.json"), profile_data()))
        self.layout.strata.mkdir(parents=True)
        self.cfg = generated_config(self.layout)
        pack = dsv41.pack_dir(self.layout)
        pack.mkdir(parents=True)
        (pack / "ds4.txt").write_text(f"model_dir {self.layout.models_dir.resolve()}\n")
        files = [entry for i, entry in enumerate(self.layout.profile.data["model"]["files"]) if i != 5]
        (pack / "tensors.txt").write_text("".join(
            f"file {i} {entry['path'].rsplit('/', 1)[-1]}\n" for i, entry in enumerate(files)))

    def write_config(self, cfg):
        self.layout.strata_config.write_text(json.dumps(cfg), encoding="utf-8")

    def test_argv_is_exact_and_every_flag_is_stock_argparse(self):
        layout = self.layout
        argv = install.setup_argv(layout)
        self.assertEqual(argv, [str(layout.venv_python), "setup.py", "--family", "deepseek41", "--model",
                               "IST-DAS-2.25bpw", "--context", "262144", "--vision", "no", "--gpu", "0",
                               "--data-dir", str(layout.data), "--gguf-dir", str(layout.models_dir),
                               "--dsv41-package", str(layout.dsv41_package), "--port", "18090", "--host",
                               "127.0.0.1", "--yes", "--no-start"])
        tree = ast.parse((REPO / "tests/fixtures/strata_0_2_11_plan.py").read_text())
        options = {a.value for n in ast.walk(tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument"
                   for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)}
        self.assertTrue({x for x in argv if x.startswith("--")} <= options)

    def test_stock_setup_review_is_exact_and_rejects_a_changed_packer(self):
        source = (REPO / "tests/fixtures/strata_0_2_11_plan.py").read_text()
        self.assertEqual(upstream_watch.dsv41_setup_review(source), dsv41.TAG)
        with self.assertRaises(upstream_watch.Incomplete):
            upstream_watch.dsv41_setup_review(source.replace('\"--dspark-noise-token\", \"128799\"',
                                                             '\"--dspark-noise-token\", \"0\"'))

    def test_generated_config_requires_pack_exe_full_quality_and_cache_privacy(self):
        self.write_config(self.cfg)
        self.assertEqual(install.verify_generated(self.layout), self.cfg)
        for mutate in (lambda c: c.update(exe=str(self.layout.strata / "engine/strata.exe")),
                       lambda c: c.update(arch="qwen"), lambda c: c.update(engine_ready_s=900),
                       lambda c: c.update(user_args=["--experts", "5"]),
                       lambda c: c.update(env={"STRATA_DS4_SLOT_KEEP": "1"}),
                       lambda c: c.update(api_key="forbidden"), lambda c: c.update(parallel=1),
                       lambda c: c["args"].extend(["--parallel", "2"]),
                       lambda c: c.update(tokenizer=str(self.layout.models_dir))):
            cfg = copy.deepcopy(self.cfg)
            mutate(cfg)
            self.write_config(cfg)
            with self.subTest(cfg=cfg), self.assertRaises(install.InstallError):
                install.verify_generated(self.layout)

    def test_user_args_use_stock_writer_without_changing_generated_args(self):
        cfg = copy.deepcopy(self.cfg)
        cfg.pop("user_args")
        self.write_config(cfg)
        fake_setup = Mock()
        fake_setup.write_config.side_effect = lambda path, value: path.write_text(json.dumps(value))
        import sys
        with patch.dict(sys.modules, {"setup": fake_setup}), patch.object(
                sys, "argv", ["-c", str(self.layout.strata_config), json.dumps(dsv41.USER_ARGS)]):
            exec(dsv41.APPLY_USER_ARGS, {})
        self.assertEqual(install.verify_generated(self.layout), self.cfg)
        install.check_setup_stamp(self.layout)  # the exact carried pin is also safe on reinstall
        self.cfg["user_args"] = ["--experts", "5"]
        self.write_config(self.cfg)
        with self.assertRaises(install.InstallError):
            install.check_setup_stamp(self.layout)

    def test_setup_stays_pip_offline_but_does_not_disable_stock_run(self):
        with patch.object(install, "run") as run, patch.dict("os.environ", {"STRATA_NO_ACQUIRE": "1", "DS4_TOPK": "5",
                                                                         "DS4_DEFAULTS": "026", "PATH": "test"}):
            install.run_setup(self.layout, log=lambda _: None)
        env = run.call_args.kwargs["env"]
        self.assertEqual(env["PIP_NO_INDEX"], "1")
        self.assertNotIn("STRATA_NO_ACQUIRE", env)
        self.assertNotIn("DS4_TOPK", env)
        self.assertNotIn("DS4_DEFAULTS", env)
        self.assertEqual(install.scrubbed_env({"PATH": "x", "ds4_topk": "5", "STRATA_API_KEY": "secret"}), {"PATH": "x"})

    def test_every_input_is_deep_hashed_and_extra_six_shard_files_refuse(self):
        with patch.object(dsv41, "verify_file") as verify:
            dsv41.verify_inputs(self.layout, log=lambda _: None)
        self.assertEqual(verify.call_count, 8)
        self.assertTrue(all(call.kwargs["deep"] is True for call in verify.call_args_list))
        self.layout.models_dir.mkdir(parents=True)
        (self.layout.models_dir / "model-00001-of-00006.gguf").touch()
        with self.assertRaisesRegex(dsv41.IntegrityError, "unreviewed GGUF"):
            dsv41.verify_inputs(self.layout, log=lambda _: None)

    def test_pack_info_refuses_an_unrecognised_or_incomplete_result(self):
        for text in ("", "MISSING", "all present MISSING"):
            with self.subTest(text=text), self.assertRaises(dsv41.IntegrityError):
                dsv41.check_pack_info(self.layout, run=Mock(return_value=Mock(stdout=text, stderr="")),
                                      env={}, log=lambda _: None)
        dsv41.check_pack_info(self.layout, run=Mock(return_value=Mock(stdout="all present", stderr="")),
                              env={}, log=lambda _: None)

    def test_runtime_identity_omits_only_the_two_mutable_pack_files(self):
        self.write_config(self.cfg)
        self.layout.shared_settings.write_text("{}")
        self.layout.dsv41_engine_dir.mkdir(parents=True)
        (self.layout.dsv41_engine_dir / dsv41.ENTRYPOINT).write_bytes(b"engine")
        pack = dsv41.pack_dir(self.layout)
        pack.mkdir(parents=True, exist_ok=True)
        for name in ("tensors.txt", "expert-profile.bin", "pack-source.json"):
            (pack / name).write_bytes(b"identity")
        with patch.object(install, "runtime_sources", return_value=()):
            identity = install.runtime_identity(self.layout, self.cfg)
        names = set(identity["files"])
        self.assertTrue(any(n.endswith("/strata-dsv41.exe") for n in names))
        self.assertTrue(any(n.endswith("/tensors.txt") for n in names))
        self.assertFalse(any(n.endswith(("/expert-profile.bin", "/pack-source.json")) for n in names))
        self.assertEqual(len([n for n in names if n.startswith("models/")]), 7)

    def test_install_skips_all_three_qwen_acquisition_steps(self):
        (self.layout.strata / "setup.py").write_text("# source review mocked independently")
        (self.layout.strata / "serve").mkdir()
        (self.layout.strata / "serve/server.py").write_text("# server review mocked independently")
        mocks = {}
        with ExitStack() as stack:
            for name in ("stage_engine", "stage_llama", "mtp_pinned", "install_python", "run_setup",
                         "check_setup_stamp", "freeze_shared_settings", "engine_build", "runtime_identity"):
                mocks[name] = stack.enter_context(patch.object(install, name))
            mocks["install_python"].return_value = {}
            mocks["engine_build"].return_value = {}
            mocks["runtime_identity"].return_value = {}
            stack.enter_context(patch.object(install, "checkout_strata", return_value=dsv41.COMMIT))
            stack.enter_context(patch.object(install.fetch_mod, "fetch"))
            stack.enter_context(patch.object(install, "verify_generated", return_value=self.cfg))
            for name in ("verify_inputs", "inspect_package", "apply_user_args", "check_pack_info"):
                stack.enter_context(patch.object(dsv41, name))
            stack.enter_context(patch.object(upstream_watch, "dsv41_setup_review"))
            stack.enter_context(patch.object(upstream_watch, "dsv41_server_review"))
            stack.enter_context(patch.object(install, "runtime_sources", return_value=()))
            stack.enter_context(patch.object(install, "apply_engine_env"))
            record = install.install(self.layout, log=lambda _: None)
        for name in ("stage_engine", "stage_llama", "mtp_pinned"):
            mocks[name].assert_not_called()
        self.assertIsNone(record["mtp_tensor_manifest_sha256"])


START_LINES = [
    "[strata] 2026-11-06 00:00:00 engine started: strata-dsv41.exe --serve --experts 6",
    "ds4: experts per word: 6 (full quality)",
    "ds4: DSpark not loaded: the routed experts (149 GB) are far more than the GPU holds (99 GB), where its verify "
    "rounds read 3.3x a token's bytes and gain nothing (--dspark on loads it anyway)",
    "ds4: --mmap-experts auto: the CPU lane's experts (59.8 GB) fit the RAM this process can get (98.6 GB beside "
    "9 GB for the rest): copied in at load, no demand store (--mmap-experts on keeps them in place)",
    "ds4: 6117 of the CPU lane's 6117 experts copied into RAM (59.4 GB, 1 NUMA part) in 15.6 s",
    "ds4: CUDA0 layers [0, 39] + head: weights 5.86 GB, experts 90.08 GB (9243 of 15360 in VRAM), caches 0.24 GB, 408 MiB free",
    "ds4: 6117 routed experts on the CPU lane (59.4 GB): 6117 copied into RAM (1 NUMA parts), the rest in place in "
    "the model's files; 24 threads",
]


class Startup(unittest.TestCase):
    def test_known_start_requires_six_experts_auto_decision_and_complete_copy(self):
        observed = dsv41.start_evidence('{"mtp": false}', "\n".join(START_LINES))
        self.assertEqual((observed["experts_per_word"], observed["dspark"], observed["cpu_experts"]), (6, "auto-declined", 6117))
        self.assertEqual(observed["reasoning_effort_wire"], {"low": 50, "medium": 62, "high": 75})
        for index in range(len(START_LINES)):
            with self.subTest(missing=index), self.assertRaises(ValueError):
                dsv41.start_evidence("", "\n".join(START_LINES[:index] + START_LINES[index + 1:]))

    def test_unknown_partial_degraded_or_repeated_start_never_passes(self):
        text = "\n".join(START_LINES)
        bad = [text.replace("6 (full quality)", "5 (faster mode)"),
               text.replace("DSpark not loaded:", "DSpark enabled:"),
               text.replace("(149 GB)", "(140 GB)"),
               text.replace("6117 of the CPU lane's", "6000 of the CPU lane's"),
               text + "\nds4: RAM store: up to 100 slots",
               text + "\nds4 slots: folder cache: 0 conversation(s) kept",
               text + "\n" + START_LINES[0], text + "\n" + START_LINES[1]]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):
                dsv41.start_evidence("", item)
        with self.assertRaises(ValueError):
            dsv41.start_evidence(START_LINES[1], text)

    def test_start_evidence_is_bound_to_the_owned_log_intervals(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout = Layout(Path(tmp), Profile(Path("profiles/test.json"), profile_data()))
            layout.state.mkdir()
            layout.run_record.write_text("{}")
            def interval(_layout, _run, name, _base):
                return ('{"mtp": false}' if name == "log" else "\n".join(START_LINES), {"offset": 17})
            with patch.object(lifecycle, "_startup_log_interval", side_effect=interval):
                lifecycle._check_dsv41_start(layout)
            record = read_json(layout.run_record)
            self.assertEqual(record["dsv41_start"]["engine_log_interval"], {"offset": 17})
            self.assertNotIn("drafting", record)
            self.assertNotIn("start_fallbacks", record)

    def test_server_env_scrubs_ds4_even_for_qwen(self):
        for data in (profile_data(), read_json(PROFILE)):
            layout = Layout(Path("root"), Profile(Path("profiles/test.json"), data))
            with patch.dict("os.environ", {"DS4_TOPK": "5", "ds4_defaults": "026", "PATH": "test"}):
                env = lifecycle.server_env(layout, "test-key")
            self.assertNotIn("DS4_TOPK", env)
            self.assertNotIn("ds4_defaults", env)
            self.assertEqual(env["STRATA_API_KEY"], "test-key")

    def test_runtime_identity_requires_deepseek_build_health_and_pack(self):
        layout = Layout(Path("root").resolve(), Profile(Path("profiles/test.json"), profile_data()))
        health = {"api_key": True, "model": dsv41.MODEL_NAME, "max_context": 262144, "loaded": True,
                  "status": "ok", "service": "strata", "images": False}
        props = {"build_info": "Strata ds4-0.1", "model_path": str(dsv41.pack_dir(layout)),
                 "default_generation_settings": {"n_ctx": 262144}}
        def check(h, p):
            replies = [(200, h), (401, {}), (200, {"data": [{"id": dsv41.MODEL_NAME}]}), (200, p),
                       (200, {"shared": False, "defaults": {}})]
            with patch.object(lifecycle, "http_json", side_effect=replies):
                return lifecycle.runtime_checks(layout, "test-key")
        self.assertTrue(check(health, props)["ready"])
        for changes in ({"build_info": "Strata 0.1.57"}, {"build_info": None}, {"model_path": None},
                        {"model_path": str(layout.model_file(layout.profile.data["model"]["files"][0]))}):
            with self.subTest(changes=changes):
                self.assertFalse(check(health, {**props, **changes})["ready"])
        self.assertFalse(check({k: v for k, v in health.items() if k != "loaded"}, props)["ready"])
        self.assertEqual(runtime_build_labels(layout.profile.data["strata"]), frozenset({"Strata ds4-0.1"}))
        qwen = read_json(PROFILE)["strata"]
        self.assertEqual(runtime_build_labels(qwen), frozenset({"Strata 0.1.57"}))


class GateBudgets(unittest.TestCase):
    def test_deepseek_makes_no_g19_parking_claim(self):
        layout = Layout(Path("root"), Profile(Path("profiles/test.json"), profile_data()))
        with patch.object(gates, "http", side_effect=AssertionError("Qwen cache probe must not run")):
            self.assertEqual(gates.conversation_claim(layout, "test-key"), (False, None))

    def test_comparison_timeouts_do_not_change_any_qwen_timeout(self):
        for step, timeout in dsv41.STEP_TIMEOUTS.items():
            self.assertEqual(requalify.step_timeout(step, deepseek=True), timeout)
        self.assertEqual(requalify.step_timeout("g18"), 3600)
        self.assertEqual(requalify.step_timeout("eval"), 10800)
        self.assertEqual(requalify.step_timeout("install"), 7200)

    def test_tracer_family_default_and_explicit_timeout(self):
        layout = Layout(Path("root"), Profile(Path("profiles/test.json"), profile_data()))
        for extra, expected in (([], 3600), (["--max-time", "123"], 123)):
            with patch("sys.argv", ["tracer", "--profile", "test.json", *extra]), \
                    patch.object(tracer, "load", return_value=layout.profile), \
                    patch.object(tracer.lifecycle, "ensure_healthy", return_value="test-key"), \
                    patch.object(tracer, "one_run", return_value={"protocol_pass": True, "task_pass": True}) as run, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tracer.main(), 0)
                self.assertEqual(run.call_args.args[3], expected)
                self.assertEqual(run.call_args.args[4], "high")

    def test_g18_and_g18l_use_family_invocation_budgets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "calc.py").write_text("return a + b")
            layout = Layout(root, Profile(Path("profiles/test.json"), profile_data()))
            result = Mock(exit_code=0, wall_ms=1)
            result.final_text.return_value = ""
            for gate in (gates.g18, gates.g18l):
                with patch.object(gates.hostrun, "git_fixture", return_value=root), \
                        patch.object(gates.hostrun, "run_omp", return_value=result) as run, \
                        patch.object(gates, "session_for", return_value=None), \
                        patch.object(gates, "engine_requests", return_value=[]), \
                        patch.object(gates, "g18l_doc_count", return_value=3):
                    gate(layout, "test-key", root)
                    self.assertTrue(all(c.kwargs["max_time_s"] == 3600 for c in run.call_args_list))

    def test_deepseek_perf_emits_no_mtp_metrics_but_checks_exclusivity(self):
        self.assertEqual(perf_probe.acceptance({"totals": {"requests": 2}},
                                               {"totals": {"requests": 3}}, 1, mtp=False), [])
        with self.assertRaises(perf_probe.ProtocolError):
            perf_probe.acceptance({"totals": {"requests": 2}}, {"totals": {"requests": 4}}, 1, mtp=False)

    def test_perf_samples_and_queue_pair_have_no_mtp_fields(self):
        from tests.mock.scripted_server import ResponseSpec, ScriptedServer
        server = ScriptedServer([ResponseSpec(), ResponseSpec(), ResponseSpec(completion_delay_s=.6), ResponseSpec()],
                                model=dsv41.MODEL_NAME, context=262144, api_key="x" * 40, perf_enabled=True)
        self.addCleanup(server.close)
        with tempfile.TemporaryDirectory() as tmp:
            data = profile_data()
            data["server"]["port"] = server.httpd.server_port
            layout = Layout(Path(tmp), Profile(Path("profiles/test.json"), data))
            layout.state.mkdir()
            layout.key_file.write_text("x" * 40)
            result = perf_probe.run(layout, [0], 0, 16, 3)
        self.assertTrue(result["queue"]["both_complete"])
        metrics = [m for row in [*result["samples"], *result["queue"]["requests"]] for m in row["metrics"]]
        self.assertFalse(any(m["name"].startswith("mtp_") for m in metrics))
        self.assertEqual(result["queue"]["metrics"], [])


if __name__ == "__main__":
    unittest.main()
