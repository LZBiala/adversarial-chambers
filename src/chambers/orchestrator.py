"""The chamber loop: propose → dedicated refutation → judged verdict → ledger.

Structural role separation is enforced here: the same object may not occupy
two seats in one chamber. This is not etiquette — an agent that judges its
own proposal collapses the whole design back into a single opinion wearing
three hats.
"""
from __future__ import annotations

from chambers.ledger import KillLedger
from chambers.roles import DEFAULTS, Generator, Judge, Refuter, Verdict


class ChamberError(ValueError):
    """Raised when the chamber's structural rules are violated."""


def run_chamber(
    generator: Generator,
    refuter: Refuter,
    judge: Judge,
    ledger: KillLedger,
    default_instruction: str,
) -> list[Verdict]:
    # Seat separation is BEST-EFFORT, and says so: identity catches the same
    # object in two seats; the type check catches the cheapest collusion (a
    # dual-role class instantiated twice for generator and judge). Collusion
    # via delegation or shared state is undetectable in Python — this is a
    # guardrail against accidents, not a provenance proof, and the README
    # design notes say the same.
    seats = [generator, refuter, judge]
    if len({id(s) for s in seats}) != len(seats):
        raise ChamberError("one object may not occupy two seats in a chamber")
    if type(generator) is type(judge):
        raise ChamberError(
            "generator and judge share a class — a dual-role type judging its "
            "own proposals is the cheapest collusion, refused"
        )
    if default_instruction not in DEFAULTS:
        raise ChamberError(f"unknown default instruction {default_instruction!r}")

    verdicts: list[Verdict] = []
    for proposal in generator.propose():
        objection = refuter.refute(proposal)
        if objection.proposal_id != proposal.proposal_id:
            raise ChamberError(
                f"refuter answered {objection.proposal_id!r} for "
                f"{proposal.proposal_id!r} — objections are per-proposal"
            )
        verdict = judge.judge(proposal, objection, default_instruction)
        if verdict.proposal_id != proposal.proposal_id:
            raise ChamberError(
                f"judge ruled on {verdict.proposal_id!r} while trying "
                f"{proposal.proposal_id!r} — verdicts are per-proposal"
            )
        if verdict.default_instruction != default_instruction:
            raise ChamberError(
                f"judge stamped {verdict.default_instruction!r} in a chamber "
                f"running under {default_instruction!r}"
            )
        ledger.record(verdict)
        verdicts.append(verdict)
    return verdicts
