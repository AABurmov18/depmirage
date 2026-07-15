"""Command-line interface for depmirage.

    depmirage scan <path>            scan folder or file (default: .)
    depmirage scan . --offline       cached fixtures, no network
    depmirage scan . --json          machine-readable output

Exit code is 0 when there are no findings, 1 when there is at least one — so it
drops straight into a CI job or pre-commit hook as a gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Optional

from . import __version__
from . import parsers, registry, typosquat, secrets, report, banner


def _load_fixtures() -> Dict:
    """Load bundled fixtures.json. Returns {} if unavailable (never crashes)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "fixtures.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run_scan(path: str, offline: bool = False) -> report.ScanReport:
    """Core scan logic, independent of output formatting."""
    fixtures = _load_fixtures()
    pkg_fixtures = fixtures.get("packages", {}) if offline else {}
    reg = registry.Registry(offline=offline, fixtures=pkg_fixtures)

    rep = report.ScanReport()

    # (a)+(b) Dependencies: existence + typosquat.
    req_files = parsers.find_requirements_files(path)
    for req_file in req_files:
        try:
            with open(req_file, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception:
            continue
        for name in parsers.parse_requirements(text):
            existence = reg.check_pypi(name)
            lookalike = ""
            near = typosquat.nearest_popular(name)
            # Flag as lookalike if it's a near-miss of a popular name, OR if it
            # does not exist and is close to a popular name.
            if near is not None:
                lookalike = near
            rep.deps.append(
                report.DepResult(
                    name=name,
                    source=os.path.relpath(req_file, path)
                    if os.path.isdir(path) else req_file,
                    existence=existence,
                    lookalike=lookalike,
                )
            )
    reg.save()

    # (c) Secrets: scan .py files.
    for py_file in parsers.find_py_files(path):
        rep.secrets.extend(secrets.scan_file(py_file))

    return rep


def _cmd_scan(args) -> int:
    path = args.path
    # Banner: human mode only. Suppressed for --json and --no-banner so machine
    # consumers and CI logs stay clean.
    if not args.json and not args.no_banner:
        banner.render_banner()

    if not os.path.exists(path):
        sys.stderr.write(f"error: path not found: {path}\n")
        return 2

    rep = run_scan(path, offline=args.offline)

    if args.json:
        print(json.dumps(report.to_dict(rep, offline=args.offline), indent=2))
    else:
        report.render(rep, offline=args.offline)

    return rep.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="depmirage",
        description="Spot AI-hallucinated and slopsquatting Python dependencies, "
        "typosquats, and hardcoded secrets.",
    )
    parser.add_argument(
        "--version", action="version", version=f"depmirage {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="scan a folder or file")
    scan.add_argument(
        "path", nargs="?", default=".",
        help="folder, requirements.txt, or .py file (default: current dir)",
    )
    scan.add_argument(
        "--offline", action="store_true",
        help="use bundled fixtures, make zero network calls",
    )
    scan.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON",
    )
    scan.add_argument(
        "--no-banner", action="store_true", help="suppress the ASCII banner",
    )
    scan.set_defaults(func=_cmd_scan)
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
