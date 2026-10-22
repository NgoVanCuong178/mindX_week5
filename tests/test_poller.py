from automation.entrypoints.poller import build_parser, run_loop


class StubProcessor:
    def __init__(self):
        self.calls = []

    def run_once(self, dry_run=False):
        self.calls.append(dry_run)
        return []


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.once is False and args.dry_run is False and args.interval is None


def test_parser_flags():
    args = build_parser().parse_args(["--once", "--dry-run", "--interval", "60"])
    assert args.once is True and args.dry_run is True and args.interval == 60


def test_once_runs_a_single_cycle_without_sleeping():
    processor, sleeps = StubProcessor(), []
    cycles = run_loop(processor, interval_seconds=120, once=True, dry_run=True, sleep=sleeps.append)
    assert cycles == 1 and processor.calls == [True] and sleeps == []


def test_loop_sleeps_between_cycles():
    processor, sleeps = StubProcessor(), []
    cycles = run_loop(processor, interval_seconds=60, once=False, dry_run=False, sleep=sleeps.append, max_cycles=3)
    assert cycles == 3 and processor.calls == [False, False, False]
    assert sleeps == [60, 60]


def test_loop_survives_a_failing_cycle():
    class Flaky(StubProcessor):
        def run_once(self, dry_run=False):
            super().run_once(dry_run)
            if len(self.calls) == 1:
                raise RuntimeError("network")
            return []

    processor = Flaky()
    assert run_loop(processor, 1, once=False, dry_run=False, sleep=lambda s: None, max_cycles=2) == 2
