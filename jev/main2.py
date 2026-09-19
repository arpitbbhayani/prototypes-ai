"""PR Sentinel: AI-powered pull request risk & release gatekeeper.

Jev evaluates PR diffs and descriptions against typed risk criteria.
Plain Python implements release safety gates and merge policies.
Terminal presentation follows the ape-cli-terminal-experience skill.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient, TypeSafeError

import ui

PULL_REQUESTS = [
    {
        "number": 1042,
        "author": "maya, frontend",
        "title": "Bump lodash and fix markdown links in developer README",
        "diff_summary": "Package.json dependency version bump from 4.17.20 to 4.17.21. Fixed 3 broken URLs in README.md.",
    },
    {
        "number": 1043,
        "author": "chen, backend",
        "title": "Drop legacy password hash column and alter accounts foreign key",
        "diff_summary": "Migration script drops accounts.legacy_hash without fallback. Recreates foreign key on orders without NOT VALID clause on a 50M row table.",
    },
    {
        "number": 1044,
        "author": "elena, security",
        "title": "Migrate session tokens from HS256 to RS256 with key rotation",
        "diff_summary": "Adds public key verification endpoint, dual-validates old HS256 and new RS256 tokens during 14-day transition period.",
    },
    {
        "number": 1045,
        "author": "marcus, devops",
        "title": "Update k8s ingress rate limiting and decrease min replicas to 1",
        "diff_summary": "Configures Envoy rate limiter filter to 50 req/sec per IP and reduces core payment API minimum pod count to 1 to save cloud costs.",
    },
]

QUESTIONS = {
    "risk_category": Choice(
        instructions="What primary architectural domain does this pull request affect?",
        criteria={
            "docs": "Documentation, typos, formatting, comments",
            "frontend": "Client UI, stylesheets, non-critical web components",
            "backend": "Application business logic, API controllers, worker tasks",
            "database": "Schema migrations, ORM changes, index modifications",
            "security": "Authentication, authorization, secrets, cryptography",
            "infra": "Kubernetes manifests, Terraform, CI/CD pipelines, rate limits",
        },
    ),
    "breaking_change": Noul(
        instructions="The changes in this PR introduce breaking compatibility issues for existing API consumers, databases, or dependent microservices.",
    ),
    "downtime_risk": Noul(
        instructions="Applying or merging this PR carries a significant risk of table locks, outage, connection exhaustion, or high latency.",
    ),
    "reversibility": Score(
        instructions="How easy and safe is it to rollback or revert this change if an issue occurs in production?",
        criteria=[
            "Catastrophic/Irreversible: data loss or manual database repair required",
            "Difficult: requires forward-fix, data backfill, or cache flush",
            "Moderate: standard git revert and full service redeployment required",
            "Instant: feature-flagged, additive-only, zero-downtime rollback",
        ],
    ),
}


def gatekeep(result: Any) -> tuple[str, str, str]:
    """Release safety policy: plain Python over Jev's typed judgments.

    Returns (decision, detail, role).
    """
    category = result.choices["risk_category"]
    breaking = result.nouls["breaking_change"].noul
    downtime = result.nouls["downtime_risk"].noul
    reversibility = result.scores["reversibility"].score  # 0..3

    if category.confidence < 0.5:
        decision = "Uncertain"
        detail = "Ambiguous risk profile. Escalating to Staff Engineer for manual inspection."
        role = "info"
    elif category.choice == "database" and (downtime > 0.6 or reversibility < 2):
        decision = "Blocked"
        detail = "Hazardous database migration: lock/downtime risk or poor reversibility."
        role = "err"
    elif breaking > 0.7:
        decision = "Blocked"
        detail = "High probability of breaking backward compatibility without deprecation window."
        role = "err"
    elif category.choice in ("infra", "security"):
        if downtime > 0.5 or reversibility < 2:
            decision = "Blocked"
            detail = "Critical infra/security change with elevated outage or rollback hazards."
            role = "err"
        else:
            decision = "Review Required"
            detail = "Requires approval from Security/Infra code owners before merge."
            role = "warn"
    elif reversibility >= 2 and breaking < 0.2 and downtime < 0.2:
        decision = "Auto-Approved"
        detail = "Safe low-blast-radius change. Fast-track merge gate approved."
        role = "ok"
    else:
        decision = "Review Required"
        detail = "Standard peer review required before staging deployment."
        role = "warn"

    return decision, detail, role


def format_record(pr: dict[str, Any], result: Any, duration: float) -> dict[str, Any]:
    """Structure PR evaluation record for presentation and JSON output."""
    category = result.choices["risk_category"]
    breaking = result.nouls["breaking_change"].noul
    downtime = result.nouls["downtime_risk"].noul
    reversibility = result.scores["reversibility"]
    decision, detail, role = gatekeep(result)

    return {
        "number": pr.get("number", 0),
        "author": pr.get("author", "unknown"),
        "title": pr.get("title", "Untitled PR"),
        "diff_summary": pr.get("diff_summary", ""),
        "risk_category": category.choice,
        "category_confidence": category.confidence,
        "breaking_change": breaking,
        "downtime_risk": downtime,
        "reversibility": reversibility.score,
        "decision": decision,
        "detail": detail,
        "role": role,
        "request_time": round(duration, 2),
    }


def render_pr(record: dict[str, Any]) -> None:
    """Render a single PR evaluation using the 7 line shapes."""
    ui.heading(f"PR #{record['number']} · {record['author']}")
    ui.kv("title", record["title"], width=16)
    ui.kv("summary", f'"{record["diff_summary"]}"', width=16)
    ui.kv(
        "risk category",
        f"{record['risk_category']} (confidence {record['category_confidence']:.2f})",
        width=16,
    )
    ui.kv("breaking", f"{record['breaking_change']:.2f}", width=16)
    ui.kv("downtime risk", f"{record['downtime_risk']:.2f}", width=16)
    ui.kv("reversibility", f"{record['reversibility']:.2f} / 3", width=16)
    ui.kv("request time", f"{record['request_time']:.2f}s", width=16)

    ui._status(record["role"], record["decision"].lower(), record["detail"], stream=sys.stdout)


def render_summary(records: list[dict[str, Any]]) -> None:
    """Render an aligned PR listing summary using ui.table."""
    ui.heading("pull request gatekeeper summary", len(records))

    def outcome_color(decision: str) -> str | None:
        if decision == "Auto-Approved":
            return "71"  # ok (muted green)
        if decision == "Blocked":
            return "167"  # err (muted red)
        if decision == "Review Required":
            return "179"  # warn (muted amber-yellow)
        return "110"  # info (muted blue)

    rows = [
        [
            f"#{r['number']}",
            r["author"],
            r["risk_category"],
            f"{r['reversibility']:.2f} / 3",
            f"{r['request_time']:.2f}s",
            r["decision"],
        ]
        for r in records
    ]
    ui.table(rows, color=(5, outcome_color), dims=(1, 2, 3, 4))

    total_time = sum(r["request_time"] for r in records)
    ui.hint(f"{len(records)} pull requests evaluated in {total_time:.2f}s · try next:")
    ui.command('python main2.py review --number 1046 --author "sam, sre" --title "..." --diff "..."')


def evaluate_prs(prs: list[dict[str, Any]], is_json: bool) -> int:
    """Adjudicate pull requests with TypeSafeClient, handling progress narration."""
    if not is_json:
        ui.heading("pull request sentinel", len(prs))
        ui.rule()

    adjudicated: list[dict[str, Any]] = []

    with TypeSafeClient() as client:
        for pr in prs:
            t0 = time.monotonic()
            with ui.spinner(f"Analyzing PR #{pr.get('number', 0)}: {pr.get('title', '')}"):
                case_input = {
                    "title": pr.get("title", ""),
                    "diff": pr.get("diff_summary", ""),
                    "author": pr.get("author", ""),
                }
                result = client.system_one(case_input, QUESTIONS)
            duration = time.monotonic() - t0

            record = format_record(pr, result, duration)
            adjudicated.append(record)

            if not is_json:
                render_pr(record)

    if is_json:
        print(json.dumps(adjudicated, indent=2), file=sys.stdout, flush=True)
    else:
        if len(adjudicated) > 1:
            ui.rule()
            render_summary(adjudicated)

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pr-sentinel",
        description="PR Sentinel: Automated PR risk & release gatekeeper powered by Jev.",
    )
    parser.add_argument("--no-color", action="store_true", help="Force colour off, keeping Unicode glyphs and rules intact")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output on stdout, quiet narration")
    parser.add_argument("--quiet", action="store_true", help="Suppress narration and spinners, keeping only essential output")
    parser.add_argument("--yes", action="store_true", help="Accept defaults for all prompts without blocking")

    subparsers = parser.add_subparsers(dest="subcommand")

    # 'queue' subcommand
    queue_parser = subparsers.add_parser("queue", help="Evaluate the staging PR queue")
    queue_parser.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    queue_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    queue_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    queue_parser.add_argument("--yes", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    # 'review' subcommand
    review_parser = subparsers.add_parser("review", help="Review an individual PR")
    review_parser.add_argument("--number", type=int, default=0, help="PR number")
    review_parser.add_argument("--author", type=str, default="", help="Author handle and team")
    review_parser.add_argument("--title", type=str, default="", help="PR title")
    review_parser.add_argument("--diff", type=str, default="", help="PR diff summary")
    review_parser.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    review_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    review_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    review_parser.add_argument("--yes", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    return parser.parse_args(argv)


def cli_main(argv: list[str] | None = None) -> int:
    ui.init()
    args = parse_args(argv)

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

    if args.subcommand == "review":
        number = args.number or 1001
        author = args.author
        title = args.title
        diff = args.diff

        if not author:
            author = ui.prompt("PR author handle and role", default="dev, engineering")
        if not title:
            title = ui.prompt("PR title")
            if not title:
                raise ui.Cancelled("no PR title provided")
        if not diff:
            diff = ui.prompt("PR diff summary")
            if not diff:
                raise ui.Cancelled("no PR diff provided")

        pr_data = {
            "number": number,
            "author": author,
            "title": title,
            "diff_summary": diff,
        }
        return evaluate_prs([pr_data], is_json)

    # Default: evaluate standard queue
    return evaluate_prs(PULL_REQUESTS, is_json)


def main() -> None:
    sys.exit(ui.run(cli_main, {TypeSafeError: 2}))


if __name__ == "__main__":
    main()
