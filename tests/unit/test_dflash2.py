"""Behavioral boundaries for the explicit, pinned stock DFlash2 arm."""
import copy
from pathlib import Path
import unittest

from omp_strata import dflash2
from omp_strata.profile import DFLASH2_START_FLAGS, validate
from tests.unit.test_profile import multi_gpu_data


def source_pin():
    return {
        "repository": dflash2.REPO, "revision": dflash2.REVISION, "license": dflash2.LICENSE,
        "kind": "locally-packed",
        "files": [{"path": path, "bytes": size, "sha256": sha,
                   "sha256_source": "stock v0.2.10 strata_control/drafting.py"}
                  for path, size, sha in dflash2.FILES],
        "packs": copy.deepcopy(dflash2.PACKS), "runtime_pack": "selq4",
        "vocab_sha256": "b1e1d3a7a9e4bf862dcd5923ce661fb59bbd07907e594df5cf86a62ac235cb91",
    }


def variant_data():
    data = multi_gpu_data()
    strata = data["strata"]
    strata["engine_version"] = "0.1.56"
    strata["setup_args"].pop("parallel", None)
    strata["drafting"] = "dflash2"
    strata["forbidden_engine_flags"] = list(dict.fromkeys([*strata["forbidden_engine_flags"], *DFLASH2_START_FLAGS]))
    data["model"]["dflash2_source"] = source_pin()
    return data


class DFlash2ProfileTests(unittest.TestCase):
    def test_explicit_pinned_layer_split_is_admitted(self):
        data = variant_data()
        self.assertEqual([], validate(data))
        self.assertTrue(dflash2.is_pinned(data))
        data["model"]["dflash2_source"]["runtime_pack"] = "q4_0"
        self.assertEqual([], validate(data))

    def test_incompatible_modes_and_settings_are_refused(self):
        mutations = [
            (("strata", "drafting"), "auto"), (("strata", "drafting"), "mtp"),
            (("strata", "drafting"), "off"), (("strata", "drafting"), []),
            (("strata", "engine_version"), "0.1.55"), (("strata", "pipeline_windows"), 2),
            (("strata", "batch_mtp"), True), (("strata", "calibration"), {}),
            (("strata", "setup_args", "parallel"), 4), (("strata", "setup_args", "family"), "coder"),
            (("model", "format"), "modelopt-fp4-local"),
        ]
        for path, value in mutations:
            data = variant_data()
            block = data
            for key in path[:-1]:
                block = block[key]
            block[path[-1]] = value
            with self.subTest(path=path, value=value):
                self.assertTrue(any(p.startswith("strata.drafting:") for p in validate(data)))

    def test_source_identity_and_provenance_are_required(self):
        for path, value in [
            (("revision",), "0" * 40), (("repository",), "other/model"),
            (("license",), "MIT"), (("kind",), "download"),
            (("runtime_pack",), "q8"), (("vocab_sha256",), "bad"),
            (("files", 0, "path"), "../config.json"), (("files", 1, "sha256"), "0" * 64),
            (("files", 0, "bytes"), 10), (("files", 0, "sha256_source"), ""),
            (("packs", "selq4", "sha256"), "0" * 64),
        ]:
            data = variant_data()
            block = data["model"]["dflash2_source"]
            for key in path[:-1]:
                block = block[key]
            block[path[-1]] = value
            with self.subTest(path=path):
                self.assertTrue(any(p.startswith("model.dflash2_source") for p in validate(data)))
        data = variant_data()
        del data["model"]["dflash2_source"]
        self.assertTrue(any(p.startswith("model.dflash2_source") for p in validate(data)))

    def test_source_without_explicit_mode_is_refused(self):
        data = variant_data()
        del data["strata"]["drafting"]
        self.assertTrue(any(p.startswith("model.dflash2_source:") for p in validate(data)))

    def test_every_start_time_flag_stays_forbidden(self):
        for flag in DFLASH2_START_FLAGS:
            data = variant_data()
            data["strata"]["forbidden_engine_flags"].remove(flag)
            with self.subTest(flag=flag):
                self.assertTrue(any(p.startswith("strata.drafting:") for p in validate(data)))
