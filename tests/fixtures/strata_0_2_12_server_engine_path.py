# Stock Niko1221/Strata v0.2.12 serve/server.py; parsed, never imported or executed.
# Source SHA-256: 18c8303780c87908106156826876563c8e37e7fc7af805b390e55c38a1212685
# Payload SHA-256: 147c4f2b79e50a7c2336619c1f321a449f54708ca021aad8de2863b6ae459c23
# Stock payload follows.
from strata_control import draft_layer


from strata_control import drafting


from strata_control import vram_fit


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


def gpu_all_off(cfg: dict) -> bool:
    """Every card is set to Off ("gpu_roles" with no card on, or "gpu_none": true)."""
    roles, _ = gpu_roles.saved_roles(cfg)
    return roles is not None and not any(r != "off" for r in roles.values())


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


def layer_split_of(cfg: dict) -> bool:
    """Several GPUs in the config are a layer split, unless the args put the later card(s) to another use: with
    --peer-device the second card is an expert-cache tier, and the engine refuses that beside --layer-split (#665)."""
    return len(gpu_list(cfg)) > 1 and "--peer-device" not in cfg["args"]


def drafting_card_class() -> str:
    """The class of this computer's graphics card for the drafter table (strata_control/drafting.py), looked up once."""
    if not _CARD_CLASS:
        archs: list[str] = []
        try:
            from strata_control import engine_component
            archs = list(engine_component.cuda_archs_present()) + list(engine_component.hip_archs_present())
        except Exception:                                    # noqa: BLE001 - an unknown card is the "other" class, never an error
            pass
        _CARD_CLASS.append(drafting.card_class(archs))
    return _CARD_CLASS[0]


def drafting_vram_mib(cfg: dict, backend: str | None, archs) -> float | None:
    """MiB of graphics memory of the ONE card DFlash2 would run on, for the drafter's confidence (drafting.expected_slots); None for several cards, a
    chip that shares the computer's memory (Strix Halo, the Spark: their experts are all "resident") or a card the driver does not answer for."""
    try:
        gl = gpu_list(cfg)
        arch = str((list(archs or [""]) or [""])[0]).lower()
        if len(gl) > 1 or arch in HIP_IGPU_ARCHS or arch == "sm_121":
            return None
        got = gpu_vram_mib(gl or [0], hip=(backend == "hip"))
        return float(next(iter(got.values()))) if got else None
    except Exception:                                        # noqa: BLE001 - an unreadable card keeps the plain 0.35, never stops a start
        return None


def mtp_retry_args(cfg: dict, exe: str | None, extra: list[str] | None = None) -> list[str] | None:
    """The arguments to start again with when an Auto start that picked DFlash2 ends before the engine is ready: the same start with the MTP (or no drafter, when
    the MTP layer is not on this computer). None when there is nothing to retry: the person named DFlash2 themselves (that start fails with its reason, as it
    should), the choice was not DFlash2, or the MTP arguments are the same. Builds the arguments without any line or note (engine_args announce=False)."""
    if drafting.normalize(cfg.get("drafting")) != "auto" or "args" not in cfg:
        return None
    try:
        first = engine_args(cfg, exe, announce=False)
        if "--draft" not in first or first[first.index("--draft") + 1:first.index("--draft") + 2] != ["dflash2"]:
            return None
        alt = engine_args({**cfg, "drafting": "mtp"}, exe, announce=False) + list(extra or [])
    except Exception:                                  # noqa: BLE001 - a retry that cannot be worked out is no retry
        return None
    return alt if alt != first + list(extra or []) else None


def nodraft_retry_args(cfg: dict, exe: str | None, extra: list[str] | None = None) -> list[str] | None:
    """The arguments to start again with when an Auto start ends before the engine is ready because a card ran out of memory: the same start with no drafter
    (the draft layer and DFlash2's buffers are the biggest optional part on a card that is short), never the MTP in place of DFlash2.  None when the drafting
    was not Auto (the person named a drafter: that start fails with the engine's reason), when the first start has no drafter anyway, or when nothing differs."""
    if drafting.normalize(cfg.get("drafting")) != "auto" or "args" not in cfg:
        return None
    try:
        first = engine_args(cfg, exe, announce=False)
        if "--draft" not in first and "--mtp" not in first:
            return None
        alt = engine_args({**cfg, "drafting": "off"}, exe, announce=False) + list(extra or [])
    except Exception:                                  # noqa: BLE001 - a retry that cannot be worked out is no retry
        return None
    return alt if alt != first + list(extra or []) else None


def engine_args(cfg: dict, exe: str | None = None, *, announce: bool = True) -> list[str]:
    """The engine's arguments: the config's, and with several GPUs the layer split across them ("layer_split" in the
    config: "auto" by default, or the first layer of each later GPU's share, e.g. "18" or "16,32"; see
    layer_split_value). `exe` is the engine program that will start: the drafter's flags follow what that program takes
    (strata_control/drafting.py engine_form). `announce=False` builds the arguments without the "[strata] drafting" lines
    and without leaving a note for the next engine start (the retry arguments of mtp_retry_args)."""
    args = list(cfg["args"])
    # "user_args" (strata_control/user_args.py): the options the person set by hand, over the generated ones at every start,
    # so a setup run or the app rewriting "args" cannot undo them (#3216 #3215 #3270)
    if cfg.get("user_args"):
        args = user_args.merge(args, cfg["user_args"])
    # "drafting": auto | mtp | dflash2 | off (strata_control/drafting.py; the Models screen and `strata launch --drafting` write it): which drafter
    # guesses ahead. ONE drafter per run: DFlash2 alone (no --mtp, --draft-fallback none) or the MTP alone (no DFlash2 option). Auto is DFlash2 where the engine
    # has it, on one card and on a layer split over several cards. A choice that cannot be applied (no drafter file yet, several requests at once) starts the other one if it is on this computer,
    # else none, and says why in the engine's /metrics ("drafting_note"). The start never downloads.
    shaped = {**cfg, "args": args}
    backend, archs = drafting.detect_hardware()
    parallel_n = cfg.get("parallel")
    decision = drafting.apply(shaped, klass=drafting_card_class(), data_dir=drafting.data_dir_of(args), backend=backend, archs=archs,
                              vram_mib=drafting_vram_mib(cfg, backend, archs),
                              slots=parallel_n if isinstance(parallel_n, int) and not isinstance(parallel_n, bool) else 0, engine=exe)
    args = shaped["args"]
    if announce:
        drafting.remember_note(decision.note)
        if decision.note:
            print(f"[strata] {drafting.line(decision.drafter, decision.note)}", flush=True)
        elif decision.flags:
            print(f"[strata] drafting: DFlash2 alone ({' '.join(decision.flags[:2])}, --draft-conf {args[args.index('--draft-conf') + 1] if '--draft-conf' in args else '-'})", flush=True)
    # A card that is short of VRAM for this start (a single request on a small card, or "parallel" 2 or more, every request slot a session of its own) gets work moved off
    # the GPU, never a smaller context and never fewer requests (owner, 2026-11-02): a smaller KV window on CUDA, a smaller prompt chunk and reserve on Arc, and the
    # engine sizes the rest; one plain note says it is slower (strata_control/vram_fit.py fit_start).  The person's own values are kept.  Nothing changes without one
    # card's memory, on a layer split, or for DeepSeek.
    try:
        args, fit_parallel, fit_note = vram_fit.fit_start(cfg, args, drafting_vram_mib(cfg, backend, archs), backend)
    except Exception:                                        # noqa: BLE001 - an estimate that fails decides nothing; the engine still refuses what does not fit
        fit_parallel, fit_note = None, ""
    if fit_note and announce:                                # (announce=False builds the arguments without any line)
        print(f"[strata] {fit_note}", flush=True)
    if fit_parallel is not None:
        cfg = {**cfg, "parallel": fit_parallel}
    # "mtp": false (the Models settings, `strata launch --mtp off`, or by hand): no draft layer, whatever the args say.  A setup run
    # that writes --mtp back into the args cannot undo it, because this is applied at every start. (A DFlash2 start keeps its own --mtp DIR, which only names
    # the vocabulary for an engine that takes it that way.)
    if draft_layer.is_off(cfg) and not decision.flags:
        args, removed = draft_layer.strip(args)
        if removed:
            print(f'[strata] "mtp": false - starting without the draft layer ({" ".join(removed)} left out)', flush=True)
    # #1322: a config with a "vision" section but without --vision in its args (written by an older setup run, or edited by
    # hand) advertised images and then refused every picture ("this engine was started without --vision").  The section
    # says images are wanted: start the engine with them, and keep the encoder's VRAM free as setup does for a GPU encoder
    # (only when the config has no reserve of its own).
    if isinstance(cfg.get("vision"), dict) and "--vision" not in args:
        args.append("--vision")
        note = "added --vision"
        if cfg["vision"].get("gpu") and "--vram-reserve-mib" not in args:
            args += ["--vram-reserve-mib", "700"]
            note += " and --vram-reserve-mib 700"
        print(f'[strata] the config has a "vision" section but no --vision in its args: {note} (run setup again with '
              "--vision to write them)", flush=True)
    if layer_split_of(cfg) and "--layer-split" not in args:
        args += ["--layer-split", layer_split_value(cfg)]
    # opt-in: an auto split runs on the first card alone when it holds every profiled expert and the KV
    if layer_split_of(cfg) and cfg.get("split_skip_if_fits") and "--split-skip-if-fits" not in args:
        args.append("--split-skip-if-fits")
    # #533 (opt-in): "vram_elastic": true - the expert cache in segments, so POST /v1/vram can give VRAM back to other
    # programs and take it back; "vram_segment_mib" sets the segment size (the engine's default: 512)
    if cfg.get("vram_elastic") is True and "--vram-elastic" not in args:
        args.append("--vram-elastic")
        seg = cfg.get("vram_segment_mib")
        if isinstance(seg, int) and not isinstance(seg, bool) and seg > 0 and "--vram-segment-mib" not in args:
            args += ["--vram-segment-mib", str(seg)]
    args += parallel_args(cfg, args)
    args += pool_cores_args(cfg, args)
    return learned_profile_args(cfg, args)


def parallel_args(cfg: dict, args: list[str]) -> list[str]:
    """#465 (opt-in): "parallel": N in the config - up to N requests decode together in the engine's batch slots
    (--batch N); more wait their turn.  1 or absent: one request at a time, as before.  A value the engine cannot use
    is said and passed on: the engine warns and adjusts (recommend, never force)."""
    ds = (cfg.get("arch") or "") == "deepseek41"
    if cfg.get("split_engine_note") and "--batch" in args:
        # the all-cards split engine: its run config carries --batch N (its lanes); "parallel" (the Terminal's --parallel, the app's Concurrent requests) sets N
        n = cfg.get("parallel")
        if isinstance(n, int) and not isinstance(n, bool) and n >= 1:
            args[args.index("--batch") + 1] = str(min(n, SPLIT_MAX_LANES))
        return []
    if "--batch" in args or "--slots" in args or (ds and "--parallel" in args):
        return []
    n = cfg.get("parallel")
    if n is None or n is False:
        return []
    if isinstance(n, bool) or not isinstance(n, int):
        print(f'[strata] "parallel" must be a whole number of requests (2..{PARALLEL_MAX}), not {n!r}: ignored',
              flush=True)
        return []
    if n <= 1:
        return []
    if ds:
        # DeepSeek: --parallel N (the engine holds N conversations at once, each its own rings and KV in VRAM, taken out of the
        # experts' room; their tokens are decoded together).  Not --batch: that is the Qwen engine's slots.
        # An engine package from before this flag would stop at the start on it ("unknown option"): asked of the engine itself, and said.
        try:
            from strata_control import dsv41_flags
            old_engine = dsv41_flags.takes_parallel(cfg.get("exe")) is False
        except Exception:                                # noqa: BLE001 - a probe that fails decides nothing
            old_engine = False
        if old_engine:
            print(f'[strata] "parallel": {n} - this DeepSeek engine ({cfg.get("exe")}) is from before --parallel, so it answers one request at a '
                  "time. Update the engine (strata update) to answer several at once.", flush=True)
            return []
        if n > PARALLEL_MAX:
            print(f'[strata] "parallel": {n} - the DeepSeek engine runs at most {PARALLEL_MAX} conversations at once; it will use '
                  f"{PARALLEL_MAX}", flush=True)
        return ["--parallel", str(min(n, PARALLEL_MAX))]
    # (on a layer split the pipelined groups each hold up to 8 slots - 16 in a HIP engine with wide windows - so more than 8 is
    # not a limit there: the engine says how many slots it runs, INFO batch_slots)
    if (n > PARALLEL_MAX and "--batch-mtp" not in args and os.environ.get("STRATA_BATCH_MTP", "0") in ("", "0")
            and not layer_split_of(cfg)):
        print(f'[strata] "parallel": {n} - the engine runs at most {PARALLEL_MAX} requests together; it will use '
              f"{PARALLEL_MAX}", flush=True)
    return ["--batch", str(n)]


def pool_cores_args(cfg: dict, args: list[str]) -> list[str]:
    """Experimental, off by default: "pool_cores": "0,2,4,6" (or "2-14:2", or a list of numbers) in the config pins the CPU
    expert workers to exactly those logical processors (--pool-cores; docs/DETAILS.md, "Which logical processors the CPU
    workers use").  The engine warns about two entries on one core or the host's own and leaves out processors the process may
    not use; a text this cannot read is said here and ignored (recommend, never force).  An engine option already in the args wins."""
    value = cfg.get("pool_cores")
    if value is None or value is False or value == "" or value == []:
        return []
    if "--pool-cores" in args:
        return []
    if isinstance(value, list) and value and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in value):
        text = ",".join(str(v) for v in value)
    elif isinstance(value, str):
        text = value.replace(" ", "")
    else:
        text = ""
    if not _POOL_CORES_OK.match(text):
        print(f'[strata] "pool_cores" must be logical processor numbers like "0,2,4,6" or "2-14:2", not {value!r}: ignored '
              "(the CPU workers keep their default placement)", flush=True)
        return []
    return ["--pool-cores", text]


def profile_shape(path: str) -> tuple[int, int] | None:
    """An expert profile's (layers, experts per layer), from its header (tools/make_profile.py's format), or None
    when the file is missing, is not one or is shorter than the pairs its header promises."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
            size = os.fstat(f.fileno()).st_size
    except OSError:
        return None
    if len(head) < 24 or head[:4] != b"STRP":
        return None
    _, nl, ne, _, n = struct.unpack("<5I", head[4:])
    return (nl, ne) if size >= 24 + 4 * n else None


def learned_profile_args(cfg: dict, args: list[str]) -> list[str]:
    """#477 (opt-in): "expert_profile_save": "<path>" in the config has the engine (0.1.36+) save what its adaptive
    tier learned there - on QUIT and every "expert_profile_save_every" minutes (10 by default, 0 = at QUIT only) -
    and the next start begins from it instead of the config's --expert-profile, when it is a profile of the same
    model (its header's layers and experts match); otherwise from the config's own, as before.  A relative path is
    the engine's (the config's "cwd").  Without the key, the arguments are the config's, unchanged."""
    save = cfg.get("expert_profile_save")
    if not isinstance(save, str) or not save.strip() or "--expert-profile-save" in args:
        return args
    args = args + ["--expert-profile-save", save]
    every = cfg.get("expert_profile_save_every")
    if isinstance(every, (int, float)) and not isinstance(every, bool) and every >= 0:
        args += ["--expert-profile-save-every", str(every)]
    if "--expert-profile" in args[:-1]:
        i = args.index("--expert-profile") + 1
        here = cfg.get("cwd") or "."
        learned = profile_shape(save if os.path.isabs(save) else os.path.join(here, save))
        base = profile_shape(args[i] if os.path.isabs(args[i]) else os.path.join(here, args[i]))
        if learned is not None and learned == base:
            args[i] = save
    return args


def hip_visible(cfg: dict) -> list[int]:
    """AMD: the devices the engine should see, as the HIP runtime numbers them (HIP_VISIBLE_DEVICES).

    On Linux setup's KFD order is HIP's order, so the config's "gpu" is it.  On Windows setup finds the cards in the
    display-adapter order, and an integrated Radeon that HIP also enumerates takes ordinal 0 and pushes the discrete
    card to 1 (#325): setup records the ordinal `strata-device --list-devices` gave the card as "hip_ordinal", which
    wins for a one-card config.  Without it (a config from before), the config's "gpu"."""
    ordinal = cfg.get("hip_ordinal")
    if ordinal is not None and str(ordinal).strip() != "" and len(gpu_list(cfg)) <= 1:
        try:
            return [int(str(ordinal).strip())]
        except ValueError:
            pass
    return ordered_gpus(cfg)


def gpu_speed_scores(indices: list[int]) -> dict[int, float] | None:
    """Multiprocessors x max clock for each NVIDIA card, numbered as nvidia-smi numbers them (the CUDA driver API,
    which every driver ships: no toolkit needed); None when it cannot say for every one of them."""
    code = (
        "import ctypes,sys,os\n"
        "os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID'\n"
        "lib=ctypes.CDLL('nvcuda.dll' if os.name=='nt' else 'libcuda.so.1')\n"
        "assert lib.cuInit(0)==0\n"
        "n=ctypes.c_int()\n"
        "assert lib.cuDeviceGetCount(ctypes.byref(n))==0\n"
        "for i in range(n.value):\n"
        "    d=ctypes.c_int()\n"
        "    assert lib.cuDeviceGet(ctypes.byref(d),i)==0\n"
        "    sm=ctypes.c_int(); mhz=ctypes.c_int()\n"
        "    lib.cuDeviceGetAttribute(ctypes.byref(sm),16,d)\n"
        "    lib.cuDeviceGetAttribute(ctypes.byref(mhz),13,d)\n"
        "    print(i,sm.value,mhz.value)\n")
    try:
        env = dict(os.environ)
        env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        env.pop("CUDA_VISIBLE_DEVICES", None)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30, env=env)
        got = {}
        for line in r.stdout.splitlines():
            i, sm, khz = (int(x) for x in line.split())
            got[i] = float(sm) * float(khz)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return got if all(i in got and got[i] > 0 for i in indices) else None


def hip_speed_scores(indices: list[int], root: str = "/sys/class/kfd/kfd/topology/nodes") -> dict[int, float] | None:
    """AMD on Linux: SIMDs x max engine clock of each card, from the KFD topology (the order setup and the engine use
    for "gpu" there: the GPU nodes in node order).  None when the files are not there (Windows, no ROCm driver)."""
    try:
        nodes = sorted((int(n) for n in os.listdir(root) if n.isdigit()))
    except OSError:
        return None
    cards = []
    for n in nodes:
        try:
            with open(os.path.join(root, str(n), "properties")) as fh:
                props = dict(line.split() for line in fh if len(line.split()) == 2)
            simd, clk = int(props.get("simd_count", 0)), int(props.get("max_engine_clk_fcompute", 0))
        except (OSError, ValueError):
            continue
        if simd > 0:
            cards.append(float(simd) * float(clk or 1))
    got = dict(enumerate(cards))
    return got if all(i in got for i in indices) else None


def hip_gpu_archs(root: str = "/sys/class/kfd/kfd/topology/nodes") -> dict[int, str] | None:
    """AMD on Linux: {HIP ordinal: "gfx1151"} from the KFD topology (GPU nodes in node order, as hip_speed_scores and setup number them).
    None when the files are not there (Windows, no ROCm driver)."""
    try:
        nodes = sorted(int(n) for n in os.listdir(root) if n.isdigit())
    except OSError:
        return None
    out: dict[int, str] = {}
    for n in nodes:
        try:
            with open(os.path.join(root, str(n), "properties")) as fh:
                props = dict(line.split() for line in fh if len(line.split()) == 2)
            ver, simd = int(props.get("gfx_target_version", 0)), int(props.get("simd_count", 0))
        except (OSError, ValueError):
            continue
        if simd > 0 and ver > 0:
            out[len(out)] = f"gfx{ver // 10000}{(ver // 100) % 100:x}{ver % 100:x}"
    return out or None


def igpu_cards(indices: list[int], archs: dict[int, str] | None) -> set[int]:
    """The cards of `indices` that are integrated (their memory is the system RAM, and they usually draw the desktop)."""
    return {i for i in indices if archs and archs.get(i) in HIP_IGPU_ARCHS}


def gpu_vram_mib(indices: list[int], hip: bool = False) -> dict[int, int] | None:
    """Total VRAM of each card in MiB (NVML / amdgpu sysfs); None when any of them cannot be read."""
    try:
        from serve.telemetry import gpu_reader
    except ImportError:
        return None
    out = {}
    for i in indices:
        g = gpu_reader(i, amd=hip)
        if not g.ok():
            return None
        total = g.read().get("mem_total")
        if total is None:
            return None
        out[i] = int(total) >> 20
    return out


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


def parse_hip_devices(text: str) -> list[dict]:
    """`strata-device --list-devices`: [{"index", "name", "arch", "vram_gb", "integrated", "cannot_run"}], numbered as the HIP runtime numbers them."""
    found: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"device\s+(\d+):\s*(.*)$", s)
        if m:
            found.append({"index": int(m.group(1)), "name": m.group(2).strip(), "arch": "", "vram_gb": 0.0, "integrated": False, "cannot_run": None})
            continue
        if not found:
            continue
        a = re.match(r"arch\s+(gfx[0-9a-f]+)\s*,\s*([\d.]+)\s*GiB(.*)$", s)
        if a and not found[-1]["arch"]:
            found[-1]["arch"], found[-1]["vram_gb"] = a.group(1), float(a.group(2))
            found[-1]["integrated"] = "integrated" in a.group(3)      # a newer engine says so itself
        elif s.startswith("cannot run:"):
            found[-1]["cannot_run"] = s[len("cannot run:"):].strip()
    for d in found:
        d["integrated"] = d["integrated"] or d["arch"] in HIP_IGPU_ARCHS
    return found


def hip_no_card_message(devices: list[dict]) -> str:
    """The plain line when the engine has code for none of the computer's cards."""
    cards = ", ".join(f"{d['name'] or 'graphics card'} ({d['arch'] or 'unknown'}{', integrated' if d['integrated'] else ''})" for d in devices)
    built = next((m.group(1) for d in devices for m in [re.search(r"compiled for \(([^)]*)\)", d["cannot_run"] or "")] if m), "")
    text = f"[strata] none of this computer's graphics cards has code in this Strata engine{f' (it is built for {built})' if built else ''}. Cards found: {cards}."
    note = engine_component.no_package_note([d["arch"] for d in devices])
    return text + (f" {note}" if note else "")


def pick_hip_devices(devices: list[dict]) -> tuple[list[int] | None, str | None]:
    """Which card an "Automatic" start runs on: (HIP_VISIBLE_DEVICES to set, or None to leave the runtime's own order; a plain problem or
    None).  Cards this engine has no code for are skipped, and so are integrated chips while a card of its own can run (#3203: a mini PC's
    Radeon 760M is HIP's device 0 and the engine died on it; the RX 6800 XT behind it was never tried).  When device 0 is already the right
    kind nothing changes."""
    if not devices:
        return None, None
    runnable = [d for d in devices if not d["cannot_run"]]
    if not runnable:
        return None, hip_no_card_message(devices)
    pool = [d for d in runnable if not d["integrated"]] or runnable
    if devices[0] in pool:
        return None, None
    best = max(pool, key=lambda d: (round(d["vram_gb"]), -d["index"]))
    return [best["index"]], None


def hip_auto_devices(cfg: dict, env: dict) -> list[int] | None:
    """HIP_VISIBLE_DEVICES for a start that names no card (see pick_hip_devices), asked of the engine package's own `strata-device`.
    None leaves everything as it was: a card the config or the environment names, no probe next to the engine, or a probe that fails.
    SystemExit with the plain line when no card of this computer can run."""
    if cfg.get("backend") != "hip" or gpu_list(cfg) or gpu_all_off(cfg) or str(cfg.get("hip_ordinal") if cfg.get("hip_ordinal") is not None else "").strip() \
            or env.get("HIP_VISIBLE_DEVICES") or env.get("ROCR_VISIBLE_DEVICES"):
        return None
    exe = cfg.get("exe")
    if not isinstance(exe, str) or not exe or engine_component.is_reference(exe):
        return None
    probe = Path(exe).with_name("strata-device.exe" if os.name == "nt" else "strata-device")
    if not probe.is_file():
        return None
    try:
        done = subprocess.run([str(probe), "--list-devices"], capture_output=True, text=True, timeout=60, cwd=str(probe.parent), env=env,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    devices = parse_hip_devices(done.stdout)
    visible, problem = pick_hip_devices(devices)
    if problem:
        raise SystemExit(problem)
    if visible:
        d = next(x for x in devices if x["index"] == visible[0])
        print(f"[strata] automatic GPU choice: GPU {d['index']} ({d['name']}, {d['arch']}); the engine skips cards it has no code for and "
              f"integrated chips while a card of its own can run", flush=True)
    return visible


def deepseek_slot_env(env: dict, cfg: dict) -> None:
    """DeepSeek-V4.1 only.  The engine sets a conversation aside when another request takes the model and takes it back
    at its checkpoints (agents and sub-agents that take turns do not read their prompts again).  STRATA_DS4_SLOT_KEEP
    switches it (the default above; a config's env or the shell wins); the folder is `ds4-slots` next to the run log, in
    Strata's data folder (STRATA_DS4_SLOT_DIR names another), and the engine caps it (STRATA_DS4_SLOT_GB, 2 here, 16 in the engine) and
    removes what is older than a week or not this model's.  On by default; STRATA_DS4_SLOT_KEEP=0 turns it off."""
    env.setdefault("STRATA_DS4_SLOT_KEEP", DS41_SLOT_KEEP_DEFAULT)
    env.setdefault("STRATA_DS4_SLOT_GB", DS41_SLOT_GB_DEFAULT)
    log = cfg.get("log")
    if "STRATA_DS4_SLOT_DIR" not in env and log:
        env["STRATA_DS4_SLOT_DIR"] = str(Path(log).parent / "ds4-slots")


PARALLEL_STACK_ENV = {
    "STRATA_CKPT_POOL": "1", "STRATA_CKPT_POOL_READY": "4", "STRATA_SLOT_CKPT_MOVE": "1", "STRATA_SLOT_COPY_DIRECT": "1",
    "STRATA_SLOT_COPY_BATCHSYNC": "1", "STRATA_BATCH_GDN_GROUPS": "1", "STRATA_BATCH_ATTN_ROWS": "1",
    "STRATA_BATCH_SELF_COMMIT": "1", "STRATA_QSA_SLOTS": "1",
}


def parallel_slots(cfg: dict) -> int:
    """How many batch slots the config asks for (0 = none): the args' own --batch/--slots, else "parallel"."""
    args = list(cfg.get("args") or [])
    for k in ("--batch", "--slots"):
        if k in args:
            try:
                return int(args[args.index(k) + 1])
            except (IndexError, ValueError):
                return 0
    n = cfg.get("parallel")
    return n if isinstance(n, int) and not isinstance(n, bool) and n > 1 else 0


def parallel_stack_platform() -> bool:
    """Linux only: the stack was run on Linux CUDA; Windows (own host-arena path) and macOS were not."""
    return sys.platform.startswith("linux")


def parallel_stack_env(env: dict, cfg: dict) -> None:
    """Switch the exact parallel stack on (setdefault: a value the user or the config set stays) when the config runs batch
    slots on a CUDA or HIP Qwen engine.  Other engines (DeepSeek, SYCL, Metal) do not read these."""
    if parallel_slots(cfg) < 2 or (cfg.get("arch") or "") == "deepseek41" or cfg.get("backend") in ("sycl", "metal", "vulkan"):
        return
    if not parallel_stack_platform():
        return
    if cfg.get("backend") == "hip":
        return
    for k, v in PARALLEL_STACK_ENV.items():
        env.setdefault(k, v)


GDN_STACK_CUDA = {"STRATA_GDN_TC": "1", "STRATA_GDN_CONVL2": "2"}


def gdn_stack_env(env: dict, cfg: dict, archs: dict | None = None) -> None:
    if not parallel_stack_platform():                                   # Linux only (same rule as the parallel stack)
        return
    if (cfg.get("arch") or "qwen4exp") != "qwen4exp" or cfg.get("backend") in ("sycl", "metal", "vulkan"):
        return                                                          # only the model the numbers are from
    if cfg.get("backend") != "hip":
        for k, v in GDN_STACK_CUDA.items():
            env.setdefault(k, v)
        return
    ar = archs if archs is not None else hip_gpu_archs()
    if not ar:
        return                                                          # cannot tell the card: leave AMD out
    want = hip_visible(cfg) or list(ar)
    seen = [ar.get(i, "") for i in want]
    if seen and all(a.startswith("gfx12") for a in seen):
        for k, v in GDN_STACK_GFX12.items():
            env.setdefault(k, v)


def child_env(cfg: dict, *, offline: bool = False) -> dict:
    """The engine's environment: the CUDA libraries setup installed (pip's nvidia packages, or the toolkit that
    compiled it) first on the library search path."""
    env = dict(os.environ)
    if gpu_all_off(cfg):                             # every card Off: the engine sees none (a CPU engine runs; the others say so at start)
        env["CUDA_VISIBLE_DEVICES"] = ""
        env["HIP_VISIBLE_DEVICES"] = ""
    elif hip_visible(cfg) and cfg.get("backend") == "hip":   # AMD: numbered as HIP numbers them (hip_visible)
        env["HIP_VISIBLE_DEVICES"] = ",".join(str(i) for i in hip_visible(cfg))
    elif gpu_list(cfg):                              # issue #51: the GPU(s) to run on, numbered as nvidia-smi does; CUDA's
        env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"      # own default order (fastest first) can number the cards otherwise
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i in ordered_gpus(cfg))
    for k, v in (cfg.get("env") or {}).items():      # engine settings the config carries (AMD: the GEMM tuning table)
        env[str(k)] = str(v)
    if (cfg.get("arch") or "") == "deepseek41":      # (only this engine reads these; Qwen's environment is untouched)
        deepseek_slot_env(env, cfg)
    parallel_stack_env(env, cfg)
    gdn_stack_env(env, cfg)
    # Strict offline reaches children through the environment, because a tool subprocess or a model
    # loader is code this server does not own. Applied last so a profile's own `env` cannot remove
    # the policy by naming the same variable.
    if offline:
        try:
            from strata_control import offline as offline_policy
            env.update(offline_policy.OFFLINE_ENV)
        except ImportError:
            # The policy module is part of the application; without it, refuse rather than silently
            # running a child with network access under a flag that promised otherwise.
            env["STRATA_OFFLINE"] = "1"
            env["HF_HUB_OFFLINE"] = "1"
            env["TRANSFORMERS_OFFLINE"] = "1"
    dirs = [d for d in cfg.get("lib_dirs") or [] if Path(d).is_dir()]
    if dirs:
        var = "PATH" if os.name == "nt" else "LD_LIBRARY_PATH"
        env[var] = os.pathsep.join(dirs + ([env[var]] if env.get(var) else []))
    if cfg.get("backend") == "hip":
        hip_env_guard(env, cfg)
        note = sh_stream_warning(env, cfg)
        if note:
            print(note, flush=True)
        auto = hip_auto_devices(cfg, env)
        if auto:
            env["HIP_VISIBLE_DEVICES"] = ",".join(str(i) for i in auto)
    return env


def _dir_writable(p: str) -> bool:
    try:
        with tempfile.TemporaryFile(dir=p):
            return True
    except OSError:
        return False


def sh_stream_warning(env: dict, cfg: dict) -> str | None:
    """#3895: the shared-expert fork (STRATA_SH_STREAM=1) together with KV streaming (--kv-resident) made one Windows RX 6900 XT fail on the first
    request ("verify: unspecified launch failure"); each alone, or Linux, did not. A warning, not a refusal: the person set the variable, the
    engine runs as asked, and the line says what to take out."""
    if os.name != "nt" or str(env.get("STRATA_SH_STREAM", "")).strip() in ("", "0"):
        return None
    args = [str(a) for a in cfg.get("args") or []]
    if "--kv-resident" not in args:
        return None
    return ("[strata] WARNING: STRATA_SH_STREAM=1 with --kv-resident (KV streaming) failed on the first request on one Windows RX 6000 PC "
            "(\"verify: unspecified launch failure\", #3895). If the engine stops that way, take STRATA_SH_STREAM out of the config's env "
            "(AMD runs without it by default) or run without --kv-resident, and tell us the card and the driver.")


def hip_env_guard(env: dict, cfg: dict) -> list[str]:
    """#654: two things in an AMD user's environment that crash the HIP runtime before it prints a line.  (1) HIP_PATH,
    HIP_DEVICE_LIB_PATH or LLVM_PATH naming a folder that is gone (a ROCm build that was deleted): the bundled runtime
    follows them.  They are dropped, and only when the folder does not exist.  (2) A TEMP / TMP / TMPDIR the engine cannot
    create a file in: the runtime's comgr JIT builds its blit kernels through temporary files and the first call
    crashes in amdhip64 (0xC0000005).  A writable folder next to the engine's log takes its place.  Returns what it
    changed (said once, on stderr); a healthy environment is left exactly as it was."""
    said: list[str] = []
    for k in ("HIP_PATH", "HIP_DEVICE_LIB_PATH", "LLVM_PATH"):
        v = env.get(k)
        if v and not Path(v).exists():
            del env[k]
            said.append(f"{k}={v} does not exist: not passed to the engine")
    bad = [k for k in ("TEMP", "TMP", "TMPDIR") if env.get(k) and not _dir_writable(env[k])]
    if bad:
        base = Path(cfg.get("log") or cfg.get("cwd") or ROOT).resolve()
        for d in (base.parent / "tmp", ROOT / "tmp"):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                continue
            if _dir_writable(str(d)):
                for k in bad:
                    said.append(f"{k}={env[k]} is not writable: using {d}")
                    env[k] = str(d)
                break
        else:
            said.append(f"{', '.join(bad)} not writable (AMD's runtime needs a writable temporary folder)")
    for line in said:
        print(f"strata serve: AMD: {line}", file=sys.stderr, flush=True)
    return said
