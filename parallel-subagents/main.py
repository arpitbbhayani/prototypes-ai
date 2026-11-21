#!/usr/bin/env python3
"""All-in-one teaching demo for Subagents vs. Parallel Execution.

Run with no flags:
    python main.py

Walks through all stages in sequence:
1. Subagents (Sequential)  -- 4 specialist subagents run one-by-one + lead synthesizer
2. Subagents (Parallel)    -- the exact same 4 subagents run concurrently + lead synthesizer
3. Side-by-Side Comparison -- wall-clock timing & speedup between sequential and parallel
"""

import asyncio
import os
import sys
from pathlib import Path
from google import genai

import ui
from models import ReviewRunResult
from agents import (
    SUBAGENTS,
    SubagentError,
    run_parallel_review,
    run_serial_review,
)

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_TARGET = Path(__file__).parent / "sample_target.py"


def severity_color(val: str) -> str:
    """Maps finding severity or verdict to 256-palette color code."""
    v = val.upper()
    if v in ("CRITICAL", "HIGH", "REQUEST_CHANGES"):
        return "167"  # muted red
    if v in ("MEDIUM", "WARN", "NEEDS_DISCUSSION"):
        return "179"  # muted amber
    if v in ("LOW", "INFO", "APPROVE"):
        return "71"   # muted green
    return "245"      # dim grey


def render_findings_table(result: ReviewRunResult) -> None:
    """Render consolidated findings using aligned tabular listing."""
    findings = result.synthesis.consolidated_findings
    if not findings:
        ui.ok("no critical issues detected")
        return

    rows = [[f.severity, f.location, f.title] for f in findings]
    ui.table(rows, color=(0, severity_color), dims=(1,))


async def run_stage(
    client: genai.Client,
    model: str,
    target_path: Path,
    target_code: str,
    mode: str,
) -> ReviewRunResult:
    """Execute one full review pass (Phase 1 subagents + Phase 2 lead synthesis)."""
    is_parallel = mode == "parallel"
    runner = run_parallel_review if is_parallel else run_serial_review
    total_agents = len(SUBAGENTS)

    if is_parallel:
        ui.heading("demo 2: same subagents in parallel", "asyncio.create_task")
    else:
        ui.heading("demo 1: subagents in sequence", "one-by-one, no parallelism")

    phase1_label = (
        f"parallel, {total_agents} subagents"
        if is_parallel
        else f"sequential, {total_agents} subagents"
    )
    ui.heading("phase 1: subagent fan-out", phase1_label)

    completed_reports = []
    agent_label_width = max(len(f"[{s['id']}] {s['name']}") for s in SUBAGENTS)
    active_spinner: ui.Spinner | None = None

    initial_msg = (
        f"Running {total_agents} specialist subagents in parallel"
        if is_parallel
        else f"Running {total_agents} specialist subagents sequentially"
    )
    active_spinner = ui.Spinner(initial_msg).start()

    def on_subagent_done(report) -> None:
        completed_reports.append(report)
        if active_spinner is not None:
            active_spinner._erase()
        n_issues = len(report.findings)
        detail = f"{n_issues} finding{'s' if n_issues != 1 else ''} ({report.latency_seconds:.1f}s)"
        ui.ok(f"[{report.agent_id}] {report.agent_name}", detail, width=agent_label_width)
        remaining = total_agents - len(completed_reports)
        if remaining > 0 and active_spinner is not None:
            if is_parallel:
                active_spinner.message = (
                    f"Waiting on {remaining} parallel subagent{'s' if remaining != 1 else ''}"
                )
            else:
                active_spinner.message = f"Running subagents sequentially ({remaining} remaining)"

    def on_synthesis_start() -> None:
        nonlocal active_spinner
        if active_spinner is not None:
            active_spinner.stop()
            active_spinner = None
        ui.heading("phase 2: lead agent synthesis", "sequential")
        active_spinner = ui.Spinner(
            f"Synthesizing {total_agents} subagent reports into final verdict"
        ).start()

    try:
        result = await runner(
            client=client,
            model=model,
            target_path=str(target_path),
            target_code=target_code,
            on_agent_complete=on_subagent_done,
            on_synthesis_start=on_synthesis_start,
        )
    finally:
        if active_spinner is not None:
            active_spinner.stop()
            active_spinner = None

    ui.ok("lead synthesizer verdict ready", f"{result.synthesis_time:.1f}s")
    ui.kv(
        "subagents wall",
        f"{result.subagents_wall_time:.2f}s (sum of agent times: {result.subagents_serial_sum:.2f}s)",
        width=16,
    )
    ui.kv("synthesis time", f"{result.synthesis_time:.2f}s (sequential reduce)", width=16)
    return result


def execute_demo() -> int:
    target_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_TARGET.resolve()
    if not target_path.exists():
        ui.err(f"target file not found: {target_path}")
        return 1

    try:
        target_code = target_path.read_text(encoding="utf-8")
    except Exception as e:
        ui.err(f"failed to read target file: {e}")
        return 1

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        ui.err("missing GEMINI_API_KEY environment variable")
        ui.hint("export your API key with:")
        ui.command("export GEMINI_API_KEY='your-key-here'")
        return 1

    async def run_all_stages() -> tuple[ReviewRunResult, ReviewRunResult]:
        client = genai.Client()
        try:
            # 1. Sequential subagents
            serial_res = await run_stage(
                client, DEFAULT_MODEL, target_path, target_code, mode="serial"
            )
            # 2. Parallel subagents
            parallel_res = await run_stage(
                client, DEFAULT_MODEL, target_path, target_code, mode="parallel"
            )
            return serial_res, parallel_res
        finally:
            await client.aio.aclose()

    total_agents = len(SUBAGENTS)

    # Overview
    ui.heading("subagents vs parallel execution", f"{total_agents} subagents + 1 lead synthesizer")
    ui.kv("target", str(target_path), width=14)
    ui.kv("model", DEFAULT_MODEL, width=14)
    ui.kv("architecture", f"{total_agents} specialist subagents -> 1 lead synthesizer", width=14)
    ui.kv("demo flow", "1) sequential subagents -> 2) parallel subagents -> 3) comparison", width=14)

    serial_result, parallel_result = asyncio.run(run_all_stages())

    # 3. Synthesized review details (from parallel run)
    synth = parallel_result.synthesis
    ui.heading("final review verdict")
    verdict_styled = ui.paint(synth.verdict, severity_color(synth.verdict), bold=True)
    ui.kv("verdict", verdict_styled, width=14)
    ui.kv("risk score", f"{synth.risk_score} / 100", width=14)

    ui.heading("executive summary")
    ui.bullet(synth.executive_summary)

    ui.heading("consolidated findings", len(synth.consolidated_findings))
    render_findings_table(parallel_result)

    ui.heading("recommended action items", len(synth.top_action_items))
    for item in synth.top_action_items:
        ui.bullet(item)

    # 4. Side-by-side comparison
    ui.heading("demo 3: sequential vs parallel comparison")
    actual_speedup = (
        serial_result.subagents_wall_time / parallel_result.subagents_wall_time
        if parallel_result.subagents_wall_time > 0
        else 1.0
    )
    bench_rows = [
        ["sequential subagents", f"{serial_result.subagents_wall_time:.2f}s", "1.0x baseline"],
        ["parallel subagents", f"{parallel_result.subagents_wall_time:.2f}s", f"{actual_speedup:.1f}x faster"],
    ]
    ui.table(bench_rows, dims=(0,))
    time_saved = serial_result.subagents_wall_time - parallel_result.subagents_wall_time
    pct = (
        (time_saved / serial_result.subagents_wall_time * 100)
        if serial_result.subagents_wall_time > 0
        else 0.0
    )
    ui.info(f"parallel execution saved {time_saved:.2f}s ({pct:.0f}% subagent latency reduction)")

    return 4 if synth.verdict == "REQUEST_CHANGES" else 0


def main() -> int:
    return ui.run(
        execute_demo,
        {
            SubagentError: 2,
            FileNotFoundError: 1,
        },
    )


if __name__ == "__main__":
    sys.exit(main())
