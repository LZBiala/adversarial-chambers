"""The chamber's cast: frozen value objects and the three role seams.

Role separation is the architecture claim: a Generator can only propose, a
Refuter can only object, a Judge can only judge — and the orchestrator
refuses to let one object play two seats in the same chamber. An agent that
judges its own proposal is not a chamber; it is a rubber stamp with extra
steps.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

PRESUME_DIES = "presume-dies"
PRESUME_SURVIVES = "presume-survives"
DEFAULTS = (PRESUME_DIES, PRESUME_SURVIVES)

KILL = "KILL"
SURVIVE = "SURVIVE"


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    title: str
    pitch: str
    evidence_for: int  # 0-5, from the fixture record
    evidence_against: int  # 0-5


@dataclass(frozen=True)
class Objection:
    proposal_id: str
    text: str
    severity: int  # 0-5


@dataclass(frozen=True)
class Verdict:
    proposal_id: str
    outcome: str  # KILL | SURVIVE
    reason: str  # the cause of death (or survival grounds) — never empty
    judge: str
    default_instruction: str


class Generator(ABC):
    name: str

    @abstractmethod
    def propose(self) -> list[Proposal]: ...


class Refuter(ABC):
    name: str

    @abstractmethod
    def refute(self, proposal: Proposal) -> Objection: ...


class Judge(ABC):
    """The seam a live model would implement. The bundled judges are
    deterministic rules that prove the harness; live judging behavior — and
    its flip rate — belongs to whoever wires a model in (v1.1)."""

    name: str

    @abstractmethod
    def judge(
        self, proposal: Proposal, objection: Objection, default_instruction: str
    ) -> Verdict: ...
