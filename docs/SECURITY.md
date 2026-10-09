# Security boundary

This integration runs one stock Strata server on loopback for one local user and drives it with the stock OMP
client. It is a single-user, single-host route. It is not a multi-tenant service, an OS sandbox or an egress
firewall. Everything below was observed on the qualification host (G02/G04 on the mock tier, G13 on the real
host) unless it is marked as a source reading. Where the two candidates differ (stock Strata v0.1.27 + OMP 18.4.0
against v0.1.30 + 18.4.6), both are stated; the third tuple (Strata v0.1.31 + OMP 18.4.8, two 24 GB hosts), the
fourth (Strata v0.1.34 + OMP 18.4.10, three hosts), the RTX PRO 6000 tuples (Strata v0.1.40.2 + OMP 18.8.0, and
Strata v0.1.40.3 + OMP 18.8.3 with batch slots and conversation parking), the Strata v0.1.40.3 + OMP 18.8.4 tuple
(the RTX PRO 6000 with slots and parking, the RTX 5090 and the RTX 3090) and the current Strata v0.1.41 + OMP 18.8.6
tuple (the RTX PRO 6000 with slots and parking, and the RTX 5090) are named where they change something.

## Server exposure

- Strata listens on `127.0.0.1:18090` only (G10: the only listener on the port is owned by the integration's
  process tree). `0.0.0.0` is not supported. Remote clients reach it only through a client route over an
  authenticated loopback-to-loopback SSH forward (below); one route, a Mac Studio to the RTX PRO 6000 profile, is
  qualified by G23 on its own ledger, and no fleet route is published.
- The server's environment is the operator's environment minus every variable whose name looks like a secret
  (`KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`) and minus every inherited `STRATA_*` variable: those are the
  engine's tuning and debug switches (v0.1.31 alone added 16), and a setting changes only through a new profile.
  The API key is then added explicitly.
- Every model, control and metrics route needs the API key (`Authorization: Bearer` or `x-api-key`). G13 checked
  `GET /v1/models /models /props /metrics /settings /slots /v1/status /mcp` (plus `/status` on the second
  candidate) and `POST /v1/chat/completions /v1/messages /settings`: no key and wrong keys get 401, and the correct
  key gets 200 (the mutating `POST /settings` was only tried without a valid key). Shared server settings stayed at
  the frozen empty defaults. On the fourth tuple G13 also sent missing and wrong keys to `POST /load /unload
  /v1/load /v1/unload /v1/messages/count_tokens` (401 on all three hosts; stock checks the key before it routes any
  POST), found the opt-in request monitor absent (`/api-monitor` and `/api/requests` 404 with the key) and a CORS
  preflight answered 204 without `Access-Control-Allow-Origin`; `/health`, `/api/health` and `/` stay public. On the
  RTX PRO 6000 tuple G13 also refused missing and wrong keys on `GET /config` and on `POST /config /slots/
  /v1/responses /v1/vram` (401), and the egress trace recorded zero non-loopback events among 2,416 attributed ones
  (2,796 on the slots-and-parking profile). `tests/unit/test_strata_surface.py` fails when a pinned server routes a
  path G13 does not probe, and install accepts only the config keys every pinned setup writes (`"parallel"` only as a
  profile's pinned batch slots), so CORS origins, the monitor or lazy loading cannot be switched on by a generated
  config.
- **Batch slots and conversation parking (current RTX PRO 6000 profile).** The server decodes up to four requests at
  once, and OMP may send it four; they come from the one local user's OMP processes. Parking keeps up to four recent
  conversations' engine state in host RAM inside the engine process (an 8 GiB budget). Nothing is written to disk,
  and the state goes when the engine stops. A conversation is restored only for a prompt that starts with exactly its
  tokens.
- **Unauthenticated by design in stock Strata v0.1.27 (first candidate):** `/health`, `/status`, `/` (the web app)
  and its static assets. `/status` includes a `tail` of the text being generated, so any local process can read the
  end of the current answer without the key. Treat the host as single-user. Strata v0.1.28 puts `/status` behind
  the key and drops the tail when a request ends (Strata#212); on the second candidate (v0.1.30) G13 observed
  `/status` answering 401 without the key, leaving `/health` and `/` public.
- Stock Strata v0.1.27 **disables authentication when its key is empty**. `keygen` writes a 32-byte random key to
  `<root>\state\strata-api-key`, restricted to the current user (`icacls /inheritance:r`); `start` refuses a
  missing, blank or short key. The key reaches the server only through the detached `serve` wrapper's
  environment. It is never put on a command line, printed, logged or committed. Stock Strata v0.1.27 compares keys
  with `==`, which is not constant-time; this is acceptable only because the listener is loopback-only. Strata
  v0.1.28 and later (second candidate) refuse an explicitly empty key and compare keys in constant time
  (Strata#213; an absent key still means no authentication, so the launcher's refusal stays).
- Vision is off in this profile. Stock Strata can fetch `image_url` values (HTTP(S) or local paths) when vision is
  on, so enabling vision needs its own review (G22).

## Remote client routes and fleets (one qualified single-host route; no fleet route)

Design and commands: [`REMOTE.md`](REMOTE.md).

- The server side does not change: it still binds loopback only and requires its key. A client reaches it through
  `ssh -NT -L 127.0.0.1:<local>:127.0.0.1:<server>` run as an argv-only child of the foreground `launch-omp`, with
  `BatchMode=yes`, `ExitOnForwardFailure=yes` and multiplexing/background-after-authentication disabled. The
  child lives in an owned POSIX session or a Windows kill-on-close job and is torn down on every exit path; no
  forward outlives the session. An occupied local port is refused, never adopted.
- `pull-key` reads the host root's key over the SSH session's stdout (stdin closed) into a user-only file under
  the client root (`state/keys/<label>.key`); it never appears in argv, launcher errors, logs or receipts. A
  user-only `<label>.key.json` beside it binds the key's digest to the binding it came from (SSH alias, remote
  root, platform); after any binding change the launcher refuses with "binding changed since pull-key" until
  `pull-key` runs again. The client root holds the keys, the private bindings and the isolated OMP home; none of
  them belongs in the repository. Fetch, key pull and proof writers check the root identity and server-install
  exclusion before writes/network effects, recording a new identity under the client lock. Derived proof roots
  have the same check before keys are copied into them.
- Before OMP starts, the platform ownership query (`lsof` on macOS, `/proc` on Linux, `Get-NetTCPConnection` on
  Windows) must attribute every listener on the port, on any address including IPv4/IPv6 wildcards, to the SSH
  child. A stale listener sample never authorizes a launcher/probe request: its HTTPConnection first connects,
  then checks that the server half of that exact established TCP four-tuple belongs exclusively to the live
  SSH child, before sending any HTTP bytes. Failed or incomplete checks refuse credentials. A subsequent port
  rebind cannot replace the peer of that established connection. Before OMP starts, every member must pass `/health`, refuse
  unauthenticated `/v1/models` with 401, and match the pinned model id, exact Strata build, context and empty
  shared settings with the key. Preflight follows no redirects and ignores ambient proxies, so the bearer key
  cannot be forwarded to another origin.
- When an SSH child exits, a watcher kills OMP's process group (Windows: job) at once, with no grace period, to
  curtail retries into a listener that takes over the freed port. The turn in flight is lost; the transcript
  saved before it resumes explicitly. Nothing falls back to another provider. Stock OMP's own requests are not
  checked one by one (that would need a proxy or a fork): the remaining window is the time between the SSH
  child's exit and that kill. SIGINT/SIGTERM are deferred while a child is started or registered and while the
  session tears down; teardown attempts every tunnel and keeps the handle of any that failed to close.
  Group signals for a reaped leader are skipped if its PID now names a live process; otherwise descendant
  cleanup is preserved. Windows uses the owned job handle, not PID-based group signalling.
- A fleet adds one `strata-<label>` provider per host (one request in flight each). Stock OMP's
  `task.agentModelOverrides` routes the unmodified stock `task` (full coding tools) and `scout` (read-only tools)
  agents to a worker; only the extra named scouts are generated definitions, with `model:` pinned and tools
  limited to read/find/grep/glob (a mock-tier test with the real pinned OMP binary confirms their write, edit and
  bash attempts are refused). Every role still resolves to a Strata provider only.
- Trust boundaries that stay with the operator: the SSH client, its configuration (including any
  `ProxyCommand`) and host-key trust; model-generated tools, which run with the client user's privileges and
  can read whatever that user can, including the client root's key files, as tools on the server host can
  read the server key. The egress guard is defense in depth, not an OS firewall. Native Windows job containment
  has not run on a real client yet.

## Client isolation (`launch-omp`)

- OMP runs with a named profile (`omp-strata`) in an isolated HOME/USERPROFILE/APPDATA/TEMP under the root.
  Your normal `~/.omp` is never read or written. G20 checked that the user's `.omp` directory had no change after
  the integration root was created, and that stock Strata's `%APPDATA%\Strata` was never created.
- The environment is an allowlist (PATH, system roots, locale). Provider API keys, tokens, proxies, OTEL
  exporters, `NODE_OPTIONS`, shell startup files and credential sockets are dropped (unit and mock tests).
- Every OMP model role (default, smol, slow, plan, commit, task, advisor, judge, ...) is pinned to the profile's
  model on `strata-local` (`qwen3.8-flash-next-iq3_s` on the RTX PRO 6000, `qwen3.8-flash-next-coder-iq1_m` on the
  Coder profiles). The route census over every session made during qualification found only that provider and model
  (G13), including OMP compaction's summarization calls (G13, G18).
- Extension, skill, rule, LSP, title and project-MCP discovery are off; flags that would override the provider,
  model, profile, config or extensions are refused by the launcher.
- **Stock OMP (18.4.0 and 18.4.6) sends the literal text `Bearer STRATA_API_KEY` when the key variable is unset**,
  instead of failing. The launcher refuses a missing or blank key before starting OMP.

## Network egress

- **Stock OMP contacts the internet at every start, whatever the settings** (observed without the guard on 18.4.0;
  on 18.4.6 only the guarded run was traced, where the local-port probes below were still visible and the catalog
  opt-out request can1357/oh-my-pi#10934 remained open). Its background model
  registry refresh downloads the public model catalog (`catalog.stencil.so`, a models.dev mirror). It also probes
  the default local ports of other model servers: 127.0.0.1:11434 (Ollama), :8080 (llama.cpp) and :1234
  (LM Studio). With the plain isolated profile, an ETW trace of the OMP process tree showed 244 packet events to
  two non-loopback endpoints (G13 attempt 1). No prompt content is sent there (source reading: a GET for catalog
  metadata), but it is egress.
- The launcher therefore sets `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` to a closed loopback port (`127.0.0.1:9`)
  and `NO_PROXY` to loopback. The Strata route stays direct. OMP's catalog fetch and any HTTP from tools the model
  runs then fail locally. With this guard, a test-scoped ETW trace (`Microsoft-Windows-Kernel-Network`, attributed
  by process) covered a typed tool turn plus a turn that forced an OMP compaction. It recorded 3,711 events for
  the OMP and Strata process trees and **zero non-loopback events** (G13).
- **This is not enforcement.** A process that ignores proxy variables (raw sockets, some tools) can still reach
  the network. No firewall rule was added, because the host's network policy is out of scope. For a hard
  guarantee, use a host or container that has no route out.

## Model-generated actions

- OMP executes tools (shell, edit, write) with your privileges. The integration adds no sandbox. Run it only on
  code and machines where that is acceptable.
- **Known upstream defect, fixed in the fourth tuple (G04).** When the model ends its turn in the middle of a tool
  call, stock Strata up to v0.1.30 closes the partial JSON and reports `finish_reason: tool_calls`, and stock OMP up
  to 18.4.9 runs the tool with the truncated arguments: a partial file write happens and the run exits 0. A cut on
  `finish_reason: length` is handled safely: OMP answers the call with an error result and does not run it. Strata
  v0.1.31 fixed its half (the call stays unfinished, its JSON open, and the answer ends with `stop`; Strata#231) and
  OMP 18.4.10 the other (can1357/oh-my-pi#13868: the call gets the parse error and is not run). G04 passes on the
  fourth tuple, both earlier RTX PRO 6000 tuples, the 18.8.4 tuple and the current tuple (mock tier);
  the first and second candidates and the third tuple still have the defect.
- The bounded evaluation (G24) ran under the host operator's account without an OS sandbox, for both candidates,
  the third tuple's 24 GB hosts, the fourth tuple's three hosts, the RTX PRO 6000, the 18.8.4 tuple's three hosts and
  the current tuple's two hosts. This was a recorded deviation, approved by the owner, from the packet's
  restricted-account rule (for the 24 GB hosts, as part of handing them over for the overnight runs); the later runs
  used the same arrangement under the owner's go-ahead for each qualification.

## Supply chain

- Every downloaded artifact is pinned by URL, size and SHA-256 in the profile, and verified before it is
  promoted from `.partial`. Only HTTPS downloads are accepted.
- The stock `setup.py` up to v0.1.30 would otherwise fetch the latest release, `main` model revisions and unpinned
  PyPI packages (Strata#214; v0.1.31 pins all three). It runs unmodified, but only after every one
  of those inputs is local and verified. Python packages are installed with `--require-hashes --no-index` from the
  committed lock, which for v0.1.31 is resolved from its pinned `requirements.txt`.
- The Strata engine binary is a maintainer-uploaded release asset with no build attestation. Its bytes are
  pinned, but it is not rebuilt from source here.
- CI is hosted, runs host-free tests with read-only permissions and pinned actions, and has no access to GPU
  hosts or secrets. A public-hygiene scan (tracked files and history) blocks commits that contain private host
  details.
