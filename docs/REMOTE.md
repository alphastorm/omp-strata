# Remote clients and static fleet roles

This is a **client route**, not a second server installation. Stock [Oh My Pi](https://github.com/can1357/oh-my-pi)
(OMP) speaks OpenAI Chat Completions directly to stock [Strata](https://github.com/Niko1221/Strata) through an
authenticated SSH local forward. There is no request proxy, daemon, engine-state store or OMP fork. The server
continues to bind only `127.0.0.1` and requires its API key.

- **Current client route (qualified, 2026-10-31):**
  `routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json` — one 262K RTX PRO 6000 server, the
  current `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0` (four batch slots
  with per-slot multi-token prediction (MTP) and direct per-layer embedding (PLE) reads), every chat role on it.
- **Rollback client route (qualified, 2026-10-30):**
  `routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json` — one 262K RTX PRO 6000 server, the rollback
  `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0` (four batch slots), every chat role on it.
- **Earlier qualified history:** eight earlier RTX PRO 6000 routes (`v0.2.7` at 262K, owner 2026-10-28; `v0.2.3`
  at 262K, owner 2026-10-23; `v0.2.1` at 262K, owner 2026-10-21; `v0.1.44.1` at 262K, owner 2026-10-14;
  `v0.1.43.1` at 262K, owner 2026-10-13; `v0.1.43` and `v0.1.42` at 262K, owner 2026-10-12; `v0.1.41` at 131K,
  owner 2026-10-09) remain qualified history, not the current server profile or its immediate rollback (details
  and receipts in the collapsed route sections below).
- **Fleet routes:** no fleet route is currently published or qualified; the Strata v0.1.36 drafts for the removed
  RTX 4090 (one single-host route and a three-GPU fleet) were retired.

This route targets only the PRO's current 262K batch-MTP + PLE-direct profile
(`win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0`, rolling back to
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0`); the PRO's `slots4-pledirect-parking` qualified
alternative, the RTX 5090 262K default and 131K alternative (rolling back to `v0.2.7`), and the RTX 4090 + RTX 3090
pair's current split-24 trim + PLE-direct profile
(`win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-split24-trimweights-pledirect-parking-strata0.2.8-omp18.14.0`,
rolling back to `win11-rtx3090-rtx4090-iq3s-262k-pw2-disp4090-roles-pledirect-parking-strata0.2.8-omp18.14.0`) are
local-only and are not members of the Studio route ([decision](DECISION.md)).

The current route's independent `releases/<route-id>/` ledger requires G23, which **passed on 2026-10-31** from
the Mac Studio client at implementation `610be03`
([receipt](../releases/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0/receipts/ef6fcbc23ead437dae827704ce4d632f.json)):
a missing key was refused before launch and a wrong key got 401; health RTT was 5.1-8.8 ms and stream TTFT
through the tunnel 0.278 s; a tunnel drop failed the turn in flight with the prior transcript preserved; nonce
recall passed after tunnel reopen (0.88 s), client restart (0.66 s) and verified server restart (1.62 s,
changed server instance); and a one-turn `launch-omp` smoke answered `ROUTE OK`. This route qualified on 2026-10-31
([decision](DECISION.md)); no blockers and `--require-ready` passes.

TTFT includes server work; these receipts establish neither SSH-only overhead nor a direct-path baseline. Each server
profile is qualified for local use on its own ledger; a route inherits none of that evidence, and every referenced
server retains its own independent profile, root and ledger. `capabilities.remote_client` remains false on server
profiles; true on a route means that G23 is in scope. `verify_release.py --require-ready` requires G23 **and**
independently qualified server manifests. The server owns its GPU only while it serves: on that host the operator
stops the GPU's other tenant before `start` and restores it after `stop` (see OPERATIONS.md, "Sharing the GPU").

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

### Current 262K route

Use the Studio's current qualified route and a client root of its own. Its member, `rtxpro6000-win-a`, uses
local port **18191**. Do not reuse the `0.2.8` `slots4-parking` rollback, `0.2.7`, `0.2.3`, `0.2.1`, `0.1.44.1`,
`0.1.43.1`, `0.1.43`, `0.1.42` or `0.1.41` client roots or their private bindings: they remain bound to those routes'
identities.

From the repository checkout on the **client**:

```sh
ROUTE=routes/client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
```

The committed example is a neutral **template bound to the earlier 0.1.41 route**, not configured current-route
bindings. In the new private copy, set these public identity fields **before fetch, key pull or launch**:

| Binding field | Current-route value |
|---|---|
| `route_id` | `client-rtxpro6000-262k-batchmtp-pledirect-strata0.2.8-omp18.14.0` |
| `route_fingerprint` | `9dfafc293621e80a7ba8129a652449da465223d8b1d46b84fa9d50728ace8d74` |
| `members[0].server_profile` | `win11-rtxpro6000-iq3s-262k-slots4-batchmtp-pledirect-parking-strata0.2.8-omp18.14.0` |
| `members[0].server_fingerprint` | `9f4a2da58a71a25236c54e177659295a662fcb477a73d868de8133650ffd96ff` |
| `members[0].label` / `members[0].local_port` | `rtxpro6000-win-a` / `18191` |
| `roles` | The current route's complete role map, every role on `rtxpro6000-win-a` |
Then edit only `alias`, `remote_root` and `remote_platform` in that private copy to
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

### Qualified 0.2.8 rollback route

<details>
<summary>Rollback procedure and 2026-10-30 G23 receipt (Strata v0.2.8 + OMP 18.14.0, PRO slots4-parking rollback)</summary>

The rollback route's independent `releases/<route-id>/` ledger requires G23, which **passed on 2026-10-30** from
the Mac Studio client at implementation `4853ab3`
([receipt](../releases/client-rtxpro6000-262k-strata0.2.8-omp18.14.0/receipts/e0d2532492834f928703268e14bdd7b9.json)):
a missing key was refused before launch and a wrong key got 401; health RTT was 6.1-6.7 ms and stream TTFT
through the tunnel 0.199 s; a tunnel drop failed the turn in flight with the prior transcript preserved; nonce
recall passed after tunnel reopen (0.85 s), client restart (0.75 s) and verified server restart (1.65 s,
changed server instance). The v0.2.8 `slots4-parking` route qualified on 2026-10-30; its manifest has no blockers and
`--require-ready` passes.

These commands belong to the PRO's qualified **262K v0.2.8 `slots4-parking` rollback profile**, not its current
batch-MTP + PLE-direct profile. Start from the same template and set this route's identity before fetch, key pull or
launch: `route_id` `client-rtxpro6000-262k-strata0.2.8-omp18.14.0`, `route_fingerprint`
`e33711b249dfc92363164cb8097abe32f30ebeff7b0d4c33c66fb957ee4666b9`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.8-omp18.14.0` and `members[0].server_fingerprint`
`5612e5970d1470b9a3bdd70b399e3a2a83946c4cc22bc37d8eb0165e13f883aa`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.2.8-omp18.14.0.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.2.8-omp18.14.0"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

</details>

### Qualified 0.1.42 route for the earlier 262K profile

<details>
<summary>Earlier 262K routes (v0.2.7 on 2026-10-28, v0.2.3 on 2026-10-23, v0.2.1 on 2026-10-21, v0.1.44.1 on 2026-10-14, v0.1.43.1 on 2026-10-13, v0.1.43 on 2026-10-12 and v0.1.42 on 2026-10-11) and v0.2.7 / v0.2.3 / v0.2.1 / v0.1.44.1 / v0.1.43.1 / v0.1.42 procedures</summary>

- `routes/client-rtxpro6000-262k-strata0.2.7-omp18.13.2.json` (qualified, earlier route, owner 2026-10-28): one
  262K RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2` (four batch slots),
  every chat role on it. Its ledger records G23 **passing on 2026-10-28** from the Mac Studio client at
  implementation `15c7426`
  ([receipt](../releases/client-rtxpro6000-262k-strata0.2.7-omp18.13.2/receipts/b394c29467ac49548f14c1abecf29c0a.json)):
  a missing key was refused before launch and a wrong key got 401; health RTT was 8.0-41.4 ms and stream TTFT
  through the tunnel 0.316 s; a tunnel drop failed the turn in flight with the prior transcript preserved; nonce
  recall passed after tunnel reopen (1.04 s), client restart (0.78 s) and verified server restart (1.60 s,
  changed server instance). The owner qualified the v0.2.7 route on 2026-10-28; its manifest has no blockers and
  `--require-ready` passes.
- `routes/client-rtxpro6000-262k-strata0.2.3-omp18.12.6.json` (qualified, earlier route, owner 2026-10-23): one
  262K RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6` (four batch slots),
  every chat role on it. Its ledger records G23 **passing on 2026-10-23** from the Mac Studio client at
  implementation `de60693`
  ([receipt](../releases/client-rtxpro6000-262k-strata0.2.3-omp18.12.6/receipts/26f8ca50bad64aa796c4611452ae92da.json)):
  a missing key was refused before launch and a wrong key got 401; health RTT was 4.6-5.2 ms and stream TTFT
  through the tunnel 0.171 s; a tunnel drop failed the turn in flight with the prior transcript preserved; nonce
  recall passed after tunnel reopen (0.77 s), client restart (0.71 s) and verified server restart (2.67 s,
  changed server instance). The owner qualified the v0.2.3 route on 2026-10-23; its manifest has no blockers and
  `--require-ready` passes.
- `routes/client-rtxpro6000-262k-strata0.2.1-omp18.10.1.json` (qualified, earlier route, owner 2026-10-21): one
  262K RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1` (four batch slots),
  every chat role on it. Its ledger records G23 **passing on 2026-10-21** from the Mac Studio client at
  implementation `3f52b65`
  ([receipt](../releases/client-rtxpro6000-262k-strata0.2.1-omp18.10.1/receipts/69fd6b56f3d34f2490285dbce19cfbc5.json)):
  a missing key was refused before launch and a wrong key got 401; health RTT was 4.7-5.1 ms and stream TTFT
  through the tunnel 0.171 s; a tunnel drop failed the turn in flight with the prior transcript preserved; nonce
  recall passed after tunnel reopen (0.81 s), client restart (0.68 s) and verified server restart (1.16 s,
  changed server instance). The owner qualified the v0.2.1 route on 2026-10-21; its manifest has no blockers and
  `--require-ready` passes.
- `routes/client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1.json` (qualified, earlier route, owner 2026-10-14): one
  262K RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1` (four batch slots),
  every chat role on it. Its ledger records G23 **passing on 2026-10-14** from the Mac Studio client at
  implementation `78a26bf`
  ([receipt](../releases/client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1/receipts/07b3084bc2a846418c2e5b5696aae12a.json)):
  a missing key was refused before launch and a wrong key got 401; health RTT was 4.8-5.2 ms and stream TTFT
  through the tunnel 0.189 s; a tunnel drop failed the turn in flight with the prior transcript preserved; nonce
  recall passed after tunnel reopen (0.76 s), client restart (0.78 s) and verified server restart (1.35 s,
  changed server instance). The owner qualified the v0.1.44.1 route on 2026-10-14; its manifest has no blockers and
  `--require-ready` passes.
- `routes/client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1.json` (qualified, earlier route, owner 2026-10-13): one
  262K RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1` (four batch slots),
  every chat role on it. Its ledger records G23 **passing on 2026-10-13** from the Mac Studio client at
  implementation `d2fac61`
  ([receipt](../releases/client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1/receipts/396f56907ffe4fc49b95a5edcf3919d0.json)):
  a missing key was refused before launch and a wrong key got 401; health RTT was 5.2-13.5 ms and stream TTFT
  through the tunnel 0.191 s; a tunnel drop failed the turn in flight with the transcript intact; the nonce was
  recalled after reopening the tunnel (0.76 s), restarting the client (0.91 s) and a verified server restart
  (1.39 s, changed server instance). A one-turn `launch-omp` smoke answered `ROUTE OK` (operator run context).
  The owner qualified the v0.1.43.1 route on 2026-10-13; its manifest has no blockers and `--require-ready` passes.
- `routes/client-rtxpro6000-262k-strata0.1.43-omp18.10.1.json` (qualified, earlier route, owner 2026-10-12): one 262K
  RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43-omp18.10.1` (four batch slots),
  every chat role on it. Its ledger records G23 **passing on 2026-10-12**
  ([receipt](../releases/client-rtxpro6000-262k-strata0.1.43-omp18.10.1/receipts/368c9143f3884b0f9df6ee47cb828966.json)):
  the same refusals and 401, health RTT 4.6-5.3 ms, stream TTFT 0.195 s, a tunnel drop failing the turn in flight
  with the transcript intact, and nonce recall after tunnel reopen (1.41 s), client restart (1.79 s) and verified
  server restart (2.18 s).
- `routes/client-rtxpro6000-262k-strata0.1.42-omp18.8.9.json` (qualified, earlier route, owner 2026-10-12): one 262K
  RTX PRO 6000 server, `win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9` (four batch slots), every
  chat role on it. Its ledger records G23 **passing twice on 2026-10-11**
  ([first](../releases/client-rtxpro6000-262k-strata0.1.42-omp18.8.9/receipts/6b60de1bd6544a9fa142cc0730cbae6f.json),
  [second](../releases/client-rtxpro6000-262k-strata0.1.42-omp18.8.9/receipts/98a7433c697d4cef9d61a8c5f876508e.json)):
  the same refusals and 401, TTFT 0.196 s both times, transcript preservation on tunnel drop, and nonce recall
  after tunnel reopen (0.78-0.80 s), client restart (0.72-0.79 s) and verified server restart (1.35-1.48 s).

These commands belong to the PRO's qualified **earlier 262K v0.2.7 profile**, not its current v0.2.8 profile.
Start from the same template and set this route's identity before fetch, key pull or launch: `route_id`
`client-rtxpro6000-262k-strata0.2.7-omp18.13.2`, `route_fingerprint`
`f65463389d3166b2e46566c7703d6d35b0ce5502009f888ddb5a4f6f9a0c99ce`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.7-omp18.13.2` and `members[0].server_fingerprint`
`6f8fc6b2683ef4e1118b36401b93517916b31a1da12949260cc96e85d9f47e3d`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.2.7-omp18.13.2.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.2.7-omp18.13.2"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

These commands belong to the PRO's qualified **earlier 262K v0.2.3 profile**, not its current v0.2.8 profile.
Start from the same template and set this route's identity before fetch, key pull or launch: `route_id`
`client-rtxpro6000-262k-strata0.2.3-omp18.12.6`, `route_fingerprint`
`cc0749cfdb5da0eebb9589c3b2190ec511f381b427d32955ffcdeae8daf4b089`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.3-omp18.12.6` and `members[0].server_fingerprint`
`349248ac0b60d278e37d607576a48148fb68ab052f32850c37680b2c659b2468`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.2.3-omp18.12.6.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.2.3-omp18.12.6"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

These commands belong to the PRO's qualified **earlier 262K v0.2.1 profile**, not its current v0.2.8 profile.
Start from the same template and set this route's identity before fetch, key pull or launch: `route_id`
`client-rtxpro6000-262k-strata0.2.1-omp18.10.1`, `route_fingerprint`
`1ec38fd6eb1f9e5d6c4bda07309bdf976d127167cb631e83661f17d6f12dcb8b`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.2.1-omp18.10.1` and `members[0].server_fingerprint`
`7b5d41632623fa8e3bbf78ff23d8413b3a17d7f1997d06f03f390eb38945b969`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.2.1-omp18.10.1.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.2.1-omp18.10.1"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

These commands belong to the PRO's qualified **earlier 262K v0.1.44.1 profile**, not its current v0.2.8 profile.
Start from the same template and set this route's identity before fetch, key pull or launch: `route_id`
`client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1`, `route_fingerprint`
`f0dbedcb73d94cd85432bb2e879ea71fefb4c037857b5603b3fa1cac86bbd202`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.44.1-omp18.10.1` and `members[0].server_fingerprint`
`80a6a9936a2972a7c7553b9bcef94315f1b2a863ccfc44654023643eb71b4042`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.1.44.1-omp18.10.1"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

These commands belong to the PRO's qualified **earlier 262K v0.1.43.1 profile**, not its current v0.2.8 profile.
Start from the same template and set this route's identity before fetch, key pull or launch: `route_id`
`client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1`, `route_fingerprint`
`547bbee99c4384ab6c56b2312f6313e64f66a2690591e6a0aebc1f38151598ef`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.43.1-omp18.10.1` and `members[0].server_fingerprint`
`eeaf4c597182a8dec8a681c975452bcc4c04970ed69086a72ae4fbf9fc8b8011`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.1.43.1-omp18.10.1"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

These commands belong to the PRO's qualified **earlier 262K v0.1.42 profile**, not its current v0.2.8 profile.
Start from the same template and set this route's identity before fetch, key pull or launch: `route_id`
`client-rtxpro6000-262k-strata0.1.42-omp18.8.9`, `route_fingerprint`
`c9c0eb9649f9c4703ac175ab086c8d1a80fe74089b4e65ef12fc17a92bb78145`, `members[0].server_profile`
`win11-rtxpro6000-iq3s-262k-slots4-parking-strata0.1.42-omp18.8.9` and `members[0].server_fingerprint`
`7ee9263ca729bf308ef3c14a0196e0608b216da93140ee9a5cd6be638a993660`, with the same member, port and roles. Keep this
root separate from the other routes' roots. All ten routes use local port 18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-262k-strata0.1.42-omp18.8.9.json
ROOT="$HOME/omp-strata-client-rtxpro6000-262k-strata0.1.42-omp18.8.9"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set this route's identity fields and the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

</details>

### Qualified 0.1.41 route for the earlier 131K profile

<details>
<summary>Earlier 131K route (v0.1.41 on 2026-10-09) and procedure</summary>

- `routes/client-rtxpro6000-strata0.1.41-omp18.8.6.json` (qualified, earlier route, owner 2026-10-09): one 131K RTX PRO
  6000 server (`win11-rtxpro6000-iq3s-131k-slots4-parking-strata0.1.41-omp18.8.6`, four batch slots), every chat role
  on it. Its ledger records G23 **passing on 2026-10-09** from a Mac Studio client
  ([receipt](../releases/client-rtxpro6000-strata0.1.41-omp18.8.6/receipts/cd43354d72c0421c8d21ab3c72257b51.json))
  with the same checks; stream TTFT through the tunnel was 0.19 s.

These commands belong to the PRO's qualified **earlier 131K v0.1.41 profile**, not its current 262K profile.
The committed example already pins this route; edit only its private `alias`, `remote_root` and
`remote_platform` fields. Keep this root separate from the other routes' roots. All ten routes use local port
18191, so run only one at a time.

```sh
ROUTE=routes/client-rtxpro6000-strata0.1.41-omp18.8.6.json
ROOT="$HOME/omp-strata-client-rtxpro6000-strata0.1.41-omp18.8.6"
mkdir -p "$ROOT/state"
install -m 600 examples/remote/bindings.example.json "$ROOT/state/bindings.json"
# Set the private binding fields before running the commands below.
python3 scripts/omp_strata.py fetch --profile "$ROUTE" --root "$ROOT" --only omp
python3 scripts/omp_strata.py pull-key --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
python3 scripts/omp_strata.py launch-omp --profile "$ROUTE" --root "$ROOT" --remote rtxpro6000-win-a
```

</details>

### Binding and key handling (every route)

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

No fleet route is currently published or qualified; a fleet route remains a draft until its own G23 and all referenced
server manifests are qualified. This is how one is used once drafted:

<details>
<summary>Draft fleet route configuration and stock OMP subagent routing</summary>

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

Stock OMP 18.13.2 adds `ast_grep` to its bundled scout; it does not change this integration's explicit
allowlist for additional named scouts. The supplemental fan-out proof requires a nonempty named-agent map
and does not claim a fixed tool census for OMP's bundled scout.

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
OMP 18.13's `--warn-cost` and `--max-cost` are reviewed pass-through options:
stock v18.13.2 parses USD thresholds and applies only non-persisted session-cost
overrides. They neither select another provider/model nor load config or code;
the max-cost gate can stop new requests (print-mode exit 3), not cancel ones
already in flight. These local Strata providers declare zero token prices, so
the flags are not a host-resource or power-use limit.
The real-binary probes also require glued short values, short clusters containing
a forbidden alias, and abbreviated forbidden long options (separate and `=`
values) to fail as unknown flags, in an isolated HOME/environment.

</details>

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
