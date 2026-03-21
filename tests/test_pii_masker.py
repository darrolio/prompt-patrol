"""Tests for PII masking module."""
import pytest

from prompt_review.services.pii_masker import mask_pii


class TestSSN:
    def test_dashed_ssn(self):
        assert "XXX-XX-XXXX" in mask_pii("my ssn is 436-23-3422")

    def test_spaced_ssn(self):
        assert "XXX-XX-XXXX" in mask_pii("ssn: 436 23 3422")

    def test_does_not_mask_non_ssn(self):
        # Version numbers, zip codes, etc. should not be masked
        result = mask_pii("version 1.2.3")
        assert "1.2.3" in result


class TestCreditCard:
    def test_visa(self):
        assert "[CREDIT_CARD_REDACTED]" in mask_pii("card: 4111-1111-1111-1111")

    def test_visa_no_dashes(self):
        assert "[CREDIT_CARD_REDACTED]" in mask_pii("card: 4111111111111111")

    def test_mastercard(self):
        assert "[CREDIT_CARD_REDACTED]" in mask_pii("mc: 5500 0000 0000 0004")

    def test_amex(self):
        assert "[CREDIT_CARD_REDACTED]" in mask_pii("amex: 3782 822463 10005")


class TestEmail:
    def test_simple_email(self):
        assert "[EMAIL_REDACTED]" in mask_pii("contact john.doe@example.com please")

    def test_email_with_plus(self):
        assert "[EMAIL_REDACTED]" in mask_pii("send to user+tag@company.org")

    def test_does_not_mask_non_email(self):
        result = mask_pii("use the @ operator")
        assert "@" in result


class TestPhone:
    def test_parenthesized(self):
        assert "[PHONE_REDACTED]" in mask_pii("call (555) 123-4567")

    def test_dashed(self):
        assert "[PHONE_REDACTED]" in mask_pii("phone: 555-123-4567")

    def test_dotted(self):
        assert "[PHONE_REDACTED]" in mask_pii("fax: 555.123.4567")

    def test_with_country_code(self):
        assert "[PHONE_REDACTED]" in mask_pii("call +1-555-123-4567")


class TestAWSKeys:
    def test_access_key_id(self):
        assert "[AWS_KEY_REDACTED]" in mask_pii("key: AKIAIOSFODNN7EXAMPLE")

    def test_does_not_mask_short_string(self):
        result = mask_pii("AKIA is a prefix")
        assert "AKIA is a prefix" == result


class TestAPIKeys:
    def test_anthropic_key(self):
        assert "[API_KEY_REDACTED]" in mask_pii("key: sk-ant-api03-abcdefghijklmnopqrstuvwxyz")

    def test_github_pat(self):
        assert "[GITHUB_TOKEN_REDACTED]" in mask_pii("token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn")

    def test_slack_token(self):
        assert "[SLACK_TOKEN_REDACTED]" in mask_pii("token: xoxb-123456789012-1234567890123-abcdefghijklmnop")

    def test_bearer_token(self):
        assert "[TOKEN_REDACTED]" in mask_pii("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")


class TestIPAddresses:
    def test_public_ip(self):
        assert "[IP_REDACTED]" in mask_pii("server at 203.0.113.42")

    def test_preserves_localhost(self):
        result = mask_pii("connect to 127.0.0.1:5432")
        assert "127.0.0.1" in result

    def test_preserves_private_192(self):
        result = mask_pii("network 192.168.1.1")
        assert "192.168.1.1" in result

    def test_preserves_private_10(self):
        result = mask_pii("subnet 10.0.0.1")
        assert "10.0.0.1" in result


class TestEdgeCases:
    def test_empty_string(self):
        assert mask_pii("") == ""

    def test_none_returns_none(self):
        assert mask_pii(None) is None

    def test_no_pii(self):
        text = "please refactor the database module to use async sessions"
        assert mask_pii(text) == text

    def test_multiple_pii_types(self):
        text = "email john@acme.com, ssn 123-45-6789, call 555-123-4567"
        result = mask_pii(text)
        assert "[EMAIL_REDACTED]" in result
        assert "XXX-XX-XXXX" in result
        assert "[PHONE_REDACTED]" in result
        assert "john@acme.com" not in result
        assert "123-45-6789" not in result
        assert "555-123-4567" not in result

    def test_preserves_surrounding_text(self):
        result = mask_pii("before john@test.com after")
        assert result == "before [EMAIL_REDACTED] after"
