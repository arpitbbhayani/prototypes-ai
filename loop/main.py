#!/usr/bin/env python3
"""Educational Agent Loop in a Single File.

This script demonstrates what an AI Agent Loop actually is under the hood:
  A simple iterative control loop (Think -> Act -> Observe -> Repeat).

Core Lifecycle:
  1. THINK   - Prompt LLM with conversation history and available tools (streamed).
  2. ACT     - Inspect if the model requested any tool / function calls.
  3. OBSERVE - Safely run the Python functions, catch errors, format observations.
  4. REPEAT  - Append tool observations back to history and repeat until the model
               decides it is finished (no more tool calls) or limits are reached.

Key Architectural Components:
  - Tools: Ordinary Python functions passed directly to the agent.
  - Guardrails: Maximum turn limits and tool retry tracking to prevent runaway loops.
  - Lifecycle Hooks: Callbacks for logging, observability, and debugging.
  - Streaming: Real-time token output directly to the terminal.
  - Terminal UX: Claude Code / ape-cli aesthetic (muted palette, glyphs, no emoji).
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from google import genai
from google.genai import types

# ==============================================================================
# 1. TERMINAL PRESENTATION (ape-cli terminal experience)
# ==============================================================================
# Palette: 256-color codes (muted, semantic, mostly grey, no bright clown colors)
_ACCENT = "208"  # amber: prompt, active step, highlight
_OK = "71"       # muted green: tool success, finish
_ERR = "167"     # muted red: errors, tool failure
_WARN = "179"    # muted yellow: warnings, retries
_INFO = "110"    # muted blue: turn info, narration
_DIM = "245"     # secondary details, parameter values
_FAINT = "240"   # rules, borders, chrome

_GLYPHS = {
    "ok": ("✓", "[OK]", _OK),
    "err": ("✗", "[FAIL]", _ERR),
    "warn": ("!", "[WARN]", _WARN),
    "info": ("·", "[INFO]", _INFO),
    "step": ("›", ">", _ACCENT),
}


def is_tty(stream=None) -> bool:
    """Check if stream is an interactive terminal."""
    stream = stream or sys.stdout
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def color_enabled(stream=None) -> bool:
    """Check if ANSI color escape sequences are allowed."""
    if os.environ.get("NO_COLOR"):
        return False
    force = os.environ.get("FORCE_COLOR")
    if force is not None:
        return force not in ("0", "false")
    if os.environ.get("TERM") == "dumb":
        return False
    return is_tty(stream)


def paint(text: str, code: str, *, bold: bool = False, stream=None) -> str:
    """Format text with ANSI 256-color code if coloring is supported."""
    if not text or not color_enabled(stream):
        return text
    prefix = "\033[1m" if bold else ""
    return f"{prefix}\033[38;5;{code}m{text}\033[0m"


def dim(text: str, stream=None) -> str:
    return paint(text, _DIM, stream=stream)


def faint(text: str, stream=None) -> str:
    return paint(text, _FAINT, stream=stream)


def accent(text: str, stream=None) -> str:
    return paint(text, _ACCENT, stream=stream)


def strong(text: str, stream=None) -> str:
    return f"\033[1m{text}\033[0m" if color_enabled(stream) else text


def glyph(role: str, stream=None) -> str:
    """Select appropriate glyph: unicode for TTY, bracketed ASCII for piped stdout."""
    mark, fallback, code = _GLYPHS[role]
    chosen = mark if is_tty(stream) else fallback
    return paint(chosen, code, stream=stream)


def status(role: str, message: str, detail: str = "", *, stream=None) -> None:
    """Print standard status line: <glyph> <message>  <dim detail>"""
    stream = stream or sys.stdout
    line = f"{glyph(role, stream)} {message}"
    if detail:
        line += f"  {dim(detail, stream=stream)}"
    print(line, file=stream, flush=True)


def heading(title: str, subtitle: str = "", *, stream=None) -> None:
    """Print a bold heading with optional dimmed subtitle."""
    stream = stream or sys.stdout
    print(file=stream)
    line = strong(title, stream=stream)
    if subtitle:
        line += f" {dim(f'({subtitle})', stream=stream)}"
    print(line, file=stream, flush=True)


def rule(stream=None) -> None:
    """Print a subtle horizontal divider line in TTY mode."""
    stream = stream or sys.stdout
    if is_tty(stream):
        print(faint("─" * 60, stream=stream), file=stream, flush=True)


def kv(label: str, value: str, width: int = 16, stream=None) -> None:
    """Print key-value summary row with aligned dimmed label."""
    stream = stream or sys.stdout
    print(f"  {dim(label.ljust(width), stream=stream)} {value}", file=stream, flush=True)


# ==============================================================================
# 2. TOOLS (Simple Python functions passed to the agent)
# ==============================================================================
# In Google GenAI SDK, any standard Python function with type annotations
# and a docstring can be passed directly to the model as a tool!

def get_weather(city: str) -> str:
    """Get the current weather conditions and temperature for a given city."""
    forecasts = {
        "tokyo": "Sunny, 22°C with light wind",
        "paris": "Partly cloudy, 17°C",
        "san francisco": "Morning mist clearing to 19°C",
        "bengaluru": "Clear skies, 26°C with gentle breeze",
        "london": "Light drizzle, 14°C",
    }
    key = city.strip().lower()
    if key in forecasts:
        return f"Weather in {city}: {forecasts[key]}"
    return f"Weather in {city}: Clear skies, 20°C"


def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression like '42 * 17' or 'sqrt(144)'."""
    allowed_names = {
        "sqrt": math.sqrt,
        "pow": math.pow,
        "pi": math.pi,
        "abs": abs,
        "round": round,
    }
    try:
        # Evaluate within a restricted namespace for safety
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as exc:
        raise ValueError(f"Math error in '{expression}': {exc}") from exc


def search_knowledge_base(topic: str) -> str:
    """Search internal facts and definitions for a topic or keyword."""
    knowledge = {
        "agent loop": (
            "An agent loop is a while-loop pattern where an LLM is queried iteratively. "
            "If the model requests tool calls, the program runs them and feeds the "
            "results back. The loop ends when the model produces a final answer."
        ),
        "guardrail": (
            "Guardrails are programmatic limits—such as maximum loop turns, "
            "tool retry limits, and output validation—that keep agents predictable."
        ),
        "hooks": (
            "Lifecycle hooks are callbacks fired during agent execution "
            "(e.g., on_turn_start, on_tool_call) to allow external observability."
        ),
    }
    normalized = topic.strip().lower()
    for key, text in knowledge.items():
        if key in normalized or normalized in key:
            return text
    return f"No specific entry found for '{topic}'. Available topics: agent loop, guardrail, hooks."


DEFAULT_TOOLS = [get_weather, calculate, search_knowledge_base]


# ==============================================================================
# 3. GUARDRAILS & HOOKS
# ==============================================================================

@dataclass
class Guardrails:
    """Safety bounds to prevent infinite loops and runaway retries."""

    max_turns: int = 6           # Max reasoning/tool cycles before breaking
    max_tool_retries: int = 2    # Consecutive retries allowed per tool on failure


@dataclass
class AgentHooks:
    """Lifecycle callbacks triggered at key moments in the agent loop.

    Allows you to attach logging, UI spinners, metrics, or telemetry
    without polluting the core decision loop logic.
    """

    on_turn_start: Callable[[int, int], None] = lambda turn, max_turns: None
    on_stream_chunk: Callable[[str], None] = lambda chunk: None
    on_tool_call: Callable[[str, dict[str, Any]], None] = lambda name, args: None
    on_tool_result: Callable[[str, Any, bool], None] = lambda name, result, is_error: None
    on_turn_end: Callable[[int], None] = lambda turn: None
    on_finish: Callable[[str, int], None] = lambda final_text, total_turns: None


# ==============================================================================
# 4. THE CORE AGENT LOOP
# ==============================================================================

def run_agent_loop(
    prompt: str,
    tools: list[Callable],
    model: str = "gemini-2.5-flash",
    guardrails: Guardrails | None = None,
    hooks: AgentHooks | None = None,
    client: genai.Client | None = None,
) -> str:
    """Run the educational Think -> Act -> Observe -> Repeat Agent Loop.

    Under the hood, an AI agent is simply:
      while True:
          response = LLM(conversation_history + tools)
          if response wants to call tools:
              results = execute_tools(response.tool_calls)
              conversation_history.append(results)
          else:
              return response.text

    Args:
        prompt: The user query or task.
        tools: List of Python functions available to the agent.
        model: Gemini model name.
        guardrails: Safety limits (max turns, retries).
        hooks: Lifecycle callbacks.
        client: Google GenAI Client instance.

    Returns:
        The final response text from the agent.
    """
    guardrails = guardrails or Guardrails()
    hooks = hooks or AgentHooks()
    client = client or genai.Client()

    # Dynamic registry mapping tool names to actual Python functions
    tool_map: dict[str, Callable] = {fn.__name__: fn for fn in tools}

    # Track consecutive failures per tool for the retry guardrail
    tool_failure_counts: dict[str, int] = {}

    # Initial conversation history starting with the user's prompt
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]

    # Model configuration:
    # We explicitly disable automatic function calling (AFC) so that
    # WE control the loop, execute the tools, and observe what happens!
    config = types.GenerateContentConfig(
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        system_instruction=(
            "You are a helpful AI assistant with access to tools. "
            "Solve the user's request step-by-step. Use tools whenever needed. "
            "When you have enough information, give a clear, direct answer."
        ),
    )

    turn = 0
    final_text_accumulated = ""

    # ==========================================================================
    # THE MAIN LOOP
    # ==========================================================================
    while turn < guardrails.max_turns:
        turn += 1
        hooks.on_turn_start(turn, guardrails.max_turns)

        # ----------------------------------------------------------------------
        # PHASE 1: THINK (Call LLM with conversation history and stream response)
        # ----------------------------------------------------------------------
        response_stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )

        model_parts: list[types.Part] = []
        function_calls: list[types.FunctionCall] = []
        turn_text = ""

        for chunk in response_stream:
            for candidate in chunk.candidates or []:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        model_parts.append(part)

                        # Check for streamed text token
                        if part.text:
                            turn_text += part.text
                            hooks.on_stream_chunk(part.text)

                        # Check for requested tool / function call
                        if part.function_call:
                            function_calls.append(part.function_call)

        # Append assistant's turn into conversation history
        contents.append(types.Content(role="model", parts=model_parts))

        # ----------------------------------------------------------------------
        # PHASE 2: ACT (Did the model decide to call tools?)
        # ----------------------------------------------------------------------
        if not function_calls:
            # No tool calls requested: the agent has finished its work!
            final_text_accumulated = turn_text.strip()
            hooks.on_finish(final_text_accumulated, turn)
            return final_text_accumulated

        # ----------------------------------------------------------------------
        # PHASE 3: OBSERVE (Execute tools, apply guardrails, format results)
        # ----------------------------------------------------------------------
        tool_response_parts: list[types.Part] = []

        for fc in function_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            hooks.on_tool_call(tool_name, tool_args)

            # Check if the requested tool exists
            if tool_name not in tool_map:
                error_msg = f"Unknown tool '{tool_name}'. Available: {list(tool_map.keys())}"
                hooks.on_tool_result(tool_name, error_msg, is_error=True)
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"error": error_msg},
                    )
                )
                continue

            # Execute tool with Guardrail: Retries & graceful exception handling
            func = tool_map[tool_name]
            try:
                result = func(**tool_args)
                tool_failure_counts[tool_name] = 0  # Reset failure count on success
                hooks.on_tool_result(tool_name, result, is_error=False)

                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result},
                    )
                )
            except Exception as exc:
                failures = tool_failure_counts.get(tool_name, 0) + 1
                tool_failure_counts[tool_name] = failures

                # Guardrail check: Have we exceeded retry budget for this tool?
                if failures > guardrails.max_tool_retries:
                    err_detail = (
                        f"Tool '{tool_name}' failed {failures} times. "
                        f"Retry guardrail reached. Error: {exc}. Do not retry this tool."
                    )
                else:
                    err_detail = (
                        f"Tool '{tool_name}' raised error: {exc}. "
                        f"Attempt {failures}/{guardrails.max_tool_retries}. Please fix arguments or adjust."
                    )

                hooks.on_tool_result(tool_name, err_detail, is_error=True)
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"error": err_detail},
                    )
                )

        # ----------------------------------------------------------------------
        # PHASE 4: REPEAT (Feed observations back into history for next turn)
        # ----------------------------------------------------------------------
        contents.append(types.Content(role="user", parts=tool_response_parts))
        hooks.on_turn_end(turn)

    # If the loop exited because turn limit was reached (Guardrail triggered)
    guardrail_msg = f"Guardrail triggered: Reached maximum of {guardrails.max_turns} turns without completion."
    status("warn", guardrail_msg)
    hooks.on_finish(guardrail_msg, turn)
    return guardrail_msg


# ==============================================================================
# 5. TERMINAL UI HOOKS IMPLEMENTATION
# ==============================================================================

def create_terminal_hooks() -> AgentHooks:
    """Build lifecycle hooks wired to our ape-cli terminal presentation."""

    def on_turn_start(turn: int, max_turns: int) -> None:
        heading(f"Turn {turn}/{max_turns}", "agent loop cycle")

    def on_stream_chunk(chunk: str) -> None:
        # Stream text directly as tokens arrive
        sys.stdout.write(chunk)
        sys.stdout.flush()

    def on_tool_call(name: str, args: dict[str, Any]) -> None:
        args_formatted = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        status("step", f"Model requested tool: {name}", f"({args_formatted})")

    def on_tool_result(name: str, result: Any, is_error: bool) -> None:
        summary = str(result)
        if len(summary) > 80:
            summary = summary[:77] + "..."
        if is_error:
            status("err", f"Tool {name} failed", summary)
        else:
            status("ok", f"Tool {name} succeeded", summary)

    def on_turn_end(turn: int) -> None:
        rule()

    def on_finish(final_text: str, total_turns: int) -> None:
        print(file=sys.stdout)  # newline after streaming completes
        rule()
        status("ok", "Agent loop complete", f"Total turns: {total_turns}")

    return AgentHooks(
        on_turn_start=on_turn_start,
        on_stream_chunk=on_stream_chunk,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_turn_end=on_turn_end,
        on_finish=on_finish,
    )


# ==============================================================================
# 6. DEMO ORCHESTRATION & CLI ENTRYPOINT
# ==============================================================================

def print_banner() -> None:
    """Print educational overview of the agent loop mechanics."""
    heading("The Agent Loop", "educational walkthrough")
    print(dim("  How an AI Agent actually works under the hood:"))
    print(f"  {paint('1. THINK', _ACCENT, bold=True)}   Send history & tool definitions to LLM (streaming)")
    print(f"  {paint('2. ACT', _ACCENT, bold=True)}     Check if LLM requested any tool/function calls")
    print(f"  {paint('3. OBSERVE', _ACCENT, bold=True)} Execute functions safely, apply guardrails, get results")
    print(f"  {paint('4. REPEAT', _ACCENT, bold=True)}  Feed observations back into history; repeat until done")
    rule()


def run_demo(user_prompt: str | None = None) -> None:
    """Run an educational walkthrough of the agent loop."""
    print_banner()

    prompt = user_prompt or (
        "What is the weather in Tokyo, and what is 18 multiplied by 24? "
        "Also check what our knowledge base says about agent loop."
    )

    heading("User Prompt")
    status("info", prompt)
    rule()

    hooks = create_terminal_hooks()
    guardrails = Guardrails(max_turns=5, max_tool_retries=2)

    try:
        run_agent_loop(
            prompt=prompt,
            tools=DEFAULT_TOOLS,
            guardrails=guardrails,
            hooks=hooks,
        )
    except Exception as exc:
        status("err", "Execution failed", str(exc))
        sys.exit(1)


def interactive_mode() -> None:
    """Run an interactive prompt session."""
    print_banner()
    heading("Interactive Mode", "type 'exit' or 'quit' to quit")
    hooks = create_terminal_hooks()
    guardrails = Guardrails(max_turns=6, max_tool_retries=2)

    while True:
        try:
            print()
            prompt = input(accent("Agent › ")).strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                status("info", "Exiting agent session.")
                break

            run_agent_loop(
                prompt=prompt,
                tools=DEFAULT_TOOLS,
                guardrails=guardrails,
                hooks=hooks,
            )
        except (KeyboardInterrupt, EOFError):
            print()
            status("info", "Session interrupted.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Educational Agent Loop: Think -> Act -> Observe -> Repeat",
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        help="Custom prompt to test with the agent loop.",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive REPL mode.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output.",
    )
    args = parser.parse_args()

    if args.no_color:
        os.environ["NO_COLOR"] = "1"

    if args.interactive:
        interactive_mode()
    else:
        run_demo(args.prompt)


if __name__ == "__main__":
    main()
