# Security boundary

OMP Strata runs one stock Strata server on loopback (`127.0.0.1:18090`) behind a required API key for one local user
and drives it with the stock Oh My Pi (OMP) client, or reaches that loopback server from another machine through an
optional qualified SSH local forward. It is a single-user route: it is not a multi-tenant service, an OS sandbox or an
egress firewall.

Everything below was observed on the qualification host (G02/G04 on the mock tier, G13 on the real host) unless it is
marked as a source reading. The current qualified server profiles run stock Strata v0.2.7 (engine 0.1.52) + OMP
18.13.2 on the RTX PRO 6000, the RTX 5090 (131K default; the 262K opt-in stays on v0.2.3 + OMP 18.12.6, rolling back
to v0.2.1 + OMP 18.10.1, because the v0.2.7 262K draft is held on 35.7-36.2 GiB host RAM headroom against its 36 GiB
startup floor) and the `rtx3090-win-a` RTX 4090 + RTX 3090 pair (IQ3_S at 262,144 tokens, stock layer split with stock
roles, RTX 4090 as Main staged last, pipeline windows 2, no batch slots, display on the RTX 4090, with the engine's
automatic conversation cache off on this 128 GB-RAM host after locking the 26.8 GiB per-layer embedding (PLE) table in
RAM; the PRO, RTX 5090 131K default and pair roles profiles roll back to v0.2.3 + OMP 18.12.6, while the unmeasured
v0.2.7 default-split draft, the default and split-32 v0.2.3 pair drafts and the v0.1.44.1 pair release remain draft,
not qualified). Model pins and contexts stay unchanged.

<details><summary>Earlier tuples and hardware rollback constraints covered in this document</summary>

- Where the first two candidates differ (stock Strata v0.1.27 + OMP 18.4.0 against v0.1.30 + 18.4.6), both are stated.
- Later tuples are named where they change something: the third tuple (Strata v0.1.31 + OMP 18.4.8, two 24 GB hosts),
  the fourth (Strata v0.1.34 + OMP 18.4.10, three hosts), the RTX PRO 6000 tuples (Strata v0.1.40.2 + OMP 18.8.0, and
  Strata v0.1.40.3 + OMP 18.8.3 with batch slots and conversation parking), the Strata v0.1.40.3 + OMP 18.8.4 tuple (the
  RTX PRO 6000 with slots and parking, the RTX 5090 and the single-card RTX 3090), the Strata v0.1.41 + OMP 18.8.6
  tuple on the RTX PRO 6000 with slots and parking and the RTX 5090, the earlier Strata v0.1.42 + OMP 18.8.9 and
  Strata v0.1.43 + OMP 18.10.1 tuples, Strata v0.1.43.1 + OMP 18.10.1, Strata v0.1.44.1 + OMP 18.10.1 (on the PRO and
  RTX 5090), Strata v0.2.1 (engine 0.1.46) + OMP 18.10.1 (the rollback for the RTX 5090 262K opt-in, earlier history on
  every host), Strata v0.2.3 (engine 0.1.48) + OMP 18.12.6 (the current rollback on every host and current RTX 5090 262K
  opt-in), and current Strata v0.2.7 (engine 0.1.52) + OMP 18.13.2 on the PRO, RTX 5090 131K default and pair.
- The pair's qualified display-on-RTX-3090 predecessor is rollback only after restoring that display placement. The
  single-card RTX 3090 profiles stay qualified for single-card hosts, but are not rollbacks on `rtx3090-win-a` while
  both cards are installed.

</details>

## Server exposure

- **Loopback listener only.** Strata listens on `127.0.0.1:18090` only (G10: the only listener on the port is owned by
  the integration's process tree). `0.0.0.0` is not supported. Remote clients reach it only through a client route over
  an authenticated loopback-to-loopback SSH forward (below). The Mac Studio's current route to the RTX PRO 6000 262K
  v0.2.7 profile is qualified by G23 on its own ledger; its 0.2.3 route is the rollback, while the 0.2.1, 0.1.44.1,
  0.1.43.1, 0.1.43 and 0.1.42 262K and 0.1.41 131K routes remain earlier qualified history. No fleet route is published.
- **Server environment subtraction.** The server's environment is the operator's environment minus every variable whose
  name looks like a secret (`KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`) and minus every inherited `STRATA_*`
  variable: those are the engine's tuning and debug switches (v0.1.31 alone added 16), and a setting changes only
  through a new profile. The API key is then added explicitly.
- **API key generation and storage.** `keygen` writes a 32-byte random key to `<root>\state\strata-api-key`, restricted
  to the current user (`icacls /inheritance:r`); `start` refuses a missing, blank or short key. The key reaches the
  server only through the detached `serve` wrapper's environment. It is never put on a command line, printed, logged or
  committed.
- **Route authentication and config guard.** Every model, control, metrics, telemetry and MCP tool-media route needs
  the API key (`Authorization: Bearer` or `x-api-key`), while `/health`, `/api/health` and `/` stay public.
  `tests/unit/test_strata_surface.py` fails when a pinned server routes a path G13 does not probe, and install accepts
  only the config keys every pinned setup writes (`"parallel"` only as a profile's pinned batch slots, v0.2.3+'s
  `gpu_roles` and `gpu_order` only as a profile's pinned stock roles, and v0.2.1+'s `args_written` only when equal to
  `args` with no `user_args`), so CORS origins, the monitor, `telemetry_read_key` or lazy loading cannot be switched on
  by a generated config.
- **Batch slots and conversation parking.** On the current RTX PRO 6000 profile the server decodes up to four requests
  at once, and OMP may send it four; they come from the one local user's OMP processes. Parking keeps up to four recent
  conversations' engine state in host RAM inside the engine process (from engine 0.1.48 in v0.2.3 and engine 0.1.52 in
  v0.2.7, sized automatically by the engine from the RAM free after load: 8,192 MiB on the PRO on v0.2.7 and v0.2.3 and
  on the pair on v0.2.3, 1,024-1,280 MiB on the RTX 5090 131K on v0.2.3, and off on the pair on v0.2.7 after locking
  the 26.8 GiB PLE table in RAM, on the RTX 5090 131K on v0.2.7 while the host's resident Docker Desktop/WSL VM held
  RAM, and on the RTX 5090 262K). Nothing is written to disk, and the state goes when the engine stops. A conversation
  is restored only for a prompt that starts with exactly its tokens.
- **Vision off.** Vision is off in this profile. Stock Strata can fetch `image_url` values (HTTP(S) or local paths)
  when vision is on, so enabling vision needs its own review (G22).

<details><summary>G13 route probes and historical Strata v0.1.27–v0.1.30 authentication observations</summary>

- **G13 route probe scope.** G13 checked `GET /v1/models /models /props /metrics /settings /slots /v1/status /mcp`
  (plus `/status` on the second candidate) and `POST /v1/chat/completions /v1/messages /settings`: no key and wrong
  keys get 401, and the correct key gets 200 (the mutating `POST /settings` was only tried without a valid key). Shared
  server settings stayed at the frozen empty defaults. On the fourth tuple G13 also sent missing and wrong keys to
  `POST /load /unload /v1/load /v1/unload /v1/messages/count_tokens` (401 on all three hosts; stock checks the key
  before it routes any POST), found the opt-in request monitor absent (`/api-monitor` and `/api/requests` 404 with the
  key) and a CORS preflight answered 204 without `Access-Control-Allow-Origin`; `/health`, `/api/health` and `/` stay
  public. On the RTX PRO 6000 tuple G13 also refused missing and wrong keys on `GET /config` and on
  `POST /config /slots/ /v1/responses /v1/vram` (401), and the egress trace recorded zero non-loopback events among
  2,416 attributed ones (2,796 on the slots-and-parking profile). On v0.2.1 (engine 0.1.46), v0.2.3 (engine 0.1.48) and
  v0.2.7 (engine 0.1.52) G13 also probes the authenticated `GET /v1/telemetry` (which arrived in v0.2.0-beta, engine
  0.1.45.3; the read-only telemetry key from the environment is scrubbed and config `telemetry_read_key` is refused by
  install) and sends missing and wrong keys to the key-only `POST /v1/v1/messages` and
  `POST /v1/v1/messages/count_tokens` Anthropic aliases (401); on v0.2.7 (engine 0.1.52) G13 also probes the key-gated
  `GET /tool-media/` route (401 without or with a wrong key, 404 with the valid key because Strata-side MCP is
  unconfigured; 0 non-loopback network events among 10,067 attributed ETW events on the PRO, 4,397 on the RTX 5090
  131K and 4,451 on the pair).
- **Unauthenticated by design in stock Strata v0.1.27 (first candidate):** `/health`, `/status`, `/` (the web app) and
  its static assets. `/status` includes a `tail` of the text being generated, so any local process can read the end of
  the current answer without the key. Treat the host as single-user. Strata v0.1.28 puts `/status` behind the key and
  drops the tail when a request ends (Strata#212); on the second candidate (v0.1.30) G13 observed `/status` answering
  401 without the key, leaving `/health` and `/` public.
- **Empty-key and key-comparison behavior in stock Strata v0.1.27:** Stock Strata v0.1.27 **disables authentication
  when its key is empty** and compares keys with `==`, which is not constant-time; this is acceptable only because the
  listener is loopback-only. Strata v0.1.28 and later (second candidate) refuse an explicitly empty key and compare keys
  in constant time (Strata#213; an absent key still means no authentication, so the launcher's refusal stays).

</details>

## Remote client routes and fleets

Design and commands: [`REMOTE.md`](REMOTE.md).

- **Owned SSH tunnel.** The server side does not change: it still binds loopback only and requires its key. A client
  reaches it through `ssh -NT -L 127.0.0.1:<local>:127.0.0.1:<server>` run as an argv-only child of the foreground
  `launch-omp`, with `BatchMode=yes`, `ExitOnForwardFailure=yes` and multiplexing/background-after-authentication
  disabled. The child lives in an owned POSIX session or a Windows kill-on-close job and is torn down on every exit
  path; no forward outlives the session. An occupied local port is refused, never adopted.
- **Key transfer and binding provenance.** `pull-key` reads the host root's key over the SSH session's stdout (stdin
  closed) into a user-only file under the client root (`state/keys/<label>.key`); it never appears in argv, launcher
  errors, logs or receipts. A user-only `<label>.key.json` beside it binds the key's digest to the binding it came from
  (SSH alias, remote root, platform); after any binding change the launcher refuses with "binding changed since
  pull-key" until `pull-key` runs again. The client root holds the keys, the private bindings and the isolated OMP home;
  none of them belongs in the repository. Fetch, key pull and proof writers check the root identity and server-install
  exclusion before writes/network effects, recording a new identity under the client lock. Derived proof roots have the
  same check before keys are copied into them.
- **Established-peer verification and preflight.** Before OMP starts, the platform ownership query (`lsof` on macOS,
  `/proc` on Linux, `Get-NetTCPConnection` on Windows) must attribute every listener on the port, on any address
  including IPv4/IPv6 wildcards, to the SSH child. A stale listener sample never authorizes a launcher/probe request:
  its HTTPConnection first connects, then checks that the server half of that exact established TCP four-tuple belongs
  exclusively to the live SSH child, before sending any HTTP bytes. Failed or incomplete checks refuse credentials. A
  subsequent port rebind cannot replace the peer of that established connection. Before OMP starts, every member must
  pass `/health`, refuse unauthenticated `/v1/models` with 401, and match the pinned model id, exact Strata build,
  context and empty shared settings with the key. Preflight follows no redirects and ignores ambient proxies, so the
  bearer key cannot be forwarded to another origin.
- **Disconnect teardown and exit-to-kill window.** When an SSH child exits, a watcher kills OMP's process group
  (Windows: job) at once, with no grace period, to curtail retries into a listener that takes over the freed port. The
  turn in flight is lost; the transcript saved before it resumes explicitly. Nothing falls back to another provider.
  Stock OMP's own requests are not checked one by one (that would need a proxy or a fork): the remaining window is the
  time between the SSH child's exit and that kill. SIGINT/SIGTERM are deferred while a child is started or registered
  and while the session tears down; teardown attempts every tunnel and keeps the handle of any that failed to close.
  Group signals for a reaped leader are skipped if its PID now names a live process; otherwise descendant cleanup is
  preserved. Windows uses the owned job handle, not PID-based group signalling.
- **Fleet routing (design only; no fleet route is published).** A fleet adds one `strata-<label>` provider per host (one
  request in flight each). Stock OMP's `task.agentModelOverrides` routes the unmodified stock `task` (full coding tools)
  and `scout` (read-only tools) agents to a worker; only the extra named scouts are generated definitions, with `model:`
  pinned and tools limited to read/find/grep/glob (a mock-tier test with the real pinned OMP binary confirms their
  write, edit and bash attempts are refused). Every role still resolves to a Strata provider only.
- **Trust boundaries that stay with the operator:** the SSH client, its configuration (including any `ProxyCommand`) and
  host-key trust; model-generated tools, which run with the client user's privileges and can read whatever that user
  can, including the client root's key files, as tools on the server host can read the server key. The egress guard is
  defense in depth, not an OS firewall. Native Windows job containment has not run on a real client yet.
- **Qualified Mac Studio route and rollback observations.** The current Mac Studio route,
  `client-rtxpro6000-262k-strata0.2.7-omp18.13.2`, pins the PRO's current
  `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2` profile. Its independent G23 passed on
  2026-10-28 at `15c7426`: missing key refused before launch, wrong key refused with 401, health RTT 8.0-41.4 ms, stream
  TTFT 0.316 s through the tunnel, the turn in flight failing on tunnel drop with the prior transcript preserved, and
  nonce recall after tunnel reopen (1.04 s), client restart (0.78 s) and verified server restart (1.60 s, changed
  server instance). TTFT includes server work, not SSH-only overhead. Its qualified rollback,
  `client-rtxpro6000-262k-strata0.2.3-omp18.12.6`, pins the PRO's v0.2.3 262K rollback (G23 pass on 2026-10-23 at
  `de60693`: RTT 4.6-5.2 ms, TTFT 0.171 s, recalls 0.77 / 0.71 / 2.67 s). The 0.2.1, 0.1.44.1, 0.1.43.1, 0.1.43 and
  0.1.42 262K routes and the 0.1.41 131K route stay earlier qualified history. Each route keeps its own ledger and
  independently qualified server.

## Client isolation (`launch-omp`)

- **Isolated profile and home.** OMP runs with a named profile (`omp-strata`) in an isolated
  HOME/USERPROFILE/APPDATA/TEMP under the root. Your normal `~/.omp` is never read or written. G20 checked that the
  user's `.omp` directory had no change after the integration root was created, and that stock Strata's
  `%APPDATA%\Strata` was never created.
- **Client environment allowlist.** The environment is an allowlist (PATH, system roots, locale). Provider API keys,
  tokens, proxies, OTEL exporters, `NODE_OPTIONS`, shell startup files and credential sockets are dropped (unit and mock
  tests).
- **Pinned model roles.** Every OMP model role (default, smol, slow, plan, commit, task, advisor, judge, ...) is pinned
  to the profile's model on `strata-local` (`qwen3.8-flash-next-iq3_s` on the RTX PRO 6000,
  `qwen3.8-flash-next-coder-iq1_m` on the Coder profiles). The route census over every session made during qualification
  found only that provider and model (G13), including OMP compaction's summarization calls (G13, G18).
- **Discovery disabled.** Extension, skill, rule, LSP, title and project-MCP discovery are off; flags that would
  override the provider, model, profile, config or extensions are refused by the launcher.
- **Missing-key refusal.** The launcher refuses a missing or blank key before starting OMP, because **stock OMP (18.4.0
  and 18.4.6) sends the literal text `Bearer STRATA_API_KEY` when the key variable is unset**, instead of failing.

## Network egress

- **Loopback proxy guard.** The launcher sets `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` to a closed loopback port
  (`127.0.0.1:9`) and `NO_PROXY` to loopback. The Strata route stays direct. OMP's catalog fetch and any HTTP from tools
  the model runs then fail locally.
- **This is not enforcement.** A process that ignores proxy variables (raw sockets, some tools) can still reach the
  network. No firewall rule was added, because the host's network policy is out of scope. For a hard guarantee, use a
  host or container that has no route out.
- **Observed egress with and without the guard.** With the proxy guard enabled, a test-scoped ETW trace
  (`Microsoft-Windows-Kernel-Network`, attributed by process) covered a typed tool turn plus a turn that forced an OMP
  compaction; it recorded 3,711 events for the OMP and Strata process trees and **zero non-loopback events** (G13).
  **Stock OMP contacts the internet at every start, whatever the settings** (observed without the guard on 18.4.0; on
  18.4.6 only the guarded run was traced, where the local-port probes below were still visible and the catalog opt-out
  request can1357/oh-my-pi#10934 remained open). Its background model registry refresh downloads the public model
  catalog (`catalog.stencil.so`, a models.dev mirror). It also probes the default local ports of other model servers:
  127.0.0.1:11434 (Ollama), :8080 (llama.cpp) and :1234 (LM Studio). With the plain isolated profile, an ETW trace of
  the OMP process tree showed 244 packet events to two non-loopback endpoints (G13 attempt 1). No prompt content is sent
  there (source reading: a GET for catalog metadata), but it is egress.

## Model-generated actions

- **User-privilege execution.** OMP executes tools (shell, edit, write) with your privileges. The integration adds no
  sandbox. Run it only on code and machines where that is acceptable.
- **Truncated tool-call handling (G04).** A cut on `finish_reason: length` is handled safely: OMP answers the call with
  an error result and does not run it. When the model ends its turn in the middle of a tool call, Strata v0.1.31 fixed
  its half (the call stays unfinished, its JSON open, and the answer ends with `stop`; Strata#231) and OMP 18.4.10 the
  other (can1357/oh-my-pi#13868: the call gets the parse error and is not run). G04 passes on the fourth tuple, both
  earlier RTX PRO 6000 tuples, the 18.8.4, v0.1.41 and v0.1.42 tuples (mock tier).

<details><summary>Historical G04 defect (pre-v0.1.31 / pre-18.4.10) and G24 operator-account deviation</summary>

- **Known upstream defect, fixed in the fourth tuple (G04).** When the model ends its turn in the middle of a tool
  call, stock Strata up to v0.1.30 closes the partial JSON and reports `finish_reason: tool_calls`, and stock OMP up to
  18.4.9 runs the tool with the truncated arguments: a partial file write happens and the run exits 0. The first and
  second candidates and the third tuple still have the defect.
- **G24 operator-account deviation.** The bounded evaluation (G24) ran under the host operator's account without an OS
  sandbox, for both candidates, the third tuple's 24 GB hosts, the fourth tuple's three hosts, the RTX PRO 6000, the
  18.8.4 tuple's three hosts, the v0.1.41 tuple's two hosts and the v0.1.42 tuple's three. This was a recorded
  deviation, approved by the owner, from the packet's restricted-account rule (for the 24 GB hosts, as part of handing
  them over for the overnight runs); the later runs used the same arrangement under the owner's go-ahead for each
  qualification.

</details>

## Supply chain

- **Pinned artifacts.** Every downloaded artifact is pinned by URL, size and SHA-256 in the profile, and verified
  before it is promoted from `.partial`. Only HTTPS downloads are accepted.
- **Guarded stock setup and hash-locked wheels.** Stock `setup.py` runs unmodified, but only after every input is local
  and verified. Python packages are installed with `--require-hashes --no-index` from the committed lock, which for
  v0.1.31 is resolved from its pinned `requirements.txt`. (The stock `setup.py` up to v0.1.30 would otherwise fetch the
  latest release, `main` model revisions and unpinned PyPI packages; Strata#214; v0.1.31 pins all three.)
- **Binary provenance limitation.** The Strata engine binary is a maintainer-uploaded release asset with no build
  attestation. Its bytes are pinned, but it is not rebuilt from source here.
- **Hosted CI and hygiene scan.** CI is hosted, runs host-free tests with read-only permissions and pinned actions, and
  has no access to GPU hosts or secrets. A public-hygiene scan (tracked files and history) blocks commits that contain
  private host details.
