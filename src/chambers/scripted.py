"""The scripted cast: deterministic agents that prove the harness.

Two judges ship, and their CONTRAST is the demonstration:

- EvidenceJudge decides from the evidence balance alone, with a fixed
  tie-break (a tie survives, always, regardless of instruction). Its flip
  rate under the instruction-flip test is 0 by construction.
- DeferentialJudge decides from evidence only when the balance is CLEAR;
  on ambiguous items it follows whatever standing default instruction it was
  given — and says so in its written reason. Its flip rate equals the number
  of ambiguous items, by construction.

Neither says anything about any model. They prove the instrument: if a judge
defers to its instructions, the flip test lights up; if it weighs evidence,
it stays dark.
"""
from __future__ import annotations

import json
from pathlib import Path

from chambers.roles import (
    KILL,
    PRESUME_DIES,
    SURVIVE,
    Generator,
    Judge,
    Objection,
    Proposal,
    Refuter,
    Verdict,
)

CLEAR_MARGIN = 2  # |for - against| >= CLEAR_MARGIN counts as clear evidence


def load_proposals(path: Path) -> list[tuple[Proposal, str]]:
    """Fixture rows -> (proposal, scripted objection text) pairs."""
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    out: list[tuple[Proposal, str]] = []
    for row in data["proposals"]:
        out.append(
            (
                Proposal(
                    proposal_id=str(row["id"]),
                    title=str(row["title"]),
                    pitch=str(row["pitch"]),
                    evidence_for=int(row["evidence_for"]),
                    evidence_against=int(row["evidence_against"]),
                ),
                str(row["objection"]),
            )
        )
    return out


def is_ambiguous(proposal: Proposal) -> bool:
    return abs(proposal.evidence_for - proposal.evidence_against) < CLEAR_MARGIN


class ScriptedGenerator(Generator):
    name = "ScriptedGenerator"

    def __init__(self, pairs: list[tuple[Proposal, str]]) -> None:
        self._pairs = pairs

    def propose(self) -> list[Proposal]:
        return [p for p, _ in self._pairs]


class ScriptedRefuter(Refuter):
    name = "ScriptedRefuter"

    def __init__(self, pairs: list[tuple[Proposal, str]]) -> None:
        self._objections = {p.proposal_id: text for p, text in pairs}
        self._severities = {p.proposal_id: p.evidence_against for p, _ in pairs}

    def refute(self, proposal: Proposal) -> Objection:
        return Objection(
            proposal_id=proposal.proposal_id,
            text=self._objections[proposal.proposal_id],
            severity=self._severities[proposal.proposal_id],
        )


class EvidenceJudge(Judge):
    """Instruction-INSENSITIVE by construction: evidence decides; ties survive."""

    name = "EvidenceJudge"

    def judge(
        self, proposal: Proposal, objection: Objection, default_instruction: str
    ) -> Verdict:
        margin = proposal.evidence_for - proposal.evidence_against
        if margin < 0:
            outcome, why = KILL, (
                f"objection outweighs the case ({proposal.evidence_against} vs "
                f"{proposal.evidence_for}): {objection.text}"
            )
        elif margin > 0:
            outcome, why = SURVIVE, (
                f"case outweighs the objection ({proposal.evidence_for} vs "
                f"{proposal.evidence_against})"
            )
        else:
            outcome, why = SURVIVE, (
                "evidence tied — fixed tie-break: a tie survives, regardless "
                "of the standing instruction"
            )
        return Verdict(
            proposal_id=proposal.proposal_id,
            outcome=outcome,
            reason=why,
            judge=self.name,
            default_instruction=default_instruction,
        )


class DeferentialJudge(Judge):
    """Instruction-SENSITIVE by construction: on ambiguous evidence it follows
    the standing default — and admits it in the written reason."""

    name = "DeferentialJudge"

    def judge(
        self, proposal: Proposal, objection: Objection, default_instruction: str
    ) -> Verdict:
        if not is_ambiguous(proposal):
            margin = proposal.evidence_for - proposal.evidence_against
            outcome = KILL if margin < 0 else SURVIVE
            why = (
                f"clear evidence ({proposal.evidence_for} for, "
                f"{proposal.evidence_against} against)"
            )
        else:
            outcome = KILL if default_instruction == PRESUME_DIES else SURVIVE
            why = (
                f"evidence ambiguous ({proposal.evidence_for} for, "
                f"{proposal.evidence_against} against) — default presumption "
                f"'{default_instruction}' applied"
            )
        return Verdict(
            proposal_id=proposal.proposal_id,
            outcome=outcome,
            reason=why,
            judge=self.name,
            default_instruction=default_instruction,
        )
