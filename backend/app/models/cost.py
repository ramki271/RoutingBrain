from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModelPricing(BaseModel):
    model_id: str
    provider: str
    input_cost_per_mtok: float  # USD per million input tokens
    output_cost_per_mtok: float  # USD per million output tokens
    tier: str
    context_window: int = 0
    supports_streaming: bool = True
    supports_tools: bool = True


class CostRecord(BaseModel):
    request_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    department: str = "general"
    model_requested: str
    model_used: str
    provider: str
    task_type: str
    complexity: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    meta_llm_cost_usd: float
    fallback_used: bool = False
    latency_ms: int = 0
    created_at: datetime = None

    def model_post_init(self, __context):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
