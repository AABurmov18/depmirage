"""The depmirage startup banner (sqlmap-style ASCII wordmark).

Pure ASCII art (no box-drawing / non-latin-1 glyphs) so it renders cleanly on
any Windows code page as well as UTF-8 terminals. Colour is applied with rich;
if colour is unavailable the raw ASCII still reads fine.
"""

from __future__ import annotations

from . import __version__

# "slant" figlet wordmark. Raw string so the backslashes stay literal.
_WORDMARK = r"""       __                     _
  ____/ /__  ____  ____ ___  (_)________ _____ ____
 / __  / _ \/ __ \/ __ `__ \/ / ___/ __ `/ __ `/ _ \
/ /_/ /  __/ /_/ / / / / / / / /  / /_/ / /_/ /  __/
\__,_/\___/ .___/_/ /_/ /_/_/_/   \__,_/\__, /\___/
         /_/                           /____/"""

# A cool -> warm gradient, evoking heat-shimmer over the wordmark.
_GRADIENT = [
    "bright_cyan",
    "cyan",
    "blue",
    "magenta",
    "bright_magenta",
    "bright_magenta",
]

_TAGLINE = "hallucinated & slopsquatting dependency scanner"
_MOTIF = "~ spotting mirages in your dependency supply chain ~"
_URL = "https://github.com/AABurmov18/depmirage"


def render_banner(console=None) -> None:
    """Print the coloured banner. Never raises (cosmetic only)."""
    try:
        from rich.console import Console
        from rich.text import Text

        console = console or Console()
        lines = _WORDMARK.split("\n")
        block = Text()
        for i, line in enumerate(lines):
            colour = _GRADIENT[min(i, len(_GRADIENT) - 1)]
            block.append(line + "\n", style=f"bold {colour}")
        console.print(block, end="")
        console.print(f"   [dim italic]{_MOTIF}[/dim italic]")
        console.print(
            f"   [bold white]{_TAGLINE}[/bold white]   "
            f"[bold bright_cyan]v{__version__}[/bold bright_cyan]"
        )
        console.print(f"   [dim]{_URL}[/dim]\n")
    except Exception:
        # Fall back to a plain print so a rich failure never breaks a scan.
        print(_WORDMARK)
        print(f"   {_MOTIF}")
        print(f"   {_TAGLINE}   v{__version__}")
        print(f"   {_URL}\n")


def banner_text() -> str:
    """Return the uncoloured banner as a string (for tests / --help)."""
    return (
        f"{_WORDMARK}\n   {_MOTIF}\n"
        f"   {_TAGLINE}   v{__version__}\n   {_URL}\n"
    )
