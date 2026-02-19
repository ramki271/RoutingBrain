"""
Risk Classifier — deterministic heuristic pass, runs BEFORE RoutingBrain.

Risk level constrains which PROVIDER TYPES are allowed — not the model tier.
This is not advisory — it is a hard gate.

Data residency model:
  ┌──────────────────┬──────────────────────────────────────────────────────┐
  │ Provider type    │ Data residency                                       │
  ├──────────────────┼──────────────────────────────────────────────────────┤
  │ OSS (Ollama/     │ Stays on YOUR infra — safe for ALL data including    │
  │ vLLM)            │ PII, PHI, regulated. Routing is quality/cost only.  │
  ├──────────────────┼──────────────────────────────────────────────────────┤
  │ Direct commercial│ Data leaves your infra to Anthropic/OpenAI/Google   │
  │ API              │ servers — NOT safe for regulated/PII/PHI without BAA│
  ├──────────────────┼──────────────────────────────────────────────────────┤
  │ Compliant cloud  │ AWS Bedrock, Azure AI Foundry — data stays in your  │
  │ (Bedrock/Azure)  │ cloud account with BAA/DPA — safe for regulated      │
  └──────────────────┴──────────────────────────────────────────────────────┘

Risk levels and their constraints:
  low        → Any provider allowed (OSS, direct commercial, compliant cloud)
  medium     → OSS allowed + compliant cloud; direct commercial allowed but logged
  high       → OSS allowed + compliant cloud only; direct commercial APIs FORBIDDEN
  regulated  → OSS allowed + compliant cloud only; direct commercial APIs FORBIDDEN + audit required
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from app.models.request import ChatCompletionRequest


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    REGULATED = "regulated"


# Provider categories — populated from config/providers
# OSS = self-hosted on your infra, data never leaves
OSS_PROVIDERS = {"ollama", "vllm"}
# Direct commercial = data leaves your infra to vendor
DIRECT_COMMERCIAL_PROVIDERS = {"anthropic", "openai", "gemini"}
# Compliant cloud = data stays in your cloud account (BAA/DPA covered)
COMPLIANT_CLOUD_PROVIDERS = {"bedrock", "azure"}  # Phase 2+


@dataclass
class RiskSignal:
    category: str
    matched_terms: List[str]
    weight: int  # 1=low, 2=medium, 3=high, 4=regulated


@dataclass
class RiskAssessment:
    risk_level: RiskLevel
    signals: List[RiskSignal] = field(default_factory=list)
    # Provider-type constraints (not model tier constraints)
    direct_commercial_forbidden: bool = False  # forbids Anthropic/OpenAI/Gemini direct APIs
    oss_forbidden: bool = False                # OSS is NEVER forbidden (self-hosted = safe)
    required_min_tier: str = "fast_cheap"      # still used for quality floor, not data residency
    audit_required: bool = False
    rationale: str = ""
    data_residency_note: str = ""


# ── Signal Definitions ────────────────────────────────────────────────────────

# Weight 4 — REGULATED: direct commercial APIs forbidden, OSS + compliant cloud only
# Rationale: PII/PHI/financial regulation requires data residency guarantees
REGULATED_PATTERNS = {
    "pii_phi": [
        r"\bssn\b", r"\bsocial security\b", r"\bdate of birth\b", r"\bdob\b",
        r"\bmedical record\b", r"\bpatient\b", r"\bdiagnos\w+\b", r"\bprescription\b",
        r"\bhealth insurance\b", r"\bhipaa\b", r"\bphi\b", r"\behr\b", r"\bemr\b",
        r"\bpii\b", r"\bpersonal identifiable\b",
    ],
    "financial_regulated": [
        r"\bsox\b", r"\bsarbanes\b", r"\bpci.?dss\b", r"\bpci\b",
        r"\bglba\b", r"\baml\b", r"\bkyc\b", r"\bfinra\b", r"\bsec filing\b",
        r"\baudited financial\b", r"\bregulatory filing\b",
    ],
    "legal_regulated": [
        r"\bgdpr\b", r"\bccpa\b", r"\bcopa\b", r"\bhipaa compliance\b",
        r"\bdata protection\b", r"\bprivacy regulation\b", r"\bcompliance report\b",
    ],
}

# Weight 3 — HIGH: direct commercial APIs forbidden, prefer OSS + compliant cloud
# Rationale: legal/financial/exec data shouldn't leave org infra without explicit approval
HIGH_RISK_PATTERNS = {
    "legal_contract": [
        r"\bcontract\b", r"\bagreement\b", r"\bindemnif\w+\b", r"\bliabilit\w+\b",
        r"\bnda\b", r"\bnon.?disclosure\b", r"\bterms of service\b", r"\bterms and conditions\b",
        r"\blegal counsel\b", r"\blitigation\b", r"\bsettlement\b", r"\barbitration\b",
        r"\bintellectual property\b", r"\bpatent\b", r"\btrademark\b", r"\bcopyright\b",
    ],
    "financial_sensitive": [
        r"\bsalary\b", r"\bcompensation\b", r"\bpayroll\b",
        r"\bm&a\b", r"\bacquisition\b", r"\bmerger\b", r"\bvaluation\b",
        r"\binvestor\b", r"\bfundraising\b", r"\bterm sheet\b",
        r"\bcap table\b", r"\bequity\b", r"\bvesting\b",
    ],
    "executive_comms": [
        r"\bceo\b", r"\bcto\b", r"\bcfo\b", r"\bboard of directors\b",
        r"\bc-suite\b", r"\bconfidential\b",
        r"\bproprietary\b", r"\btrade secret\b",
    ],
    "security_sensitive": [
        r"\bpassword\b", r"\bcredential\b", r"\bapi.?key\b", r"\bsecret.?key\b",
        r"\bprivate.?key\b", r"\baccess.?token\b", r"\bencryption.?key\b",
        r"\bvulnerabilit\w+\b", r"\bexploit\b", r"\bpen.?test\b", r"\bpenetration test\b",
    ],
}

# Weight 2 — MEDIUM: direct commercial APIs allowed but logged; OSS preferred
# Rationale: business-sensitive but no hard regulatory requirement
MEDIUM_RISK_PATTERNS = {
    "customer_data": [
        r"\bcustomer\b", r"\buser data\b", r"\bpersonal data\b",
        r"\bemail address\b", r"\bphone number\b",
        r"\baccount\b", r"\bsubscriber\b",
    ],
    "business_sensitive": [
        r"\bpipeline\b", r"\bforecast\b", r"\brevenue\b", r"\bchurn\b",
        r"\bkpi\b", r"\bperformance review\b",
        r"\bemployee\b", r"\bhiring\b", r"\btermination\b",
    ],
    "external_comms": [
        r"\bproposal\b", r"\bpitch\b",
        r"\bclient\b", r"\bprospect\b", r"\bpartner\b",
        r"\bpress release\b", r"\bannouncement\b",
    ],
}

# Compile all patterns once at module load
def _compile(patterns: dict) -> dict:
    return {
        cat: [re.compile(p, re.IGNORECASE) for p in terms]
        for cat, terms in patterns.items()
    }

_REGULATED_RE = _compile(REGULATED_PATTERNS)
_HIGH_RE = _compile(HIGH_RISK_PATTERNS)
_MEDIUM_RE = _compile(MEDIUM_RISK_PATTERNS)


def _scan(text: str, compiled: dict, category_prefix: str, weight: int) -> List[RiskSignal]:
    signals = []
    for category, patterns in compiled.items():
        matched = [p.pattern for p in patterns if p.search(text)]
        if matched:
            signals.append(RiskSignal(
                category=f"{category_prefix}.{category}",
                matched_terms=matched[:5],
                weight=weight,
            ))
    return signals


def is_provider_allowed(provider: str, assessment: "RiskAssessment") -> bool:
    """
    Returns True if the given provider is allowed for this risk level.
    Called by PolicyEngine when selecting from fallback chains.
    """
    if provider in OSS_PROVIDERS:
        return True  # OSS is always allowed — data never leaves your infra
    if provider in COMPLIANT_CLOUD_PROVIDERS:
        return True  # Bedrock/Azure have BAA/DPA — safe for regulated
    if provider in DIRECT_COMMERCIAL_PROVIDERS:
        return not assessment.direct_commercial_forbidden
    return True  # unknown providers: allow and let it fail at call time


def assess(request: ChatCompletionRequest) -> RiskAssessment:
    """
    Runs a fast heuristic risk scan on the full message text.
    Returns a RiskAssessment with level, provider constraints, and audit flag.
    """
    full_text = " ".join(msg.text_content() for msg in request.messages)

    regulated_signals = _scan(full_text, _REGULATED_RE, "regulated", 4)
    high_signals = _scan(full_text, _HIGH_RE, "high", 3)
    medium_signals = _scan(full_text, _MEDIUM_RE, "medium", 2)

    all_signals = regulated_signals + high_signals + medium_signals

    if regulated_signals:
        return RiskAssessment(
            risk_level=RiskLevel.REGULATED,
            signals=all_signals,
            direct_commercial_forbidden=True,
            oss_forbidden=False,  # OSS is self-hosted — data stays on your infra
            required_min_tier="balanced",  # quality floor for regulated content
            audit_required=True,
            rationale=f"Regulated content detected: {', '.join(s.category for s in regulated_signals)}",
            data_residency_note=(
                "Direct commercial APIs (Anthropic/OpenAI/Gemini) forbidden — data must stay on-prem. "
                "Use self-hosted OSS or AWS Bedrock / Azure AI Foundry with BAA."
            ),
        )

    if high_signals:
        return RiskAssessment(
            risk_level=RiskLevel.HIGH,
            signals=all_signals,
            direct_commercial_forbidden=True,
            oss_forbidden=False,  # OSS is self-hosted — safe
            required_min_tier="balanced",
            audit_required=True,
            rationale=f"High-risk content detected: {', '.join(s.category for s in high_signals)}",
            data_residency_note=(
                "Sensitive business content — direct commercial APIs forbidden. "
                "Use self-hosted OSS or compliant cloud (Bedrock/Azure)."
            ),
        )

    if medium_signals:
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            signals=all_signals,
            direct_commercial_forbidden=False,  # allowed but logged
            oss_forbidden=False,
            required_min_tier="fast_cheap",
            audit_required=False,
            rationale=f"Business-sensitive content detected: {', '.join(s.category for s in medium_signals)}",
            data_residency_note=(
                "Commercial APIs allowed — consider self-hosted OSS for cost savings and data control."
            ),
        )

    return RiskAssessment(
        risk_level=RiskLevel.LOW,
        signals=[],
        direct_commercial_forbidden=False,
        oss_forbidden=False,
        required_min_tier="fast_cheap",
        audit_required=False,
        rationale="No sensitive signals detected — all providers available",
        data_residency_note="",
    )
