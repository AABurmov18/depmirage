"""Input parsing: requirements.txt dependency names and file discovery.

Everything here is pure, local, and network-free so it stays reliable on any
platform (Windows, macOS, Linux) with no C-extension dependencies.
"""

from __future__ import annotations

import os
import re
from typing import List

# Version specifiers and separators we strip to recover the bare package name.
# Order matters a little: we cut at the first specifier/marker character.
_SPEC_SPLIT = re.compile(r"[<>=!~;\[ ]")


def normalize_name(raw: str) -> str:
    """Return the canonical distribution name for a raw requirement token.

    Strips extras ("pkg[extra]"), version specifiers ("==1.0", ">=2"),
    environment markers ("; python_version<'3.8'") and surrounding whitespace.
    PyPI treats runs of -, _ and . as equivalent and is case-insensitive, so we
    lower-case but keep the separators as-is for display; callers that need the
    PyPI-normalized form use ``pypi_normalize``.
    """
    token = raw.strip()
    # Cut off inline comments if any slipped through.
    token = token.split("#", 1)[0].strip()
    # Split at the first specifier/extra/marker character.
    name = _SPEC_SPLIT.split(token, 1)[0].strip()
    return name


def pypi_normalize(name: str) -> str:
    """PEP 503 normalization: lower-case, runs of [-_.] collapse to a single -."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(text: str) -> List[str]:
    """Parse requirements.txt content into a list of package names.

    Rules:
      * one name per line
      * strip version specifiers, extras and env markers
      * ignore blank lines and ``# comment`` lines
      * ignore ``-r``/``-e``/other option lines and bare URLs
    Order is preserved and duplicates are removed (first occurrence wins).
    """
    names: List[str] = []
    seen = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Option lines: -r other.txt, -e ., --hash=..., -c constraints.txt
        if stripped.startswith("-"):
            continue
        # Editable / VCS / direct URLs — not a plain PyPI name we can check.
        low = stripped.lower()
        if "://" in low or low.startswith(("git+", "http:", "https:", "file:")):
            continue
        name = normalize_name(stripped)
        if not name:
            continue
        # A leftover URL fragment or path is not a valid distribution name.
        if "/" in name or "\\" in name:
            continue
        key = pypi_normalize(name)
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def find_requirements_files(path: str) -> List[str]:
    """Return requirements*.txt files under ``path`` (or the file itself)."""
    if os.path.isfile(path):
        if path.endswith(".txt"):
            return [path]
        return []
    matches: List[str] = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        for f in files:
            if f.startswith("requirements") and f.endswith(".txt"):
                matches.append(os.path.join(root, f))
    return sorted(matches)


def find_py_files(path: str) -> List[str]:
    """Return .py files under ``path`` (or the file itself if it is one)."""
    if os.path.isfile(path):
        return [path] if path.endswith(".py") else []
    matches: List[str] = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        for f in files:
            if f.endswith(".py"):
                matches.append(os.path.join(root, f))
    return sorted(matches)


def _skip_dir(name: str) -> bool:
    """Skip virtualenvs, VCS and cache dirs to keep scans fast and quiet."""
    return name in {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        ".eggs",
        "build",
        "dist",
    }
