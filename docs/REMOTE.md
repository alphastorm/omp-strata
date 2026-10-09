# Remote clients and static fleet roles

This is a **client route**, not a second server installation. Stock OMP speaks
OpenAI Chat Completions directly to stock Strata through an authenticated SSH
local forward. There is no request proxy, daemon, engine-state store or OMP fork.
The server continues to bind only `127.0.0.1` and requires its API key.

The one public route is **qualified** (owner, 2026-10-09):

- `routes/client-rtxpro6000-strata0.1.41-omp18.8.6.json`: one 131k RTX PRO 6000 server
  (`win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6`, four batch slots), every chat role on it.

Its independent `releases/<route-id>/` ledger requires G23, which **passed on 2026-10-09** from a Mac Studio client
([receipt](../releases/client-rtxpro6000-strata0.1.41-omp18.8.6/receipts/cd43354d72c0421c8d21ab3c72257b51.json)):
a missing key was refused before launch and a wrong key got 401; stream TTFT through the tunnel was 0.19 s; a tunnel
drop failed the turn in flight with the transcript intact; the nonce was recalled after reopening the tunnel,
restarting the client and a verified server restart. The server profile is qualified for local use on its own
ledger; the route inherits none of that evidence, and every referenced server retains its own independent profile,
root and ledger. The server owns its GPU only while it serves: on that host the operator stops the GPU's other
tenant before `start` and restores it after `stop` (see OPERATIONS.md, "Sharing the GPU").
No fleet route is currently published: the Strata v0.1.36 drafts for the removed
RTX 4090 (one single-host route and a three-GPU fleet) were retired.
`capabilities.remote_client` remains false on server profiles; true on a route means that G23 is in scope.
`verify_release.py --require-ready` requires G23 **and** independently qualified server manifests.

## Identity and private state

A public client-route specification pins server **profile ids and canonical
fingerprints**, local ports, every chat model role, and named scout assignments.
It does not copy model artifacts or the roughly model-sized server root. A
changed measured route needs a new id and fresh ledger, just like a server.

Private bindings contain the SSH alias, absolute remote root and remote platform
(`windows` or `posix`). Their duplicated profile pins, ports and role map must
match the public route exactly; bindings cannot silently retarget a route. Keep
bindings outside the checkout in a user-only file. Never commit actual aliases,
remote paths, keys or raw logs. The committed example uses neutral labels only:
`examples/remote/bindings.example.json`.

A client root contains only its verified client download, private key files,
route identity, isolated OMP home/transcripts and raw proof artifacts. It contains
no local Strata install. Fetch, pull-key, launch and the proof scripts refuse a root already bound to
another route fingerprint or to a server install, before downloading or replacing
anything. A first fetch or key pull records the root identity under the client lock;
proofs also check and record each derived run root before copying keys or starting SSH.
Do not reuse a client root for a changed route.

For maintainers refreshing **unmeasured drafts only**, this command recomputes
server fingerprints, route fingerprint, ledger binding and neutral example:

```sh
python3 scripts/verify_release.py \
  --manifest releases/client-rtxpro6000-strata0.1.41-omp18.8.6/manifest.json \
  --refresh-route-draft --bindings-example examples/remote/bindings.example.json --json
```

For a fleet route, pass its own manifest and example. The refresh refuses any
non-draft route, measured gate or existing receipt history; it never rewrites a
receipt or inherits a predecessor's evidence. Already created private bindings
and client roots remain bound to the old fingerprint and must not be reused.

## Single remote client

From the repository checkout on the **client**:

```sh
ROUTE=routes/client-rtxpro6000-strata0.1.41-omp18.8.6.json
ROOT="$HOME/omp-strata-client-rtxpro6000-strata0.1.41-omp18.8.6"
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
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
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
is not mistaken for a running listener. Readiness and OMP startup require that
every listener on the port, on any address (including IPv4 and IPv6 wildcards),
belongs exclusively to the still-running SSH child. A listener sample does not
authorize a later connection: each key-bearing launcher/probe HTTP connection
connects without sending HTTP bytes, then verifies that the server half of that
exact established TCP four-tuple belongs exclusively to the live SSH child.
Only then may it send the request. Ownership is queried with macOS
`/usr/sbin/lsof`, Linux `/proc` TCP inode/descriptor tables, or Windows
`Get-NetTCPConnection` via `powershell.exe -NoProfile`. Missing, incomplete or
unavailable ownership data refuses credentials. A replacement listener cannot
inherit an already established TCP connection. Before OMP starts, the launcher checks
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
After a leader has been reaped, a live process at its old PID prevents any group
signal: that PID has been reused. If no such process exists, descendant-group
cleanup remains enabled. Windows containment continues to use the job handle.
Native Windows job behavior still requires its real-client qualification gate.

OMP uses the same isolated HOME, named profile, credential allowlist, discovery-
off flags, retry/model-fallback settings and closed-loopback proxy egress guard
as local launch. The guard is defense in depth, not an OS firewall. An SSH-exit
watcher immediately kills the owned OMP process group/job, without a transport
grace period or a provider switch. Stock OMP's documented HTTP transport retries
still exist; disabling retry settings is not a promise of zero transport resends.
The stock OMP transport is unmodified: its startup ownership check plus an exit watcher
are not an atomic per-request credential firewall against a hostile local
process. Host-free regressions exercise a squatter taking the port after the
readiness probe, a squatter rebinding immediately after SSH dies, and a stale
listener sample before launcher/probe connect; none receives an Authorization
header in those exercised races. Only launcher/probe HTTP connections have the
established-peer check; stock OMP retains the exit-to-kill window described above.

To continue after an outage, deliberately launch again with the same root and
`-- --continue`. OMP's previously persisted transcript is authoritative. Immediate
termination can discard the unfinished turn and its unflushed tail; no final
aborted/error event is guaranteed. A new server does cold re-prefill; no GPU cache
or durable engine state is claimed restored.

## Fleet roles

No fleet route is currently published; this is how one is used once drafted.
Its neutral bindings example has one entry per member: copy it into a
**different** client root and edit each member's private binding. Then, with
`FLEET_ROUTE_ID` standing for the fleet route's id:

```sh
ROUTE=routes/FLEET_ROUTE_ID.json
ROOT="$HOME/omp-strata-FLEET_ROUTE_ID"
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT"
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" \
  --fleet "$ROOT/state/bindings.json"
```

One tunnel is opened and authenticated per member before OMP starts. A partial
startup failure closes every tunnel already opened. Every member becomes one
`strata-<label>` provider, `api: openai-completions`, with
`providers.maxInFlightRequests[provider]` equal to that server profile's batch
slots (stock setup `--parallel N`), else 1. Without slots each Strata server
executes one request at a time. This setting is not a global distributed
concurrency limiter; server FIFO history is the authority for measured service
overlap.

Every chat role is explicit. Main-session roles stay on the main member; task,
advisor and judge roles select a worker. `task.agentModelOverrides` pins the
stock `task` and `scout` to that worker without replacing their definitions:
stock prompts, tools, output schemas and thinking levels are preserved. These
two names are reserved and cannot be redefined in a public route. Additional
named scouts from a route's `agents` map use native user-agent
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
count an invalid routing proof. A route remains a draft until its independent
qualification is complete.

The pinned real-binary CLI-policy check also parses value-taking options and
short aliases from `--help`: every option must be blocked by the wrapper or
explicitly reviewed as safe. A new value-taking routing/configuration/extension
option cannot silently become a launcher escape on the next pinned upgrade.
The real-binary probes also require glued short values, short clusters containing
a forbidden alias, and abbreviated forbidden long options (separate and `=`
values) to fail as unknown flags, in an isolated HOME/environment.

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
after connect and established-peer verification. Metrics timing bounds include ownership-query
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
