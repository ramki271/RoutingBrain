import re
from typing import List, Optional

import tiktoken

from app.models.request import ChatCompletionRequest
from app.models.routing import Complexity, PreAnalysis, TaskType

# Keyword → task type signals
TASK_KEYWORDS: dict[TaskType, List[str]] = {
    TaskType.CODE_GENERATION: [
        "write", "implement", "create", "build", "generate", "code", "function",
        "class", "module", "script", "program",
    ],
    TaskType.CODE_REVIEW: [
        "review", "check", "audit", "critique", "feedback", "improve",
        "issues", "problems", "suggestions",
    ],
    TaskType.TEST_GENERATION: [
        "test", "tests", "unit test", "integration test", "pytest", "jest",
        "test case", "test cases", "test suite", "spec", "coverage",
        "playwright", "selenium", "cypress", "e2e", "automation script",
        "qa automation", "automated test",
    ],
    TaskType.DEBUGGING: [
        "debug", "bug", "error", "exception", "traceback", "fix", "broken",
        "failing", "crash", "issue", "not working", "unexpected",
    ],
    TaskType.ARCHITECTURE_DESIGN: [
        "architecture", "design", "system design", "trade-off", "tradeoff",
        "scalability", "microservice", "diagram", "component", "pattern",
        "structure", "schema",
    ],
    TaskType.DOCUMENTATION: [
        "document", "documentation", "readme", "docstring", "comment",
        "explain", "describe", "summarize", "wiki", "api docs",
    ],
    TaskType.REQUIREMENT_ANALYSIS: [
        "requirement", "requirements", "spec", "specification", "user story",
        "acceptance criteria", "prd", "evaluate", "feasibility", "ambiguity",
        "completeness", "scope",
    ],
    TaskType.DATA_ANALYSIS: [
        "analyze", "analysis", "data", "dataset", "statistics", "metrics",
        "csv", "sql", "query", "log", "logs", "report",
    ],
    TaskType.MATH_REASONING: [
        "math", "algorithm", "complexity", "proof", "equation", "optimize",
        "big o", "dynamic programming", "graph", "tree", "sorting",
    ],
    TaskType.QUESTION_ANSWER: [
        "what is", "how does", "explain", "tell me", "can you", "?",
    ],
}

COMPLEXITY_HIGH_SIGNALS = [
    "complex", "advanced", "production", "scale", "distributed", "multi",
    "architecture", "system design", "novel", "algorithm", "optimize",
    "performance", "security", "enterprise",
]

COMPLEXITY_LOW_SIGNALS = [
    "simple", "basic", "quick", "small", "beginner", "starter",
    "boilerplate", "template", "hello world", "example",
]

CODE_BLOCK_RE = re.compile(r"```[\w]*\n[\s\S]+?```")
LANG_DETECT_RE = re.compile(r"```(python|javascript|typescript|go|rust|java|cpp|c\+\+|ruby|php|swift|kotlin|bash|sql)", re.IGNORECASE)

_tokenizer: Optional[tiktoken.Encoding] = None


def _get_tokenizer() -> tiktoken.Encoding:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def _estimate_tokens(text: str) -> int:
    try:
        return len(_get_tokenizer().encode(text))
    except Exception:
        return len(text) // 4


def _extract_full_text(request: ChatCompletionRequest) -> str:
    return " ".join(msg.text_content() for msg in request.messages).lower()


def analyze(request: ChatCompletionRequest) -> PreAnalysis:
    full_text = _extract_full_text(request)
    raw_text = " ".join(msg.text_content() for msg in request.messages)

    # Token count
    estimated_tokens = _estimate_tokens(raw_text)

    # Code detection
    has_code_blocks = bool(CODE_BLOCK_RE.search(raw_text))
    detected_languages = list({m.group(1).lower() for m in LANG_DETECT_RE.finditer(raw_text)})

    # Keyword matching
    detected_keywords: List[str] = []
    task_scores: dict[TaskType, int] = {}
    for task_type, keywords in TASK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in full_text)
        if score > 0:
            task_scores[task_type] = score
            detected_keywords.extend(kw for kw in keywords if kw in full_text)

    # Heuristic task type — highest scoring
    heuristic_task_type: Optional[TaskType] = None
    if task_scores:
        heuristic_task_type = max(task_scores, key=task_scores.get)

    # Department hint
    department_hint: Optional[str] = None
    if request.x_department:
        department_hint = request.x_department
    elif any(w in full_text for w in ["code", "debug", "architecture", "test", "deploy"]):
        department_hint = "rd"

    # Heuristic complexity
    high_signals = sum(1 for s in COMPLEXITY_HIGH_SIGNALS if s in full_text)
    low_signals = sum(1 for s in COMPLEXITY_LOW_SIGNALS if s in full_text)

    if estimated_tokens > 3000 or high_signals >= 2:
        heuristic_complexity = Complexity.COMPLEX
    elif estimated_tokens > 800 or high_signals >= 1:
        heuristic_complexity = Complexity.MEDIUM
    elif low_signals >= 1 or estimated_tokens < 200:
        heuristic_complexity = Complexity.SIMPLE
    else:
        heuristic_complexity = Complexity.MEDIUM

    # Conversation turns
    conversation_turns = sum(1 for m in request.messages if m.role in ("user", "assistant"))

    return PreAnalysis(
        estimated_tokens=estimated_tokens,
        has_code_blocks=has_code_blocks,
        detected_languages=detected_languages,
        detected_keywords=list(set(detected_keywords))[:10],
        department_hint=department_hint,
        conversation_turns=conversation_turns,
        heuristic_task_type=heuristic_task_type,
        heuristic_complexity=heuristic_complexity,
    )
