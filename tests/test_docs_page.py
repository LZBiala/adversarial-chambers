"""The walkthrough page is quoted-and-TESTED (house law, third repo running):
every replay beat is verbatim from the committed transcript, headline numbers
match the metrics, hand-typed counts match their arrays, and the case study
carries its non-regenerable label.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HTML = (REPO / "docs" / "index.html").read_text(encoding="utf-8")


def metrics() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    rows = [
        json.loads(line)
        for line in (REPO / "metrics.jsonl").read_text("utf-8").splitlines()
        if line
    ]
    chamber = next(r for r in rows if r["kind"] == "chamber")
    flips = {str(r["judge"]): r for r in rows if r["kind"] == "flip"}
    return chamber, flips


class TestBeatsAreVerbatim:
    def test_every_beat_line_is_in_the_transcript(self) -> None:
        transcript = (REPO / "runs" / "chamber.md").read_text("utf-8")
        lines = re.findall(r'\bline: "((?:[^"\\]|\\.)*)"', HTML)
        assert len(lines) >= 7
        for raw in lines:
            line = raw.replace('\\"', '"')
            assert line in transcript, line[:70]

    def test_beat_count_matches_the_copy(self) -> None:
        n = len(re.findall(r'\bline: "', HTML))
        words = {6: "Six", 7: "Seven", 8: "Eight"}
        assert f"{words[n]} beats" in HTML


class TestHeadlineNumbers:
    def test_flip_contrast_matches_metrics(self) -> None:
        chamber, flips = metrics()
        ev, de = flips["EvidenceJudge"], flips["DeferentialJudge"]
        assert f"<b>{ev['flips']}/{ev['total']}</b>" in HTML
        assert f"<b>{de['flips']}/{de['total']}</b>" in HTML
        n_proposals = int(chamber["proposals"])  # type: ignore[arg-type]
        words = {8: "eight", 9: "nine"}
        assert f"same {words[n_proposals]} proposals" in HTML

    def test_stage_count_matches_the_array(self) -> None:
        n = len(re.findall(r'\{ k: "', HTML))
        words = {4: "Four", 5: "Five"}
        assert f"{words[n]} structural rules" in HTML


class TestCaseStudyDiscipline:
    def test_labels_present(self) -> None:
        assert "NARRATIVE, NOT A BENCHMARK" in HTML
        assert "NOT REGENERABLE FROM THIS REPOSITORY" in HTML
        assert "3 of 4" in HTML
        assert "direction" in HTML  # the not-established half stated
