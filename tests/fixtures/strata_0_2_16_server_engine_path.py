# Stock Niko1221/Strata v0.2.16 terminal/serve/server.py; read as data only.
# Source SHA-256: c31b8b5c3de3b40901fd0f81f53343e3139a0dca22c73ef0e846c6eb098edd00
# Payload SHA-256: 3acdd931c8ea4be5e41b41b3030af0d79a26c13d50332343e08fc0080e167b95
# Stock payload follows.
from serve.server_parts.engines import (  # noqa: F401  (moved unchanged, file split)
    ByteTokenizer,
    ClientGone,
    DRAFT_COSTS_DEFAULT_PLATFORMS,
    DRAFT_HEAD_FAIL,
    DRAFT_HEAD_HINT,
    ENGINE_REQUEST,
    Engine,
    EngineClosing,
    EngineDied,
    EngineNonFinite,
    EngineSilent,
    EngineStarting,
    EngineStuck,
    FATAL_PREFIXES,
    GpuBusy,
    HIP_IGPU_ARCHS,
    HOOK_REASON_MAX,
    ModelBusy,
    PAGE_CSP,
    PARALLEL_MAX,
    QueueCancelled,
    QueueWaitExpired,
    SPLIT_MAX_LANES,
    ServerStopping,
    SessionRefused,
    TRANSIENT_START_MARKS,
    VisionNoRoom,
    _BTRACE,
    _POOL_CORES_OK,
    _RequestOwned,
    _VISION_ARCH_SIGNS,
    _WIN_CRASH,
    _dir_writable,
    _echoing,
    _engine_texts,
    _gpu_numbers,
    btrace,
    card_note,
    card_roles_lines,
    conversation_cache_view,
    conversation_slots,
    cpu_isa_words,
    died_note,
    draft_costs_default,
    draft_costs_dir,
    engine_arch_note,
    engine_binary,
    engine_crashed,
    engine_exit_words,
    engine_has_text,
    engine_silence_s,
    experts_loading_words,
    gpu_all_off,
    gpu_list,
    gpu_roles_active,
    gpu_speed_scores,
    hip_no_card_message,
    hip_speed_scores,
    hook_echo,
    hook_reason,
    hook_text,
    igpu_cards,
    layer_split_of,
    layer_split_value,
    learned_profile_args,
    monitored_gpu,
    network_path,
    own_path_context_warning,
    parallel_args,
    parallel_flag_conflicts,
    parallel_slots,
    parse_batch_window_sample,
    parse_engine_stage_line,
    parse_hip_devices,
    parse_stage_in_flight_sample,
    pick_hip_devices,
    pool_cores_args,
    profile_shape,
    read_engine_stage_log,
    sh_stream_warning,
    start_exit_note,
    start_failure_hint,
    start_log_marks,
    start_log_tail,
    start_log_text,
    unload_wait,
    visible_device_order,
    vision_log_size,
    vision_log_tail,
    vision_start_error,
)


from strata_control.childenv import arena_env, limit_own_arenas, quiet_crash_env  # noqa: E402


from strata_control import draft_layer  # noqa: E402


from strata_control import drafting  # noqa: E402


from strata_control import vram_fit  # noqa: E402


from strata_control import gpu_roles  # noqa: E402


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
    backend, archs = drafting.hardware_for(cfg.get("backend"))   # #5109: the config's engine family, not an idle card of another vendor
    parallel_n = cfg.get("parallel")
    decision = drafting.apply(shaped, klass=drafting.card_class(archs) if archs else drafting_card_class(), data_dir=drafting.data_dir_of(args), backend=backend, archs=archs,
                              vram_mib=drafting_vram_mib(cfg, backend, archs),
                              slots=parallel_n if isinstance(parallel_n, int) and not isinstance(parallel_n, bool) else 0,
                              engine=engine_binary(exe, cfg) if exe else exe,
                              stages=len(gpu_list(cfg)) if layer_split_of(cfg) else 1)
    args = shaped["args"]
    if announce:
        drafting.remember_note(decision.note)
        if decision.note:
            print(f"[strata] {drafting.line(decision.drafter, decision.note)}", flush=True)
            hint = drafting.fetch_hint(decision, model_name=cfg.get("model_name"), backend=backend, archs=archs, data_dir=drafting.data_dir_of(args), args=args,
                                       vram_mib=drafting_vram_mib(cfg, backend, archs))
            if hint:
                print(f"[strata] {hint}", flush=True)
        elif decision.flags and drafting.slot_drafts_run(args, parallel_n, layer_split_of(cfg)):
            print(f"[strata] {drafting.SLOT_DRAFTS_LINE}", flush=True)
        elif decision.flags:
            print(f"[strata] drafting: DFlash2 alone ({' '.join(decision.flags[:2])}, --draft-conf {args[args.index('--draft-conf') + 1] if '--draft-conf' in args else '-'})", flush=True)
        if decision.vocab:                                   # log only (a support log shows which draft vocabulary was used and why)
            print(f"[strata] drafting: {decision.vocab}", flush=True)
    # A card that is short of VRAM for this start (a single request on a small card, or "parallel" 2 or more, every request slot a session of its own) gets work moved off
    # the GPU, never a smaller context and never fewer requests (owner, 2026-11-02): a smaller KV window on CUDA, a smaller prompt chunk and reserve on Arc, and the
    # engine sizes the rest; one plain note says it is slower (strata_control/vram_fit.py fit_start).  The person's own values are kept.  Nothing changes without one
    # card's memory, or on a layer split.
    try:
        args, fit_parallel, fit_note = vram_fit.fit_start(cfg, args, drafting_vram_mib(cfg, backend, archs), backend)
    except Exception:                                        # noqa: BLE001 - an estimate that fails decides nothing; the engine still refuses what does not fit
        fit_parallel, fit_note = None, ""
    if fit_note and announce:                                # (announce=False builds the arguments without any line)
        print(f"[strata] {fit_note}", flush=True)
    if announce:                                             # #5715: Qwen3.6 with a context its card cannot hold: said before the start, nothing changed
        too_big = own_path_context_warning(cfg, args, drafting_vram_mib(cfg, backend, archs))
        if too_big:
            print(f"[strata] {too_big}", flush=True)
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
    return draft_costs_args(cfg, learned_profile_args(cfg, args), exe or cfg.get("exe"))


DRAFT_COSTS_DEFAULT = draft_costs_default()    # "draft_costs": true / false in a config overrides it


def draft_costs_args(cfg: dict, args: list[str], exe: str | None = None) -> list[str]:
    """Repeatable output: the engine (0.1.60+ with --draft-costs) fixes its draft window costs to a table it learned once on this computer, so
    the same request gives the same answer on every start; until the table exists it learns it in the background with today's policy.
    "draft_costs": true / false in the config overrides DRAFT_COSTS_DEFAULT.  The file name follows the model and every engine argument, so
    another model or setting gets its own table; the engine itself checks the card, the driver and its own version inside the file and
    learns again when they changed.  An engine that does not know the flag is not given it."""
    explicit = "draft_costs" in cfg
    want = cfg.get("draft_costs", DRAFT_COSTS_DEFAULT)
    if want is not True or "--draft-costs" in args:
        return args
    knows = engine_has_text(exe, b"--draft-costs") if exe else None
    # by default only an engine that is seen to have the option gets it; a config that asks for it by name gets it unless the engine is seen without it
    if knows is False or (not explicit and knows is not True):
        return args
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(cfg.get("model_name") or "model"))[:64]
    digest = hashlib.sha256("\0".join(map(str, args)).encode("utf-8", "replace")).hexdigest()[:12]
    out = args + ["--draft-costs", str(draft_costs_dir() / f"{name}-{digest}.costs")]
    try:
        size = os.path.getsize(exe) if exe else None
    except OSError:
        size = None
    if size:
        out += ["--draft-costs-key", f"engine file {size} bytes"]
    return out


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
    # the decision itself (5% rule #1760, faster card last #1352, VRAM guard #1576) is strata_control/gpu_roles.speed_stage_order, which `strata launch --plan`
    # calls too (gpu_roles.from_legacy), so the plan names the same Main card as this start
    out, why, seen = gpu_roles.speed_stage_order(
        gl, sc, vrams if vrams is not None else (None if scores is not None else (lambda: gpu_vram_mib(gl, hip))))
    if why == "kept-vram":
        print(f"[strata] layer split: keeping card order {','.join(map(str, gl))} - the faster card has "
              f"less VRAM than the one the split ends on ({seen[0]} vs {seen[1]} MiB, #1576)",
              flush=True)
    elif why == "faster-last":
        print(f"[strata] layer split: card order {','.join(map(str, out))} (the faster card last; "
              f'"gpu_order": "as_given" keeps {",".join(map(str, gl))}, #1352)', flush=True)
    return out


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
        done = subprocess.run([str(probe), "--list-devices"], capture_output=True, stdin=subprocess.DEVNULL, text=True, timeout=60, cwd=str(probe.parent), env=env,
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


def child_env(cfg: dict, *, offline: bool = False) -> dict:
    """The engine's environment: the CUDA libraries setup installed (pip's nvidia packages, or the toolkit that
    compiled it) first on the library search path."""
    env = arena_env(quiet_crash_env(dict(os.environ)))   # no debugger on a user's machine (ggml's abort path forks gdb); glibc arenas capped (strata_control/childenv.py)
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
