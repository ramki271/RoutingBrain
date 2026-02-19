import asyncio
import json
from pathlib import Path
from typing import Optional

import anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.routing import (
    ClassificationResult,
    ClassifiedBy,
    Complexity,
    Department,
    PreAnalysis,
    TaskType,
)

logger = get_logger(__name__)

_SYSTEM_PROMPT_CACHE: Optional[str] = None


def _load_system_prompt(path: str) -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        p = Path(path)
        if p.exists():
            _SYSTEM_PROMPT_CACHE = p.read_text()
        else:
            _SYSTEM_PROMPT_CACHE = _default_system_prompt()
    return _SYSTEM_PROMPT_CACHE


def _default_system_prompt() -> str:
    return """You are RoutingBrain, an expert LLM request classifier.
Your job is to analyze a user's request and return a structured JSON classification.

Valid task_type values:
- code_generation: Writing new code, functions, classes, scripts, QA automation scripts (Playwright/Selenium/Cypress)
- code_review: Reviewing, auditing, or giving feedback on existing code
- test_generation: Writing unit tests, integration tests, test cases, test suites
- debugging: Finding and fixing bugs, errors, exceptions, or unexpected behavior
- architecture_design: System design, component design, trade-off analysis, diagrams
- documentation: Writing READMEs, docstrings, API docs, technical explanations
- requirement_analysis: Evaluating requirements, user stories, specs for completeness/ambiguity/feasibility
- question_answer: General questions, how-to, explanations
- data_analysis: Analyzing data, logs, SQL queries, metrics, reports
- math_reasoning: Mathematical proofs, algorithms, complexity analysis, optimization
- general: Anything that doesn't fit above

Valid complexity values: simple, medium, complex
Valid department values: rd, sales, marketing, hr, finance, general
Valid estimated_output_length values: short, medium, long

Return ONLY valid JSON, no explanation, no markdown fences:
{
  "task_type": "<value>",
  "complexity": "<value>",
  "department": "<value>",
  "required_capability": ["<capability1>", "<capability2>"],
  "estimated_output_length": "<value>",
  "confidence": <0.0-1.0>,
  "routing_rationale": "<1 sentence explanation>"
}"""


def _build_user_message(pre_analysis: PreAnalysis, message_excerpt: str) -> str:
    return f"""Classify this LLM request:

Pre-analysis signals:
- Estimated tokens: {pre_analysis.estimated_tokens}
- Has code blocks: {pre_analysis.has_code_blocks}
- Detected languages: {pre_analysis.detected_languages}
- Detected keywords: {pre_analysis.detected_keywords}
- Department hint: {pre_analysis.department_hint or 'none'}
- Conversation turns: {pre_analysis.conversation_turns}
- Heuristic task type: {pre_analysis.heuristic_task_type}
- Heuristic complexity: {pre_analysis.heuristic_complexity}

Message excerpt (first 1000 chars):
{message_excerpt[:1000]}

Return JSON classification."""


def _heuristic_fallback(pre_analysis: PreAnalysis) -> ClassificationResult:
    """Fallback when RoutingBrain times out or returns low confidence."""
    return ClassificationResult(
        task_type=pre_analysis.heuristic_task_type or TaskType.GENERAL,
        complexity=pre_analysis.heuristic_complexity or Complexity.MEDIUM,
        department=Department(pre_analysis.department_hint or "general")
        if pre_analysis.department_hint in Department._value2member_map_
        else Department.GENERAL,
        required_capability=[],
        estimated_output_length="medium",
        confidence=0.5,
        routing_rationale="Heuristic fallback — RoutingBrain unavailable or low confidence",
        classified_by=ClassifiedBy.HEURISTIC_FALLBACK,
    )


class RoutingBrain:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.routing_brain_model
        self.timeout = settings.routing_brain_timeout_seconds
        self.confidence_threshold = settings.routing_brain_confidence_threshold

    async def classify(
        self, pre_analysis: PreAnalysis, message_excerpt: str
    ) -> ClassificationResult:
        if not self.settings.anthropic_api_key:
            logger.warning("routing_brain_skipped", reason="no_anthropic_key")
            return _heuristic_fallback(pre_analysis)

        system_prompt = _load_system_prompt(self.settings.meta_llm_system_prompt_path)
        user_message = _build_user_message(pre_analysis, message_excerpt)

        try:
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    temperature=0.1,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                ),
                timeout=self.timeout,
            )

            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)

            result = ClassificationResult(
                task_type=TaskType(data.get("task_type", "general")),
                complexity=Complexity(data.get("complexity", "medium")),
                department=Department(data.get("department", "general")),
                required_capability=data.get("required_capability", []),
                estimated_output_length=data.get("estimated_output_length", "medium"),
                confidence=float(data.get("confidence", 0.5)),
                routing_rationale=data.get("routing_rationale", ""),
                classified_by=ClassifiedBy.META_LLM,
            )

            if result.confidence < self.confidence_threshold:
                logger.warning(
                    "routing_brain_low_confidence",
                    confidence=result.confidence,
                    threshold=self.confidence_threshold,
                )
                return _heuristic_fallback(pre_analysis)

            logger.info(
                "routing_brain_classified",
                task_type=result.task_type,
                complexity=result.complexity,
                confidence=result.confidence,
            )
            return result

        except asyncio.TimeoutError:
            logger.warning("routing_brain_timeout", timeout_seconds=self.timeout)
            return _heuristic_fallback(pre_analysis)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("routing_brain_parse_error", error=str(e))
            return _heuristic_fallback(pre_analysis)
        except Exception as e:
            logger.error("routing_brain_error", error=str(e))
            return _heuristic_fallback(pre_analysis)
