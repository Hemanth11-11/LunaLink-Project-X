"""CLI wrapper for building the LunaLink markdown report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from lunalink.reporting import build_markdown_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a LunaLink report from an evidence bundle.")
    parser.add_argument("--evidence", default="outputs/baseline", help="Evidence directory.")
    parser.add_argument("--out", default="report/LunaLink_Report_Draft.md", help="Report path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = build_markdown_report(args.evidence, args.out)
    print(f"Wrote report to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
