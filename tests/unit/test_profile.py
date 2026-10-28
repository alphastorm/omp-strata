"""G01: reject unusable or silently expanded candidate configurations."""
import copy
from pathlib import Path
import unittest

from omp_strata.common import read_json
from omp_strata.profile import Profile, gpu_requirements, load, validate
from omp_strata.receipts import schema_errors

from tests.candidate import PROFILE


def unpipelined_data():
    """Explicit default engine subject even when the selected lane pins pipeline windows or PLE direct reads."""
    data = read_json(PROFILE)
    flags = data["strata"]["expected_engine_flags"]
    for field, flag in (("pipeline_windows", "--pipeline-windows"), ("ple_io", "--ple-io")):
        data["strata"].pop(field, None)
        if flag in flags:
            index = flags.index(flag)
            del flags[index:index + 2]
    return data


def single_gpu_data():
    """Explicit scalar-card subject, even when the selected test lane uses a layer split or stock roles."""
    data = unpipelined_data()
    host = data["host"]
    card = gpu_requirements(host)[0]
    host.pop("gpus", None)
    host.update({key: card[key] for key in ("gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached")})
    setup = data["strata"]["setup_args"]
    for key in ("gpus", "layer_split", "gpu_roles"):
        setup.pop(key, None)
    setup["gpu"] = card["gpu_index"]
    return data


def multi_gpu_data():
    """Neutral two-card fixture in stock setup order, independent of observed host ordinals and the lane's roles."""
    data = unpipelined_data()
    host = data["host"]
    for field in ("gpu_index", "gpu_model", "min_gpu_vram_mib", "display_attached", "cpu_cores"):
        host.pop(field, None)
    host["os"] = "windows"
    host["gpus"] = [
        {"gpu_index": 1, "gpu_model": "NVIDIA GeForce RTX 4090", "arch": "89",
         "pci_bus_id": "00000000:02:00.0", "min_gpu_vram_mib": 24000, "display_attached": False},
        {"gpu_index": 0, "gpu_model": "NVIDIA GeForce RTX 3090", "arch": "86",
         "pci_bus_id": "00000000:01:00.0", "min_gpu_vram_mib": 24000, "display_attached": True},
    ]
    setup = data["strata"]["setup_args"]
    for key in ("gpu", "gpu_roles"):
        setup.pop(key, None)
    setup.update(gpus=[1, 0], layer_split="auto", low_ram="off")
    data["strata"]["engine_version"] = "0.1.42"
    data["strata"].pop("engine_component", None)  # the reviewed v0.1.42 single-zip engine, whatever the lane ships
    flags = data["strata"]["expected_engine_flags"]
    if "--pool-workers" in flags:
        index = flags.index("--pool-workers")
        del flags[index:index + 2]
    return data


CALIBRATION_SETTINGS = {"--pcie-frac": "0.20", "--spec-min-p": "0.70", "--pool-workers": "6",
                        "--adapt-every": "1", "--adapt-swaps": "160", "--adapt-decay": "0.97"}


def calibrated_multi_gpu_data():
    data = multi_gpu_data()
    source = Profile(PROFILE, copy.deepcopy(data))
    strata = data["strata"]
    strata["calibration"] = {"settings": dict(CALIBRATION_SETTINGS), "measured_on": "fixture-win-a",
                             "date": "2026-10-10", "source_profile": source.id,
                             "source_fingerprint": source.fingerprint, "report": {"tok_s": 80.0}}
    flags = strata["expected_engine_flags"]
    for flag, value in CALIBRATION_SETTINGS.items():
        if flag in flags:
            index = flags.index(flag)
            del flags[index:index + 2]
        flags.extend([flag, value])
    strata["forbidden_engine_flags"] = [f for f in strata["forbidden_engine_flags"] if f not in CALIBRATION_SETTINGS]
    return data


# Stock Strata v0.2.1's Windows CUDA 13 engine component, as omp_strata.engine_component.inspect_archive pins it.
COMPONENT_PIN = {"format": "tar.gz", "platform": "windows-x86_64", "backend": "cuda", "variant": "cuda13",
                 "manifest_sha256": "d6ea7d4ae8dce1e646a55363d14c97f9659197f63d500da90efe0d4a8fd82d3e",
                 "build_id": "a7bdbfdabc9a+cuda13.0", "build_source": "f-021-rel", "build_commit": "a7bdbfdabc9a"}
COMPONENT_FILE = "strata-engine-0.1.46-windows-x86_64-cuda-cuda13.tar.gz"


def component_data():
    """A single-card profile whose engine is v0.2.1's component tarball (engine 0.1.46, versioned apart from the app)."""
    data = single_gpu_data()
    strata = data["strata"]
    strata.update(tag="v0.2.1", commit="90767252f420e25223c739d604145ad15911d48b", engine_version="0.1.46",
                  engine_component=dict(COMPONENT_PIN))
    strata["artifacts"]["engine_archive"] = {
        "bytes": 579792118, "file": COMPONENT_FILE,
        "sha256": "2966143ca8df7919448556e7d148e49ccecae0932bb0d5d31294ccde723f94cd",
        "sha256_source": "GitHub release asset digest for Niko1221/Strata v0.2.1",
        "url": f"https://github.com/Niko1221/Strata/releases/download/v0.2.1/{COMPONENT_FILE}"}
    return data


class ComponentEngineProfileTests(unittest.TestCase):
    def test_a_component_engine_is_pinned_apart_from_the_app_tag(self):
        self.assertEqual([], validate(component_data()))

    def test_component_pin_outside_the_reviewed_lane_or_release_is_refused(self):
        def changed(path, value):
            data = component_data()
            parent = data
            for key in path[:-1]:
                parent = parent[key]
            if value is None:
                del parent[path[-1]]
            else:
                parent[path[-1]] = value
            return data
        comp = ("strata", "engine_component")
        cases = {"variant": changed(comp + ("variant",), "cuda12"),
                 "format": changed(comp + ("format",), "zip"),
                 "local build": changed(comp + ("build_source",), "local"),
                 "manifest hash": changed(comp + ("manifest_sha256",), "d6ea7d4a"),
                 "missing key": changed(comp + ("build_id",), None),
                 "extra key": changed(comp + ("signature",), "unverified"),
                 "engine version is the app tag": changed(("strata", "engine_version"), "v0.2.1"),
                 "beta app tag": changed(("strata", "tag"), "v0.2.0-beta"),
                 "archive of another release": changed(("strata", "artifacts", "engine_archive", "url"),
                                                       "https://github.com/Niko1221/Strata/releases/download/"
                                                       f"v0.2.0-beta/{COMPONENT_FILE}"),
                 "archive of another engine": changed(("strata", "artifacts", "engine_archive", "file"),
                                                      COMPONENT_FILE.replace("0.1.46", "0.1.45.3"))}
        for label, data in cases.items():
            with self.subTest(label):
                self.assertTrue([p for p in validate(data) if "engine" in p or "strata.tag" in p], validate(data))


class MultiGpuProfileTests(unittest.TestCase):
    def test_pipeline_windows_accepts_only_the_pinned_multi_card_option(self):
        data = multi_gpu_data()
        data["strata"]["setup_args"].pop("parallel", None)
        data["strata"]["pipeline_windows"] = 2
        data["strata"]["expected_engine_flags"].extend(["--pipeline-windows", "2"])
        self.assertEqual([], validate(data))
        self.assertNotIn("parallel", data["strata"]["setup_args"])
        manual = copy.deepcopy(data)
        manual["strata"]["setup_args"]["layer_split"] = "32"  # the pipeline runs on a pinned manual split too
        self.assertEqual([], validate(manual))

        def single_card(changed):
            changed["host"] = single_gpu_data()["host"]
            changed["strata"]["setup_args"] = single_gpu_data()["strata"]["setup_args"]

        def without_flag(changed):
            flags = changed["strata"]["expected_engine_flags"]
            index = flags.index("--pipeline-windows")
            del flags[index:index + 2]

        def different_flag_value(changed):
            flags = changed["strata"]["expected_engine_flags"]
            flags[flags.index("--pipeline-windows") + 1] = "1"

        cases = [(f"value {value!r}", lambda d, value=value: d["strata"].update(pipeline_windows=value))
                 for value in (1, 3, True, None)]
        cases += [("single card", single_card),
                  ("batch slots", lambda d: d["strata"]["setup_args"].update(parallel=4)),
                  ("flag without field", lambda d: d["strata"].pop("pipeline_windows")),
                  ("field without flag", without_flag),
                  ("different flag value", different_flag_value),
                  ("duplicate flag", lambda d: d["strata"]["expected_engine_flags"].extend(
                      ["--pipeline-windows", "2"]))]
        for name, change in cases:
            with self.subTest(name=name):
                changed = copy.deepcopy(data)
                change(changed)
                self.assertTrue(any("strata.pipeline_windows" in p for p in validate(changed)), validate(changed))

    def test_pinned_stock_calibration_and_budget_refusal(self):
        data = calibrated_multi_gpu_data()
        self.assertEqual([], validate(data))
        for change in (lambda d: d["strata"].update(budget_plan={}),
                       lambda d: d["strata"]["setup_args"].update(family="unsloth", model="UD-Q4_K_XL")):
            changed = copy.deepcopy(data)
            change(changed)
            self.assertIn("strata: budget lanes are not supported for multi-GPU", validate(changed))
        for flag in CALIBRATION_SETTINGS:
            with self.subTest(flag=flag):
                changed = copy.deepcopy(data)
                changed["strata"]["calibration"]["settings"].pop(flag)
                self.assertTrue(validate(changed))
        for swaps in ("80", "160"):
            changed = copy.deepcopy(data)
            changed["strata"]["calibration"]["settings"]["--adapt-swaps"] = swaps
            flags = changed["strata"]["expected_engine_flags"]
            flags[flags.index("--adapt-swaps") + 1] = swaps
            self.assertEqual([], validate(changed))

    def test_existing_profiles_still_load_and_gpu_selection_matches(self):
        paths = sorted((Path(__file__).resolve().parents[2] / "profiles").glob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(profile=path.name):
                profile = load(path)
                if not profile.multi_gpu:
                    self.assertEqual(profile.data["host"]["gpu_index"], profile.data["strata"]["setup_args"]["gpu"])

    def test_valid_multi_and_single_adapters_are_fresh(self):
        data = multi_gpu_data()
        self.assertEqual([], validate(data))
        profile = Profile(PROFILE, data)
        self.assertTrue(profile.multi_gpu)
        self.assertEqual((1, 0), profile.gpu_indices)
        profile.gpu_requirements[0]["gpu_model"] = "changed"
        self.assertEqual("NVIDIA GeForce RTX 4090", profile.gpu_requirements[0]["gpu_model"])
        single = Profile(PROFILE, single_gpu_data())
        self.assertEqual([], validate(single.data))
        self.assertFalse(single.multi_gpu)
        self.assertEqual((single.data["host"]["gpu_index"],), single.gpu_indices)
        self.assertIsNone(single.gpu_requirements[0]["arch"])
        self.assertIsNone(single.gpu_requirements[0]["pci_bus_id"])
        single.gpu_requirements[0]["gpu_model"] = "changed"
        self.assertEqual(single.data["host"]["gpu_model"], single.gpu_requirements[0]["gpu_model"])
        host = dict(single.data["host"])
        host.pop("display_attached", None)
        self.assertFalse(gpu_requirements(host)[0]["display_attached"])

    def test_invalid_card_identity_types_uniqueness_and_shape(self):
        changes = [lambda d: d["host"].update(gpu_index=0),
                   lambda d: d["host"].update(gpus=[]),
                   lambda d: d["host"].update(gpus=d["host"]["gpus"][:1]),
                   lambda d: d["host"]["gpus"].__setitem__(0, None),
                   lambda d: d["host"]["gpus"][1].update(gpu_index=1),
                   lambda d: d["host"]["gpus"][1].update(pci_bus_id="00000000:02:00.0")]
        for key, value in (("gpu_index", True), ("gpu_index", -1), ("gpu_model", "AMD card"), ("arch", "61"),
                           ("arch", 89), ("pci_bus_id", "0000:02:00.0"), ("pci_bus_id", "00000000:AA:00.0"),
                           ("min_gpu_vram_mib", 0), ("min_gpu_vram_mib", 24000.0), ("display_attached", 0)):
            changes.append(lambda d, k=key, v=value: d["host"]["gpus"][0].update({k: v}))
        changes.append(lambda d: d["host"]["gpus"][0].update(unreviewed=True))
        for change in changes:
            data = multi_gpu_data()
            change(data)
            self.assertTrue(validate(data), data["host"])

    def test_invalid_selection_and_unreviewed_lanes(self):
        cases = [("host", "os", "linux"), ("strata", "calibration", {}), ("strata", "budget_plan", {}),
                 ("strata", "gpu_order", "as_given"), ("strata", "env", {"STRATA_ARENA_PIN_GIB": "0"})]
        for key, value in (("gpu", 1), ("gpus", [0, 1]), ("gpus", [True, 0]), ("layer_split", "0"),
                           ("layer_split", "24,36"), ("layer_split", 24), ("layer_split", None),
                           ("low_ram", "on"), ("replicas", 2), ("peer_device", 1), ("reserve_mib", 0)):
            cases.append(("setup", key, value))
        for block, key, value in cases:
            with self.subTest(block=block, key=key):
                data = multi_gpu_data()
                target = data["strata"]["setup_args"] if block == "setup" else data[block]
                target[key] = value
                self.assertTrue(validate(data))
        for flag in ("--layer-split", "--batch", "--peer-device", "--remote-expert-opt"):
            data = multi_gpu_data()
            data["strata"]["expected_engine_flags"].extend([flag, "auto"])
            self.assertTrue(validate(data))

    def test_stock_roles_and_manual_split_are_pinned_exactly(self):
        manual = multi_gpu_data()
        manual["strata"]["setup_args"]["layer_split"] = "32"
        self.assertEqual([], validate(manual))
        roles = multi_gpu_data()  # the 4090 (card 1) as Main: Helpers by number, Main last
        roles["host"]["gpus"].reverse()
        roles["strata"]["setup_args"].update(gpus=[0, 1], gpu_roles={"0": "helper", "1": "main"})
        self.assertEqual([], validate(roles))
        for name, change in (
                ("main not last", lambda s: s.update(gpu_roles={"0": "main", "1": "helper"})),
                ("card off", lambda s: s.update(gpu_roles={"0": "off", "1": "main"})),
                ("integer keys", lambda s: s.update(gpu_roles={0: "helper", 1: "main"})),
                ("missing card", lambda s: s.update(gpu_roles={"1": "main"})),
                ("roles with a manual split", lambda s: s.update(layer_split="32"))):
            with self.subTest(name=name):
                changed = copy.deepcopy(roles)
                change(changed["strata"]["setup_args"])
                self.assertTrue(validate(changed))
        single = single_gpu_data()
        single["strata"]["setup_args"]["gpu_roles"] = {"0": "main"}
        self.assertTrue(validate(single))

    def test_single_card_cannot_claim_multi_setup_or_mismatched_selection(self):
        baseline = single_gpu_data()
        self.assertEqual([], validate(baseline))
        for key, value in (("gpus", [0, 1]), ("layer_split", "auto"), ("gpu", baseline["host"]["gpu_index"] + 1)):
            with self.subTest(key=key):
                data = copy.deepcopy(baseline)
                data["strata"]["setup_args"][key] = value
                self.assertTrue(validate(data))


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.data = read_json(PROFILE)

    def test_ple_io_pins_only_stock_direct_reads(self):
        pair = multi_gpu_data()
        pair["profile_id"] = ("win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking"
                              "-strata0.2.7-omp18.13.2")
        pair["strata"]["setup_args"].pop("parallel", None)
        pair["strata"].update(engine_version="0.1.52", pipeline_windows=2, ple_io="direct")
        pair["strata"]["expected_engine_flags"].extend(["--pipeline-windows", "2", "--ple-io", "direct"])
        self.assertEqual([], validate(pair))
        single = single_gpu_data()
        single["strata"].pop("engine_component", None)
        single["strata"].update(engine_version="0.1.52", ple_io="direct")
        single["strata"]["expected_engine_flags"].extend(["--ple-io", "direct"])
        self.assertEqual([], validate(single))
        newer = copy.deepcopy(single)
        newer["strata"]["engine_version"] = "0.1.53"
        self.assertEqual([], validate(newer))

        def without_flag(data):
            flags = data["strata"]["expected_engine_flags"]
            index = flags.index("--ple-io")
            del flags[index:index + 2]

        def ram_flag(data):
            flags = data["strata"]["expected_engine_flags"]
            flags[flags.index("--ple-io") + 1] = "ram"

        cases = [(f"value {value!r}", lambda d, value=value: d["strata"].update(ple_io=value))
                 for value in ("ram", "Direct", True, None)]
        cases += [("field without flag", without_flag),
                  ("flag without field", lambda d: d["strata"].pop("ple_io")),
                  ("ram flag with field", ram_flag),
                  ("duplicate flag", lambda d: d["strata"]["expected_engine_flags"].extend(["--ple-io", "direct"])),
                  ("older engine", lambda d: d["strata"].update(engine_version="0.1.51")),
                  ("unknown engine", lambda d: d["strata"].update(engine_version="unversioned"))]
        for name, change in cases:
            with self.subTest(name=name):
                changed = copy.deepcopy(pair)
                change(changed)
                problems = validate(changed)
                self.assertTrue(any(p.startswith("strata.ple_io:") for p in problems), problems)
        old_component = component_data()
        old_component["strata"]["ple_io"] = "direct"
        old_component["strata"]["expected_engine_flags"].extend(["--ple-io", "direct"])
        self.assertTrue(any(p.startswith("strata.ple_io:") for p in validate(old_component)))
        stock_ram = copy.deepcopy(pair)
        stock_ram["strata"].pop("ple_io")
        ram_flag(stock_ram)
        self.assertEqual([], validate(stock_ram))

    def test_profile_ids_leave_room_for_lane_variants(self):
        pair_id = ("win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking"
                   "-strata0.2.7-omp18.13.2")
        self.assertEqual(91, len(pair_id))
        route = read_json(Path(__file__).resolve().parents[2] / "schemas/client-route.schema.json")
        schemas = [route["properties"]["profile_id"],
                   route["properties"]["members"]["items"]["properties"]["server_profile"]]
        for identifier, accepted in ((pair_id, True), ("a" * 120, True), ("a" * 121, False)):
            with self.subTest(length=len(identifier)):
                self.data["profile_id"] = identifier
                problems = [p for p in validate(self.data) if p.startswith("profile_id:")]
                self.assertEqual(accepted, not problems, problems)
                for schema in schemas:
                    self.assertEqual(accepted, not schema_errors(identifier, schema))

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

    def test_engine_0148_parks_automatically_unless_a_cache_flag_is_pinned(self):
        # Batch slots and stock's parking tip pin keeping; engine 0.1.48 without --conversation-cache-mib sizes its own
        # cache from the RAM free after load (Strata #3493), and an explicit flag (0 included) replaces that.
        base = read_json(Path(__file__).resolve().parents[2] /
                         "profiles/win11-rtx5090-coder-iq1m-131k-strata0.2.2-omp18.10.1.json")

        def kinds(engine, parallel=None, tip=False, flag=None):
            data = copy.deepcopy(base)
            data["strata"]["engine_version"] = engine
            if parallel:
                data["strata"]["setup_args"]["parallel"] = parallel
            if tip:
                data["strata"]["stock_tips"] = {"--conversation-cache-mib": "8192"}
                data["strata"]["expected_engine_flags"] += ["--conversation-cache-mib", "8192"]
            if flag is not None:
                data["strata"]["expected_engine_flags"] += ["--conversation-cache-mib", flag]
            profile = Profile(Path("profile.json"), data)
            return profile.keeps_conversations, profile.parks_automatically

        cases = {("0.1.47",): (False, False), ("0.1.47", 4): (True, False), ("0.1.47", None, True): (True, False),
                 ("0.1.48",): (False, True), ("0.1.48.1",): (False, True), ("0.1.48", 4): (True, True),
                 ("0.1.48", None, True): (True, False), ("0.1.48", None, False, "0"): (False, False)}
        for arguments, expected in cases.items():
            with self.subTest(arguments=arguments):
                self.assertEqual(expected, kinds(*arguments))

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
