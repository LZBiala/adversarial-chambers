"""End-to-end guarantees: determinism (double run byte-identical), no
wall-clock, AST-keyless, hygiene gate, README pinned (prose + excerpt), and
the in-process demo on a temp copy.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WALLCLOCK_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}:\d{2}")


def run_demo(workdir: Path) -> None:
    shutil.copytree(REPO / "src", workdir / "src")
    shutil.copytree(REPO / "fixtures", workdir / "fixtures")
    shutil.copy(REPO / "README.md", workdir / "README.md")
    result = subprocess.run(  # noqa: S603 — running our own module under test
        [sys.executable, "-m", "chambers", "demo", "--quiet"],
        cwd=workdir,
        env={**os.environ, "PYTHONPATH": str(workdir / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def artifact_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for sub in ("runs", "report"):
        out.extend(sorted(p for p in (root / sub).rglob("*") if p.is_file()))
    out.append(root / "metrics.jsonl")
    out.append(root / "README.md")
    return out


@pytest.fixture(scope="module")
def demo_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workdir = tmp_path_factory.mktemp("run_a")
    run_demo(workdir)
    return workdir


class TestPipeline:
    def test_metrics_match_design(self, demo_run: Path) -> None:
        rows = [
            json.loads(line)
            for line in (demo_run / "metrics.jsonl").read_text("utf-8").splitlines()
        ]
        chamber = next(r for r in rows if r["kind"] == "chamber")
        flips = {r["judge"]: r for r in rows if r["kind"] == "flip"}
        assert chamber["verdicts"] == chamber["proposals"]
        assert chamber["reasons_logged"] == chamber["verdicts"]
        assert flips["EvidenceJudge"]["flips"] == 0
        assert flips["DeferentialJudge"]["flips"] == chamber["ambiguous_items"]

    def test_ledger_and_transcript_agree(self, demo_run: Path) -> None:
        entries = [
            json.loads(line)
            for line in (demo_run / "runs" / "kill-ledger.jsonl").read_text("utf-8").splitlines()
        ]
        transcript = (demo_run / "runs" / "chamber.md").read_text("utf-8")
        for entry in entries:
            assert f"- {entry['proposal_id']}: {entry['outcome']}" in transcript

    def test_no_wallclock_in_artifacts(self, demo_run: Path) -> None:
        hits: list[str] = []
        for path in artifact_files(demo_run):
            for lineno, line in enumerate(path.read_text("utf-8").splitlines(), 1):
                if WALLCLOCK_RE.search(line):
                    hits.append(f"{path.name}:{lineno}")
        assert not hits, hits


class TestDeterminism:
    def test_two_runs_are_byte_identical(
        self, demo_run: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        second = tmp_path_factory.mktemp("run_b")
        run_demo(second)
        files_a, files_b = artifact_files(demo_run), artifact_files(second)
        assert [p.relative_to(demo_run) for p in files_a] == [
            p.relative_to(second) for p in files_b
        ]
        for pa, pb in zip(files_a, files_b, strict=True):
            assert pa.read_bytes() == pb.read_bytes(), pa.name


class TestKeylessViaAst:
    FORBIDDEN = {"socket", "urllib", "http", "requests", "subprocess", "datetime", "time", "random"}

    def test_no_forbidden_imports_in_package(self) -> None:
        for path in sorted((REPO / "src" / "chambers").glob("*.py")):
            tree = ast.parse(path.read_text("utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    tops = {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    tops = {(node.module or "").split(".")[0]}
                else:
                    continue
                assert not tops & self.FORBIDDEN, path.name


class TestReadmePinned:
    README_TEXT = (REPO / "README.md").read_text(encoding="utf-8")

    def test_transcript_excerpt_is_verbatim_modulo_wrapping(self) -> None:
        transcript_norm = re.sub(
            r"\s+", " ", (REPO / "runs" / "chamber.md").read_text("utf-8")
        )
        fences = re.findall(r"```\n(.*?)```", self.README_TEXT, flags=re.S)
        excerpt = next(f for f in fences if "glass-gazebo" in f)
        for raw_line in re.split(r"\n(?=- )", excerpt.strip()):
            norm = re.sub(r"\s+", " ", raw_line).strip()
            assert norm in transcript_norm, norm[:60]

    def test_prose_counts_match_fixture(self) -> None:
        data = json.loads((REPO / "fixtures" / "proposals.json").read_text("utf-8"))
        n = len(data["proposals"])
        words = {8: "Eight", 9: "Nine", 10: "Ten"}
        assert f"{words[n]} town-improvement proposals" in self.README_TEXT

    def test_case_study_carries_its_non_regenerable_label(self) -> None:
        assert "not regenerable from this repository" in self.README_TEXT
        assert "narrative, not a benchmark" in self.README_TEXT
        assert "3 of 4" in self.README_TEXT and "direction" in self.README_TEXT

    def test_no_wallclock_in_readme(self) -> None:
        assert not WALLCLOCK_RE.search(self.README_TEXT)


class TestInProcessCoverage:
    def test_demo_runs_in_process_on_a_temp_copy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import chambers.__main__ as main_mod

        shutil.copytree(REPO / "fixtures", tmp_path / "fixtures")
        shutil.copy(REPO / "README.md", tmp_path / "README.md")
        monkeypatch.setattr(main_mod, "FIXTURE", tmp_path / "fixtures" / "proposals.json")
        monkeypatch.setattr(main_mod, "README", tmp_path / "README.md")
        monkeypatch.setattr(main_mod, "RUNS_DIR", tmp_path / "runs")
        monkeypatch.setattr(main_mod, "REPORT_DIR", tmp_path / "report")
        monkeypatch.setattr(main_mod, "METRICS", tmp_path / "metrics.jsonl")
        assert main_mod.demo(quiet=True) == 0
        assert (tmp_path / "report" / "fliptest.svg").exists()
        committed = (REPO / "metrics.jsonl").read_bytes()
        assert (tmp_path / "metrics.jsonl").read_bytes() == committed


class TestHygieneGate:
    def test_repo_passes_its_own_gate(self) -> None:
        result = subprocess.run(  # noqa: S603 — running our own tool under test
            [sys.executable, str(REPO / "tools" / "blocklist_check.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout
