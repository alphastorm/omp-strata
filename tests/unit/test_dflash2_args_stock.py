"""Host-free v0.2.13 user_args merge proof against the dev-env's pinned stock checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from omp_strata.common import read_json


STOCK_COMMIT = "d2f096475817d4666c364c820b0ca830f751cfc5"
PROFILES = Path(__file__).resolve().parents[2] / "profiles"
PAIR = ("win11-rtx3090-rtx4090-iq3s-262k-df2-disp4090-roles-split24-trimweights-pledirect"
        "-env86gt-strata0.2.13-omp18.18.3")
PRO = "win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.13-omp18.18.3"

# Separate interpreter, real unmodified stock engine_args and merge/apply helpers; no GPU, engine or network.
PROOF = r'''
import json
from pathlib import Path
import sys
from unittest.mock import patch

from serve import server
from strata_control import drafting

request = json.loads(sys.argv[1])
root = Path(request["root"])
data = root / "data"
folder = data / drafting.FOLDER
folder.mkdir(parents=True)
with (folder / drafting.PACK_NAME).open("wb") as pack:
    pack.truncate((1 << 20) + 1)  # stock _here requires strictly more than 1 MiB
(folder / drafting.VOCAB_NAME).write_bytes(b"host-free vocabulary fixture")
engine = root / "engine.exe"
engine.write_bytes(b"--mtp-draft-vocab FILE (or --mtp DIR\0")
args = request["flags"] + ["--pack", str(data / "packs/iq3_s"), "--mtp", str(data / "mtp/rt")]
# A stale base confidence is deliberately present: merge and drafting must leave exactly the person's pin.
args += ["--draft-conf", "0.8"]
cfg = {"args": args, "args_written": list(args), "model_name": "qwen3.8-flash-next-iq3_s",
       "drafting": "dflash2", "user_args": ["--draft-conf", request["confidence"]]}
if request["pair"]:
    cfg.update(gpu=[0, 1], layer_split="24", gpu_order="as_given", gpu_roles={"0": "main", "1": "helper"})
else:
    cfg.update(gpu=0, parallel=4)
before = json.loads(json.dumps(cfg))
with patch.object(drafting, "detect_hardware", return_value=("cuda", request["archs"])), \
        patch.object(server, "drafting_card_class", return_value="other"), \
        patch.object(server, "drafting_vram_mib", return_value=request["vram_mib"]) as vram:
    actual = server.engine_args(cfg, str(engine), announce=False)
assert vram.called, "engine_args must use the server's card-memory seam"
assert cfg == before, "engine_args changed the persisted config instead of shaping a copy"
print(json.dumps(actual))
'''

# Unmodified stock setup.py carry_user_args: what a requalify install's setup re-run leaves over an installed root.
CARRY = r'''
import json
import sys

import setup

request = json.loads(sys.argv[1])
generated, pin = request["generated"], request["pin"]
old = {"args": list(generated), "args_written": list(generated), "user_args": list(pin)}
new = {"args": list(generated)}
kept = setup.carry_user_args(old, new)
print(json.dumps({"new": new, "kept": kept}))
'''


class StockDraftingArgsProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_STRATA_SRC")
        if not value or not Path(value).is_dir():
            raise unittest.SkipTest("dev-env supplies the pinned v0.2.13 checkout")
        cls.source = Path(value).resolve()
        cls.python = os.environ.get("OMP_STRATA_STRATA_PYTHON", sys.executable)
        result = subprocess.run(["git", "-C", str(cls.source), "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise AssertionError("OMP_STRATA_STRATA_SRC is not a readable pinned checkout")
        if result.stdout.strip() != STOCK_COMMIT:
            raise unittest.SkipTest("this proof needs the v0.2.13 pin selected by dev-env")

    def prove(self, *, pair, confidence, window):
        with tempfile.TemporaryDirectory() as temporary:
            request = {"root": temporary, "pair": pair, "confidence": confidence,
                       "archs": ["sm_86", "sm_89"] if pair else ["sm_120"],
                       "vram_mib": None if pair else 97887,
                       "flags": read_json(PROFILES / ((PAIR if pair else PRO) + ".json"))["strata"]["expected_engine_flags"]}
            result = subprocess.run([self.python, "-c", PROOF, json.dumps(request)], cwd=self.source,
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)
        actual = json.loads(result.stdout)
        for flag, value in (("--draft-conf", confidence), ("--spec", window), ("--draft", "dflash2"),
                            ("--draft-fallback", "none")):
            self.assertEqual(1, actual.count(flag), actual)
            self.assertEqual(value, actual[actual.index(flag) + 1], actual)
        self.assertNotIn("--mtp", actual)
        self.assertEqual(1, actual.count("--mtp-draft-vocab"))

    def test_pair_keeps_its_pinned_point_five_and_stock_window_six(self):
        self.prove(pair=True, confidence="0.5", window="6")

    def test_four_slot_pro_keeps_its_pinned_point_five_five_and_stock_window_eight(self):
        self.prove(pair=False, confidence="0.55", window="8")

    def test_setup_rerun_carries_the_pin_to_the_end_of_args_and_stamps_it(self):
        generated = read_json(PROFILES / (PAIR + ".json"))["strata"]["expected_engine_flags"]
        pin = ["--draft-conf", "0.5"]
        result = subprocess.run([self.python, "-c", CARRY, json.dumps({"generated": generated, "pin": pin})],
                                cwd=self.source, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)
        new = json.loads(result.stdout)["new"]
        self.assertEqual({"args": generated + pin, "args_written": generated + pin, "user_args": pin}, new)


if __name__ == "__main__":
    unittest.main()
