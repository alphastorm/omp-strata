"""Host-free v0.2.12 engine_args proof; dev-env supplies the pinned checkout and its Python env."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from omp_strata import dflash2
from omp_strata.common import read_json


STOCK_COMMIT = "146df3c468739147f520ac3816de806f71232571"
PRO_PROFILE = (Path(__file__).resolve().parents[2] / "profiles" /
               "win11-rtxpro6000-iq3s-262k-slots4-df2-pledirect-kvvram-envpg-parking-strata0.2.11-omp18.16.0.json")

# Run the unmodified stock server in its own interpreter: no module-cache collisions with composed tests,
# no engine process, network, packer or GPU. Sparse contents cannot pass either stock pack's SHA-256.
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
for name, size, digest in request["packs"]:
    target = folder / name
    with target.open("wb") as output:
        output.truncate(size)
    info = target.stat()
    target.with_name(name + ".ok").write_text(json.dumps({
        "size": size, "mtime_ns": info.st_mtime_ns, "sha256": digest}), encoding="utf-8")
(folder / drafting.VOCAB_NAME).write_bytes(b"host-free vocabulary fixture")
engine = root / "engine.exe"
engine.write_bytes(b"selector codebooks: Q4_0 rows\0--mtp-draft-vocab FILE (or --mtp DIR\0")
args = request["flags"] + ["--pack", str(data / "packs/iq3_s"), "--mtp", str(data / "mtp/rt")]
cfg = {"args": args, "model_name": "qwen3.8-flash-next-iq3_s", "drafting": "dflash2", "gpu": 0, "parallel": 4}

def snapshot():
    return {p.name: {"size": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns,
                     "marker": p.read_bytes().hex() if p.name.endswith(".ok") else None}
            for p in folder.iterdir()}

before = snapshot()
with patch.object(drafting, "detect_hardware", return_value=("cuda", ["sm_120"])), \
        patch.object(server, "drafting_card_class", return_value="other"), \
        patch.object(server, "drafting_vram_mib", return_value=request["vram_mib"]) as vram, \
        patch.object(drafting, "sha256_of", side_effect=AssertionError("marker hit must not hash a sparse pack")):
    actual = server.engine_args(cfg, str(engine), announce=False)
assert vram.called, "engine_args must use the server's card-memory seam"
assert snapshot() == before, "stock start changed the directory or marker identity"
slots = drafting.expected_slots(97000, args)
assert slots >= drafting.CONF_STEPS[0][0], (slots, drafting.CONF_STEPS)
print(json.dumps({"pack": Path(actual[actual.index("--draft-model") + 1]).name,
                  "confidence": actual[actual.index("--draft-conf") + 1], "slots": slots}))
'''


class StockTunedDFlash2Proof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OMP_STRATA_STRATA_SRC")
        if not value or not Path(value).is_dir():
            raise unittest.SkipTest("set OMP_STRATA_STRATA_SRC through dev-env to the pinned v0.2.12 checkout")
        cls.source = Path(value).resolve()
        cls.python = os.environ.get("OMP_STRATA_STRATA_PYTHON", sys.executable)
        result = subprocess.run(["git", "-C", str(cls.source), "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise AssertionError("OMP_STRATA_STRATA_SRC is not a readable pinned checkout")
        if result.stdout.strip() != STOCK_COMMIT:
            raise unittest.SkipTest("this proof needs the v0.2.12 pin; dev-env checks out its selected profile's commit")

    def prove(self, *, tuned, vram_mib):
        packs = [dflash2.PACKS["q4_0"], dflash2.PACKS["selq4"]]
        if tuned:
            packs.append({"file": dflash2.TUNED_NAME, "bytes": dflash2.TUNED_BYTES, "sha256": dflash2.TUNED_SHA256})
        with tempfile.TemporaryDirectory() as temporary:
            request = {"root": temporary, "vram_mib": vram_mib,
                       "flags": read_json(PRO_PROFILE)["strata"]["expected_engine_flags"],
                       "packs": [[spec[k] for k in ("file", "bytes", "sha256")] for spec in packs]}
            result = subprocess.run([self.python, "-c", PROOF, json.dumps(request)], cwd=self.source,
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(dflash2.TUNED_NAME if tuned and vram_mib is not None else dflash2.CONVERTED_NAME,
                         observed["pack"])
        self.assertEqual("0.35", observed["confidence"])
        self.assertGreaterEqual(observed["slots"], 12000)

    def test_tuned_pro_uses_the_resident_pack_without_hashes_or_writes(self):
        self.prove(tuned=True, vram_mib=97000)

    def test_several_cards_keep_the_converted_pack_without_writes(self):
        self.prove(tuned=True, vram_mib=None)

    def test_standard_pro_keeps_the_converted_pack_without_writes(self):
        self.prove(tuned=False, vram_mib=97000)


if __name__ == "__main__":
    unittest.main()
