# Stock Niko1221/Strata v0.2.3 card ordering; tag target 5c8dd322528cc84f68f461ad54a506b9da8fa8d4.
# Extracted AST nodes of strata_control/gpu_roles.py, then serve/server.py. Tests inject score/VRAM seams; no
# hardware probe, import of the stock modules or HIP path runs. The one line after the gpu_roles nodes is test glue:
# serve/server.py calls these two functions through its `gpu_roles` module import.
from __future__ import annotations
from types import SimpleNamespace
from typing import Any

ROLES = ("main", "helper", "off")


def _int_list(g: Any) -> list[int]:
    if g is None or g == "":
        return []
    items = g if isinstance(g, (list, tuple)) else str(g).split(",")
    return [int(str(x).strip()) for x in items if str(x).strip() != ""]


def parse_saved(value: Any) -> dict[int, str] | None:
    """A saved "gpu_roles" object -> {index: role}; None when it is not one (the setting is then ignored)."""
    if not isinstance(value, dict) or not value:
        return None
    out: dict[int, str] = {}
    for k, v in value.items():
        try:
            i = int(str(k).strip())
        except ValueError:
            return None
        if str(v).lower() not in ROLES:
            return None
        out[i] = str(v).lower()
    if sum(1 for r in out.values() if r == "main") > 1:
        return None
    return out


def saved_roles(cfg: dict) -> tuple[dict[int, str] | None, str | None]:
    """(the roles a run settings dict carries, a problem line or None). Roles win when the legacy "gpu" is the mirror of them, or when "gpu" is
    missing; a "gpu" that was edited by hand (it names other cards, or another Main) wins and the roles are ignored (#3256: a file that names
    its GPUs keeps them)."""
    roles = parse_saved(cfg.get("gpu_roles"))
    if roles is None:
        return None, ("run settings: gpu_roles is not {card: main|helper|off} with one main; ignored" if cfg.get("gpu_roles") is not None else None)
    try:
        gl = _int_list(cfg.get("gpu"))
    except ValueError:
        return None, "run settings: gpu is not a card number or a list; gpu_roles ignored"
    on = [i for i, r in roles.items() if r != "off"]
    main = next((i for i, r in roles.items() if r == "main"), None)
    if cfg.get("gpu_none") and not on:
        return roles, None
    if not gl:
        return (roles, None) if on else (None, None)
    if sorted(gl) != sorted(on) or (main is not None and gl[-1] != main):
        return None, "run settings: gpu was edited by hand, gpu_roles ignored"
    return roles, None


def engine_order(roles: dict[int, str], speeds: dict[int, float] | None = None) -> list[int]:
    """The card list of saved roles for the server: Helpers slowest first (ties by number), then Main. Used where only numbers and
    (maybe) measured speeds are known."""
    sp = speeds or {}
    helpers = sorted([i for i, r in roles.items() if r == "helper"], key=lambda i: (sp.get(i, 0.0), i))
    return helpers + sorted(i for i, r in roles.items() if r == "main")


gpu_roles = SimpleNamespace(saved_roles=saved_roles, engine_order=engine_order)


def gpu_list(cfg: dict) -> list[int]:
    """The config's "gpu": one card (2), or several for a layer split ([0, 2] or "0,2"), numbered as nvidia-smi
    numbers them; [] when it names none."""
    roles, _ = gpu_roles.saved_roles(cfg)       # "gpu_roles" (Main / Helper / Off per card) wins unless "gpu" was edited by hand
    if roles is not None:
        legacy = _gpu_numbers(cfg.get("gpu"))
        return legacy if legacy else gpu_roles.engine_order(roles)     # Main LAST; Off cards left out; [] when every card is Off
    return _gpu_numbers(cfg.get("gpu"))


def _gpu_numbers(g) -> list[int]:
    if g is None or g == "":
        return []
    items = g if isinstance(g, (list, tuple)) else str(g).split(",")
    return [int(str(x).strip()) for x in items if str(x).strip() != ""]


def gpu_roles_active(cfg: dict) -> bool:
    """True when the run settings carry usable "gpu_roles": the card order is the person's (Main last), never re-sorted by speed."""
    return gpu_roles.saved_roles(cfg)[0] is not None


def layer_split_value(cfg: dict) -> str:
    """#644: the config's "layer_split" as the engine's --layer-split value: "auto" (the default), or the FIRST LAYER of
    each later GPU's share - one rising number per GPU after the first, e.g. "24,36,42" for 4 GPUs (layers 0-23 on the
    first card, 24-35, 36-41, 42 to the end) - as a string or a JSON list ([24, 36, 42]).  ValueError with the format
    and an example for anything else, such as per-card layer counts ("24,16,12,12")."""
    v = cfg.get("layer_split")
    if v is None or (isinstance(v, str) and v.strip().lower() in ("", "auto")):
        return "auto"
    n = len(gpu_list(cfg))
    items = v if isinstance(v, (list, tuple)) else str(v).split(",") if isinstance(v, (str, int)) else None
    vals = []
    for x in items or []:
        try:
            if isinstance(x, bool) or isinstance(x, float):
                raise ValueError
            vals.append(int(str(x).strip()))
        except ValueError:
            vals = None
            break
    want = max(n - 1, 1)
    example = ",".join(str(round(48 * (i + 1) / (want + 1))) for i in range(want))
    hint = (f'"layer_split" is the first layer of each later GPU, one rising number per GPU after the first '
            f'({want} for {n} GPUs), not a count of layers per card - e.g. "{example}" (or [{example.replace(",", ", ")}])'
            f' for an even share of 48 layers, or "auto" (the default) to place them by each card\'s free VRAM')
    if not vals:
        raise ValueError(f"{hint}; got {v!r}")
    if n > 1 and len(vals) != n - 1:
        raise ValueError(f"{hint}; got {len(vals)} number(s) ({v!r}) for {n} GPUs")
    if vals[0] < 2 or any(b <= a for a, b in zip(vals, vals[1:])):
        raise ValueError(f"{hint}; got {v!r}, which does not rise from 2 or more")
    return ",".join(str(x) for x in vals)


def ordered_gpus(cfg: dict, scores=None, vrams=None, archs=None) -> list[int]:
    """#1352: the cards of a layer split in the order the engine stages them.  With "layer_split": "auto" (the
    default) the faster card goes LAST - the last stage runs the head, the draft layer and the verify, and a prompt
    chunk waits on it (the reporter's 4070 Ti SUPER + 5060 Ti: a 6K prompt took 50 s one way round and 15 s the
    other); "faster" is multiprocessors x max clock.  Equal cards - scores within 5% - keep the config's order, and
    so does anything we cannot measure.  "gpu_order": "as_given" keeps the config's order whatever the cards.  A
    manual "layer_split" ("24") also keeps it: the user placed the layers.  #1576: the reorder is skipped when it
    would land the last stage on a card with less total VRAM than the one the config put there - that stage's head,
    draft and verify have a floor the smaller card cannot afford.  scores/vrams: {index: value} (tests); None asks
    the driver - injected scores without injected vrams means no VRAM check (a test seam is a test seam)."""
    gl = gpu_list(cfg)
    if len(gl) < 2 or cfg.get("gpu_order") == "as_given" or gpu_roles_active(cfg):
        return gl
    args = cfg.get("args") or []
    if "--peer-device" in args or "--layer-split" in args or layer_split_value(cfg) != "auto":
        return gl
    hip = cfg.get("backend") == "hip"
    if hip:
        # An integrated Radeon (Strix Halo beside an R9700) is never the LAST stage: that stage runs the head, the draft layer and the
        # check of the guesses, and the iGPU usually draws the desktop.  Its "VRAM" is the BIOS carve-out (up to 96 GB), which made the
        # #1576 memory guard below keep it last.  It goes first, the cards with memory of their own follow in speed order.
        # archs: {index: "gfx1151"} (tests); None asks the KFD topology, unless scores were injected (a test seam).
        ar = archs if archs is not None else (hip_gpu_archs() if scores is None else None)
        ig = igpu_cards(gl, ar)
        if ig and len(ig) < len(gl):
            sc0 = scores if scores is not None else hip_speed_scores(gl)
            rest = [i for i in gl if i not in ig]
            if sc0 and all(i in sc0 for i in rest):
                rest = sorted(rest, key=lambda i: sc0[i]) if max(sc0[i] for i in rest) >= 1.05 * min(sc0[i] for i in rest) else rest
            out = [i for i in gl if i in ig] + rest
            if out != gl:
                print(f"[strata] layer split: card order {','.join(map(str, out))} (GPU {','.join(str(i) for i in sorted(ig))} is built-in "
                      f"graphics: it takes the first layers, never the last stage; \"gpu_order\": \"as_given\" keeps {','.join(map(str, gl))})",
                      flush=True)
            return out
    sc = scores if scores is not None else (hip_speed_scores(gl) if hip else gpu_speed_scores(gl))
    if not sc or any(i not in sc for i in gl):
        return gl
    if max(sc[i] for i in gl) < 1.05 * min(sc[i] for i in gl):
        return gl     # #1760: cards within 5% of each other are the same card (two 5070 Ti read 1.2% apart on the clock): keep the order
    out = sorted(gl, key=lambda i: sc[i])
    if out != gl:
        vram = vrams if vrams is not None else (None if scores is not None else gpu_vram_mib(gl, hip))
        if vram is not None and all(i in vram for i in gl) and vram[out[-1]] < vram[gl[-1]]:
            print(f"[strata] layer split: keeping card order {','.join(map(str, gl))} - the faster card has "
                  f"less VRAM than the one the split ends on ({vram[out[-1]]} vs {vram[gl[-1]]} MiB, #1576)",
                  flush=True)
            return gl
        print(f"[strata] layer split: card order {','.join(map(str, out))} (the faster card last; "
              f'"gpu_order": "as_given" keeps {",".join(map(str, gl))}, #1352)', flush=True)
    return out
