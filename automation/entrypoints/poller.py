"""Trigger chính: quét Odoo định kỳ.

python -m automation.entrypoints.poller [--once] [--dry-run] [--interval GIÂY]
"""
from __future__ import annotations

import argparse
import time
from typing import Callable


def build_parser() -> argparse.ArgumentParser:
    raise NotImplementedError


def run_loop(processor, interval_seconds: int, once: bool, dry_run: bool,
             sleep: Callable[[float], None] = time.sleep, max_cycles: int | None = None) -> int:
    """Chạy processor.run_once theo chu kỳ; trả về số lượt đã chạy."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
