# Security boundary

This integration runs one stock Strata server on loopback for one local user and drives it with the stock OMP
client. It is a single-user, single-host route. It is not a multi-tenant service, an OS sandbox or an egress
firewall. Everything below was observed on the qualification host (G02/G04 on the mock tier, G13 on the real
host) unless it is marked as a source reading.

## Server exposure

- Strata listens on `127.0.0.1:18090` only (G10: the only listener on the port is owned by the integration's
  process tree). `0.0.0.0` and remote clients are not supported. The remote-client route (G23) is disabled.
- Every model, control and metrics route needs the API key (`Authorization: Bearer` or `x-api-key`). G13 checked
  `GET /v1/models /models /props /metrics /settings /slots /v1/status /mcp` and `POST /v1/chat/completions
  /v1/messages /settings`: no key and wrong keys get 401, and the correct key gets 200 (the mutating
  `POST /settings` was only tried without a valid key). Shared server settings stayed at the frozen empty defaults.
- **Unauthenticated by design in stock Strata v0.1.27:** `/health`, `/status`, `/` (the web app) and its static
  assets. `/status` includes a `tail` of the text being generated, so any local process can read the end of the
  current answer without the key. Treat the host as single-user. Strata v0.1.28 puts `/status` behind the key
  and drops the tail when a request ends (Strata#212; mock tier, see `docs/UPSTREAM.md`).
- Stock Strata v0.1.27 **disables authentication when its key is empty**. `keygen` writes a 32-byte random key to
  `<root>\state\strata-api-key`, restricted to the current user (`icacls /inheritance:r`); `start` refuses a
  missing, blank or short key. The key reaches the server only through the detached `serve` wrapper's
  environment. It is never put on a command line, printed, logged or committed. Stock Strata compares keys with
  `==`, which is not constant-time; this is acceptable only because the listener is loopback-only. Strata
  v0.1.28 refuses an explicitly empty key and compares keys in constant time (Strata#213; see `docs/UPSTREAM.md`).
- Vision is off in this profile. Stock Strata can fetch `image_url` values (HTTP(S) or local paths) when vision is
  on, so enabling vision needs its own review (G22).

## Client isolation (`launch-omp`)

- OMP runs with a named profile (`omp-strata`) in an isolated HOME/USERPROFILE/APPDATA/TEMP under the root.
  Your normal `~/.omp` is never read or written. G20 checked that the user's `.omp` directory had no change after
  the integration root was created, and that stock Strata's `%APPDATA%\Strata` was never created.
- The environment is an allowlist (PATH, system roots, locale). Provider API keys, tokens, proxies, OTEL
  exporters, `NODE_OPTIONS`, shell startup files and credential sockets are dropped (unit and mock tests).
- Every OMP model role (default, smol, slow, plan, commit, task, advisor, judge, ...) is pinned to
  `strata-local/qwen3.8-flash-next-coder-iq1_m`. The route census over every session made during qualification
  found only that provider and model (G13), including OMP compaction's summarization calls (G13, G18).
- Extension, skill, rule, LSP, title and project-MCP discovery are off; flags that would override the provider,
  model, profile, config or extensions are refused by the launcher.
- **Stock OMP 18.4.0 sends the literal text `Bearer STRATA_API_KEY` when the key variable is unset**, instead of
  failing. The launcher refuses a missing or blank key before starting OMP.

## Network egress

- **Stock OMP 18.4.0 contacts the internet at every start, whatever the settings.** Its background model
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
- **Known upstream defect (release-blocking; G04 expected failures).** When the model ends its turn in the middle
  of a tool call, stock Strata closes the partial JSON and reports `finish_reason: tool_calls`. Stock OMP then runs
  the tool with the truncated arguments: a partial file write happens and the run exits 0. A cut on
  `finish_reason: length` is handled safely: OMP does not run the tool. Strata v0.1.28 still closes the partial call
  (mock tier). Fixes are proposed in Strata#231 and can1357/oh-my-pi#13868.
- The bounded evaluation (G24) ran under the host operator's account without an OS sandbox. This was a recorded
  deviation, approved by the owner, from the packet's restricted-account rule.

## Supply chain

- Every downloaded artifact is pinned by URL, size and SHA-256 in the profile, and verified before it is
  promoted from `.partial`. Only HTTPS downloads are accepted.
- The stock `setup.py` would otherwise fetch the latest release, `main` model revisions and unpinned PyPI
  packages (Strata#214, still open in v0.1.30; fix proposed in Strata#324). It runs unmodified, but only after
  every one of those inputs is local and verified. Python packages are installed with
  `--require-hashes --no-index` from the committed lock.
- The Strata engine binary is a maintainer-uploaded release asset with no build attestation. Its bytes are
  pinned, but it is not rebuilt from source here.
- CI is hosted, runs host-free tests with read-only permissions and pinned actions, and has no access to GPU
  hosts or secrets. A public-hygiene scan (tracked files and history) blocks commits that contain private host
  details.
