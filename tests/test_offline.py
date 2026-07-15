"""Offline path must be deterministic and make ZERO network calls."""

import os

import pytest

from depmirage.cli import run_scan
from depmirage import registry


DEMO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "demo")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Hard-fail if anything tries to import/use requests during offline tests."""
    def _boom(*a, **k):
        raise AssertionError("network call attempted in offline mode")

    # Poison the HTTP layer so any accidental call is caught.
    monkeypatch.setattr(registry.Registry, "_http_exists",
                        lambda self, url: _boom())


def test_offline_demo_is_deterministic():
    rep = run_scan(DEMO, offline=True)
    by_name = {d.name: d for d in rep.deps}

    assert by_name["requests"].existence == registry.EXISTS
    assert by_name["aqi-insights"].existence == registry.MISSING
    assert by_name["python-dotenv-secure"].existence == registry.MISSING

    # aqi-insights and python-dotenv-secure are findings
    assert by_name["aqi-insights"].is_finding
    assert by_name["python-dotenv-secure"].is_finding


def test_offline_flags_secret_and_exits_one():
    rep = run_scan(DEMO, offline=True)
    assert len(rep.secrets) >= 1
    assert rep.exit_code == 1


def test_offline_matches_repeated_runs():
    a = run_scan(DEMO, offline=True)
    b = run_scan(DEMO, offline=True)
    assert [(d.name, d.existence, d.is_finding) for d in a.deps] == \
           [(d.name, d.existence, d.is_finding) for d in b.deps]
    assert a.exit_code == b.exit_code == 1
