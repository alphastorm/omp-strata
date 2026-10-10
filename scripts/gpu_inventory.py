#!/usr/bin/env python3
"""Read-only NVIDIA inventory for stock setup planning; JSON stdout only, no UUIDs or serials.

Run before drafting a profile: python scripts/gpu_inventory.py [--profile profiles/candidate.json].
A nonzero exit means required identity/capacity facts are missing or the optional profile does not match.
Unsupported advisory PCIe/compute-mode fields stay null with explicit reasons; they do not invent capacity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omp_strata import procs
from omp_strata.common import utc_now
from omp_strata.lifecycle import canonical_pci_bus_id, parse_gpu_csv
from omp_strata.profile import Profile, load

# display_attached is the physical connection (a monitor on the card's connectors); display_active only says a display is
# initialized now and reads Disabled under WDDM even on the card driving the desktop, so it stays advisory.
IDENTITY_FIELDS = ("index", "name", "pci.bus_id", "memory.total", "compute_cap", "driver_version", "display_attached")
ADVISORY_FIELDS = {
    "compute_mode": "compute_mode",
    "display_active": "display_active",
    "pcie_gen_current": "pcie.link.gen.current",
    "pcie_gen_max": "pcie.link.gen.max",
    "pcie_width_current": "pcie.link.width.current",
    "pcie_width_max": "pcie.link.width.max",
}


def query(exe: str, fields: tuple[str, ...]) -> list[dict[str, str]]:
    result = subprocess.run([exe, "--query-gpu=" + ",".join(fields), "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)
    if result.returncode:
        raise ValueError("nvidia-smi query failed")
    return parse_gpu_csv(result.stdout, fields)


def inventory(profile: Profile | None = None) -> dict:
    """Collect public-safe identity, capacities and advisory observations without examining process ownership."""
    missing, required, cards = [], [], []
    report = {"schema_version": 1, "observed_utc": utc_now(), "gpus": cards,
              "ram": {"total_mib": None, "available_mib": None}, "complete": False, "missing": missing}
    try:
        memory = procs.memory()
        for field, source in (("total_mib", "total"), ("available_mib", "available")):
            value = memory.get(source)
            if type(value) is int and value > 0:
                report["ram"][field] = value // (1 << 20)
            else:
                required.append(f"ram.{field}: unavailable")
    except (OSError, ValueError, subprocess.SubprocessError):
        required.append("system RAM observation unavailable")
    exe = shutil.which("nvidia-smi")
    try:
        if not exe:
            raise ValueError("nvidia-smi unavailable")
        rows = query(exe, IDENTITY_FIELDS)
        seen_indices, seen_buses = set(), set()
        for row in rows:
            card = {"index": None, "name": None, "pci_bus_id": None, "memory_total_mib": None,
                    "arch": None, "driver_version": None, "display_attached": None,
                    **dict.fromkeys(ADVISORY_FIELDS), "missing": []}
            cards.append(card)
            conversions = {
                "index": ("index", lambda v: int(v) if v.isdigit() else None),
                "name": ("name", lambda v: v if v.startswith("NVIDIA ") else None),
                "pci_bus_id": ("pci.bus_id", canonical_pci_bus_id),
                "memory_total_mib": ("memory.total", lambda v: int(v) if v.isdigit() and int(v) > 0 else None),
                "arch": ("compute_cap", lambda v: v.replace(".", "") if re.fullmatch(r"[1-9]\d*\.\d", v) else None),
                "driver_version": ("driver_version", lambda v: v if re.fullmatch(r"\d+(?:\.\d+)*", v) else None),
                "display_attached": ("display_attached", lambda v: {"Yes": True, "No": False}.get(v)),
            }
            for target, (source, convert) in conversions.items():
                try:
                    card[target] = convert(row[source])
                except ValueError:
                    pass
                if card[target] is None:
                    reason = f"GPU row {len(cards) - 1}.{target}: unavailable or malformed"
                    card["missing"].append(reason)
                    required.append(reason)
            if card["index"] in seen_indices or card["pci_bus_id"] in seen_buses:
                required.append("duplicate GPU index or PCI bus ID")
            seen_indices.add(card["index"])
            seen_buses.add(card["pci_bus_id"])
        for target, source in ADVISORY_FIELDS.items():
            values = {}
            try:
                advisory = query(exe, ("index", source))
                for row in advisory:
                    if not row["index"].isdigit() or int(row["index"]) in values:
                        raise ValueError("malformed advisory GPU indices")
                    values[int(row["index"])] = row[source]
                if set(values) != seen_indices:
                    raise ValueError("advisory GPU set differs from identity query")
            except (OSError, ValueError, subprocess.SubprocessError):
                values = {}
            for card in cards:
                value = values.get(card["index"], "")
                if target == "compute_mode":
                    card[target] = value if value in ("Default", "Exclusive_Thread", "Prohibited", "Exclusive_Process") else None
                elif target == "display_active":
                    card[target] = {"Enabled": True, "Disabled": False}.get(value)
                elif value.isdigit() and int(value) > 0:
                    card[target] = int(value)
                if card[target] is None:
                    reason = f"GPU {card['index']}.{target}: unavailable"
                    card["missing"].append(reason)
                    missing.append(reason)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        required.append("GPU identity query unavailable: " + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__))
    if profile is not None:
        problems = []
        by_index = {card["index"]: card for card in cards}
        for want in profile.gpu_requirements:
            card = by_index.get(want["gpu_index"])
            if card is None:
                problems.append(f"GPU {want['gpu_index']}: missing")
                continue
            for expected, actual in (("gpu_model", "name"), ("arch", "arch"), ("pci_bus_id", "pci_bus_id")):
                if want[expected] is not None and card[actual] != want[expected]:
                    problems.append(f"GPU {want['gpu_index']}: {expected} mismatch")
            if card["memory_total_mib"] is None or card["memory_total_mib"] < want["min_gpu_vram_mib"]:
                problems.append(f"GPU {want['gpu_index']}: VRAM below profile floor")
            if card["driver_version"] is None or int(card["driver_version"].split(".")[0]) < profile.data["host"]["min_driver_major"]:
                problems.append(f"GPU {want['gpu_index']}: driver below profile floor")
            if card["display_attached"] is not want["display_attached"]:
                problems.append(f"GPU {want['gpu_index']}: display attachment differs from profile")
        report["profile_check"] = {"profile_id": profile.id, "matches": not problems, "problems": problems}
        required.extend(problems)
    missing.extend(required)
    report["complete"] = bool(cards) and not required
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, help="optionally check an already drafted profile's GPU identity")
    args = parser.parse_args(argv)
    try:
        profile = load(args.profile) if args.profile else None
    except (OSError, ValueError):
        print(json.dumps({"schema_version": 1, "observed_utc": utc_now(), "complete": False,
                          "gpus": [], "missing": ["profile unreadable or invalid"]}, indent=2))
        return 1
    report = inventory(profile)
    print(json.dumps(report, indent=2))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
