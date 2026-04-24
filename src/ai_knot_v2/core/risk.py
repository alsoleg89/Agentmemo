"""RiskClass taxonomy and classification utilities."""

from __future__ import annotations

from typing import Literal

RiskClass = Literal[
    "safety",
    "identity",
    "finance",
    "legal",
    "medical",
    "commitment",
    "scheduling",
    "preference",
    "ambient",
]

_RISK_KEYWORDS: dict[str, list[str]] = {
    "safety": [
        "danger",
        "hazard",
        "emergency",
        "accident",
        "injury",
        "fire",
        "flood",
        "threat",
        "unsafe",
        "warning",
        "critical",
    ],
    "identity": [
        "name",
        "born",
        "age",
        "gender",
        "nationality",
        "identity",
        "address",
        "lives",
        "moved",
        "married",
        "divorced",
        "child",
        "parent",
        "sibling",
        "spouse",
        "partner",
    ],
    "finance": [
        "salary",
        "income",
        "wage",
        "earn",
        "budget",
        "debt",
        "loan",
        "invest",
        "spend",
        "cost",
        "price",
        "money",
        "bank",
        "account",
        "tax",
        "payment",
        "expense",
        "profit",
        "revenue",
        "savings",
    ],
    "legal": [
        "contract",
        "sue",
        "law",
        "legal",
        "court",
        "regulation",
        "comply",
        "license",
        "permit",
        "agreement",
        "sign",
        "obligation",
    ],
    "medical": [
        "doctor",
        "hospital",
        "diagnos",
        "disease",
        "condition",
        "medication",
        "prescription",
        "surgery",
        "symptom",
        "health",
        "treatment",
        "allergy",
        "illness",
        "sick",
        "injured",
        "pain",
        "therapy",
        "nurse",
    ],
    "commitment": [
        "promise",
        "commit",
        "guarantee",
        "will",
        "shall",
        "must",
        "agree",
        "oblig",
        "pledge",
        "swear",
        "vow",
        "confirm",
        "accept",
    ],
    "scheduling": [
        "meeting",
        "appointment",
        "schedule",
        "deadline",
        "event",
        "calendar",
        "remind",
        "due",
        "plan",
        "session",
        "call",
        "interview",
    ],
    "preference": [
        "like",
        "love",
        "prefer",
        "enjoy",
        "hate",
        "dislike",
        "want",
        "wish",
        "favorite",
        "favourite",
        "avoid",
        "interest",
    ],
}


def classify_risk(predicate: str, object_value: str | None) -> tuple[RiskClass, float]:
    """Classify risk class and severity from predicate + object text.

    Returns (risk_class, severity ∈ [0,1]).
    Severity is heuristic: safety=0.9, medical/finance/legal=0.7,
    commitment/scheduling=0.5, identity=0.4, preference/ambient=0.2.
    """
    text = f"{predicate} {object_value or ''}".lower()

    _SEVERITY: dict[str, float] = {
        "safety": 0.9,
        "medical": 0.7,
        "finance": 0.7,
        "legal": 0.7,
        "commitment": 0.5,
        "scheduling": 0.5,
        "identity": 0.4,
        "preference": 0.2,
        "ambient": 0.1,
    }

    scores: dict[str, int] = {k: 0 for k in _RISK_KEYWORDS}
    for cls, keywords in _RISK_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cls] += 1

    best_cls = max(scores, key=lambda k: scores[k])
    if scores[best_cls] == 0:
        return "ambient", 0.1

    return best_cls, _SEVERITY.get(best_cls, 0.2)  # type: ignore[return-value]
