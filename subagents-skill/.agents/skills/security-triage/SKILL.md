---
name: security-triage
description: Runs a focused security triage by delegating file inspection to the persistent file-based security-reviewer custom subagent. Use when the user asks for a security triage or wants to demonstrate invoking a file-based custom subagent from a skill.
---

# Security Triage Skill

Follow this procedure to delegate a security review to the persistent `security-reviewer` custom subagent defined in `.agents/agents/security-reviewer.md`.

## Step 1: Identify Target Files

Determine which file the user wants to inspect. If no path is provided, default to `sample_app/user_service.py`.

## Step 2: Invoke the Persistent Custom Subagent

Do not call `define_subagent`. The `security-reviewer` subagent is already discovered from `.agents/agents/security-reviewer.md`.

Call `invoke_subagent` with:

- `TypeName: "security-reviewer"`
- `Role: "Security Reviewer"`
- `Workspace: "inherit"`
- `Prompt`: A self-contained instruction naming the exact target file path and asking for all security findings ranked from highest to lowest severity.

## Step 3: Wait and Present Triage Summary

Stop calling tools and wait for `security-reviewer` to return its report. Present the findings to the user along with an executive triage verdict (`Block Release`, `Fix Before Merge`, or `Safe to Ship`).
