# Stock calibration fixture from Niko1221/Strata v0.1.36 (36fa455e579b23a9c909c2c6fe1bddd9e51cb8ca), verbatim:
# tools/calibrate.py with_arg, DEFAULTS and apply, then setup.py write_config. Tests split it into the two
# stock module files of a disposable checkout.
CALIBRATE = '''
from __future__ import annotations


def with_arg(args: list[str], flag: str, value: str | None) -> list[str]:
    """`args` with `flag value` set (replaced if present), or removed when value is None."""
    out = list(args)
    if flag in out:
        i = out.index(flag)
        del out[i:i + 2]
    if value is not None:
        out += [flag, value]
    return out


DEFAULTS = {"--pcie-frac": None, "--spec-min-p": "0.5", "--pool-workers": None}   # None: the engine's own choice


def apply(args: list[str], settings: dict) -> list[str]:
    """`args` with the calibrated settings; a setting the calibration did not change goes back to the product
    default (setup's --spec-min-p 0.5, the engine's own PCIe share and worker count), so an older calibration's
    values never linger."""
    out = list(args)
    for flag, default in DEFAULTS.items():
        out = with_arg(out, flag, settings.get(flag, default))
    return out
'''

SETUP = '''
import json
import os
from pathlib import Path


def write_config(path: Path, cfg: dict):
    """A run config, written whole or not at all (#459): to a temporary file first, then moved over the old one, so
    a setup stopped half-way (a closed window, a full disk) never leaves an empty strata-*.json behind."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    os.replace(tmp, path)
'''
