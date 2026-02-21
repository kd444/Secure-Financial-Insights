"""Unit tests for PII detection and redaction."""

import pytest

from src.guardrails.pii_redactor import PIIRedactor, PIIEntityType


@pytest.fixture
def redactor():
    return PIIRedactor()


class TestPIIRedactor:
    def test_detect_ssn(self, redactor):
        text = "Employee SSN is 123-45-6789 for records."
        result = redactor.redact(text)
        assert result.was_redacted
        assert "[SSN_REDACTED]" in result.redacted_text
        assert "123-45-6789" not in result.redacted_text

    def test_detect_credit_card(self, redactor):
        text = "Payment card: 4111-1111-1111-1111 on file."
        result = redactor.redact(text)
        assert result.was_redacted
        assert "[CREDIT_CARD_REDACTED]" in result.redacted_text

    def test_detect_email(self, redactor):
        text = "Contact John at john.doe@example.com for details."
        result = redactor.redact(text)
        assert result.was_redacted
        assert "[EMAIL_REDACTED]" in result.redacted_text
        assert "john.doe@example.com" not in result.redacted_text

    def test_detect_phone(self, redactor):
        text = "Call us at (555) 123-4567 for more information."
        result = redactor.redact(text)
        assert result.was_redacted
        assert "[PHONE_REDACTED]" in result.redacted_text

    def test_detect_account_number(self, redactor):
        text = "Account number: 12345678901 for wire transfer."
        result = redactor.redact(text)
        assert result.was_redacted
        assert "[ACCOUNT_REDACTED]" in result.redacted_text

    def test_no_pii_passes_clean(self, redactor):
        text = "Revenue increased by 15% to $50 billion in Q4 2023."
        result = redactor.redact(text)
        assert not result.was_redacted
        assert result.redacted_text == text

    def test_multiple_pii_entities(self, redactor):
        text = (
            "Employee 123-45-6789 can be reached at "
            "john@example.com or (555) 123-4567."
        )
        result = redactor.redact(text)
        assert result.was_redacted
        assert result.entity_count >= 3

    def test_detect_only_returns_entities(self, redactor):
        text = "SSN: 123-45-6789, Email: test@test.com"
        entities = redactor.detect_only(text)
        assert len(entities) >= 2
        entity_types = [e.entity_type for e in entities]
        assert PIIEntityType.SSN in entity_types
        assert PIIEntityType.EMAIL in entity_types

    def test_financial_numbers_not_flagged(self, redactor):
        text = "Revenue was $394,328 million with a 45.2% gross margin."
        result = redactor.redact(text)
        assert not result.was_redacted
