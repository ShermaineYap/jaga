"""Nebius Token Factory client.

One class, three roles (fast / plan / escalate), each with a fallback chain of
Nemotron model IDs. Every call:
  * uses Token Factory's OpenAI-compatible API with JSON-schema structured
    output, so answers are validated Pydantic objects;
  * toggles Nemotron's reasoning via chat_template_kwargs.enable_thinking and
    applies a client-side budget (max_tokens) when thinking is on;
  * records tokens, cost and the model actually used;
  * degrades along the chain on 404 (model renamed), 402 (credits exhausted)
    and 429 (rate limit), and raises a clear error if the whole chain fails.

In mock mode (JAGA_MOCK=1 or no API key) the same interface is served by
deterministic heuristics in jaga.mock so the entire system runs offline.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from . import config

log = logging.getLogger("jaga.llm")
T = TypeVar("T", bound=BaseModel)

ROLE_CHAINS = {
    "vision": config.MODEL_VISION,
    "fast": config.MODEL_FAST,
    "plan": config.MODEL_PLAN,
    "escalate": config.MODEL_ESCALATE,
}


def strict_schema(model: type[BaseModel]) -> dict:
    """JSON schema with every property marked required. Nemotron's guided decoding skips
    optional fields, so list fields with defaults (entities, urgency cues) would come back
    empty. Required + maxItems keeps them present and bounded."""
    sch = model.model_json_schema()

    def fix(node: dict) -> None:
        if node.get("type") == "object" and "properties" in node:
            node["required"] = list(node["properties"].keys())
            for v in node["properties"].values():
                v.pop("default", None)
        for v in node.values():
            if isinstance(v, dict):
                fix(v)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, dict):
                        fix(x)
    fix(sch)
    for d in sch.get("$defs", {}).values():
        fix(d)
    return sch


class TokenFactoryError(RuntimeError):
    pass


class CreditsExhausted(TokenFactoryError):
    """HTTP 402 from Token Factory. The dashboard shows a 'paused' state."""


class Usage:
    """Accumulates tokens and USD across one case."""

    def __init__(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0
        self.models_used: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []

    def add(self, role: str, model: str, prompt: int, completion: int, ms: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        pin, pout = config.PRICES_PER_M.get(model, (0.0, 0.0))
        cost = prompt / 1e6 * pin + completion / 1e6 * pout
        self.cost_usd += cost
        self.models_used[role] = model
        self.calls.append({"role": role, "model": model, "prompt_tokens": prompt,
                           "completion_tokens": completion, "cost_usd": round(cost, 6), "ms": ms})

    def as_dict(self) -> dict[str, int]:
        return {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens}


class TokenFactory:
    def __init__(self, mock: bool | None = None) -> None:
        self.mock = config.MOCK if mock is None else mock
        self._client = None
        if not self.mock:
            from openai import OpenAI  # imported lazily so mock mode has no SDK dependency
            self._client = OpenAI(api_key=config.NEBIUS_API_KEY, base_url=config.NEBIUS_BASE_URL)
        self.active_models: dict[str, str] = {}

    # ------------------------------------------------------------------ public
    def structured(self, role: str, system: str, user: str, schema: type[T], *,
                   thinking: bool = False, budget: int | None = None,
                   usage: Usage | None = None, context: dict | None = None) -> T:
        """Call the role's model chain and return a validated `schema` instance."""
        if self.mock:
            from . import mock
            t0 = time.time()
            obj = mock.answer(role, schema, user, context or {})
            if usage is not None:
                # Approximate token counts so cost reports are shaped like real runs.
                model = ROLE_CHAINS[role][0]
                usage.add(role, model, len(system + user) // 4, 300 if thinking else 120,
                          int((time.time() - t0) * 1000))
            return obj

        last_err: Exception | None = None
        for model in ROLE_CHAINS[role]:
            try:
                return self._call(model, role, system, user, schema, thinking, budget, usage)
            except CreditsExhausted:
                raise
            except TokenFactoryError as e:
                last_err = e
                log.warning("model %s failed for role %s (%s); trying next", model, role, e)
        raise TokenFactoryError(f"all models failed for role {role}: {last_err}")

    def read_screenshot(self, image: bytes, mime: str = "image/jpeg", usage: Usage | None = None):
        """Transcribe a forwarded screenshot with Nemotron 3.5 Super VL."""
        import base64

        from .schemas import ScreenshotReading
        system = ("You read screenshots that Malaysian seniors forward to a scam checker. Transcribe the message "
                  "exactly as shown (Bahasa Malaysia, English or mixed), name the app, the sender as displayed, and "
                  "any visual red flags. Do not judge whether it is a scam. Output one JSON object with exactly these keys: "
                  'app, sender_shown, message_text, visual_cues, legible. Example: {"app": "whatsapp", '
                  '"sender_shown": "+60 11-0000 1234", "message_text": "...", "visual_cues": ["bank logo on a personal number"], '
                  '"legible": true}')
        if self.mock:
            return ScreenshotReading(app="whatsapp", sender_shown="", legible=True, visual_cues=[],
                                     message_text="(mock) screenshot text unavailable in demo mode")
        url = f"data:{mime};base64," + base64.b64encode(image).decode()
        last: Exception | None = None
        for model in ROLE_CHAINS["vision"]:
            t0 = time.time()
            try:
                resp = self._client.chat.completions.create(
                    model=model, temperature=0.0, max_tokens=1500,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": [
                                  {"type": "text", "text": "Read this forwarded screenshot."},
                                  {"type": "image_url", "image_url": {"url": url}}]}],
                    response_format={"type": "json_schema", "json_schema": {
                        "name": "ScreenshotReading", "schema": strict_schema(ScreenshotReading), "strict": False}})
            except Exception as e:  # noqa: BLE001
                last = e
                continue
            content = (resp.choices[0].message.content or "").split("</think>")[-1].strip().strip("`")
            if content.startswith("json"):
                content = content[4:]
            if usage is not None and resp.usage:
                usage.add("vision", model, resp.usage.prompt_tokens, resp.usage.completion_tokens, int((time.time() - t0) * 1000))
            self.active_models["vision"] = model
            try:
                obj = json.loads(content)
                if isinstance(obj, dict) and "properties" in obj and "message_text" not in obj:
                    obj = obj["properties"]  # some VL outputs wrap the answer in the schema shape
                return ScreenshotReading.model_validate(obj)
            except Exception as e:  # noqa: BLE001
                last = e
        raise TokenFactoryError(f"vision failed: {last}")

    def health(self) -> dict[str, Any]:
        """Which model IDs from each chain exist right now (for /health and the UI footer)."""
        if self.mock:
            return {"mock": True, "models": {r: c[0] for r, c in ROLE_CHAINS.items()}}
        try:
            ids = {m.id for m in self._client.models.list().data}
        except Exception as e:  # noqa: BLE001
            return {"mock": False, "error": str(e)}
        return {"mock": False, "models": {
            r: next((m for m in chain if m in ids), None) for r, chain in ROLE_CHAINS.items()},
            "catalog_size": len(ids)}

    # ----------------------------------------------------------------- private
    def _call(self, model: str, role: str, system: str, user: str, schema: type[T],
              thinking: bool, budget: int | None, usage: Usage | None) -> T:
        from openai import APIStatusError, RateLimitError

        kwargs: dict[str, Any] = dict(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": {
                "name": schema.__name__, "schema": strict_schema(schema), "strict": False}},
            temperature=0.1,
            frequency_penalty=0.3,
            extra_body={"chat_template_kwargs": {"enable_thinking": thinking}},
        )
        if budget:
            kwargs["max_tokens"] = budget
        elif not thinking:
            kwargs["max_tokens"] = 1200

        for attempt in range(2):
            t0 = time.time()
            try:
                resp = self._client.chat.completions.create(**kwargs)
            except RateLimitError as e:
                if attempt == 0:
                    time.sleep(2.0)
                    continue
                raise TokenFactoryError(f"429 from {model}: {e}") from e
            except APIStatusError as e:
                if e.status_code == 402:
                    raise CreditsExhausted("Token Factory returned 402: credits exhausted") from e
                if e.status_code == 404:
                    raise TokenFactoryError(f"model {model} not found (404)") from e
                raise TokenFactoryError(f"{e.status_code} from {model}: {e}") from e

            ms = int((time.time() - t0) * 1000)
            content = resp.choices[0].message.content or ""
            # Reasoning-capable models may wrap thinking in <think>…</think>; strip it.
            if "</think>" in content:
                content = content.split("</think>", 1)[1]
            content = content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
            if usage is not None and resp.usage:
                usage.add(role, model, resp.usage.prompt_tokens, resp.usage.completion_tokens, ms)
            self.active_models[role] = model
            try:
                return schema.model_validate(json.loads(content))
            except Exception as e:  # noqa: BLE001
                raise TokenFactoryError(f"{model} returned non-conforming JSON: {e}: {content[:200]}") from e
        raise TokenFactoryError("unreachable")
