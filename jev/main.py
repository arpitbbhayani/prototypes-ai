"""Outage Excuse Court: Jev judges why prod went down, code hands out the sentence.

Jev answers narrow typed questions about each excuse. The courtroom rules
(what counts as guilty, what the punishment is) live in plain Python below.
Terminal experience follows the ape-cli-terminal-experience skill.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient, TypeSafeError

import ui

EXCUSES = [
    {
        "engineer": "Priya, backend",
        "excuse": "Checkout was down for 40 minutes. Turns out our DNS TTL was set to "
        "a week and the old load balancer IP got recycled. Classic.",
    },
    {
        "engineer": "Dave, platform",
        "excuse": "I merged at 5:45pm Friday because the tests were green. Honestly I "
        "think a cosmic ray flipped a bit in the config. Mercury is also in retrograde.",
    },
    {
        "engineer": "Sam, SRE",
        "excuse": "My migration dropped an index on the orders table. I rolled it back, "
        "added a CI check, and wrote the postmortem already. That one is on me.",
    },
    {
        "engineer": "Alex, frontend",
        "excuse": "It worked on my machine. The new intern probably touched something. "
        "Or AWS. Probably AWS.",
    },
]

QUESTIONS = {
    "blames": Choice(
        instructions="Who or what does `excuse` blame for the outage?",
        criteria={
            "dns": "DNS records, TTLs, or name resolution",
            "cache": "A stale, cold, or poisoned cache",
            "vendor": "A cloud provider or third-party service",
            "teammate": "Another person, such as an intern or a colleague",
            "cosmic": "Cosmic rays, solar flares, astrology, gremlins, or bad luck",
            "self": "The engineer's own change or mistake",
        },
    ),
    "owns_it": Noul(
        instructions="In `excuse`, the engineer takes personal responsibility for the outage.",
        criteria={
            "true": "They admit their part and describe fixing or preventing it.",
            "false": "They deflect, speculate, or blame something else.",
        },
    ),
    "friday_deploy": Noul(
        instructions="According to `excuse`, the change that caused the outage was shipped "
        "on a Friday afternoon or evening.",
    ),
    "plausibility": Score(
        instructions="How plausible is `excuse` as the real root cause of a production outage?",
        criteria=[
            "Supernatural or physically absurd; no engineer would accept it",
            "Vague hand-waving with no evidence of an actual failure",
            "A believable failure mode, but unconfirmed",
            "A concrete, well-evidenced root cause seen in real production systems",
        ],
    ),
}


def sentence(result: Any) -> tuple[str, str, str]:
    """Courtroom policy: plain code over Jev's typed judgments.

    Returns (category, verdict_text, role).
    """
    blames = result.choices["blames"]
    owns_it = result.nouls["owns_it"].noul
    friday = result.nouls["friday_deploy"].noul
    plausible = result.scores["plausibility"].score  # 0..3

    if blames.confidence < 0.5:
        category = "Hung Jury"
        verdict = "Hung jury. Escalated to the SRE council."
        role = "info"
    elif owns_it > 0.8:
        category = "Acquitted"
        verdict = "Acquitted with honors. Blameless postmortem, buy this person a coffee."
        role = "ok"
    elif blames.choice == "dns" and plausible >= 2:
        category = "Dismissed"
        verdict = "It's always DNS. Case dismissed."
        role = "ok"
    elif blames.choice == "cosmic":
        category = "Guilty"
        verdict = "Guilty. Must write the postmortem in rhyming couplets."
        role = "err"
    elif blames.choice in ("teammate", "vendor") and plausible < 2:
        category = "Guilty"
        verdict = "Guilty of finger-pointing. Must pair with the intern for a week."
        role = "err"
    else:
        category = "Probation"
        verdict = "Probation. Add a runbook before the next on-call shift."
        role = "warn"

    if friday > 0.7:
        verdict += " Plus: pizza for the entire on-call rotation (Friday deploy)."

    return category, verdict, role


def format_record(case: dict[str, str], result: Any, duration: float) -> dict[str, Any]:
    """Structure the evaluation result for display and serialization."""
    blames = result.choices["blames"]
    owns_it = result.nouls["owns_it"].noul
    friday = result.nouls["friday_deploy"].noul
    plausibility = result.scores["plausibility"]
    category, verdict, role = sentence(result)

    return {
        "engineer": case["engineer"],
        "excuse": case["excuse"],
        "blames": blames.choice,
        "blames_confidence": blames.confidence,
        "owns_it": owns_it,
        "friday_deploy": friday,
        "plausibility": plausibility.score,
        "category": category,
        "verdict": verdict,
        "role": role,
        "request_time": round(duration, 2),
    }


def render_case(record: dict[str, Any]) -> None:
    """Render a single case evaluation using the ape line grammar."""
    ui.heading(record["engineer"])
    ui.kv("excuse", f'"{record["excuse"]}"', width=16)
    ui.kv(
        "blames",
        f"{record['blames']} (confidence {record['blames_confidence']:.2f})",
        width=16,
    )
    ui.kv("owns it", f"{record['owns_it']:.2f}", width=16)
    ui.kv("friday deploy", f"{record['friday_deploy']:.2f}", width=16)
    ui.kv("plausibility", f"{record['plausibility']:.2f} / 3", width=16)
    ui.kv("request time", f"{record['request_time']:.2f}s", width=16)

    # Route verdict status lines to stdout so they read sequentially with kv lines
    ui._status(record["role"], record["category"].lower(), record["verdict"], stream=sys.stdout)


def render_summary(records: list[dict[str, Any]]) -> None:
    """Render an aligned listing summary using the shared table formatter."""
    ui.heading("court proceedings summary", len(records))

    def outcome_color(cat: str) -> str | None:
        if cat in ("Acquitted", "Dismissed"):
            return "71"  # ok (muted green)
        if cat == "Guilty":
            return "167"  # err (muted red)
        if cat == "Probation":
            return "179"  # warn (muted amber-yellow)
        return "110"  # info (muted blue)

    rows = [
        [
            r["engineer"],
            r["blames"],
            f"{r['plausibility']:.2f} / 3",
            f"{r['request_time']:.2f}s",
            r["category"],
        ]
        for r in records
    ]
    ui.table(rows, color=(4, outcome_color), dims=(1, 2, 3))

    total_time = sum(r["request_time"] for r in records)
    ui.hint(f"{len(records)} cases evaluated in {total_time:.2f}s · try next:")
    ui.command('python main.py judge --engineer "Pat, devops" --excuse "..."')


def judge_cases(cases: list[dict[str, str]], is_json: bool) -> int:
    """Run adjudication with TypeSafeClient, handling progress narration."""
    if not is_json:
        ui.heading("outage excuse court", len(cases))
        ui.rule()

    adjudicated: list[dict[str, Any]] = []

    with TypeSafeClient() as client:
        for case in cases:
            t0 = time.monotonic()
            # Spinner writes to stderr and erases cleanly on completion
            with ui.spinner(f"Deliberating on {case['engineer']}'s excuse"):
                result = client.system_one(case, QUESTIONS)
            duration = time.monotonic() - t0

            record = format_record(case, result, duration)
            adjudicated.append(record)

            if not is_json:
                render_case(record)

    if is_json:
        # --json output is raw unadorned data on stdout
        print(json.dumps(adjudicated, indent=2), file=sys.stdout, flush=True)
    else:
        if len(adjudicated) > 1:
            ui.rule()
            render_summary(adjudicated)

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jev",
        description="Outage Excuse Court: Jev judges why prod went down, code hands out the sentence.",
    )
    # Global flags
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Force colour off, keeping Unicode glyphs and rules intact",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output on stdout, quiet narration",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress narration and spinners, keeping only essential output",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accept defaults for all prompts without blocking",
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    # 'docket' subcommand
    docket_parser = subparsers.add_parser(
        "docket", help="Adjudicate the queued docket of incident excuses"
    )
    docket_parser.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    docket_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    docket_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    docket_parser.add_argument("--yes", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    # 'judge' subcommand
    judge_parser = subparsers.add_parser("judge", help="Judge a single engineer excuse")
    judge_parser.add_argument(
        "--engineer",
        type=str,
        default="",
        help="Engineer name and team (e.g. 'Alex, frontend')",
    )
    judge_parser.add_argument(
        "--excuse",
        type=str,
        default="",
        help="The explanation or excuse given for the outage",
    )
    judge_parser.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    judge_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    judge_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    judge_parser.add_argument("--yes", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    return parser.parse_args(argv)


def cli_main(argv: list[str] | None = None) -> int:
    ui.init()
    args = parse_args(argv)

    # Handle global flags regardless of whether passed before or after subcommand
    is_json = bool(getattr(args, "json", False))
    is_no_color = bool(getattr(args, "no_color", False))
    is_quiet = bool(getattr(args, "quiet", False))
    is_yes = bool(getattr(args, "yes", False))

    if is_json:
        ui.set_quiet(True)
        ui.set_color(False)
    if is_no_color:
        ui.set_color(False)
    if is_quiet:
        ui.set_quiet(True)
    if is_yes:
        ui.set_yes(True)

    if args.subcommand == "judge":
        engineer = args.engineer
        excuse = args.excuse

        if not engineer:
            engineer = ui.prompt("engineer name and role", default="Anonymous Engineer")
        if not excuse:
            excuse = ui.prompt("outage excuse")
            if not excuse:
                raise ui.Cancelled("no excuse provided")

        return judge_cases([{"engineer": engineer, "excuse": excuse}], is_json)

    # Default: judge the pre-configured docket
    return judge_cases(EXCUSES, is_json)


def main() -> None:
    # Top-level entry point wrapped in ui.run() for consistent exit code orchestration
    sys.exit(ui.run(cli_main, {TypeSafeError: 2}))


if __name__ == "__main__":
    main()
