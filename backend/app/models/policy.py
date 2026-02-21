from typing import Dict, List, Optional

from pydantic import BaseModel


class RoutingRule(BaseModel):
    name: str
    task_type: Optional[str] = None           # None = match all
    complexity: Optional[str] = None          # None = match all
    required_capability: Optional[List[str]] = None
    primary_model: str
    provider: str = ""   # resolved from virtual registry if empty
    fallback_models: List[str] = []
    model_tier: str
    rationale: str = ""


class BudgetControls(BaseModel):
    daily_limit_usd_per_user: Optional[float] = None
    daily_limit_usd_per_tenant: Optional[float] = None
    max_tier: Optional[str] = None  # Static cap, e.g. "balanced" for MVP budget control
    downgrade_at_percent: float = 80.0   # Downgrade tier when >80% budget used
    force_cheap_at_percent: float = 100.0  # Force fast_cheap when >100%


class DepartmentPolicy(BaseModel):
    tenant_id: Optional[str] = None  # Optional tenant scope; None means global policy
    department: str
    version: str = "1.0"
    description: str = ""
    rules: List[RoutingRule]
    budget_controls: BudgetControls = BudgetControls()
    default_rule: Optional[RoutingRule] = None
