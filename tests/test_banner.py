"""The banner is cosmetic but must never crash a scan or pollute machine output."""

import json

from depmirage import banner, __version__
from depmirage.cli import main


def test_banner_text_contains_name_and_version():
    text = banner.banner_text()
    assert "depmirage" in text  # wordmark + tagline
    assert __version__ in text


def test_banner_is_pure_ascii():
    # Non-ASCII would risk mojibake on legacy Windows code pages.
    banner.banner_text().encode("ascii")


def test_render_banner_never_raises():
    # Should not raise even with no real terminal attached.
    banner.render_banner()


def test_json_output_has_no_banner(capsys):
    code = main(["scan", "examples/demo", "--offline", "--json"])
    out = capsys.readouterr().out
    # Output must be valid JSON with nothing before it.
    parsed = json.loads(out)
    assert parsed["exit_code"] == code == 1
    assert "spotting mirages" not in out


def test_no_banner_flag_suppresses_banner(capsys):
    main(["scan", "examples/demo", "--offline", "--no-banner"])
    out = capsys.readouterr().out
    assert "spotting mirages" not in out
