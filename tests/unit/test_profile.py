"""G01: reject unusable or silently expanded candidate configurations."""
import copy
from pathlib import Path
import unittest

from omp_strata.common import read_json
from omp_strata.profile import load, validate

from tests.candidate import PROFILE


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.data = read_json(PROFILE)

    def test_committed_profile_and_canonical_fingerprint(self):
        profile = load(PROFILE)
        self.assertEqual([], validate(self.data))
        from omp_strata.profile import Profile
        reordered = dict(reversed(list(self.data.items())))
        self.assertEqual(profile.fingerprint, Profile(PROFILE, reordered).fingerprint)
        changed = copy.deepcopy(self.data)
        changed["omp"]["max_tokens"] -= 1
        self.assertNotEqual(profile.fingerprint, Profile(PROFILE, changed).fingerprint)

    def test_missing_component_pins(self):
        cases = [("strata", "commit"), ("omp", "source_commit"), ("model", "revision"),
                 ("model", "mtp_source", "revision"), ("omp", "artifacts"),
                 ("model", "files"), ("strata", "artifacts", "engine_archive"),
                 ("strata", "artifacts", "llama_cpp_archive")]
        for keys in cases:
            with self.subTest(keys=keys):
                data = copy.deepcopy(self.data)
                parent = data
                for key in keys[:-1]:
                    parent = parent[key]
                del parent[keys[-1]]
                self.assertTrue(validate(data))
        for key in ("sha256", "bytes", "url", "sha256_source"):
            with self.subTest(artifact_pin=key):
                data = copy.deepcopy(self.data)
                del data["omp"]["artifacts"]["linux-x64"][key]
                self.assertTrue(validate(data))

    def test_artifact_urls_are_immutable_https(self):
        for url in ("http://example.com/pinned", "https://example.com/releases/latest/binary",
                    "https://example.com/resolve/main/model"):
            with self.subTest(url=url):
                self.data["omp"]["artifacts"]["linux-x64"]["url"] = url
                self.assertTrue(validate(self.data))

    def test_sentinels_cannot_reach_launch(self):
        for value in ("RESOLVE_" + "MODEL", "TO" + "DO", "<" + "placeholder>"):
            with self.subTest(value=value):
                self.data["strata"]["model_name"] = value
                self.assertTrue(validate(self.data))

    def test_budgets_route_key_policy_and_setup(self):
        changes = [("strata", "setup_args", "context", 100000),
                   ("omp", "context_window", 8192),
                   ("omp", "max_tokens", self.data["omp"]["context_window"] // 2 + 1),
                   ("server", "listen_host", "0.0.0.0"),
                   ("server", "api_key_env", ""),
                   ("strata", "setup_args", "low_ram", "auto"),
                   ("strata", "setup_args", "vision", "yes"),
                   ("strata", "setup_args", "experimental_speed_projection", "on")]
        for *keys, value in changes:
            with self.subTest(keys=keys):
                data = copy.deepcopy(self.data)
                parent = data
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                self.assertTrue(validate(data))

    def test_unsupported_capabilities_and_tuning(self):
        for capability in ("vision", "remote_client", "durable_engine_state", "multi_tenant"):
            with self.subTest(capability=capability):
                data = copy.deepcopy(self.data)
                data["capabilities"][capability] = True
                self.assertTrue(validate(data))
        for flag in ("--pcie-frac", "--pool-workers", "--spec-min-p-tuned", "--adapt-every"):
            with self.subTest(flag=flag):
                data = copy.deepcopy(self.data)
                data["strata"]["expected_engine_flags"].extend([flag, "1"])
                self.assertTrue(validate(data))
        self.data["strata"]["forbidden_engine_flags"].append("--max-context")
        self.assertTrue(validate(self.data))

    def test_tuning_flags_need_the_exact_pinned_stock_calibration(self):
        calibrated = read_json(Path(__file__).resolve().parents[2] /
                               "profiles/win11-rtx3090-iq3s-131k-calibrated-strata0.1.36-omp18.4.12.json")
        self.assertEqual([], validate(calibrated))

        def flags(data, flag, value):
            out = data["strata"]["expected_engine_flags"]
            out[out.index(flag) + 1] = value

        cases = [("calibration removed", lambda d: d["strata"].pop("calibration"), "must stay off unless"),
                 ("stock default kept", lambda d: flags(d, "--spec-min-p", "0.5"), "--spec-min-p must be"),
                 ("unpinned value", lambda d: flags(d, "--pcie-frac", "0.35"), "--pcie-frac must be"),
                 ("unpinned tuning flag", lambda d: d["strata"]["expected_engine_flags"].extend(["--pool-workers", "6"]),
                  "--pool-workers must be"),
                 ("non-calibration flag", lambda d: d["strata"]["calibration"]["settings"].update({"--adapt-every": "8"}),
                  "not a stock calibration setting"),
                 ("nothing kept", lambda d: d["strata"]["calibration"].update(settings={}), "nonempty settings"),
                 ("no provenance", lambda d: d["strata"]["calibration"].pop("source_fingerprint"), "source_profile")]
        for name, change, error in cases:
            with self.subTest(name):
                data = copy.deepcopy(calibrated)
                change(data)
                self.assertTrue(any(error in p for p in validate(data)), validate(data))

    def test_slots_and_stock_tips_only_as_stock_setup_writes_and_recommends_them(self):
        base = read_json(Path(__file__).resolve().parents[2] /
                         "profiles/win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0.json")
        tips = {"--conversation-cache-mib": "8192", "--prefill": "auto:32768"}

        def variant(parallel=4, pinned=None, flags=()):
            data = copy.deepcopy(base)
            if parallel is not None:
                data["strata"]["setup_args"]["parallel"] = parallel
            if pinned is not None:
                data["strata"]["stock_tips"] = pinned
            out = data["strata"]["expected_engine_flags"]
            for flag, value in flags:  # as stock's tip says: a value replaced, else the flag added
                if flag in out:
                    out[out.index(flag) + 1] = value
                else:
                    out += [flag, value]
            return data

        applied = list(tips.items())
        self.assertEqual([], validate(variant(pinned=tips, flags=applied)))
        cases = [("one slot", variant(parallel=1), "setup_args.parallel"),
                 ("past the engine's batch", variant(parallel=9), "setup_args.parallel"),
                 ("not a count", variant(parallel=True), "setup_args.parallel"),
                 ("not stock's value", variant(pinned={"--conversation-cache-mib": "16384"},
                                               flags=[("--conversation-cache-mib", "16384")]), "strata.stock_tips"),
                 ("pinned, not applied", variant(pinned=tips, flags=applied[:1]), "--prefill must be the pinned"),
                 ("cache without its tip", variant(flags=applied[:1]), "only as stock setup's pinned tip"),
                 ("unrecommended cache flag", variant(pinned=tips, flags=applied + [("--conversation-cache-slots", "8")]),
                  "--conversation-cache-slots only as"),
                 ("prefill without its tip", variant(flags=applied[1:]), "--prefill other than")]
        for name, data, error in cases:
            with self.subTest(name):
                self.assertTrue(any(error in p for p in validate(data)), validate(data))

    def test_pool_workers_only_as_stock_setups_hybrid_cpu_recommendation(self):
        profiles = Path(__file__).resolve().parents[2] / "profiles"
        current = read_json(profiles / "win11-rtx3090-iq3s-131k-strata0.1.39-omp18.5.0.json")
        older = read_json(profiles / "win11-rtx3090-iq3s-131k-strata0.1.38-omp18.5.0.json")
        calibrated = read_json(profiles / "win11-rtx3090-iq3s-131k-calibrated-strata0.1.36-omp18.4.12.json")

        def variant(base, cores, workers):
            data = copy.deepcopy(base)
            if cores is not None:
                data["host"]["cpu_cores"] = cores
            if workers is not None:  # as the draft does: a planned flag leaves the forbidden list
                data["strata"]["expected_engine_flags"] += ["--pool-workers", workers]
                data["strata"]["forbidden_engine_flags"] = [
                    f for f in data["strata"]["forbidden_engine_flags"] if f != "--pool-workers"]
            return data

        hotfix = copy.deepcopy(current)  # a hotfix release (v0.1.40.1) keeps its base's stock recommendation
        hotfix["strata"].update(tag="v0.1.39.1", engine_version="0.1.39.1")
        for base, cores, workers in ((current, [8, 16], "15"), (current, [8, 8], None), (current, None, None),
                                     (hotfix, [8, 16], "15")):
            with self.subTest(valid=(base["strata"]["engine_version"], cores, workers)):
                self.assertEqual([], validate(variant(base, cores, workers)))
        cases = [("missing on a hybrid CPU", current, [8, 16], None, "recommendation 15"),
                 ("another count", current, [8, 16], "23", "recommendation 15"),
                 ("not more efficiency cores", current, [8, 8], "15", "must stay off unless"),
                 ("stock 0.1.38 writes none", older, [8, 16], "15", "must stay off unless"),
                 ("one count", current, [8], None, "host.cpu_cores"),
                 ("zero cores", current, [8, 0], None, "host.cpu_cores"),
                 ("strings", current, ["8", "16"], None, "host.cpu_cores")]
        for name, base, cores, workers, error in cases:
            with self.subTest(name):
                problems = validate(variant(base, cores, workers))
                self.assertTrue(any(error in p for p in problems), problems)
        data = variant(current, [8, 16], "15")
        data["strata"]["calibration"] = calibrated["strata"]["calibration"]
        self.assertTrue(any("calibration on a hybrid CPU is unreviewed" in p for p in validate(data)))

    def test_context_past_the_trained_length_needs_exactly_stock_yarn(self):
        profiles = Path(__file__).resolve().parents[2] / "profiles"
        scaled = read_json(profiles / "win11-rtx3090-coder-iq1m-524k-strata0.1.36-omp18.4.12.json")
        trained = read_json(profiles / "win11-rtx3090-coder-iq1m-262k-strata0.1.36-omp18.4.12.json")
        self.assertEqual([], validate(scaled))
        self.assertEqual([], validate(trained))

        def without_rope(data):
            flags = data["strata"]["expected_engine_flags"]
            i = flags.index("--rope-scaling")
            del flags[i:i + 4]

        def rope_scale(data, value):
            flags = data["strata"]["expected_engine_flags"]
            flags[flags.index("--rope-scale") + 1] = value

        cases = [(scaled, without_rope), (scaled, lambda d: rope_scale(d, "1.5")),
                 (trained, lambda d: d["strata"]["expected_engine_flags"].extend(
                     ["--rope-scaling", "yarn", "--rope-scale", "1"]))]
        for base, change in cases:
            with self.subTest(context=base["strata"]["setup_args"]["context"]):
                data = copy.deepcopy(base)
                change(data)
                self.assertTrue(any("rope scaling must be stock setup's" in p for p in validate(data)), validate(data))

    def test_python_lock_null_is_draft_only(self):
        for status in ("draft", "candidate", "qualified"):
            for digest in (None, "a" * 64, "a" * 63):
                with self.subTest(status=status, digest=digest):
                    data = copy.deepcopy(self.data)
                    data["status"] = status
                    data["strata"]["python_lock"]["sha256"] = digest
                    problems = validate(data)
                    expected_valid = digest == "a" * 64 or (digest is None and status == "draft")
                    self.assertEqual(expected_valid, not problems, problems)

    def test_budget_flag_cannot_enable_budget_mode_for_another_model(self):
        self.data["strata"]["forbidden_engine_flags"] = []
        self.data["strata"]["expected_engine_flags"].extend(["--resident-budget-gib", "71"])
        self.assertTrue(any("only for stock budget models" in p for p in validate(self.data)))

    def test_budget_model_requires_its_planned_budget_without_low_ram_flags(self):
        data = read_json(Path(__file__).resolve().parents[2] /
                         "profiles/win11-rtx3090-ud-q4kxl-131k-strata0.1.36-omp18.4.12.json")
        self.assertEqual([], validate(data))
        for budget in ("40", "", "71.5"):
            with self.subTest(budget=budget):
                changed = copy.deepcopy(data)
                flags = changed["strata"]["expected_engine_flags"]
                flags[flags.index("--resident-budget-gib") + 1] = budget
                self.assertTrue(any("must equal" in p for p in validate(changed)))
        for low_ram, flag in (("on", None), ("off", "--mmap-experts"), ("off", "--resident-experts"),
                              ("off", "--experts")):
            with self.subTest(low_ram=low_ram, flag=flag):
                changed = copy.deepcopy(data)
                changed["strata"]["setup_args"]["low_ram"] = low_ram
                if flag:
                    changed["strata"]["expected_engine_flags"].append(flag)
                self.assertTrue(any("map GGUF experts in place" in p for p in validate(changed)))
