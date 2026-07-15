"""PyPI existence checks with on-disk caching and graceful degradation.

Only ever sends PACKAGE NAMES over the wire. Never source code, never secrets.
A network failure degrades to "unknown" (could not verify) — it never crashes.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from .parsers import pypi_normalize

# Result states.
EXISTS = "exists"
MISSING = "missing"
UNKNOWN = "unknown"

PYPI_URL = "https://pypi.org/pypi/{name}/json"
NPM_URL = "https://registry.npmjs.org/{name}"
TIMEOUT = 5  # seconds; short enough to keep scans snappy on flaky networks

_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".depmirage_cache")
_CACHE_FILE = os.path.join(_CACHE_DIR, "pypi.json")


class Registry:
    """Checks package existence against PyPI (or offline fixtures).

    Parameters
    ----------
    offline:
        When True, no network calls are made; results come from ``fixtures``.
    fixtures:
        Mapping of package-name -> {"exists": bool} used in offline mode and as
        a seed for online mode.
    """

    def __init__(self, offline: bool = False, fixtures: Optional[Dict] = None):
        self.offline = offline
        self.fixtures = fixtures or {}
        self._cache = _load_cache() if not offline else {}
        self._session = None
        self._dirty = False

    # -- public API ---------------------------------------------------------
    def check_pypi(self, name: str) -> str:
        """Return EXISTS / MISSING / UNKNOWN for a PyPI package name."""
        key = pypi_normalize(name)

        if self.offline:
            return self._from_fixtures(name)

        if key in self._cache:
            return self._cache[key]

        result = self._http_exists(PYPI_URL.format(name=name))
        # Only cache definitive answers; keep retrying on transient failures.
        if result in (EXISTS, MISSING):
            self._cache[key] = result
            self._dirty = True
        return result

    def check_npm(self, name: str) -> str:
        """Existence check against the npm registry (for package.json support)."""
        if self.offline:
            return self._from_fixtures(name)
        return self._http_exists(NPM_URL.format(name=name))

    def save(self) -> None:
        """Persist the disk cache if it changed. Never raises."""
        if self.offline or not self._dirty:
            return
        _save_cache(self._cache)

    # -- internals ----------------------------------------------------------
    def _from_fixtures(self, name: str) -> str:
        entry = self.fixtures.get(name)
        if entry is None:
            # Try the normalized form too.
            key = pypi_normalize(name)
            for fname, fentry in self.fixtures.items():
                if pypi_normalize(fname) == key:
                    entry = fentry
                    break
        if entry is None:
            return UNKNOWN
        return EXISTS if entry.get("exists") else MISSING

    def _http_exists(self, url: str) -> str:
        try:
            import requests  # imported lazily so --offline never needs it
        except Exception:
            return UNKNOWN
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "depmirage/0.1"})
        try:
            resp = self._session.get(url, timeout=TIMEOUT)
        except Exception:
            return UNKNOWN
        if resp.status_code == 200:
            return EXISTS
        if resp.status_code == 404:
            return MISSING
        return UNKNOWN


def _load_cache() -> Dict[str, str]:
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _save_cache(cache: Dict[str, str]) -> None:
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = _CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
        os.replace(tmp, _CACHE_FILE)
    except Exception:
        # Caching is best-effort; failure must never break a scan.
        pass
