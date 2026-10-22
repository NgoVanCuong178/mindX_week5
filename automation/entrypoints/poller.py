"""Trigger chính: quét Odoo định kỳ.

python -m automation.entrypoints.poller [--once] [--dry-run] [--interval GIÂY]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable

from automation.bootstrap import build_processor, load_runtime_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quét Odoo và tự xử lý ticket lỗi đăng nhập LMS")
    parser.add_argument("--once", action="store_true", help="chạy một lượt rồi dừng")
    parser.add_argument("--dry-run", action="store_true", help="chỉ đọc và quyết định, không ghi gì")
    parser.add_argument("--interval", type=int, default=None, help="số giây giữa các lượt quét")
    parser.add_argument("--env-file", default=".env", help="đường dẫn file .env")
    return parser


def run_loop(processor, interval_seconds: int, once: bool, dry_run: bool,
             sleep: Callable[[float], None] = time.sleep, max_cycles: int | None = None) -> int:
    """Chạy processor.run_once theo chu kỳ; trả về số lượt đã chạy."""
    cycles = 0
    while True:
        try:
            for outcome in processor.run_once(dry_run=dry_run) or []:
                status = outcome.error or (outcome.decision.value if outcome.decision else "bỏ qua")
                suffix = " [dry-run, không ghi]" if outcome.dry_run else ""
                print(f"#{outcome.ref} -> {status}{suffix}")
        except Exception as exc:  # lỗi một lượt không dừng poller
            print(f"[LỖI] Lượt quét thất bại: {exc}", file=sys.stderr)
        cycles += 1
        if once or (max_cycles is not None and cycles >= max_cycles):
            return cycles
        sleep(interval_seconds)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    settings = load_runtime_settings(Path(args.env_file))
    processor = build_processor(settings)
    interval = args.interval or settings.poll_interval_seconds
    print(f"Poller bắt đầu: interval={interval}s, dry_run={args.dry_run}, once={args.once}")
    run_loop(processor, interval, args.once, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
