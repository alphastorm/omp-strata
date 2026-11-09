"""Stock v0.2.13 admission boundaries; no installer, server or GPU execution."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from omp_strata import dflash2, engine_component
from omp_strata.profile import ENGINE_ENV_GROUPS, UNSLOTH_RESIDENT_SETUP_ENV, load, unsloth_resident_setup_env, validate
from scripts import upstream_watch as watch

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests/fixtures"


def fixture(name):
    return (FIXTURES / ("strata_0_2_13_" + name)).read_text()


class Stock0213Fixtures(unittest.TestCase):
    def test_source_payloads_match_their_recorded_digests(self):
        files = sorted(FIXTURES.glob("strata_0_2_13_*"))
        self.assertEqual(13, len(files))
        for path in files:
            with self.subTest(path=path.name):
                marker = b"// " if path.suffix == ".cpp" else b"# "
                header, payload = path.read_bytes().split(marker + b"Stock payload follows.\n", 1)
                hashes = dict(line.removeprefix(marker).split(b": ", 1) for line in header.splitlines()
                              if b" SHA-256: " in line)
                self.assertEqual(hashes[b"Payload SHA-256"].decode(), hashlib.sha256(payload).hexdigest())
                self.assertRegex(hashes[b"Source SHA-256"].decode(), r"^[0-9a-f]{64}$")
                if path.suffix == ".py":
                    ast.parse(payload)

    def test_runtime_requirements_and_packer_are_unchanged_from_v0212(self):
        for name in ("requirements.txt", "requirements_monitor.txt", "dflash2_pack.py"):
            previous = (FIXTURES / ("strata_0_2_12_" + name)).read_text()
            self.assertEqual(previous.split("# Stock payload follows.\n", 1)[1],
                             fixture(name).split("# Stock payload follows.\n", 1)[1])


class Stock0213Plan(unittest.TestCase):
    def plan(self, source=None, **options):
        return watch.stock_plan(fixture("plan.py") if source is None else source,
                                **({"family": "coder", "model": "IQ1_M", "context": 131072,
                                    "ram": 47.15475845336914, "vram": 31.8427734375,
                                    "engine_version": (0, 1, 59),
                                    "setup_config_source": fixture("setup_config.py")} | options))

    def test_current_lane_setup_outputs_match_v0212(self):
        from tests.unit.test_strata_0212 import Stock0212Plan
        previous = Stock0212Plan()
        inventory = json.loads((FIXTURES / "strata_0_1_42_gpu_inventory.json").read_text())
        pair = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 127.68849182128906,
                "vram": None, "gpu_inventory": inventory, "gpu_roles": {0: "main", 1: "helper"},
                "layer_split": "24"}
        pro = {"family": "qwen", "model": "IQ3_S", "context": 262144, "ram": 191.69942092895508,
               "vram": 95.5927734375, "parallel": 4, "cpu_cores": (8, 16),
               "kv_streaming": "off", "gpu_arch": "120"}
        for options in ({}, {"context": 262144, "kv_streaming": "off"}, pro, pair):
            with self.subTest(options=options):
                old, new = previous.plan(**options), self.plan(**options)
                for key in ("setup_args", "expected_engine_flags", "config_keys", "model_files", "model_url",
                            "host", "thresholds", "stock_tips", "stock_default_recommendation"):
                    self.assertEqual(old[key], new[key], key)
                self.assertNotIn("env", new["config_keys"])
                self.assertNotIn("shape_title", new["config_keys"])

    def test_missing_changed_or_mixed_seam_refuses(self):
        for config in (None, fixture("setup_config.py") + "\nchanged = True\n",
                       fixture("setup_config.py").replace("a = inp.a", "a = inp.chosen", 1)):
            with self.subTest(config=config is None), self.assertRaises(watch.Incomplete):
                self.plan(setup_config_source=config)
        with self.assertRaisesRegex(watch.Incomplete, "module or caller changed"):
            self.plan(fixture("plan.py").replace("a=a, adopted=adopted", "a=adopted, adopted=adopted", 1))

    def test_changed_feed_shape_and_write_guards_refuse(self):
        tree = ast.parse(fixture("plan.py"))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        shape = next(n for n in main.body if isinstance(n, ast.If)
                     and ast.unparse(n.test) == "fam.get('shape')")
        shape.test = ast.Constant(True)
        with self.assertRaises(watch.Incomplete):
            self.plan(ast.unparse(ast.fix_missing_locations(tree)))
        for before, after in (
            ('if not a.family and not a.yes and FEED_MODELS is None:',
             'if not a.family and FEED_MODELS is None:'),
            ('if fam.get("feed") and fam.get("drafter") == "none" and a.mtp is None:',
             'if fam.get("feed") and a.mtp is None:'),
            ('SHAPE_ENGINE: dict = {}', 'SHAPE_ENGINE: dict = {"shape": "q4_lite"}'),
            ('if SHAPE_ENGINE.get("title") and SHAPE_ENGINE.get("shape") and cfg.get("exe")',
             'if SHAPE_ENGINE.get("title") and cfg.get("exe")'),
        ):
            with self.subTest(before=before), self.assertRaises(watch.Incomplete):
                source = fixture("plan.py").replace(before, after, 1)
                self.assertNotEqual(fixture("plan.py"), source)
                self.plan(source)

    def test_neutral_profile_io_is_not_in_generic_vocabulary(self):
        with self.assertRaisesRegex(watch.Incomplete, "new call"):
            watch.pure_exec(ast.parse("neutral_profile_if_other_shape(1)").body, {})

    def test_stock_write_config_retains_the_existing_install_review(self):
        from omp_strata import dsv41
        tree = ast.parse(fixture("plan.py"))
        writer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "write_config")
        self.assertEqual(dsv41.SETUP_FUNCTIONS["write_config"], watch.reviewed_hash(writer))

    def test_unsloth_setup_env_tracks_engine_owned_hc_q8_without_admitting_budget_planning(self):
        namespace = {}
        watch.run_reviewed(ast.parse(fixture("plan.py")), ("unsloth_default_env",), namespace)
        for model in UNSLOTH_RESIDENT_SETUP_ENV:
            with self.subTest(model=model):
                self.assertEqual(UNSLOTH_RESIDENT_SETUP_ENV[model],
                                 unsloth_resident_setup_env(model, "0.1.58"))
                expected = namespace["unsloth_default_env"]("unsloth", model, False, False)
                self.assertEqual(expected, unsloth_resident_setup_env(model, "0.1.59"))
                self.assertNotIn("STRATA_HC_Q8", expected)
        with self.assertRaisesRegex(watch.Incomplete, "Unsloth budget planning is unreviewed"):
            self.plan(family="unsloth", model="UD-Q4_K_XL", context=262144, ram=192, vram=96,
                      parallel=4, cpu_cores=(8, 16))


class Stock0213Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture("server_engine_path.py")
        cls.sources = {"strata_control/drafting.py": fixture("drafting.py"),
                       "strata_control/runtime.py": fixture("runtime.py"),
                       "strata_control/user_args.py": fixture("user_args.py"),
                       "tools/strata_tokenizer.py": fixture("strata_tokenizer.py"),
                       "serve/toolformat.py": fixture("toolformat.py")}
        previous = watch.SERVER_REVIEWS["0.2.12"]
        for path in (dict(previous["modules"].values()) | previous["sources"]):
            if path not in cls.sources:
                cls.sources[path] = (FIXTURES / ("strata_0_2_11_" + Path(path).name)).read_text()
        cls.modules = {path: watch.reviewed_hash(ast.parse(source)) for path, source in cls.sources.items()}
        cls.engine_sources = {"src/core/arch_defaults.cpp": fixture("arch_defaults.cpp")}

    def review(self, groups=(), **options):
        return watch.server_pinned_path_review(self.source, groups,
                                               **({"module_digests": self.modules,
                                                   "engine_sources": self.engine_sources} | options))

    def test_recomputed_review_has_only_the_reachable_closure(self):
        for groups in ((), tuple(ENGINE_ENV_GROUPS)):
            self.assertEqual("0.2.13", self.review(groups))
        previous, current = watch.SERVER_REVIEWS["0.2.12"], watch.SERVER_REVIEWS["0.2.13"]
        removed = {"parallel_stack_env", "parallel_stack_platform", "gdn_stack_env", "parallel_slots"}
        self.assertEqual(set(previous["functions"]) - removed, set(current["functions"]))
        self.assertEqual(("child_env", "engine_args", "mtp_retry_args", "nodraft_retry_args"), current["roots"])
        self.assertEqual(previous["imports"], current["imports"])
        self.assertEqual({}, current["env_constants"])
        for name in set(current["functions"]) - {"child_env", "engine_args"}:
            self.assertEqual(previous["functions"][name], current["functions"][name])

    def test_missing_changed_and_mixed_modules_refuse(self):
        for path in self.modules:
            for modules in ({p: h for p, h in self.modules.items() if p != path},
                            self.modules | {path: "0" * 64}):
                with self.subTest(path=path), self.assertRaisesRegex(watch.Incomplete, "engine environment/argv"):
                    self.review(module_digests=modules)
        with patch.dict(watch.SERVER_REVIEWS, {"duplicate": copy.deepcopy(watch.SERVER_REVIEWS["0.2.13"])}):
            with self.assertRaises(watch.Incomplete):
                self.review()

    def test_stack_literals_are_read_from_the_pinned_engine_source(self):
        path = "src/core/arch_defaults.cpp"
        source = self.engine_sources[path]
        for group, key, value in (("parallel_stack", "STRATA_CKPT_POOL_READY", "4"),
                                  ("gdn_stack", "STRATA_GDN_CONVL2", "2")):
            changed = source.replace(f'{{"{key}", "{value}"}}', f'{{"{key}", "0"}}')
            self.assertNotEqual(source, changed)
            for sources in ({}, {path: changed}, {path: source.replace(f'{{"{key}", "{value}"}}',
                                                                      f'{{"{key}", "{value}"}}, {{"{key}", "{value}"}}')}):
                with self.subTest(group=group), self.assertRaises(watch.Incomplete):
                    self.review((group,), engine_sources=sources)

    def test_source_review_reads_engine_tables_at_the_same_commit(self):
        reads = []
        def stock(_src, operation, spec, **_kwargs):
            reads.append(spec)
            path = spec.split(":", 1)[1]
            return self.source if path == "serve/server.py" else self.engine_sources[path]
        with patch.object(watch, "git_blob", side_effect=lambda src, commit, path: self.sources.get(path)), \
                patch.object(watch, "git", side_effect=stock):
            self.assertEqual("0.2.13", watch.source_server_review(None, "pinned", "0.1.59",
                                                                 ("parallel_stack", "gdn_stack")))
            self.assertEqual(["pinned:src/core/arch_defaults.cpp", "pinned:serve/server.py"], reads)
            with self.assertRaisesRegex(watch.Incomplete, "review 0.2.13 is for engine 0.1.59, not 0.1.58"):
                watch.source_server_review(None, "pinned", "0.1.58", ())


class Stock0213DFlash2(unittest.TestCase):
    def pins(self, *, fetch_source=None, server_key="0.2.13"):
        from tests.unit.test_component_engine import NAME, members, write_archive
        from tests.unit.test_upstream_watch import FixtureTransport

        sources = {"strata_control/drafting.py": fixture("drafting.py"),
                   "strata_control/drafting_fetch.py": fixture("drafting_fetch.py") if fetch_source is None
                   else fetch_source, "tools/dflash2_pack.py": fixture("dflash2_pack.py")}
        metadata = {"sha": dflash2.REVISION, "cardData": {"license": "apache-2.0"}, "siblings": [
            {"rfilename": name, "size": size,
             **({"lfs": {"size": size, "sha256": sha}} if name.endswith(".safetensors") else {})}
            for name, size, sha in dflash2.FILES]}
        url = f"{watch.HF}/api/models/{dflash2.REPO}/revision/{dflash2.REVISION}?blobs=true"
        api = watch.API(FixtureTransport({url: (metadata, {})}), allow_github=False)
        def source(_src, operation, spec, **kwargs):
            path = spec.split(":", 1)[1]
            return b"shipped vocabulary" if path == "data/draft_vocab.bin" else sources[path]
        with tempfile.TemporaryDirectory() as directory, patch.object(watch, "git", side_effect=source):
            archive = Path(directory) / NAME
            pin = write_archive(archive, members(payload={
                "strata.exe": b"\0".join((dflash2.MARK_ON, dflash2.MARK_VOCAB, dflash2.MARK_SELQ4))}))
            return watch.dflash2_pins(api, None, "a" * 40, archive, pin,
                                     server_key=server_key, strata_tag="v" + server_key)

    def test_v0213_modules_keep_the_pinned_offline_inputs(self):
        pins = self.pins()
        self.assertEqual([], dflash2.validate_source({"dflash2_source": pins}))
        self.assertEqual("locally-packed", pins["kind"])
        self.assertEqual("selq4", pins["runtime_pack"])
        self.assertTrue(all(p["sha256_source"].startswith("Stock v0.2.13 drafting.FILES;") for p in pins["files"]))

    def test_fetch_module_is_release_specific_and_fail_closed(self):
        for source in (fixture("drafting_fetch.py") + "\nchanged = True\n",
                       (FIXTURES / "strata_0_2_12_drafting_fetch.py").read_text()):
            with self.subTest(source=source[-25:]), self.assertRaisesRegex(watch.Incomplete, "DFlash2 module changed"):
                self.pins(fetch_source=source)
        with self.assertRaisesRegex(watch.Incomplete, "DFlash2 module changed"):
            self.pins(server_key="0.2.12")


class Stock0213Engine(unittest.TestCase):
    def test_published_component_manifests_bind_engine_0159(self):
        manifest_raw = (FIXTURES / "engine_0_1_59_engine-component.json").read_bytes()
        build_raw = (FIXTURES / "engine_0_1_59_BUILD.json").read_bytes()
        self.assertEqual("102238fc50b9941a990cafcb0ead565eaf34ae235685d8fbdd4471774f066f88",
                         hashlib.sha256(manifest_raw).hexdigest())
        manifest, build = json.loads(manifest_raw), json.loads(build_raw)
        files = engine_component._manifest_files(manifest, platform="windows-x86_64", backend="cuda",
                                                  variant="cuda13")
        engine_component._build_checks(build, "0.1.59")
        self.assertEqual(files["BUILD.json"]["sha256"], hashlib.sha256(build_raw).hexdigest())
        self.assertEqual(240, files["BUILD.json"]["bytes"])
        self.assertEqual("712fec6b4297+cuda13.0", manifest["build_id"])
        self.assertEqual(("f-0213-rc", "712fec6b4297"), (build["source"], build["commit"]))
        previous = json.loads((FIXTURES / "engine_0_1_58_engine-component.json").read_text())
        self.assertEqual({f["path"] for f in previous["files"]}, set(files))

    def test_all_22_environment_variables_keep_the_reviewed_lane_unions(self):
        from tests.unit.test_profile import EngineEnvProfileTests
        self.assertEqual(22, sum(len(values) for values in ENGINE_ENV_GROUPS.values()))
        case = EngineEnvProfileTests()
        for lane, groups in (("pro", ("parallel_stack", "gdn_stack")),
                              ("5090", ("gdn_stack",)),
                              ("pair", ("sm86_table", "gdn_stack", "select_two_pass")),
                              ("pair", ("sm86_table", "gdn_stack", "iq4nl_w4a8"))):
            data = case.prompt_data(lane, *groups)
            data["strata"]["engine_version"] = "0.1.59"
            with self.subTest(lane=lane, groups=groups):
                self.assertEqual([], validate(data))

    def test_defaults_note_covers_stock_0159_changes_and_retained_guards(self):
        for multi in (False, True):
            note = watch.engine_defaults_note("0.1.59", multi_gpu=multi, ple_io="direct")
            for text in ("Stock engine 0.1.59", "window 8", "confidence 0.55", "Linux-only engine defaults",
                         "HC_Q8", "tokenizer pre", "stdout", "60 s", "no drafter",
                         "8192-token chunks" if multi else "32768-token chunks"):
                with self.subTest(multi=multi, text=text):
                    self.assertIn(text, note)

    def test_source_review_does_not_admit_unmeasured_pair_stage_order(self):
        from omp_strata.lifecycle import STAGE_ORDER_REVIEWED_ENGINES
        self.assertNotIn("0.1.59", STAGE_ORDER_REVIEWED_ENGINES)

    def test_new_runtime_identity_sources_leave_rollback_lists_unchanged(self):
        from omp_strata.profile import start_path_sources
        previous = start_path_sources("0.1.58")
        self.assertEqual(9, len(previous))
        self.assertEqual(start_path_sources("0.1.57"), previous)
        self.assertEqual(previous + ("tools/strata_tokenizer.py", "serve/toolformat.py"),
                         start_path_sources("0.1.59"))


class Stock0213Drafts(unittest.TestCase):
    LANES = (
        "win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking",
        "win11-rtxpro6000-iq3s-262k-slots4-df2tuned-pledirect-kvvram-envpg-parking",
        "win11-rtx5090-coder-iq1m-262k-kvvram-kvgrow-envg",
        "win11-rtx5090-coder-iq1m-131k",
        "win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect-env86gt",
    )

    def test_version_drafts_preserve_all_host_setup_and_flag_choices(self):
        def changes(before, after, path=""):
            if isinstance(before, dict) and isinstance(after, dict):
                return [p for key in before.keys() | after.keys()
                        for p in changes(before.get(key), after.get(key), path + "." + key if path else key)]
            if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
                return [p for i, (old, new) in enumerate(zip(before, after))
                        for p in changes(old, new, f"{path}.{i}")]
            return [] if before == after else [path]

        ci = (REPO / ".github/workflows/ci.yml").read_text()
        for stem in self.LANES:
            old = load(REPO / "profiles" / (stem + "-strata0.2.12-omp18.18.0.json")).data
            new = load(REPO / "profiles" / (stem + "-strata0.2.13-omp18.18.3.json")).data
            with self.subTest(lane=stem):
                self.assertEqual([], validate(new))
                self.assertEqual("d2f096475817d4666c364c820b0ca830f751cfc5", new["strata"]["commit"])
                self.assertEqual("0.1.59", new["strata"]["engine_version"])
                self.assertEqual("712fec6b4297+cuda13.0", new["strata"]["engine_component"]["build_id"])
                self.assertEqual("21f1188cf88b2f534c092181968cd5a4d1a9c296", new["omp"]["source_commit"])
                self.assertEqual("v18.18.3", new["omp"]["tag"])
                self.assertEqual(old["host"], new["host"])
                self.assertEqual(old["strata"]["python_lock"], new["strata"]["python_lock"])
                self.assertIn("- " + new["profile_id"], ci)
                for path in changes(old, new):
                    allowed = (path in ("profile_id", "description", "strata.tag", "strata.commit",
                                        "strata.engine_version", "omp.tag", "omp.version", "omp.source_commit")
                               or path.startswith(("omp.artifacts.", "strata.artifacts.engine_archive.",
                                                   "strata.engine_component."))
                               or path.startswith("model.dflash2_source.files.") and path.endswith(".sha256_source")
                               or path in ("model.dflash2_source.tuned.tag", "model.dflash2_source.tuned.url",
                                           "model.dflash2_source.tuned.sha256_source")
                               or path == "host_floors.min_free_disk_gib.predecessor")
                    self.assertTrue(allowed, path)

    def test_server_and_client_drafts_inherit_no_qualification(self):
        from omp_strata.profile import load_route
        ids = [stem + "-strata0.2.13-omp18.18.3" for stem in self.LANES]
        for kind in ("df2", "df2tuned"):
            identifier = f"client-rtxpro6000-262k-{kind}-pledirect-kvvram-envpg-strata0.2.13-omp18.18.3"
            route = load_route(REPO / "routes" / (identifier + ".json"))
            self.assertEqual("draft", route.data["status"])
            self.assertEqual(1, len(route.servers))
            ids.append(identifier)
        for identifier in ids:
            directory = REPO / "releases" / identifier
            manifest = json.loads((directory / "manifest.json").read_text())
            ledger = json.loads((directory / "qualification.json").read_text())
            with self.subTest(identifier=identifier):
                self.assertEqual("draft", manifest["status"])
                self.assertFalse(manifest["publication_authorized"])
                self.assertTrue(manifest["blockers"])
                self.assertTrue(all(gate["status"] == "not_run" and not gate["receipt_paths"]
                                    and not gate["receipts"] for gate in ledger["gates"]))
