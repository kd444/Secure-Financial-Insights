"""PII detection and redaction for financial documents and LLM outputs.

Uses Microsoft Presidio for entity recognition with custom financial
entity patterns (account numbers, SSNs, routing numbers).
Falls back to regex-based detection when Presidio is unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class PIIEntityType(str, Enum):
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    ACCOUNT_NUMBER = "ACCOUNT_NUMBER"
    ROUTING_NUMBER = "ROUTING_NUMBER"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PERSON_NAME = "PERSON_NAME"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"


@dataclass
class PIIEntity:
    entity_type: PIIEntityType
    start: int
    end: int
    text: str
    confidence: float = 0.9


@dataclass
class RedactionResult:
    original_text: str
    redacted_text: str
    entities_found: list[PIIEntity] = field(default_factory=list)
    entity_count: int = 0
    was_redacted: bool = False


# Regex patterns for financial PII (fallback when Presidio unavailable)
PII_PATTERNS: dict[PIIEntityType, re.Pattern[str]] = {
    PIIEntityType.SSN: re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    PIIEntityType.CREDIT_CARD: re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    ),
    PIIEntityType.ACCOUNT_NUMBER: re.compile(
        r'\b(?:account\s*(?:number|#|no\.?)?[:.\s]*)\d{8,17}\b',
        re.IGNORECASE,
    ),
    PIIEntityType.ROUTING_NUMBER: re.compile(
        r'\b(?:routing\s*(?:number|#|no\.?)?[:.\s]*)\d{9}\b',
        re.IGNORECASE,
    ),
    PIIEntityType.EMAIL: re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ),
    PIIEntityType.PHONE: re.compile(
        r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    ),
}

# Redaction markers by entity type
REDACTION_MARKERS: dict[PIIEntityType, str] = {
    PIIEntityType.SSN: "[SSN_REDACTED]",
    PIIEntityType.CREDIT_CARD: "[CREDIT_CARD_REDACTED]",
    PIIEntityType.ACCOUNT_NUMBER: "[ACCOUNT_REDACTED]",
    PIIEntityType.ROUTING_NUMBER: "[ROUTING_REDACTED]",
    PIIEntityType.EMAIL: "[EMAIL_REDACTED]",
    PIIEntityType.PHONE: "[PHONE_REDACTED]",
    PIIEntityType.PERSON_NAME: "[NAME_REDACTED]",
    PIIEntityType.ADDRESS: "[ADDRESS_REDACTED]",
    PIIEntityType.DATE_OF_BIRTH: "[DOB_REDACTED]",
}


class PIIRedactor:
    """Detects and redacts PII from text using Presidio or regex fallback.

    In production, uses Microsoft Presidio with custom recognizers for
    financial entities. Falls back to regex patterns for development.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = settings.pii_detection_enabled
        self._use_presidio = False
        self._analyzer = None
        self._anonymizer = None

        if self._enabled:
            self._try_init_presidio()

    def _try_init_presidio(self) -> None:
        """Try to initialize Presidio analyzer and anonymizer."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine

            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
            self._use_presidio = True
            logger.info("presidio_initialized")
        except (ImportError, Exception) as e:
            logger.warning(
                "presidio_unavailable_using_regex_fallback",
                error=str(e),
            )
            self._use_presidio = False

    def redact(self, text: str) -> RedactionResult:
        """Detect and redact PII from text.

        Args:
            text: Input text to scan for PII.

        Returns:
            RedactionResult with redacted text and entity details.
        """
        if not self._enabled:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                was_redacted=False,
            )

        if self._use_presidio:
            return self._redact_with_presidio(text)
        return self._redact_with_regex(text)

    def detect_only(self, text: str) -> list[PIIEntity]:
        """Detect PII without redacting. Used for audit logging."""
        if not self._enabled:
            return []

        if self._use_presidio:
            return self._detect_with_presidio(text)
        return self._detect_with_regex(text)

    def _redact_with_presidio(self, text: str) -> RedactionResult:
        """Redact using Presidio engine with financial entity support."""
        from presidio_analyzer import RecognizerResult
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        try:
            results = self._analyzer.analyze(
                text=text,
                language="en",
                entities=[
                    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                    "CREDIT_CARD", "US_SSN", "US_BANK_NUMBER",
                ],
            )

            if not results:
                return RedactionResult(
                    original_text=text,
                    redacted_text=text,
                    was_redacted=False,
                )

            # Also run regex for financial-specific patterns
            regex_entities = self._detect_with_regex(text)

            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[PII_REDACTED]"})},
            )

            entities = [
                PIIEntity(
                    entity_type=self._map_presidio_type(r.entity_type),
                    start=r.start,
                    end=r.end,
                    text=text[r.start:r.end],
                    confidence=r.score,
                )
                for r in results
            ]
            entities.extend(regex_entities)

            redacted_text = anonymized.text

            # Apply regex-based redactions on top
            for entity in regex_entities:
                marker = REDACTION_MARKERS.get(entity.entity_type, "[REDACTED]")
                redacted_text = redacted_text.replace(entity.text, marker)

            return RedactionResult(
                original_text=text,
                redacted_text=redacted_text,
                entities_found=entities,
                entity_count=len(entities),
                was_redacted=True,
            )

        except Exception as e:
            logger.error("presidio_redaction_error", error=str(e))
            return self._redact_with_regex(text)

    def _redact_with_regex(self, text: str) -> RedactionResult:
        """Regex-based PII redaction (fallback)."""
        entities = self._detect_with_regex(text)

        if not entities:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                was_redacted=False,
            )

        redacted = text
        # Sort by position descending so replacements don't shift indices
        for entity in sorted(entities, key=lambda e: e.start, reverse=True):
            marker = REDACTION_MARKERS.get(entity.entity_type, "[REDACTED]")
            redacted = redacted[:entity.start] + marker + redacted[entity.end:]

        return RedactionResult(
            original_text=text,
            redacted_text=redacted,
            entities_found=entities,
            entity_count=len(entities),
            was_redacted=True,
        )

    def _detect_with_regex(self, text: str) -> list[PIIEntity]:
        """Detect PII using regex patterns."""
        entities: list[PIIEntity] = []
        for entity_type, pattern in PII_PATTERNS.items():
            for match in pattern.finditer(text):
                entities.append(
                    PIIEntity(
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        text=match.group(),
                    )
                )
        return entities

    def _detect_with_presidio(self, text: str) -> list[PIIEntity]:
        """Detect PII using Presidio engine."""
        try:
            results = self._analyzer.analyze(text=text, language="en")
            return [
                PIIEntity(
                    entity_type=self._map_presidio_type(r.entity_type),
                    start=r.start,
                    end=r.end,
                    text=text[r.start:r.end],
                    confidence=r.score,
                )
                for r in results
            ]
        except Exception:
            return self._detect_with_regex(text)

    @staticmethod
    def _map_presidio_type(presidio_type: str) -> PIIEntityType:
        mapping = {
            "PERSON": PIIEntityType.PERSON_NAME,
            "EMAIL_ADDRESS": PIIEntityType.EMAIL,
            "PHONE_NUMBER": PIIEntityType.PHONE,
            "CREDIT_CARD": PIIEntityType.CREDIT_CARD,
            "US_SSN": PIIEntityType.SSN,
            "US_BANK_NUMBER": PIIEntityType.ACCOUNT_NUMBER,
        }
        return mapping.get(presidio_type, PIIEntityType.PERSON_NAME)
