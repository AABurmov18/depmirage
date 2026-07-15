"""Hardcoded-secret scanning for .py source files.

Detects OpenAI-style keys, AWS access keys, secret-looking assignments, and
generic high-entropy string literals via Shannon entropy. Line numbers are
reported; the secret value is ALWAYS masked (first/last 4 chars only).
"""

from __future__ import annotations

import math
import re
from typing import List, NamedTuple

# --- detectors ------------------------------------------------------------

# OpenAI keys: classic "sk-..." and project keys "sk-proj-...".
_OPENAI = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")
# AWS access key id.
_AWS = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
# GitHub tokens (bonus, cheap and common in demos).
_GITHUB = re.compile(r"\bghp_[A-Za-z0-9]{36}\b")
# Slack tokens.
_SLACK = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")

# Assignment to a secret-looking variable name.
_SECRET_ASSIGN = re.compile(
    r"""(?P<name>\w*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY)\w*)\s*[:=]\s*"""
    r"""(?P<quote>['"])(?P<value>[^'"]{6,})(?P=quote)""",
    re.IGNORECASE,
)

# Any quoted string literal, for generic entropy scanning.
_QUOTED = re.compile(r"""(['"])(?P<value>[^'"\n]{20,})\1""")

# Thresholds tuned to catch real secrets while staying quiet on ordinary code.
_ENTROPY_MIN = 4.0        # bits/char; base64/hex secrets sit ~4.5-6.0
_ASSIGN_ENTROPY_MIN = 3.0  # lower bar when the var name already screams "secret"


class Finding(NamedTuple):
    file: str
    line: int
    kind: str
    masked: str


def shannon_entropy(s: str) -> float:
    """Shannon entropy in bits per character. Empty string -> 0.0."""
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    entropy = 0.0
    for c in counts.values():
        p = c / n
        entropy -= p * math.log2(p)
    return entropy


def mask(secret: str) -> str:
    """Mask the middle of a secret, showing only first/last 4 characters.

    Short secrets are fully masked so we never leak a usable value.
    """
    s = secret
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}{'*' * (len(s) - 8)}{s[-4:]}"


def _looks_like_prose(value: str) -> bool:
    """Heuristic: strings with spaces or many words are probably not secrets."""
    if " " in value.strip():
        return True
    return False


def scan_text(text: str, filename: str = "<text>") -> List[Finding]:
    """Scan source text and return secret findings with line numbers."""
    findings: List[Finding] = []
    seen = set()  # (line, masked) to avoid duplicate reports on one line

    for lineno, line in enumerate(text.splitlines(), start=1):
        # 1. High-confidence pattern detectors (report the matched token).
        for kind, pattern in (
            ("OpenAI API key", _OPENAI),
            ("AWS access key", _AWS),
            ("GitHub token", _GITHUB),
            ("Slack token", _SLACK),
        ):
            for m in pattern.finditer(line):
                _add(findings, seen, filename, lineno, kind, m.group(0))

        # 2. Secret-looking variable assignments.
        for m in _SECRET_ASSIGN.finditer(line):
            value = m.group("value")
            if _looks_like_prose(value):
                continue
            # Skip obvious placeholders.
            if value.lower() in {"changeme", "password", "your_key_here", "xxx"}:
                continue
            ent = shannon_entropy(value)
            if ent >= _ASSIGN_ENTROPY_MIN or len(value) >= 16:
                _add(findings, seen, filename, lineno,
                     "Hardcoded secret assignment", value)

        # 3. Generic high-entropy string literals.
        for m in _QUOTED.finditer(line):
            value = m.group("value")
            if _looks_like_prose(value):
                continue
            if shannon_entropy(value) >= _ENTROPY_MIN:
                _add(findings, seen, filename, lineno,
                     "High-entropy string", value)

    return findings


def scan_file(path: str) -> List[Finding]:
    """Scan a single .py file. Unreadable files yield no findings (no crash)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception:
        return []
    return scan_text(text, filename=path)


def _add(findings, seen, filename, lineno, kind, value):
    masked = mask(value)
    # Dedupe by (line, value): the first (highest-confidence) detector to match
    # a given value on a line wins, so one secret is reported once — not once
    # per detector that happens to overlap it.
    key = (lineno, masked)
    if key in seen:
        return
    seen.add(key)
    findings.append(Finding(file=filename, line=lineno, kind=kind, masked=masked))
