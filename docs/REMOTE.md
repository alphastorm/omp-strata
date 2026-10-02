# Remote clients and static fleet roles

This is a **client route**, not a second server installation. Stock OMP speaks
OpenAI Chat Completions directly to stock Strata through an authenticated SSH
local forward. There is no request proxy, daemon, engine-state store or OMP fork.
The server continues to bind only `127.0.0.1` and requires its API key.

The two public routes are **drafts**, not qualified deployments:

- `routes/client-rtx4090-strata0.1.36-omp18.4.12.json`: one 131k RTX 4090 server.
- `routes/fleet-3gpu-strata0.1.36-omp18.4.12.json`: RTX 5090 main session, RTX 4090
  default worker, and explicitly selectable RTX 4090/3090 scouts.

Their independent `releases/<route-id>/` ledgers require G23 and record
`not_run`. No GPU host was contacted during implementation. In particular,
these routes do not qualify the planned RAM upgrades or the new server tuple.
Every referenced server retains its own independent profile, root and ledger.
`capabilities.remote_client` remains false on server profiles; true on a draft
route means that G23 is in scope, not that it passed. `verify_release.py
--require-ready` requires G23 **and** independently qualified server manifests.

## Identity and private state

A public client-route specification pins server **profile ids and canonical
fingerprints**, local ports, every chat model role, and named scout assignments.
It does not copy model artifacts or the roughly model-sized server root. A
changed measured route needs a new id and fresh ledger, just like a server.

Private bindings contain the SSH alias, absolute remote root and remote platform
(`windows` or `posix`). Their duplicated profile pins, ports and role map must
match the public route exactly; bindings cannot silently retarget a route. Keep
bindings outside the checkout in a user-only file. Never commit actual aliases,
remote paths, keys or raw logs. The committed examples use neutral labels only:

- `examples/remote/bindings.example.json`
- `examples/fleet/bindings.example.json`

A client root contains only its verified client download, private key files,
route identity, isolated OMP home/transcripts and raw proof artifacts. It contains
no local Strata install. Both fetch and launch refuse a root already bound to
another route fingerprint or to a server install, before downloading or replacing
anything. The first route fetch records the root identity under the client lock.
Do not reuse a client root for a changed route.

For maintainers refreshing **unmeasured drafts only**, this command recomputes
server fingerprints, route fingerprint, ledger binding and neutral example:

```sh
python3 scripts/verify_release.py \
  --manifest releases/client-rtx4090-strata0.1.36-omp18.4.12/manifest.json \
  --refresh-route-draft --bindings-example examples/remote/bindings.example.json --json
```

Use the corresponding fleet manifest/example for the fleet. It refuses any
non-draft route, measured gate or existing receipt history; it never rewrites a
receipt or inherits a predecessor's evidence. Already created private bindings
and client roots remain bound to the old fingerprint and must not be reused.

## Single remote client

From the repository checkout on the **client**:

```sh
ROUTE=routes/client-rtx4090-strata0.1.36-omp18.4.12.json
ROOT="$HOME/omp-strata-client-rtx4090-strata0.1.36-omp18.4.12"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
```

Edit only `alias`, `remote_root` and `remote_platform` in that private copy to
match your installation. Establish host-key trust and noninteractive SSH access
using your normal SSH configuration first. The launcher does not accept new host
keys automatically and will not prompt for an SSH password.

On a Windows client, copy the example to a root under `$env:USERPROFILE`, then
restrict the copy with `icacls /inheritance:r /grant:r "$($env:USERNAME):F"`.
Use ordinary PowerShell argv dispatch for the commands below; do not put a key
on a command line. `pull-key` restricts its own key files on both platforms.

```sh
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtx4090-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtx4090-win-a
```

Replace the last argument with the alias in your **private** binding; the neutral
example is not a configured host. `fetch` with a route can fetch only the current
client platform's pinned OMP binary. It never downloads the engine or model.
`--bindings FILE` selects a private binding file instead of the default
`<root>/state/bindings.json`.

`pull-key` reads `<remote-root>/state/strata-api-key` from SSH stdout with stdin
closed and `BatchMode=yes`. It refuses blank, short, non-ASCII or whitespace-
containing keys. A temporary file is restricted before secret bytes are written,
then atomically installed at `<client-root>/state/keys/<label>.key`. On POSIX the
mode is 0600; on Windows the existing current-user ACL helper is used. A failed
transfer does not replace an existing key. A sibling `<label>.key.json`, also
user-only, binds the key digest to the SSH alias, remote root and remote platform
used by `pull-key`. Changing any of those binding fields refuses launch before
network activity: `binding changed since pull-key; run pull-key again`. Missing
metadata or an interrupted key/metadata replacement also fails closed. Run
`pull-key` again; do not install a raw key file without its provenance. SSH output,
keys and response bodies are never included in launcher errors or receipts.

The forward is an argv-only child command, not a shell command:

```text
ssh -NT -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o BatchMode=yes -o ControlMaster=no -o ControlPath=none -o ForkAfterAuthentication=no -L 127.0.0.1:LOCAL_PORT:127.0.0.1:SERVER_PORT ALIAS
```

An occupied local listener is refused, not adopted. Closed-connection TIME_WAIT
is not mistaken for a running listener. After readiness and before each
key-bearing launcher/probe HTTP request, the listener must belong exclusively to
the still-running SSH child. Ownership is queried with macOS `/usr/sbin/lsof`,
Linux `/proc` TCP inode/descriptor tables, or Windows `Get-NetTCPConnection` via
`powershell.exe -NoProfile`. Missing, incomplete or unavailable ownership data
refuses credentials; a reachable port alone is never readiness proof. Ownership
is checked again before starting OMP. Before OMP starts, the launcher checks
public `/health`, requires unauthenticated `/v1/models` to return 401, then checks
the model id, exact Strata build version, context and frozen empty shared
settings with the key. Missing keys, wrong keys, a wrong model/version, stopped
servers or failed tunnels fail closed. Preflight follows no HTTP redirects and
uses no inherited proxy, so it cannot forward the bearer key to another origin.

SSH lives in an owned POSIX session/process group, or a Windows kill-on-close job
assigned while the child is suspended. Normal exit, client error, Ctrl-C, SIGTERM
and partial fleet startup all unwind ownership. ProxyCommand descendants are
included. SIGINT/SIGTERM are deferred until a spawned child is published and
contained, and throughout teardown, so interruption cannot skip escalation or
lose the process handle. Cleanup attempts every owned OMP process and tunnel
even if one close fails; failed handles remain available for another close, and
the aggregate error is reported only after the other cleanup attempts.
Inherited multiplexing and background-after-authentication are explicitly
disabled so the foreground child cannot silently become an independently persistent
master. The SSH binary and the operator's SSH configuration remain trusted; this is
not a sandbox for a hostile ProxyCommand or model-generated tools.
On macOS a zombie-only process group can report EPERM rather than ESRCH; teardown
accepts that only after a read-only process-state snapshot finds no live member.
An actual permission failure against a live group is still an error.
Native Windows job behavior still requires its real-client qualification gate.

OMP uses the same isolated HOME, named profile, credential allowlist, discovery-
off flags, retry/model-fallback settings and closed-loopback proxy egress guard
as local launch. The guard is defense in depth, not an OS firewall. An SSH-exit
watcher immediately kills the owned OMP process group/job, without a transport
grace period or a provider switch. Stock OMP's documented HTTP transport retries
still exist; disabling retry settings is not a promise of zero transport resends.
The stock OMP transport is unmodified: ownership checks plus an exit watcher
are not an atomic per-request credential firewall against a hostile local
process. Host-free regressions exercise a squatter taking the port after the
readiness probe, and a squatter rebinding immediately after SSH dies; neither
receives an Authorization header in those exercised races.

To continue after an outage, deliberately launch again with the same root and
`-- --continue`. OMP's previously persisted transcript is authoritative. Immediate
termination can discard the unfinished turn and its unflushed tail; no final
aborted/error event is guaranteed. A new server does cold re-prefill; no GPU cache
or durable engine state is claimed restored.

## Fleet roles

Copy `examples/fleet/bindings.example.json` into a **different** client root and
edit its three private bindings. Then:

```sh
ROUTE=routes/fleet-3gpu-strata0.1.36-omp18.4.12.json
ROOT="$HOME/omp-strata-fleet-strata0.1.36-omp18.4.12"
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT"
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" \
  --fleet "$ROOT/state/bindings.json"
```

One tunnel is opened and authenticated per member before OMP starts. A partial
startup failure closes every tunnel already opened. Every member becomes one
`strata-<label>` provider, `api: openai-completions`, with
`providers.maxInFlightRequests[provider] = 1`. Each Strata server executes one
request at a time. This setting is not a global distributed concurrency limiter;
server FIFO history is the authority for measured service overlap.

Every chat role is explicit. Main-session roles stay on the main member; task,
advisor and judge roles select a worker. `task.agentModelOverrides` pins the
stock `task` and `scout` to that worker without replacing their definitions:
stock prompts, tools, output schemas and thinking levels are preserved. These
two names are reserved and cannot be redefined in a public route. Additional
named scouts such as `scout-4090` and `scout-3090` use native user-agent
`model: strata-<label>/<model-id>` frontmatter and an explicit
`tools: read, find, grep, glob` allowlist; OMP supplies their result-submission
tool. No extension/plugin is installed.

**Observed with stock OMP 18.4.6, 18.4.8, 18.4.10 and 18.4.12:** model overrides
route the unmodified stock task/scout definitions, while native `model:`
frontmatter routes named scouts. `--no-extensions --no-skills --no-rules` does
**not** disable these native user agents. Real-binary mock tests require exact
worker results in the main transcript and exercise rejected named-scout
write/edit/bash calls. They answer native task-label and effort-judgment requests
separately: asynchronous auxiliary requests make a fixed parent HTTP-request
count an invalid routing proof. The public routes remain drafts until their
independent qualification is complete.

The pinned real-binary CLI-policy check also parses value-taking options and
short aliases from `--help`: every option must be blocked by the wrapper or
explicitly reviewed as safe. A new value-taking routing/configuration/extension
option cannot silently become a launcher escape on the next pinned upgrade.

## G23 and fan-out evidence

Run probes only in an explicit operator-approved server window. They make real
inference requests; G23 also restarts each server using commands you supply.
Nothing here automatically contacts a host during validation or CI.

Create a private `restart-commands.json` object mapping **each route member label**
to a nonempty argv array for your known restart operation. It is run without a
shell, with stdin closed and stdout/stderr suppressed. Do not include secrets in
argv. The probe verifies a changed `/metrics` `totals.since` and rechecks identity,
so a no-op command cannot count as a restart.

```sh
python3 scripts/remote_gates.py --profile "$ROUTE" --root "$ROOT" \
  --bindings "$ROOT/state/bindings.json" \
  --restart-commands "$ROOT/state/restart-commands.json" \
  --output "$ROOT/proofs/g23-window" --implementation-commit "$(git rev-parse HEAD)"
python3 scripts/fanout_proof.py --profile "$ROUTE" --root "$ROOT" \
  --fleet "$ROOT/state/bindings.json" --scouts 4 \
  --output "$ROOT/proofs/fanout-window" --implementation-commit "$(git rev-parse HEAD)"
```

Use a new output directory each time. Raw OMP output and transcripts remain under
the client root; only the scrubbed summary and schema-valid receipt may be
considered for export after the normal public-hygiene review.

`remote_gates.py` exercises every route member: no key refused before launch,
wrong key -> 401 and failed preflight, health RTT/stream TTFT through SSH,
mid-stream tunnel loss with a failed turn and preserved prior transcript, deliberate
reopen, client restart, and a verified server restart followed by exact nonce
recall from transcript replay. TTFT includes inference; without a direct-path
baseline it is not an isolated measurement of SSH overhead. The TTFT clock starts
after the listener ownership check. Metrics timing bounds include ownership-query
time and must be interpreted conservatively.

`fanout_proof.py` drives stock OMP's **task tool**, not independent fake clients,
first with every scout on one member and then with the fleet's model-bound
scouts. It requires the requested batch and exact completed scout results in the
persisted transcript, including stock `custom_message` / `async-result`
deliveries (not only `wait` results). Prompt echoes and parent-generated text do
not count. Authenticated `/metrics?requests=all` supplies each server's
`requests[].time` and `duration_s`, plus request-count/instance continuity. The
report records per-provider and combined overlap. Clocks are offset using the
metrics RTT midpoint; Strata durations are rounded to 0.1 seconds. Run with no
other clients and interpret small overlaps within those uncertainties cautiously.
History overflow, failed requests and server restart invalidate the comparison.

Both scripts emit `schemas/receipt.schema.json` receipts with gate G23.
`--host-free` can never produce a G23 pass. A live fan-out report is supplemental
and remains `blocked` for G23 because it does not replace the auth/drop/restart
probe. Neither script edits a release ledger automatically.
