"""CLI: `python -m chambers demo` - the chamber and the flip test, no keys.

Regenerates runs/ (chamber transcript + kill ledger), metrics.jsonl,
report/fliptest.svg, and the README AUTOGEN block. CI runs exactly this then
`git diff --exit-code`: the committed artifacts ARE the claims.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from chambers.fliptest import flip_test
from chambers.ledger import KillLedger
from chambers.orchestrator import run_chamber
from chambers.report import inject_readme, load_metrics, render_claims, render_flip_svg
from chambers.roles import KILL, PRESUME_DIES
from chambers.scripted import (
    DeferentialJudge,
    EvidenceJudge,
    ScriptedGenerator,
    ScriptedRefuter,
    is_ambiguous,
    load_proposals,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "fixtures" / "proposals.json"
RUNS_DIR = REPO_ROOT / "runs"
REPORT_DIR = REPO_ROOT / "report"
METRICS = REPO_ROOT / "metrics.jsonl"
README = REPO_ROOT / "README.md"

BANNER = (
    "CHAMBER: scripted generator/refuter/judges - deterministic, zero API keys; "
    "results are harness conformance, not any model's behavior"
)


def _clean_tree(path: Path) -> None:
    """Delete files, tolerate held directories (sync tools hold handles)."""
    if not path.exists():
        return
    for p in sorted(path.rglob("*"), reverse=True):
        if p.is_file():
            p.unlink()
        else:
            try:
                p.rmdir()
            except OSError:
                pass  # a held directory handle is harmless; files are gone
    try:
        path.rmdir()
    except OSError:
        pass


def demo(quiet: bool) -> int:
    if not FIXTURE.exists():
        print(
            "chambers demo must run from a source checkout "
            f"(pip install -e . or PYTHONPATH=src) - fixture not found at {FIXTURE}",
            file=sys.stderr,
        )
        return 1

    emit = (lambda _line: None) if quiet else print
    emit(BANNER)
    emit("")

    for path in (RUNS_DIR, REPORT_DIR):
        _clean_tree(path)
    if METRICS.exists():
        METRICS.unlink()

    pairs = load_proposals(FIXTURE)
    generator = ScriptedGenerator(pairs)
    refuter = ScriptedRefuter(pairs)
    judge = EvidenceJudge()
    ledger = KillLedger(RUNS_DIR / "kill-ledger.jsonl")

    emit(f"CHAMBER RUN: {len(pairs)} proposals, dedicated refutation, "
         f"{judge.name}, default '{PRESUME_DIES}'")
    verdicts = run_chamber(generator, refuter, judge, ledger, PRESUME_DIES)
    objections = {p.proposal_id: refuter.refute(p) for p, _ in pairs}
    transcript: list[str] = [
        "# chamber transcript",
        "",
        BANNER,
        "",
    ]
    for verdict in verdicts:
        line = f"- {verdict.proposal_id}: {verdict.outcome} - {verdict.reason}"
        objection_line = (
            f"  objection raised: {objections[verdict.proposal_id].text}"
        )
        transcript.append(line)
        transcript.append(objection_line)
        emit(line)
        emit(objection_line)

    items = [(p, refuter.refute(p)) for p, _ in pairs]
    emit("")
    emit("FLIP TEST: same items, only the standing default instruction changes")
    flip_reports = [flip_test(j, items) for j in (EvidenceJudge(), DeferentialJudge())]
    transcript.append("")
    transcript.append("## flip test")
    for flip in flip_reports:
        line = (
            f"- {flip.judge}: {flip.flips}/{flip.total} verdicts flipped"
            + (f" (flipped: {', '.join(flip.flipped_ids)})" if flip.flipped_ids else "")
        )
        transcript.append(line)
        emit(line)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with (RUNS_DIR / "chamber.md").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(transcript) + "\n")

    ambiguous = [p.proposal_id for p, _ in pairs if is_ambiguous(p)]
    rows: list[dict[str, object]] = [
        {
            "kind": "chamber",
            "proposals": len(pairs),
            "verdicts": len(verdicts),
            "kills": sum(1 for v in verdicts if v.outcome == KILL),
            "survivals": sum(1 for v in verdicts if v.outcome != KILL),
            "reasons_logged": sum(1 for v in verdicts if v.reason.strip()),
            "ambiguous_items": len(ambiguous),
            "judge": judge.name,
        }
    ]
    for flip in flip_reports:
        rows.append(
            {
                "kind": "flip",
                "judge": flip.judge,
                "total": flip.total,
                "flips": flip.flips,
                "flipped_ids": list(flip.flipped_ids),
            }
        )
    with METRICS.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    metrics = load_metrics(METRICS)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORT_DIR / "fliptest.svg").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_flip_svg(metrics))
    inject_readme(README, render_claims(metrics))

    emit("")
    emit("Look around:")
    emit("  runs/kill-ledger.jsonl   every verdict with its cause of death")
    emit("  runs/chamber.md          the transcript + flip-test results")
    emit("  report/fliptest.svg      the contrast (disclaimer inside the legend)")
    emit("  metrics.jsonl            every number the README publishes, regenerated just now")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chambers")
    sub = parser.add_subparsers(dest="command", required=True)
    p_demo = sub.add_parser("demo", help="run the chamber + flip test from clean state")
    p_demo.add_argument("--quiet", action="store_true", help="print nothing (CI mode)")
    args = parser.parse_args(argv)
    return demo(quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
