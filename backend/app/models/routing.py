from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    DEBUGGING = "debugging"
    ARCHITECTURE_DESIGN = "architecture_design"
    DOCUMENTATION = "documentation"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    QUESTION_ANSWER = "question_answer"
    DATA_ANALYSIS = "data_analysis"
    MATH_REASONING = "math_reasoning"
    GENERAL = "general"


class Complexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ModelTier(str, Enum):
    FAST_CHEAP = "fast_cheap"
    BALANCED = "balanced"
    POWERFUL = "powerful"
    LOCAL = "local"


class Department(str, Enum):
    RD = "rd"
    SALES = "sales"
    MARKETING = "marketing"
    HR = "hr"
    FINANCE = "finance"
    GENERAL = "general"


class ClassifiedBy(str, Enum):
    META_LLM = "meta_llm"
    HEURISTIC_FALLBACK = "heuristic_fallback"


class PreAnalysis(BaseModel):
    estimated_tokens: int = 0
    has_code_blocks: bool = False
    detected_languages: List[str] = Field(default_factory=list)
    detected_keywords: List[str] = Field(default_factory=list)
    department_hint: Optional[str] = None
    conversation_turns: int = 0
    heuristic_task_type: Optional[TaskType] = None
    heuristic_complexity: Optional[Complexity] = None


class ClassificationResult(BaseModel):
    task_type: TaskType
    complexity: Complexity
    department: Department
    required_capability: List[str] = Field(default_factory=list)
    estimated_output_length: Literal["short", "medium", "long"] = "medium"
    confidence: float = Field(ge=0.0, le=1.0)
    routing_rationale: str = ""
    classified_by: ClassifiedBy = ClassifiedBy.META_LLM


class RoutingDecision(BaseModel):
    primary_model: str
    provider: str
    fallback_models: List[str] = Field(default_factory=list)
    model_tier: ModelTier
    cost_budget_applied: bool = False
    policy_name: str = ""
    rule_matched: str = ""


class RoutingOutcome(BaseModel):
    request_id: str
    actual_model_used: str
    actual_provider: str
    pre_analysis: PreAnalysis
    classification: ClassificationResult
    routing_decision: RoutingDecision
    risk_level: str = "low"
    risk_rationale: str = ""
    data_residency_note: str = ""
    audit_required: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    meta_llm_cost_usd: float = 0.0
    latency_ms: int = 0
    fallback_used: bool = False
    error: Optional[str] = None
