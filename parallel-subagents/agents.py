"""Specialized subagents and execution strategies (parallel vs. serial).

Separates two orthogonal concepts for clarity:
1. Subagents (Architecture): 4 isolated specialist workers + 1 Lead Synthesizer.
2. Execution Strategy (Concurrency): running those subagents concurrently
   (asyncio.create_task + asyncio.as_completed) vs. sequentially (for-loop).

Contains zero UI or print calls. All concurrency, agent prompts, and
structured outputs are managed here.
"""

import asyncio
import json
import time
from typing import Callable
from google import genai
from models import (
    SubagentOutput,
    SubagentReport,
    SynthesizedOutput,
    ReviewRunResult,
)

# ---------------------------------------------------------------------------
# 1. SUBAGENT DEFINITIONS (Architecture: WHO does the work)
# ---------------------------------------------------------------------------

SUBAGENTS = [
    {
        "id": "sec-agent",
        "name": "Security & Vulnerability Specialist",
        "domain": "Security",
        "system_instruction": (
            "You are a Principal Application Security Auditor. Your job is to strictly evaluate "
            "the provided code for security flaws: SQL injection, hardcoded secrets, insecure credential "
            "logging, OWASP vulnerabilities, authorization bypasses, and insecure cryptographic practices. "
            "Ignore stylistic nitpicks or minor performance concerns. Focus exclusively on security."
        ),
    },
    {
        "id": "perf-agent",
        "name": "Performance & Scalability Specialist",
        "domain": "Performance",
        "system_instruction": (
            "You are a Principal Performance & Systems Engineer. Your job is to strictly evaluate "
            "the provided code for latency and throughput bottlenecks: synchronous blocking operations "
            "in async functions, N+1 query patterns, lack of batching or connection pooling, unindexed lookups, "
            "and algorithmic inefficiency. Ignore formatting and security issues. Focus exclusively on performance."
        ),
    },
    {
        "id": "arch-agent",
        "name": "Architecture & Clean Code Specialist",
        "domain": "Architecture",
        "system_instruction": (
            "You are a Software Architect. Your job is to strictly evaluate the provided code for "
            "architectural health: Single Responsibility Principle (SRP), monolithic functions, tight coupling "
            "to global state, missing abstractions, testability, and inconsistent interface contracts. "
            "Ignore raw security exploits. Focus exclusively on architectural cohesion and maintainability."
        ),
    },
    {
        "id": "rel-agent",
        "name": "Reliability & Edge Case Specialist",
        "domain": "Reliability",
        "system_instruction": (
            "You are a Site Reliability & Fault-Tolerance Engineer. Your job is to strictly evaluate "
            "the provided code for failure modes: bare except clauses that swallow critical signals, "
            "unhandled exceptions (division by zero, NoneType indexing, empty list assumptions), missing timeouts "
            "on external network calls, and unchecked return statuses. Focus exclusively on resilience."
        ),
    },
]

SYNTHESIZER_INSTRUCTION = (
    "You are the Engineering Director and Lead Review Coordinator. You have received reports "
    "from 4 specialized subagents (Security, Performance, Architecture, Reliability) who concurrently "
    "audited the target code. "
    "Your responsibility is to synthesize these findings into a unified, definitive review: "
    "1. Deduplicate any overlapping findings across agents. "
    "2. Determine an overall Pull Request verdict: REQUEST_CHANGES (if critical/high flaws exist), "
    "   NEEDS_DISCUSSION (if medium/architectural trade-offs dominate), or APPROVE (if clean). "
    "3. Compute an aggregate risk score from 0 (flawless) to 100 (critical hazard). "
    "4. Formulate a 2-3 sentence executive summary for the author and tech lead. "
    "5. Provide a prioritized list of top 3-5 immediate remediation action items."
)


class SubagentError(Exception):
    """Raised when a subagent or synthesizer LLM call fails."""


async def run_single_subagent(
    client: genai.Client,
    model: str,
    agent_spec: dict[str, str],
    target_code: str,
) -> SubagentReport:
    """Execute a single specialized subagent with structured output."""
    t0 = time.monotonic()
    prompt = (
        f"Analyze this target code file according to your specialist domain:\n\n"
        f"```python\n{target_code}\n```\n\n"
        f"Produce a structured JSON report identifying findings in your area."
    )

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "system_instruction": agent_spec["system_instruction"],
                "response_mime_type": "application/json",
                "response_schema": SubagentOutput,
                "temperature": 0.2,
            },
        )
        latency = time.monotonic() - t0
        output_data = json.loads(response.text)
        subagent_out = SubagentOutput.model_validate(output_data)

        return SubagentReport(
            agent_id=agent_spec["id"],
            agent_name=agent_spec["name"],
            domain=agent_spec["domain"],
            summary=subagent_out.summary,
            findings=subagent_out.findings,
            latency_seconds=latency,
        )
    except Exception as e:
        latency = time.monotonic() - t0
        raise SubagentError(f"Subagent '{agent_spec['name']}' failed: {e}") from e


async def run_synthesizer(
    client: genai.Client,
    model: str,
    target_code: str,
    subagent_reports: list[SubagentReport],
) -> SynthesizedOutput:
    """Lead coordinator synthesizes all parallel subagent outputs into a unified verdict."""
    reports_payload = [
        {
            "domain": r.domain,
            "agent": r.agent_name,
            "summary": r.summary,
            "findings": [f.model_dump() for f in r.findings],
        }
        for r in subagent_reports
    ]

    prompt = (
        f"Target Code:\n```python\n{target_code}\n```\n\n"
        f"Specialist Subagent Reports:\n{json.dumps(reports_payload, indent=2)}\n\n"
        f"Provide the definitive synthesized review."
    )

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "system_instruction": SYNTHESIZER_INSTRUCTION,
                "response_mime_type": "application/json",
                "response_schema": SynthesizedOutput,
                "temperature": 0.2,
            },
        )
        data = json.loads(response.text)
        return SynthesizedOutput.model_validate(data)
    except Exception as e:
        raise SubagentError(f"Lead Synthesizer failed: {e}") from e


# ---------------------------------------------------------------------------
# 2. EXECUTION STRATEGIES (Concurrency: HOW subagents are scheduled)
# ---------------------------------------------------------------------------


async def run_parallel_review(
    client: genai.Client,
    model: str,
    target_path: str,
    target_code: str,
    on_agent_complete: Callable[[SubagentReport], None] | None = None,
    on_synthesis_start: Callable[[], None] | None = None,
) -> ReviewRunResult:
    """Phase 1: Execute all 4 subagents in PARALLEL. Phase 2: Lead synthesis (sequential)."""
    wall_start = time.monotonic()

    # Phase 1: Fan-out — launch all specialist subagents concurrently
    tasks = [
        asyncio.create_task(
            run_single_subagent(client, model, agent_spec, target_code),
            name=agent_spec["name"],
        )
        for agent_spec in SUBAGENTS
    ]

    # Collect results as each subagent completes (out-of-order completion proves concurrency)
    subagent_reports: list[SubagentReport] = []
    for completed_task in asyncio.as_completed(tasks):
        report = await completed_task
        subagent_reports.append(report)
        if on_agent_complete:
            on_agent_complete(report)

    # Sort reports into canonical order for deterministic synthesis input
    domain_order = {spec["id"]: i for i, spec in enumerate(SUBAGENTS)}
    subagent_reports.sort(key=lambda r: domain_order.get(r.agent_id, 99))

    subagents_wall_time = time.monotonic() - wall_start
    subagents_serial_sum = sum(r.latency_seconds for r in subagent_reports)
    speedup_ratio = (
        subagents_serial_sum / subagents_wall_time if subagents_wall_time > 0 else 1.0
    )

    # Phase 2: Reduce — Lead Synthesizer runs sequentially after all subagents finish
    if on_synthesis_start:
        on_synthesis_start()
    synth_start = time.monotonic()
    synthesis = await run_synthesizer(client, model, target_code, subagent_reports)
    synthesis_time = time.monotonic() - synth_start

    return ReviewRunResult(
        target_path=target_path,
        model_name=model,
        execution_mode="parallel",
        subagent_reports=subagent_reports,
        synthesis=synthesis,
        subagents_wall_time=subagents_wall_time,
        subagents_serial_sum=subagents_serial_sum,
        synthesis_time=synthesis_time,
        speedup_ratio=speedup_ratio,
    )


async def run_serial_review(
    client: genai.Client,
    model: str,
    target_path: str,
    target_code: str,
    on_agent_complete: Callable[[SubagentReport], None] | None = None,
    on_synthesis_start: Callable[[], None] | None = None,
) -> ReviewRunResult:
    """Phase 1: Execute the same 4 subagents SEQUENTIALLY. Phase 2: Lead synthesis."""
    wall_start = time.monotonic()

    # Phase 1: Run each specialist subagent one-by-one (no concurrency)
    subagent_reports: list[SubagentReport] = []
    for agent_spec in SUBAGENTS:
        report = await run_single_subagent(client, model, agent_spec, target_code)
        subagent_reports.append(report)
        if on_agent_complete:
            on_agent_complete(report)

    subagents_wall_time = time.monotonic() - wall_start
    subagents_serial_sum = sum(r.latency_seconds for r in subagent_reports)

    # Phase 2: Reduce — Lead Synthesizer runs sequentially after all subagents finish
    if on_synthesis_start:
        on_synthesis_start()
    synth_start = time.monotonic()
    synthesis = await run_synthesizer(client, model, target_code, subagent_reports)
    synthesis_time = time.monotonic() - synth_start

    return ReviewRunResult(
        target_path=target_path,
        model_name=model,
        execution_mode="serial",
        subagent_reports=subagent_reports,
        synthesis=synthesis,
        subagents_wall_time=subagents_wall_time,
        subagents_serial_sum=subagents_serial_sum,
        synthesis_time=synthesis_time,
        speedup_ratio=1.0,
    )
