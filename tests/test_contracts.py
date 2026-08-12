"""Contract suites: role separation, ledger refusals, judge behavior, and
the flip-test's central identity (flipped set == ambiguous set).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from chambers.fliptest import flip_test
from chambers.ledger import KillLedger, LedgerError
from chambers.orchestrator import ChamberError, run_chamber
from chambers.roles import KILL, PRESUME_DIES, PRESUME_SURVIVES, SURVIVE, Verdict
from chambers.scripted import (
    CLEAR_MARGIN,
    DeferentialJudge,
    EvidenceJudge,
    ScriptedGenerator,
    ScriptedRefuter,
    is_ambiguous,
    load_proposals,
)

REPO = Path(__file__).resolve().parents[1]
PAIRS = load_proposals(REPO / "fixtures" / "proposals.json")
ITEMS = [(p, ScriptedRefuter(PAIRS).refute(p)) for p, _ in PAIRS]


class TestRoleSeparation:
    def test_one_object_cannot_hold_two_seats(self, tmp_path: Path) -> None:
        generator = ScriptedGenerator(PAIRS)
        ledger = KillLedger(tmp_path / "ledger.jsonl")
        with pytest.raises(ChamberError, match="two seats"):
            run_chamber(generator, ScriptedRefuter(PAIRS), generator, ledger, PRESUME_DIES)  # type: ignore[arg-type]

    def test_dual_role_class_refused_even_as_two_instances(self, tmp_path: Path) -> None:
        # The cheapest collusion: one class holding both seats via two
        # instances. Deeper collusion (delegation, shared state) is
        # undetectable — the docstring and README say so.
        class Impostor(ScriptedGenerator, EvidenceJudge):  # type: ignore[misc]
            pass

        ledger = KillLedger(tmp_path / "ledger.jsonl")
        with pytest.raises(ChamberError, match="share a class"):
            run_chamber(
                Impostor(PAIRS), ScriptedRefuter(PAIRS), Impostor(PAIRS), ledger, PRESUME_DIES
            )

    def test_judge_verdict_round_trip_validated(self, tmp_path: Path) -> None:
        class WrongIdJudge(EvidenceJudge):
            def judge(self, proposal, objection, default_instruction):  # type: ignore[override]
                verdict = super().judge(proposal, objection, default_instruction)
                return Verdict(
                    "some-other-proposal", verdict.outcome, verdict.reason,
                    self.name, verdict.default_instruction,
                )

        ledger = KillLedger(tmp_path / "ledger.jsonl")
        with pytest.raises(ChamberError, match="per-proposal"):
            run_chamber(
                ScriptedGenerator(PAIRS), ScriptedRefuter(PAIRS), WrongIdJudge(), ledger, PRESUME_DIES
            )

    def test_unknown_default_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ChamberError, match="unknown default"):
            run_chamber(
                ScriptedGenerator(PAIRS),
                ScriptedRefuter(PAIRS),
                EvidenceJudge(),
                KillLedger(tmp_path / "ledger.jsonl"),
                "presume-nothing",
            )

    def test_chamber_ledgers_every_proposal(self, tmp_path: Path) -> None:
        ledger = KillLedger(tmp_path / "ledger.jsonl")
        verdicts = run_chamber(
            ScriptedGenerator(PAIRS), ScriptedRefuter(PAIRS), EvidenceJudge(), ledger, PRESUME_DIES
        )
        assert len(verdicts) == len(PAIRS)
        assert len(ledger.entries()) == len(PAIRS)
        assert all(str(e["reason"]).strip() for e in ledger.entries())


class TestLedger:
    def test_empty_reason_refused(self, tmp_path: Path) -> None:
        ledger = KillLedger(tmp_path / "ledger.jsonl")
        bad = Verdict("x", KILL, "   ", "judge", PRESUME_DIES)
        with pytest.raises(LedgerError, match="written reason"):
            ledger.record(bad)
        assert ledger.entries() == []

    def test_unknown_outcome_and_default_refused(self, tmp_path: Path) -> None:
        ledger = KillLedger(tmp_path / "ledger.jsonl")
        with pytest.raises(LedgerError, match="unknown outcome"):
            ledger.record(Verdict("x", "MAYBE", "why", "judge", PRESUME_DIES))
        with pytest.raises(LedgerError, match="unknown default"):
            ledger.record(Verdict("x", KILL, "why", "judge", "presume-lunch"))


class TestJudges:
    def test_evidence_judge_never_flips(self) -> None:
        report = flip_test(EvidenceJudge(), ITEMS)
        assert report.flips == 0 and report.total == len(ITEMS)

    def test_deferential_judge_flips_exactly_the_ambiguous_set(self) -> None:
        report = flip_test(DeferentialJudge(), ITEMS)
        ambiguous = {p.proposal_id for p, _ in PAIRS if is_ambiguous(p)}
        assert set(report.flipped_ids) == ambiguous
        assert report.flips == len(ambiguous) >= 3

    def test_deferential_judge_admits_deference_in_its_reason(self) -> None:
        judge = DeferentialJudge()
        ambiguous_item = next((p, o) for (p, o) in ITEMS if is_ambiguous(p))
        verdict = judge.judge(*ambiguous_item, PRESUME_DIES)
        assert "default presumption" in verdict.reason
        assert verdict.outcome == KILL
        verdict2 = judge.judge(*ambiguous_item, PRESUME_SURVIVES)
        assert verdict2.outcome == SURVIVE

    def test_clear_evidence_is_instruction_proof_for_both_judges(self) -> None:
        for judge in (EvidenceJudge(), DeferentialJudge()):
            for proposal, objection in ITEMS:
                if is_ambiguous(proposal):
                    continue
                a = judge.judge(proposal, objection, PRESUME_DIES).outcome
                b = judge.judge(proposal, objection, PRESUME_SURVIVES).outcome
                assert a == b, (judge.name, proposal.proposal_id)


class TestFixtureShape:
    def test_eight_proposals_three_ambiguous(self) -> None:
        assert len(PAIRS) == 8
        ambiguous = [p for p, _ in PAIRS if is_ambiguous(p)]
        assert len(ambiguous) == 3
        assert CLEAR_MARGIN == 2

    def test_fixture_is_valid_json_with_required_fields(self) -> None:
        data = json.loads((REPO / "fixtures" / "proposals.json").read_text("utf-8"))
        for row in data["proposals"]:
            assert set(row) >= {"id", "title", "pitch", "evidence_for", "evidence_against", "objection"}
            assert 0 <= int(row["evidence_for"]) <= 5
            assert 0 <= int(row["evidence_against"]) <= 5
            assert str(row["objection"]).strip()
