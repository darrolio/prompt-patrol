"""
PII masking module for Prompt Patrol.

Detects and masks personally identifiable information (PII) and secrets
in text before storage. Used as a safety net on the server side; the hook
script has its own copy for client-side masking before data leaves the
developer's machine.
"""
import re

# Compiled patterns: (regex, replacement)
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # AWS Access Key IDs (always start with AKIA, 20 chars)
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS_KEY_REDACTED]"),

    # AWS Secret Access Keys (40 chars base64-ish, preceded by common context)
    (re.compile(r"(?<=[\s:='\"])[A-Za-z0-9/+=]{40}(?=[\s'\",$])"), "[AWS_SECRET_REDACTED]"),

    # Generic API keys/tokens: sk-ant-, sk-proj-, sk-live-, sk-test-, ghp_, gho_, github_pat_, xoxb-, xoxp-
    (re.compile(r"\b(sk-(?:ant|proj|live|test)-[A-Za-z0-9_-]{20,})\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\b(ghp_[A-Za-z0-9]{36,})\b"), "[GITHUB_TOKEN_REDACTED]"),
    (re.compile(r"\b(gho_[A-Za-z0-9]{36,})\b"), "[GITHUB_TOKEN_REDACTED]"),
    (re.compile(r"\b(github_pat_[A-Za-z0-9_]{22,})\b"), "[GITHUB_TOKEN_REDACTED]"),
    (re.compile(r"\b(xox[bp]-[A-Za-z0-9-]{24,})\b"), "[SLACK_TOKEN_REDACTED]"),

    # Bearer tokens in headers (long base64 strings)
    (re.compile(r"(Bearer\s+)([A-Za-z0-9._-]{20,})", re.IGNORECASE), r"\1[TOKEN_REDACTED]"),

    # SSNs: 123-45-6789 or 123 45 6789
    (re.compile(r"\b(\d{3})[-\s](\d{2})[-\s](\d{4})\b"), "XXX-XX-XXXX"),

    # Credit card numbers: 13-19 digits with optional separators
    # Amex: 3xx 4-6-5 grouping
    (re.compile(r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b"), "[CREDIT_CARD_REDACTED]"),
    # Visa, Mastercard, Discover: 4-4-4-4 grouping
    (re.compile(
        r"\b(?:4\d{3}|5[1-5]\d{2}|6(?:011|5\d{2}))"
        r"[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{1,4}\b"
    ), "[CREDIT_CARD_REDACTED]"),

    # US phone numbers: (555) 123-4567, 555-123-4567, 555.123.4567, +1-555-123-4567
    (re.compile(
        r"(?:\+?1[-.\s]?)?"           # optional +1 prefix
        r"\(?\d{3}\)?[-.\s]?"         # area code
        r"\d{3}[-.\s]?"              # exchange
        r"\d{4}\b"                   # subscriber
    ), "[PHONE_REDACTED]"),

    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL_REDACTED]"),

    # IPv4 addresses (not localhost/private ranges commonly used in config)
    (re.compile(
        r"\b(?!(?:127\.0\.0\.1|0\.0\.0\.0|localhost|10\.\d|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.))"
        r"(?:\d{1,3}\.){3}\d{1,3}\b"
    ), "[IP_REDACTED]"),
]


def mask_pii(text: str) -> str:
    """Mask PII and secrets in the given text.

    Returns the text with all detected PII replaced by redaction placeholders.
    If masking fails for any reason, returns the original text unchanged.
    """
    if not text:
        return text
    try:
        for pattern, replacement in _PATTERNS:
            text = pattern.sub(replacement, text)
        return text
    except Exception:
        return text
