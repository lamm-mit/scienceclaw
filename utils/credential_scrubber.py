"""
Credential scrubber: sanitizes sensitive data from strings before
they are printed, logged, or returned in error messages.
"""

import re

# Patterns that match credential-like strings
_PATTERNS = [
    # Bearer / Authorization header values
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-_\.]{20,}', re.IGNORECASE), r'\1[REDACTED]'),
    # api_key / token / secret / password in key=value or key: value form
    (re.compile(r'((?:api[_-]?key|token|secret|password|authorization)\s*[:=]\s*)[^\s,\'"}{>]+',
                re.IGNORECASE), r'\1[REDACTED]'),
    # Bare long hex strings (≥32 hex chars — typical API key format)
    (re.compile(r'\b[0-9a-fA-F]{32,}\b'), '[REDACTED]'),
    # Bare long base64-ish strings (≥40 chars of base64url alphabet)
    (re.compile(r'[A-Za-z0-9\-_]{40,}'), '[REDACTED]'),
    # JWT tokens (three base64url segments separated by dots)
    (re.compile(r'[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}'),
     '[REDACTED_JWT]'),
]


def scrub(text: str) -> str:
    """Return *text* with credential-like substrings replaced by [REDACTED]."""
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return '[non-string value redacted]'
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
