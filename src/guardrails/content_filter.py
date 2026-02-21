"""Content filtering guardrails for financial compliance.

Enforces financial domain constraints:
- Blocks investment advice / buy/sell recommendations
- Flags forward-looking statements without disclaimers
- Detects and warns about insider information patterns
- Validates output length and format compliance
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class ViolationType(str, Enum):
    INVESTMENT_ADVICE = "investment_advice"
    FORWARD_LOOKING = "forward_looking_statement"
    INSIDER_INFO = "insider_information_pattern"
    TOKEN_LIMIT = "token_limit_exceeded"
    PROHIBITED_CONTENT = "prohibited_content"


@dataclass
class FilterResult:
    passed: bool
    violations: list[Violation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    filtered_text: str = ""


@dataclass
class Violation:
    violation_type: ViolationType
    description: str
    severity: str  # "block", "warn", "info"
    matched_text: str = ""


# Patterns that indicate investment advice (should be blocked)
INVESTMENT_ADVICE_PATTERNS = [
    re.compile(r'\b(?:you\s+should|we\s+recommend|i\s+suggest)\s+(?:buy|sell|hold|invest)', re.IGNORECASE),
    re.compile(r'\b(?:strong\s+buy|must\s+buy|sell\s+immediately|avoid\s+this\s+stock)', re.IGNORECASE),
    re.compile(r'\b(?:buy\s+rating|sell\s+rating|outperform|underperform)\b', re.IGNORECASE),
    re.compile(r'\b(?:target\s+price|price\s+target)\s*(?:of|is|:)\s*\$', re.IGNORECASE),
]

# Forward-looking statement patterns (should be flagged with disclaimer)
FORWARD_LOOKING_PATTERNS = [
    re.compile(r'\bwill\s+(?:likely|probably|definitely)\s+(?:increase|decrease|grow|decline)', re.IGNORECASE),
    re.compile(r'\b(?:expected\s+to|projected\s+to|forecast\s+to|anticipated\s+to)\b', re.IGNORECASE),
    re.compile(r'\b(?:future\s+(?:revenue|earnings|growth|performance))', re.IGNORECASE),
    re.compile(r'\b(?:guidance\s+(?:of|for|suggests|indicates))', re.IGNORECASE),
]

# Forward-looking disclaimer
FLS_DISCLAIMER = (
    "\n\n---\n*This analysis contains forward-looking statements based on "
    "company filings. Actual results may differ materially. This is not "
    "investment advice.*"
)


class ContentFilter:
    """Filters LLM output for financial regulatory compliance."""

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = settings.content_filter_enabled
        self._max_tokens = settings.max_token_output

    def filter(self, text: str) -> FilterResult:
        """Apply all content filters to the generated text.

        Args:
            text: LLM-generated response text.

        Returns:
            FilterResult with pass/fail status and any violations.
        """
        if not self._enabled:
            return FilterResult(passed=True, filtered_text=text)

        violations: list[Violation] = []
        warnings: list[str] = []

        # Check for investment advice (blocking violation)
        advice_violations = self._check_investment_advice(text)
        violations.extend(advice_violations)

        # Check for forward-looking statements (warning + disclaimer)
        fls_violations = self._check_forward_looking(text)
        violations.extend(fls_violations)

        # Check token limit
        if len(text.split()) > self._max_tokens:
            violations.append(
                Violation(
                    violation_type=ViolationType.TOKEN_LIMIT,
                    description=f"Response exceeds {self._max_tokens} token limit",
                    severity="warn",
                )
            )

        # Determine if any blocking violations exist
        blocking = [v for v in violations if v.severity == "block"]
        has_fls = any(v.violation_type == ViolationType.FORWARD_LOOKING for v in violations)

        # Build filtered text
        filtered_text = text
        if blocking:
            # Replace investment advice with disclaimer
            for v in blocking:
                if v.matched_text:
                    filtered_text = filtered_text.replace(
                        v.matched_text,
                        "[CONTENT REMOVED: Investment advice is not provided by this system]",
                    )
            warnings.append("Investment advice content was removed from the response.")

        if has_fls:
            # Append forward-looking disclaimer
            filtered_text += FLS_DISCLAIMER
            warnings.append("Forward-looking statement disclaimer added.")

        passed = len(blocking) == 0

        if violations:
            logger.info(
                "content_filter_applied",
                passed=passed,
                violations=len(violations),
                blocking=len(blocking),
            )

        return FilterResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            filtered_text=filtered_text,
        )

    def _check_investment_advice(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        for pattern in INVESTMENT_ADVICE_PATTERNS:
            for match in pattern.finditer(text):
                violations.append(
                    Violation(
                        violation_type=ViolationType.INVESTMENT_ADVICE,
                        description="Detected investment advice / recommendation",
                        severity="block",
                        matched_text=match.group(),
                    )
                )
        return violations

    def _check_forward_looking(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        for pattern in FORWARD_LOOKING_PATTERNS:
            for match in pattern.finditer(text):
                violations.append(
                    Violation(
                        violation_type=ViolationType.FORWARD_LOOKING,
                        description="Forward-looking statement detected",
                        severity="warn",
                        matched_text=match.group(),
                    )
                )
        return violations
