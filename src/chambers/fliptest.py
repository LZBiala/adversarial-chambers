"""The flip test: cross-examine the judge.

Run the SAME judge over the SAME proposals and objections twice, changing
exactly one thing — the standing default instruction (presume-dies vs
presume-survives). Any item whose outcome differs between the two runs was
never decided by the evidence: it was decided by the phrasing of the
instruction. The within-item flip rate is the instrument reading.

What a flip rate establishes: instruction SENSITIVITY — a reliability
property of the judge. What it does NOT establish: the direction of bias
(that requires a design where blinding and evidence access do not covary
with the instruction — documented in the README, not run here).
"""
from __future__ import annotations

from dataclasses import dataclass

from chambers.roles import PRESUME_DIES, PRESUME_SURVIVES, Judge, Objection, Proposal


@dataclass(frozen=True)
class FlipReport:
    judge: str
    total: int
    flips: int
    flipped_ids: tuple[str, ...]
    outcomes_dies: tuple[str, ...]  # aligned with items order
    outcomes_survives: tuple[str, ...]

    @property
    def flip_rate(self) -> float:
        return self.flips / self.total if self.total else 0.0


def flip_test(judge: Judge, items: list[tuple[Proposal, Objection]]) -> FlipReport:
    outcomes_dies: list[str] = []
    outcomes_survives: list[str] = []
    flipped: list[str] = []
    for proposal, objection in items:
        a = judge.judge(proposal, objection, PRESUME_DIES).outcome
        b = judge.judge(proposal, objection, PRESUME_SURVIVES).outcome
        outcomes_dies.append(a)
        outcomes_survives.append(b)
        if a != b:
            flipped.append(proposal.proposal_id)
    return FlipReport(
        judge=judge.name,
        total=len(items),
        flips=len(flipped),
        flipped_ids=tuple(flipped),
        outcomes_dies=tuple(outcomes_dies),
        outcomes_survives=tuple(outcomes_survives),
    )
