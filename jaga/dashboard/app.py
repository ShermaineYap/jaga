"""Family dashboard + judge-facing demo endpoint.

Run:  uvicorn jaga.dashboard.app:app --host 0.0.0.0 --port 8000
Pages: /  (check a message, recent verdicts)   /case/{id}   /memory   /policy   /audit
       /export (JSON of everything Jaga holds)   POST /delete-all   /health   POST /api/check
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import config
from ..config import RunOptions
from ..llm import CreditsExhausted
from ..pipeline import Jaga

app = FastAPI(title="Jaga", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
jaga = Jaga()
HH = config.DEMO_HOUSEHOLD
_hits: dict[str, list[float]] = defaultdict(list)
STATE = {"paused": False, "paused_reason": ""}

POLICY = {
    "network_allowlist": ["api.tokenfactory.nebius.com (Nemotron inference)", "api.tavily.com (verification)",
                          "api.telegram.org (messages)"],
    "credentials": "API keys are injected by OpenShell's inference routing; the agent process never sees them.",
    "guardian_receives": ["risk level", "one-line headline", "recommended action", "one evidence link"],
    "guardian_never_receives": ["the original message text", "sender phone numbers", "screenshots"],
    "retention": "Everything is in one SQLite file you can export or delete from this page.",
    "models": "Screenshots: Nemotron 3.5 Super VL · Triage: Nemotron 3.5 Lightning · Verify & verdict: Nemotron 3 Super · Hard cases: Nemotron 3 Ultra — all on Nebius Token Factory.",
}


def _rate_ok(ip: str) -> bool:
    now = time.time()
    _hits[ip] = [t for t in _hits[ip] if now - t < 60]
    if len(_hits[ip]) >= config.DASHBOARD_RATE_LIMIT_PER_MIN:
        return False
    _hits[ip].append(now)
    return True


def _ctx(request: Request, **kw):
    base = {"request": request, "mock": jaga.tf.mock, "models": jaga.tf.active_models or jaga.tf.health().get("models", {}),
            "paused": STATE["paused"], "paused_reason": STATE["paused_reason"], "hh": HH}
    return base | kw


def _run(text: str, channel: str):
    try:
        res = jaga.run_case(text, RunOptions(household_id=HH), channel=channel)
        STATE["paused"] = False
        return res
    except CreditsExhausted as e:
        STATE["paused"], STATE["paused_reason"] = True, str(e)
        raise HTTPException(status_code=503, detail="Jaga is paused: inference credits exhausted. Cached verdicts remain available.") from e


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    cases = jaga.ledger.recent_cases(HH, 20)
    for c in cases:
        c["verdict"] = json.loads(c["verdict_json"])
    return templates.TemplateResponse(request, "home.html", _ctx(request, cases=cases))


@app.post("/check")
def check(request: Request, text: str = Form(...), channel: str = Form("whatsapp")):
    if not _rate_ok(request.client.host if request.client else "x"):
        raise HTTPException(429, "Too many checks this minute — try again shortly.")
    res = _run(text.strip()[:4000], channel)
    return RedirectResponse(f"/case/{res.case_id}", status_code=303)


@app.post("/check-image")
async def check_image(request: Request, image: UploadFile = File(...)):
    if not _rate_ok(request.client.host if request.client else "x"):
        raise HTTPException(429, "Too many checks this minute — try again shortly.")
    data = await image.read()
    if len(data) > 6_000_000:
        raise HTTPException(413, "Image too large (max 6 MB).")
    try:
        res = jaga.run_screenshot(data, image.content_type or "image/jpeg", RunOptions(household_id=HH))
    except CreditsExhausted as e:
        STATE["paused"], STATE["paused_reason"] = True, str(e)
        raise HTTPException(503, "Jaga is paused: inference credits exhausted.") from e
    return RedirectResponse(f"/case/{res.case_id}", status_code=303)


@app.post("/api/check")
def api_check(request: Request, payload: dict):
    """Judge-facing JSON endpoint: {"text": "..."} -> full case result."""
    if not _rate_ok(request.client.host if request.client else "x"):
        raise HTTPException(429, "rate limited")
    text = (payload.get("text") or "").strip()[:4000]
    if not text:
        raise HTTPException(400, "text required")
    return JSONResponse(_run(text, payload.get("channel", "api")).model_dump())


@app.get("/case/{case_id}", response_class=HTMLResponse)
def case(request: Request, case_id: str):
    c = jaga.ledger.case(case_id)
    if not c:
        raise HTTPException(404)
    for k in ("triage", "plan", "verdict", "escalation", "models", "tool_calls"):
        raw = c.get(f"{k}_json")
        c[k] = json.loads(raw) if raw else None
    return templates.TemplateResponse(request, "case.html", _ctx(request, c=c))


@app.get("/memory", response_class=HTMLResponse)
def memory(request: Request):
    return templates.TemplateResponse(request, "memory.html", _ctx(request, members=jaga.ledger.members(HH), contacts=jaga.ledger.contacts(HH), payees=jaga.ledger.payees(HH)))


@app.post("/memory/trust")
def trust(name: str = Form(...), phone: str = Form(""), org: str = Form(""), relation: str = Form("")):
    jaga.ledger.add_contact(HH, name, phone, org, relation, trusted=True, added_by="dashboard")
    return RedirectResponse("/memory", status_code=303)


@app.get("/policy", response_class=HTMLResponse)
def policy(request: Request):
    pol_file = Path(config.ROOT / "hermes" / "openshell-policy.yaml")
    return templates.TemplateResponse(request, "policy.html", _ctx(request, policy=POLICY, guardians=jaga.ledger.guardians(HH),
        policy_yaml=pol_file.read_text() if pol_file.exists() else "(policy file not found)"))


@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request):
    events = jaga.ledger.audit_events(HH, 300)
    for e in events:
        e["detail"] = json.loads(e["detail"] or "{}")
        e["when"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["ts"]))
    return templates.TemplateResponse(request, "audit.html", _ctx(request, events=events))


@app.get("/export")
def export():
    return JSONResponse(jaga.ledger.export(HH))


@app.post("/delete-all")
def delete_all():
    jaga.ledger.delete_all(HH)
    return RedirectResponse("/", status_code=303)


@app.get("/health")
def health():
    return {"ok": True, "paused": STATE["paused"], "token_factory": jaga.tf.health(),
            "tavily_mock": jaga.tavily.mock, "db": str(jaga.ledger.db_path)}
