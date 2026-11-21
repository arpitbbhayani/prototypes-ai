---
name: parallel-code-audit
description: Audits source files across security, performance, and reliability in parallel by spawning three specialized read-only subagents and synthesizing their findings into a single report. Use when the user asks to run a parallel code audit or demonstrate dynamic subagents via a skill.
---

# Parallel Code Audit Skill

Follow this procedure to audit target files using three concurrent, specialized subagents defined at runtime.

## Step 1: Identify Target Files

Determine which file or directory the user wants to audit. If the user did not specify a path, default to `sample_app/user_service.py`.

## Step 2: Define Three Specialized Subagent Types

Call `define_subagent` three times in parallel to register the following read-only subagent types (`EnableWriteTools: false`):

1. `security-auditor`: Focuses strictly on security flaws such as SQL injection, hardcoded secrets, weak cryptography, and unsafe authentication.
2. `performance-auditor`: Focuses strictly on performance bottlenecks such as N+1 queries, full-table scans in application memory, redundant commits inside loops, and unnecessary allocations.
3. `reliability-auditor`: Focuses strictly on reliability and error handling such as unclosed connections, swallowed exceptions, missing input validation, and unhandled `None` values.

Give each subagent type a concise system prompt instructing it to read the target file, ignore issues outside its assigned specialty, and return findings using the exact output contract in Step 3.

## Step 3: Launch All Three Subagents in Parallel

Subagents start with a blank context window. They do not see this conversation or this `SKILL.md` file. Every `invoke_subagent` prompt must be self-contained and include both the exact file path and the required output format.

Call `invoke_subagent` three times in the same turn:

- `TypeName: "security-auditor"`, `Role: "Security Auditor"`, `Workspace: "inherit"`
- `TypeName: "performance-auditor"`, `Role: "Performance Auditor"`, `Workspace: "inherit"`
- `TypeName: "reliability-auditor"`, `Role: "Reliability Auditor"`, `Workspace: "inherit"`

Instruct every subagent to return its findings strictly in this Markdown format so synthesis is deterministic:

```markdown
### Findings (<Category>)
- [Severity: High|Medium|Low] `<file>:<line>` - <short issue title>: <1-sentence explanation>. Fix: <concrete fix>.
```

## Step 4: Wait for Results

Stop calling tools after launching the three subagents. Antigravity wakes the parent agent automatically when each subagent sends its report. Do not poll.

## Step 5: Synthesize the Unified Audit Report

Once all three subagents have reported back, merge their outputs into one combined audit report with:

1. A summary table counting findings by category and severity.
2. Three sections (`Security`, `Performance`, `Reliability`) listing each finding with its file path, line numbers, severity, problem summary, and recommended fix.
3. A prioritized remediation list naming the top 3 fixes to apply first.
