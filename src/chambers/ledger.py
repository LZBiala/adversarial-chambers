"""The kill ledger: every verdict, with its cause of death, on the record.

A clean kill is knowledge; an unrecorded one gets re-proposed a month later
by someone who never saw it die. The ledger refuses a verdict without a
written reason — an unexplained KILL is exactly as useless as an unexplained
SURVIVE — and appends one JSON line per verdict so the record is grep-able
and diff-able forever.
"""
from __future__ import annotations

import json
from pathlib import Path

from chambers.roles import DEFAULTS, KILL, SURVIVE, Verdict


class LedgerError(ValueError):
    """Raised when a verdict would corrupt the record."""


class KillLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, verdict: Verdict) -> None:
        if not verdict.reason.strip():
            raise LedgerError(
                f"verdict on {verdict.proposal_id!r} has no written reason — "
                "an unexplained verdict is not a verdict"
            )
        if verdict.outcome not in (KILL, SURVIVE):
            raise LedgerError(f"unknown outcome {verdict.outcome!r}")
        if verdict.default_instruction not in DEFAULTS:
            raise LedgerError(f"unknown default {verdict.default_instruction!r}")
        record = {
            "proposal_id": verdict.proposal_id,
            "outcome": verdict.outcome,
            "reason": verdict.reason,
            "judge": verdict.judge,
            "default_instruction": verdict.default_instruction,
        }
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    def entries(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line
        ]
