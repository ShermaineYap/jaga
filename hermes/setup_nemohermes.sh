#!/usr/bin/env bash
# Run Jaga inside an NVIDIA OpenShell sandbox (OpenShell 0.1.4, Docker driver).
#
# This is the path that was actually TESTED on 2026-10-16 (see
# hermes/OPENSHELL_RUN.md for evidence + friction log). It does NOT use the
# `openshell` or `nemohermes` CLIs: neither was obtainable in the test box
# (GitHub release downloads blocked; the `nemoclaw` packages on PyPI/npm are
# empty placeholders with no CLI). Instead it uses the published gateway
# container + the `openshell` Python SDK (pip install openshell==0.1.4).
#
# Prereqs: Linux + Docker Engine + docker compose, python3 with
#          `pip install openshell==0.1.4 pyyaml`, and a .env in the repo root
#          containing NEBIUS_API_KEY and TAVILY_API_KEY.
# Run from the repo root:  bash hermes/setup_nemohermes.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${OPENSHELL_WORK:-$HOME/.jaga-openshell}"
mkdir -p "$WORK/img" "$WORK/gw"
export OPENSHELL_GATEWAY_ENDPOINT="${OPENSHELL_GATEWAY_ENDPOINT:-127.0.0.1:8080}"

echo "== 1. Gateway (Docker compute driver, plaintext on loopback, from deploy/docker in NVIDIA/OpenShell)"
curl -fsSL https://raw.githubusercontent.com/NVIDIA/OpenShell/main/deploy/docker/docker-compose.yml -o "$WORK/gw/docker-compose.yml"
curl -fsSL https://raw.githubusercontent.com/NVIDIA/OpenShell/main/deploy/docker/gateway.toml      -o "$WORK/gw/gateway.toml"
if [ -n "${EXTRA_CA_BUNDLE:-}" ]; then
  # Only needed behind a TLS-intercepting egress proxy: the Docker driver has no
  # `additional_ca_bundle` (Podman-only), so bake the CA into a supervisor image.
  mkdir -p "$WORK/sup"
  docker create --name tmp-sup ghcr.io/nvidia/openshell/supervisor:latest >/dev/null
  docker cp tmp-sup:/etc/ssl/certs/ca-certificates.crt "$WORK/sup/orig.crt"; docker rm tmp-sup >/dev/null
  cat "$WORK/sup/orig.crt" "$EXTRA_CA_BUNDLE" > "$WORK/sup/ca-certificates.crt"
  printf 'FROM ghcr.io/nvidia/openshell/supervisor:latest\nCOPY ca-certificates.crt /etc/ssl/certs/ca-certificates.crt\n' > "$WORK/sup/Dockerfile"
  docker build -q -t jaga-supervisor:local "$WORK/sup"
  sed -i 's#^supervisor_image .*#supervisor_image  = "jaga-supervisor:local"#' "$WORK/gw/gateway.toml"
fi
# --force-recreate: the gateway resolves supervisor_image to an image ID at startup;
# rebuilding jaga-supervisor:local under a running gateway breaks sandbox creation.
docker compose -f "$WORK/gw/docker-compose.yml" up -d --force-recreate

echo "== 2. Sandbox image: Jaga code + deps, NO secrets"
tar --exclude='__pycache__' --exclude='.env' -C "$REPO" -cf "$WORK/img/jaga.tar" jaga
cp "${EXTRA_CA_BUNDLE:-/dev/null}" "$WORK/img/extra-ca.pem"   # empty unless behind a TLS-intercepting proxy
cat > "$WORK/img/Dockerfile" <<'EOF'
FROM nvcr.io/nvidia/base/ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv ca-certificates curl iproute2 nftables && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1500 app && useradd --uid 1500 --gid app --create-home app \
    && install -d -o app -g app /sandbox /data
COPY extra-ca.pem /tmp/extra-ca.pem
RUN if [ -s /tmp/extra-ca.pem ]; then cp /tmp/extra-ca.pem /usr/local/share/ca-certificates/extra-ca.crt && update-ca-certificates; fi
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt
COPY jaga.tar /tmp/jaga.tar
RUN tar -xf /tmp/jaga.tar -C /opt && rm /tmp/jaga.tar && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir openai httpx pydantic python-dotenv jinja2 && chmod -R a+rX /opt
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/opt JAGA_DB=/data/jaga.sqlite3
WORKDIR /sandbox
USER app
EOF
docker build -q -t jaga-sandbox:local "$WORK/img"

echo "== 3+4. Provider profiles + providers (keys live in the gateway only) + sandbox with policy"
cat > "$WORK/jaga_openshell.py" <<'PY'
import os, sys, yaml
from google.protobuf import json_format
from openshell import SandboxClient
from openshell._proto import openshell_pb2, datamodel_pb2, sandbox_pb2
repo, gw = sys.argv[1], os.environ["OPENSHELL_GATEWAY_ENDPOINT"]
c = SandboxClient(gw, timeout=120); stub = c._stub
import time
for _ in range(60):  # gateway needs a few seconds after `compose up` before gRPC accepts
    try: c.health(); break
    except Exception: time.sleep(1)
ws = datamodel_pb2.WorkspaceSelector(workspace="default")
env = {}
for line in open(os.path.join(repo, ".env")):
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.strip().split("=", 1); env[k] = v.strip().strip('"').strip("'")
BINS = [sandbox_pb2.NetworkBinary(path=p) for p in ("/usr/bin/python3.12", "/usr/bin/curl")]
def ep(host):
    return sandbox_pb2.NetworkEndpoint(host=host, port=443, protocol="rest",
        access=sandbox_pb2.NETWORK_ACCESS_PRESET_READ_WRITE, enforcement=sandbox_pb2.NETWORK_ENFORCEMENT_MODE_ENFORCE)
PROFILES = {"nebius-token-factory": ("NEBIUS_API_KEY", "api.tokenfactory.nebius.com", openshell_pb2.PROVIDER_PROFILE_CATEGORY_INFERENCE),
            "tavily": ("TAVILY_API_KEY", "api.tavily.com", openshell_pb2.PROVIDER_PROFILE_CATEGORY_KNOWLEDGE)}
items = [openshell_pb2.ProviderProfileImportItem(source=f"{pid}.yaml", profile=openshell_pb2.ProviderProfile(
            id=pid, display_name=pid, category=cat, endpoints=[ep(host)], binaries=BINS,
            credentials=[openshell_pb2.ProviderProfileCredential(name="api_key", env_vars=[k], required=True,
                         auth_style="bearer", header_name="authorization")]))
         for pid, (k, host, cat) in PROFILES.items()]
r = stub.ImportProviderProfiles(openshell_pb2.ImportProviderProfilesRequest(workspace_scope=ws, profiles=items))
print("profiles imported:", r.imported, [d.message for d in r.diagnostics])
for pid, (k, _, _) in PROFILES.items():
    try:
        stub.CreateProvider(openshell_pb2.CreateProviderRequest(workspace_scope=ws, provider=datamodel_pb2.Provider(
            metadata=datamodel_pb2.ObjectMeta(name="jaga-" + pid), type=pid,
            credentials={k: env[k]}, profile_workspace="default")))  # profile_workspace is REQUIRED for workspace profiles
        print("provider created: jaga-" + pid)
    except Exception as e:
        print("provider jaga-" + pid, "->", str(e).splitlines()[0][:200])
d = yaml.safe_load(open(os.path.join(repo, "hermes/openshell-policy.yaml")))
d["filesystem"] = d.pop("filesystem_policy")  # YAML key differs from the proto field name
E = {"tls": "NETWORK_TLS_MODE_", "enforcement": "NETWORK_ENFORCEMENT_MODE_", "access": "NETWORK_ACCESS_PRESET_"}
for rule in d["network_policies"].values():
    for e in rule["endpoints"]:
        for f, p in E.items():
            if f in e: e[f] = p + e[f].upper().replace("-", "_")
spec = openshell_pb2.SandboxSpec(
    environment={"JAGA_DB": "/data/jaga.sqlite3", "PYTHONPATH": "/opt", "PATH": "/opt/venv/bin:/usr/bin:/bin"},
    template=openshell_pb2.SandboxTemplate(image="jaga-sandbox:local"),
    policy=json_format.ParseDict(d, sandbox_pb2.SandboxPolicy()),
    providers=["jaga-nebius-token-factory", "jaga-tavily"], command=["sleep", "infinity"])
c.delete("jaga", workspace="default", allow_missing=True)
try: c.wait_deleted("jaga", workspace="default")
except Exception: pass
c.create(workspace="default", spec=spec, name="jaga"); c.wait_ready("jaga", workspace="default")
print("sandbox 'jaga' ready")
for cmd in (["sh", "-c", "echo NEBIUS_API_KEY inside sandbox = ${NEBIUS_API_KEY%%_*}..."],
            ["curl", "-sS", "-m", "10", "-o", "/dev/null", "https://example.com"],
            ["python3", "-c", "from jaga.pipeline import Jaga; from jaga.config import RunOptions; "
             "r=Jaga().run_case('Pos Laju: bungkusan ditahan, bayar RM48 di poslaju-kastam.xyz', "
             "RunOptions(household_id='os', notify=False)); print('VERDICT', r.verdict.risk, r.verdict.family)"]):
    r = c.exec("jaga", cmd, workspace="default", timeout_seconds=300)
    print("$", " ".join(cmd)[:80], "->", r.exit_code, (r.stdout + r.stderr).strip()[-300:])
PY
python3 "$WORK/jaga_openshell.py" "$REPO"

echo "Done. Supervisor (OCSF) log: docker logs \$(docker ps -qf name=openshell-default--jaga- -f name=supervisor)"
# Telegram: api.telegram.org is allowlisted in the policy, but the bot token is
# NOT yet provider-managed (token sits in the URL path; needs a profile using
# path_template). Untested — see OPENSHELL_RUN.md.
# NemoClaw/Hermes (`nemohermes onboard ...`) path: NOT tested — CLI unavailable.
