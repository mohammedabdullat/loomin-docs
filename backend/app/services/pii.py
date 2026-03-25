"""PII sanitization interceptor — masks sensitive patterns before they reach the LLM."""
import re
from typing import List, Tuple

# Pattern name, regex, replacement
PII_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN-REDACTED]"),
    ("Email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL-REDACTED]"),
    ("Credit Card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[CC-REDACTED]"),
    ("Phone (US)", re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE-REDACTED]"),
    ("API Key", re.compile(r"\b(?:sk|pk|api|key|token)[-_][A-Za-z0-9]{20,}\b", re.IGNORECASE), "[APIKEY-REDACTED]"),
    ("AWS Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWSKEY-REDACTED]"),
    ("Bearer Token", re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [TOKEN-REDACTED]"),
    ("IP Address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP-REDACTED]"),
]


def sanitize_text(text: str) -> Tuple[str, List[str]]:
    """
    Scan text for PII patterns and mask them.

    Returns:
        (sanitized_text, list_of_redaction_labels)
    """
    redactions: List[str] = []
    sanitized = text

    for name, pattern, replacement in PII_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            redactions.extend([f"{name}: {m}" for m in matches])
            sanitized = pattern.sub(replacement, sanitized)

    return sanitized, redactions


def sanitize_for_llm(prompt: str) -> str:
    """Convenience wrapper that returns only the sanitized text."""
    sanitized, _ = sanitize_text(prompt)
    return sanitized
