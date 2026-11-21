## Core Mental Models

Before running the demo, anchor learners on five concepts:

1. Progressive disclosure: Antigravity loads only skill names and descriptions on each turn. It reads `SKILL.md` only when the skill matches the task.
2. No `context: fork` frontmatter: Antigravity skills do not fork automatically via YAML frontmatter. Instead, `SKILL.md` instructs the main agent to call subagent tools (`define_subagent` and `invoke_subagent`).
3. Context isolation: Every subagent starts with a blank context window. Subagents do not see the parent chat history or the parent `SKILL.md`, so the parent must pass self-contained prompts and an explicit output contract.
4. Reactive wakeup: Subagents run asynchronously in parallel. The parent stops calling tools and wakes automatically when subagents report back, without polling.
5. Least privilege: Read-only audit subagents run without write permissions (`EnableWriteTools: false` or a read-only `tools` list).

## Architecture Overview

```text
User Prompt
    |
    v
Main Agent (Coordinator)
    |-- 1. Reads SKILL.md (progressive disclosure)
    |-- 2. Registers or selects subagent types
    |-- 3. Spawns isolated subagents in parallel (invoke_subagent)
    |
    +---------------------+----------------------+
    |                     |                      |
    v                     v                      v
[Security Auditor]  [Performance Auditor]  [Reliability Auditor]
(clean context)     (clean context)        (clean context)
    |                     |                      |
    +---------------------+----------------------+
    |
    v  4. Reactive wakeup (reports return automatically)
Main Agent synthesizes one unified report for the user
```

## How Subagent Output Reaches the Main Agent

Subagents run in isolated background conversations and do not write directly to the user's chat session. The main agent does not poll subagents or read their transcript files from disk. Instead, the Antigravity runtime delivers subagent responses through its internal messaging system:

1. Calling `invoke_subagent` starts each subagent in the background and returns a `conversationId`. The main agent then ends its turn without calling more tools.
1. When a subagent finishes, the runtime wakes the main agent and injects the subagent's full message directly into the parent conversation context, tagged with the subagent's `conversationId` and timestamp.
1. Reports arrive asynchronously as each subagent completes. The main agent waits until every launched subagent has reported back.
1. Once all reports are in context, the main agent merges the findings and presents one synthesized report in the current session.

No workspace files are created during the audit unless the prompt asks for them. Each subagent's full execution log is saved on disk at `<appDataDir>/brain/<subagent-conversation-id>/.system_generated/logs/transcript.jsonl` and can be inspected in the CLI with `/agents`.

## Comparing Antigravity Subagent Patterns

| Pattern                  | Where Defined                         | Lifetime            | Best Used For                                               |
| ------------------------ | ------------------------------------- | ------------------- | ----------------------------------------------------------- |
| Built-in subagents       | Bundled (`research`, `self`, `browser`) | Always available    | General codebase research, browser checks, or cloning self  |
| Dynamic subagents        | `define_subagent` inside a `SKILL.md` | Current session     | Task-specific specialists tightly coupled to one skill      |
| File-based custom agents | `.agents/agents/<name>.md`            | Persistent in repo  | Reusable specialists shared across skills and `/agents`     |

## Defining Subagents in a Skill

Skills can use subagents in two ways: define them dynamically at runtime inside `SKILL.md`, or reference a persistent file-based agent from `.agents/agents/`.

### Pattern 1: Dynamic Subagents Inside `SKILL.md`

Use this pattern when a specialist is specific to one skill and does not need to persist across sessions. Write step-by-step instructions in `.agents/skills/<skill-name>/SKILL.md` telling the main agent to register types with `define_subagent` and launch them with `invoke_subagent`.

Key fields to specify for `define_subagent`:

- `Name`: Unique identifier passed later as `TypeName` in `invoke_subagent`.
- `Description`: Short summary of what the subagent does and when to use it.
- `SystemPrompt`: Instructions that scope the subagent's role, constraints, and output format.
- `EnableWriteTools`: Set to `false` for read-only auditors or `true` when the subagent must edit files or run commands.
- `EnableMCPTools` and `EnableSubagentTools`: Optional booleans to grant MCP access or nested subagent delegation.

Key fields to specify for `invoke_subagent`:

- `TypeName`: Matches the `Name` registered with `define_subagent`.
- `Role`: Short 2-5 word label shown in `/agents` (for example, `Security Auditor`).
- `Prompt`: Self-contained task prompt with exact file paths and output format, because subagents start with a blank context window.
- `Workspace`: `inherit` to share the current workspace (recommended for read-only subagents), `branch` for an isolated clone, or `share` for a worktree-style shared repo copy.
- `Model`: Optional override (`inherit`, `flash_lite`, `flash`, or `pro`).

Minimal example inside `.agents/skills/my-audit/SKILL.md`:

```markdown
---
name: my-audit
description: Audits a target file using a read-only specialist subagent.
---

## Step 1: Define the Subagent Type

Call `define_subagent` with:

- `Name: "security-auditor"`
- `Description: "Audits source files for security vulnerabilities."`
- `EnableWriteTools: false`
- `SystemPrompt`: Instruct the subagent to read the target file and report only security issues.

## Step 2: Launch the Subagent

Call `invoke_subagent` with:

- `TypeName: "security-auditor"`
- `Role: "Security Auditor"`
- `Workspace: "inherit"`
- `Prompt`: Include the exact target file path and the required Markdown output format.

## Step 3: Wait and Synthesize

Stop calling tools after launching the subagent. Wait for its message to arrive, then present the final report.
```

To fan out in parallel, instruct the main agent to issue multiple `define_subagent` calls in one turn and multiple `invoke_subagent` calls in the next turn, as shown in `.agents/skills/parallel-code-audit/SKILL.md`.

### Pattern 2: File-Based Custom Subagents Referenced by a Skill

Use this pattern when you want a reusable specialist available across multiple skills and sessions. Create a Markdown file in `.agents/agents/<name>.md` with YAML frontmatter and a system prompt body:

```markdown
---
name: security-reviewer
description: Persistent read-only subagent that audits source files for security vulnerabilities.
tools:
  - view_file
  - grep_search
subagent: true
mainAgent: false
model: flash
commandExecutionPolicy: off
---

# System Prompt

You are a dedicated security code reviewer. Inspect target files strictly for security flaws without modifying any files.
```

Antigravity discovers `.agents/agents/*.md` automatically at startup. In your `SKILL.md`, skip `define_subagent` and instruct the main agent to call `invoke_subagent` directly with `TypeName: "security-reviewer"`, as shown in `.agents/skills/security-triage/SKILL.md`.

## Project Layout

```text
subagents-skill/
├── README.md
├── .agents/
│   ├── skills/
│   │   ├── parallel-code-audit/
│   │   │   └── SKILL.md              # Pattern 1: Dynamic subagents in parallel
│   │   └── security-triage/
│   │       └── SKILL.md              # Pattern 2: Invoking a file-based custom subagent
│   └── agents/
│       └── security-reviewer.md      # Persistent read-only custom subagent
└── sample_app/
    └── user_service.py               # 75-line stdlib Python file with planted bugs
```

## Prerequisites

- Antigravity CLI (`agy`) or Antigravity App installed and authenticated.

## Live Demo Walkthrough

### Demo 1: Parallel Dynamic Subagents (`parallel-code-audit`)

1. Start Antigravity CLI from this directory (or open the folder in the Antigravity App):

```bash
agy
```

2. Run the skill:

```text
Run the parallel-code-audit skill on sample_app/user_service.py
```

3. While the three subagents run, open the subagent inspector:
   - In Antigravity CLI: type `/agents`, highlight any subagent, and press `Enter` to view its isolated reasoning log and tool calls. Press `Esc` to return.
   - In Antigravity App: open Overview > Subagents in the side panel and click any subagent thread.

### Demo 2: Skill Calling a File-Based Custom Subagent (`security-triage`)

1. In the same session (or a fresh one), run:

```text
Run the security-triage skill on sample_app/user_service.py
```

2. Point out the difference: the main agent skips `define_subagent` and calls `invoke_subagent` directly with `TypeName: "security-reviewer"` because Antigravity discovered `.agents/agents/security-reviewer.md` automatically.
