# Parallel Subagents Code Reviewer Prototype

---

## Architecture

```
                  ┌─────────────────────────────────┐
                  │    Target Code / Pull Request   │
                  └────────────────┬────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
     │ Security Agent  │  │Performance Agent│  │Reliability Agent│ ... (Architecture Agent)
     │ (OWASP, SQLi)   │  │ (N+1, Async I/O)│  │ (Timeouts, Err) │
     └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │  (Concurrent Async Execution)
                                   ▼
                  ┌─────────────────────────────────┐
                  │         Lead Synthesizer        │
                  │   (Deduplication & Verdict)     │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │  ape-cli Terminal Presentation  │
                  └─────────────────────────────────┘
```

### 1. Specialized Subagents
- **Security & Vulnerability Specialist**: Audits SQL injection, hardcoded secrets, credential logging, OWASP vulnerabilities.
- **Performance & Scalability Specialist**: Audits blocking calls in async loops, N+1 query patterns, unindexed queries.
- **Architecture & Clean Code Specialist**: Evaluates Single Responsibility Principle (SRP), tight coupling, and design cohesion.
- **Reliability & Edge Case Specialist**: Audits bare exception handling, missing network timeouts, and unhandled edge cases.

### 2. Lead Synthesizer
Merges all subagent outputs, removes cross-domain duplication, computes an aggregate risk score (0-100), issues a definitive verdict (`APPROVE`, `REQUEST_CHANGES`, `NEEDS_DISCUSSION`), and lists top prioritized remediation actions.

---

## Two Distinct Concepts

This prototype intentionally separates **architecture** from **execution strategy** so they can be taught independently:

1. **Subagents (Architecture — *who* does the work):** A task is decomposed across 4 isolated specialist subagents (`Security`, `Performance`, `Architecture`, `Reliability`), each with its own system prompt and structured JSON schema, followed by a **Lead Synthesizer** that merges and deduplicates their findings. Subagents work identically whether run sequentially or in parallel.
2. **Parallel Execution (Concurrency — *how* they run):** Because the 4 specialist subagents are independent, Phase 1 schedules them concurrently with `asyncio.create_task` + `asyncio.as_completed` (`--mode parallel`) instead of one-by-one in a loop (`--mode serial`). Phase 2 (Lead Synthesis) always runs sequentially after all subagents finish.

---

## File Structure

- [`ui.py`](file:///home/arpit/workspace/prototypes-ai/parallel-subagents/ui.py): Terminal presentation module (256-color palette, glyphs, braille spinner, listings, exit code mapper).
- [`models.py`](file:///home/arpit/workspace/prototypes-ai/parallel-subagents/models.py): Strongly-typed Pydantic schemas for subagent outputs, timing metadata, and synthesis.
- [`agents.py`](file:///home/arpit/workspace/prototypes-ai/parallel-subagents/agents.py): Subagent definitions (`SUBAGENTS`), Lead Synthesizer, and execution strategies (`run_parallel_review` using `asyncio.create_task`/`asyncio.as_completed` vs. `run_serial_review`).
- [`sample_target.py`](file:///home/arpit/workspace/prototypes-ai/parallel-subagents/sample_target.py): Realistic checkout & billing service containing subtle security, perf, architecture, and reliability bugs.
- [`main.py`](file:///home/arpit/workspace/prototypes-ai/parallel-subagents/main.py): CLI entrypoint orchestrating Phase 1 (subagent fan-out) and Phase 2 (lead synthesis) with live spinners and status lines.
- [`test_ui.py`](file:///home/arpit/workspace/prototypes-ai/parallel-subagents/test_ui.py): Test suite asserting terminal presentation invariants.

---

## Usage

### 1. Run the Complete Demo
No flags needed — `main.py` runs all stages in sequence (1. sequential subagents, 2. parallel subagents, 3. side-by-side timing comparison):
```bash
python main.py
```

You can also pass a custom target file:
```bash
python main.py path/to/your_code.py
```

### 2. Run UI Invariant Tests
```bash
pytest test_ui.py
```
