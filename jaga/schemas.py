"""Pydantic schemas. These double as the JSON schemas sent to Token Factory's
structured-output endpoint, so the model's answers are validated, not parsed
by hope."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ScamFamily = Literal[
    "impersonation", "investment", "love", "mule", "parcel", "phishing_otp", "legit"
]
Risk = Literal["high", "medium", "low", "unknown"]


class Entities(BaseModel):
    phones: list[str] = Field(default_factory=list, max_length=5, description="Phone numbers exactly as written")
    urls: list[str] = Field(default_factory=list, max_length=5, description="Links / domains exactly as written")
    orgs: list[str] = Field(default_factory=list, max_length=6, description="Companies, agencies, banks, schemes, brands named in the message")
    bank_accounts: list[str] = Field(default_factory=list, max_length=4, description="Bank account NUMBERS only (digits), not bank names")
    amounts: list[str] = Field(default_factory=list, max_length=5, description="Money amounts as written, e.g. 'RM5,000'")
    persons: list[str] = Field(default_factory=list, max_length=4, description="Proper names of specific people only (e.g. 'Inspektor Razak'). Never pronouns, roles or organisations. Usually 0-2 items.")


class ScreenshotReading(BaseModel):
    """Output of the vision tier (Nemotron 3.5 Super VL) on a forwarded screenshot."""
    app: Literal["whatsapp", "sms", "telegram", "email", "browser", "other"]
    sender_shown: str = Field(description="Sender name or number exactly as displayed, or ''")
    message_text: str = Field(description="The full message text transcribed verbatim, in its original language")
    visual_cues: list[str] = Field(default_factory=list, max_length=5,
                                   description="Visual red flags, e.g. 'bank logo on a personal WhatsApp account', 'unverified sender', 'shortened link'")
    legible: bool = Field(description="False if the screenshot is too blurry or cropped to read")


class Triage(BaseModel):
    """Output of the fast tier (Nemotron 3.5 Lightning, thinking off)."""
    family: ScamFamily
    confidence: float = Field(ge=0, le=1)
    language: Literal["ms", "en", "manglish", "other"]
    urgency_cues: list[str] = Field(default_factory=list, max_length=5, description="Verbatim phrases creating pressure")
    asks_for: list[str] = Field(default_factory=list, max_length=4, description="What the sender wants: 'TAC', 'transfer', 'click link', 'personal data', 'nothing'")
    entities: Entities
    one_line: str = Field(description="One plain-language sentence on what this message is")


class Check(BaseModel):
    entity: str
    tool: Literal["tavily_search_official", "tavily_search_news", "ledger_lookup", "alert_cache"]
    query: str
    reason: str


class VerificationPlan(BaseModel):
    """Output of the planning tier (Nemotron 3 Super, thinking on, budgeted)."""
    needs_live_check: bool
    checks: list[Check] = Field(default_factory=list, max_length=6)
    ledger_answers_it: bool = Field(description="True if household memory alone resolves the case (e.g. known trusted contact)")
    rationale: str


class Evidence(BaseModel):
    claim: str
    source_url: str = Field(description="URL of the authority page or '' if from household memory")
    quote: str = Field(description="Short verbatim excerpt supporting the claim, or '' ")
    kind: Literal["official_alert", "news", "ledger", "none_found"]


class Verdict(BaseModel):
    risk: Risk
    family: ScamFamily
    headline_ms: str = Field(description="One sentence in Bahasa Malaysia for the senior")
    headline_en: str = Field(description="One sentence in English for the family")
    explanation: str = Field(description="2-4 sentences, plain language, cites evidence by number")
    evidence: list[Evidence] = Field(default_factory=list)
    recommended_action: str = Field(description="Concrete next step, e.g. 'Do not transfer. Call NSRC 997.'")
    notify_family: bool
    escalate: bool = Field(description="True if high value + ambiguous evidence: send to the escalation tier")
    novelty_flags: list[str] = Field(default_factory=list, description="e.g. 'payee never seen before'")


class EscalationOpinion(BaseModel):
    """Second opinion from Nemotron 3 Ultra on hard cases."""
    agree_with_verdict: bool
    risk: Risk
    reasoning_summary: str
    additional_action: str


class CaseResult(BaseModel):
    case_id: str
    household_id: str
    text: str
    triage: Triage
    plan: VerificationPlan | None = None
    verdict: Verdict
    escalation: EscalationOpinion | None = None
    models_used: dict[str, str] = Field(default_factory=dict)
    usage: dict[str, int] = Field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: int = 0
    tool_calls: list[dict] = Field(default_factory=list)
