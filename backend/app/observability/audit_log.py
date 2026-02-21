"""
Immutable Audit Logger

Writes every routing decision to an append-only JSONL file.
Requirements (§4.2):
  - append-only writes, never mutate historical records
  - logs even if the provider call fails
  - includes identity, policy version, classification snapshot, cost estimate
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger
from app.models.routing import Department

logger = get_logger(__name__)

# Estimated cost per million tokens (input) by tier — used for cost estimation before DB
TIER_COST_ESTIMATE = {
    "fast_cheap": 0.0008,    # ~avg of haiku/gpt-4o-mini/gemini-flash
    "balanced":   0.0030,    # ~sonnet/gpt-4o
    "powerful":   0.0150,    # ~opus/o1
    "local":      0.0000,
}


class AuditLogger:
    """
    Append-only JSONL audit logger.
    Each line is a complete, self-contained routing decision record.
    Thread-safe via asyncio lock.
    """

    def __init__(self, log_path: str = "logs/audit.jsonl"):
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        logger.info("audit_logger_ready", path=str(self._path))

    async def log(self, record: dict) -> None:
        """Append a single audit record. Never raises — logs failures silently."""
        try:
            line = json.dumps(record, default=str) + "\n"
            async with self._lock:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line)
        except Exception as e:
            # Audit logging must never crash the request pipeline
            logger.error("audit_log_write_failed", error=str(e))

    def build_record(
        self,
        outcome,                    # RoutingOutcome
        tenant_id: Optional[str],
        user_id: Optional[str],
        policy_version: Optional[str],
    ) -> dict:
        """Build a complete, self-contained audit record from a RoutingOutcome."""
        # Estimate cost from token counts and tier
        tier = str(outcome.routing_decision.model_tier.value
                   if hasattr(outcome.routing_decision.model_tier, 'value')
                   else outcome.routing_decision.model_tier)
        cost_per_mtok = TIER_COST_ESTIMATE.get(tier, 0.003)
        estimated_cost_usd = round(
            (outcome.prompt_tokens + outcome.completion_tokens) / 1_000_000 * cost_per_mtok,
            6,
        )

        # Classification snapshot — the "why" behind the routing decision
        classification_snapshot = {
            "task_type": outcome.classification.task_type.value,
            "complexity": outcome.classification.complexity.value,
            "confidence": outcome.classification.confidence,
            "classified_by": outcome.classification.classified_by.value,
            "department": outcome.classification.department.value,
            "required_capability": outcome.classification.required_capability,
            "risk_signals": (
                outcome.classification_snapshot.risk_signals
                if getattr(outcome, "classification_snapshot", None) is not None
                else outcome.risk_signals
            ),
        }

        return {
            # Identity
            "request_id": outcome.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id or "unknown",
            "department": outcome.classification.department.value,
            "user_id": user_id or "unknown",

            # Policy
            "policy_version": policy_version or "unknown",
            "rule_matched": outcome.routing_decision.rule_matched,
            "policy_trace": [
                {"rule": t.rule, "result": t.result, "reason": t.reason}
                for t in outcome.policy_trace
            ],
            "constraints_applied": outcome.constraints_applied,

            # Risk
            "risk_level": outcome.risk_level,
            "risk_rationale": outcome.risk_rationale,
            "audit_required": outcome.audit_required,
            "data_residency_note": outcome.data_residency_note,

            # Classification
            "classification_snapshot": classification_snapshot,

            # Routing decision
            "model_selected": outcome.actual_model_used,
            "provider": outcome.actual_provider,
            "model_tier": tier,
            "fallback_used": outcome.fallback_used,

            # Performance + cost
            "latency_ms": outcome.latency_ms,
            "prompt_tokens": outcome.prompt_tokens,
            "completion_tokens": outcome.completion_tokens,
            "estimated_cost_usd": estimated_cost_usd,

            # Error
            "error": outcome.error,
        }

    def build_failure_record(
        self,
        request_id: str,
        tenant_id: Optional[str],
        user_id: Optional[str],
        department: Optional[str],
        error_code: str,
        error_message: str,
        governance_blocked: bool = False,
    ) -> dict:
        """Build a minimal audit record when routing fails before a RoutingOutcome exists."""
        dept = department if department in Department._value2member_map_ else "general"
        return {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id or "unknown",
            "department": dept,
            "user_id": user_id or "unknown",
            "policy_version": "unknown",
            "rule_matched": "none",
            "policy_trace": [],
            "constraints_applied": [],
            "risk_level": "unknown",
            "risk_rationale": "",
            "audit_required": governance_blocked,
            "data_residency_note": "",
            "classification_snapshot": None,
            "model_selected": "",
            "provider": "",
            "model_tier": "",
            "fallback_used": False,
            "latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost_usd": 0.0,
            "error": f"{error_code}: {error_message}",
        }
