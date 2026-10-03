#!/usr/bin/env python3
"""Select and optionally run the repository's HTML-to-PDF renderer."""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ("chrome-headless-shell", "chromium", "google-chrome", ".venv-pdf/bin/weasyprint", "weasyprint", "wkhtmltopdf")


def select_renderer(which=shutil.which, modules=importlib.util.find_spec) -> str | None:
    forced = os.environ.get("PDF_RENDERER")
    if forced and which(forced):
        return forced
    for command in COMMANDS:
        if which(command):
            return command
    if modules("weasyprint") is not None:
        return "python:weasyprint"
    return None


def render(renderer: str, html: Path, pdf: Path) -> None:
    html = html.resolve(); pdf = pdf.resolve()
    if renderer in {"chrome-headless-shell", "chromium", "google-chrome"}:
        subprocess.run([renderer, "--headless", "--no-sandbox", "--disable-gpu",
                        f"--print-to-pdf={pdf}", f"file://{html}"], check=True)
    elif renderer == "weasyprint":
        subprocess.run([renderer, str(html), str(pdf)], check=True)
    elif renderer == "python:weasyprint":
        subprocess.run(["python3", "-c",
                        "from weasyprint import HTML; import sys; HTML(filename=sys.argv[1]).write_pdf(sys.argv[2])",
                        str(html), str(pdf)], check=True)
    else:
        subprocess.run([renderer, str(html), str(pdf)], check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--html", default="docs/note.html")
    parser.add_argument("--pdf", default="docs/note.pdf")
    args = parser.parse_args(argv)
    renderer = select_renderer()
    print(f"pdf renderer: {renderer or 'none'}")
    if renderer is None:
        return 1 if args.require else 0
    if args.render:
        render(renderer, ROOT / args.html, ROOT / args.pdf)
        print(f"wrote {args.pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
