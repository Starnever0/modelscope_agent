from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalCase:
    case_id: str
    query: str
    expected_docids: List[str] = field(default_factory=list)
    reference_answer: Optional[str] = None
    bot_answer: Optional[str] = None
    user_rating: Optional[float] = None
    user_feedback: Optional[str] = None
    dataset_type: str = "qa"
    tags: List[str] = field(default_factory=list)
    difficulty: str = "easy"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalItemResult:
    case_id: str
    metrics: Dict[str, float]
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    items: List[EvalItemResult]
    summary: Dict[str, float]
