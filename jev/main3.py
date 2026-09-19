"""Pager Sentinel: AI-powered production alert triager & incident commander.

Jev analyzes alert telemetry, metric spikes, and payload context.
Plain Python implements escalation routing, paging policies, and noise filtering.
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

ALERTS = [
    {
        "id": "ALT-801",
        "service": "checkout-api",
        "name": "HighHttp500Rate",
        "source": "Datadog APM",
        "payload": "HTTP 500 error rate spiked to 14.8% across us-east-1 payment cluster over 5m window. Affecting stripe checkout endpoints.",
    },
    {
        "id": "ALT-802",
        "service": "staging-worker-04",
        "name": "DiskSpaceLow",
        "source": "Prometheus",
        "payload": "/var/log on staging-worker-04 reached 89% capacity. Non-production load generator logs rotating.",
    },
    {
        "id": "ALT-803",
        "service": "edge-gateway",
        "name": "BGPRouteFlapping",
        "source": "Network Sentinel",
        "payload": "Transit provider BGP session flapping 4 times in 10 minutes in us-west-2. Traffic automatically rerouted to backup interconnect.",
    },
    {
        "id": "ALT-804",
        "service": "redis-catalog",
        "name": "ReplicationLagHigh",
        "source": "AWS CloudWatch",
        "payload": "Read replica replication lag is 620ms. Primary CPU at 45%. Cache hit ratio steady at 98.4%.",
    },
]

QUESTIONS = {
    "alert_domain": Choice(
        instructions="What category of infrastructure or application failure does this alert describe?",
        criteria={
            "customer_api": "Customer-facing API outages, HTTP 5xx spikes, or payment failures",
            "database_cache": "Database or cache replication, memory, or connection pool issues",
            "networking": "BGP, DNS, routing, CDN, or load balancer connectivity",
            "non_prod": "Staging, dev, QA, or automated test environment alerts",
            "host_metrics": "Host-level CPU, disk, memory, or log rotation thresholds",
        },
    ),
    "customer_impact": Noul(
        instructions="End users or external customers are actively experiencing errors, failed transactions, or severe latency.",
    ),
    "requires_immediate_action": Noul(
        instructions="An on-call engineer can take a clear remedial action right now to resolve this alert.",
    ),
    "urgency": Score(
        instructions="What is the operational triage urgency for this alert?",
        criteria=[
            "Noise/Informational: safe to auto-resolve or ignore",
            "Low: non-urgent, review during next business day sprint triage",
            "Medium: investigate within 30-60 minutes; secondary redundancy degraded",
            "Critical: page primary on-call rotation immediately",
        ],
    ),
}


def route_alert(result: Any) -> tuple[str, str, str]:
    """Incident routing policy: plain Python over Jev's typed judgments.

    Returns (action, routing_detail, role).
    """
    print(result)
    domain = result.choices["alert_domain"]
    customer_impact = result.nouls["customer_impact"].noul
    actionable = result.nouls["requires_immediate_action"].noul
    urgency = result.scores["urgency"].score  # 0..3

    if domain.choice == "non_prod":
        action = "Auto-Snoozed"
        detail = "Non-production environment. Silenced alert; suppressed pager."
        role = "ok"
    elif customer_impact > 0.7 or urgency >= 2.5:
        action = "Page On-Call"
        detail = "Critical customer-facing degradation. Paging primary SRE on-call rotation."
        role = "err"
    elif domain.choice == "networking" and customer_impact < 0.3:
        action = "Monitor Auto-Heal"
        detail = "Redundant path active; transient route flap. Watching for escalation."
        role = "warn"
    elif actionable > 0.6 and urgency >= 1.0:
        action = "Create Ticket"
        detail = "Actionable defect without active outage. Assigned to service team backlog."
        role = "info"
    else:
        action = "Low Priority"
        detail = "Below paging threshold. Logged to telemetry channel."
        role = "info"

    return action, detail, role


def format_record(alert: dict[str, Any], result: Any, duration: float) -> dict[str, Any]:
    """Structure alert triage record for display and serialization."""
    domain = result.choices["alert_domain"]
    impact = result.nouls["customer_impact"].noul
    actionable = result.nouls["requires_immediate_action"].noul
    urgency = result.scores["urgency"]
    action, detail, role = route_alert(result)

    return {
        "id": alert.get("id", "ALT-000"),
        "service": alert.get("service", "unknown"),
        "name": alert.get("name", "UnnamedAlert"),
        "source": alert.get("source", "Telemetry"),
        "payload": alert.get("payload", ""),
        "domain": domain.choice,
        "domain_confidence": domain.confidence,
        "customer_impact": impact,
        "actionable": actionable,
        "urgency": urgency.score,
        "action": action,
        "detail": detail,
        "role": role,
        "request_time": round(duration, 2),
    }


def render_alert(record: dict[str, Any]) -> None:
    """Render a single alert triage evaluation using ape line grammar."""
    ui.heading(f"Alert {record['id']} · {record['service']}")
    ui.kv("alert name", record["name"], width=16)
    ui.kv("source", record["source"], width=16)
    ui.kv("payload", f'"{record["payload"]}"', width=16)
    ui.kv(
        "domain",
        f"{record['domain']} (confidence {record['domain_confidence']:.2f})",
        width=16,
    )
    ui.kv("customer impact", f"{record['customer_impact']:.2f}", width=16)
    ui.kv("actionable", f"{record['actionable']:.2f}", width=16)
    ui.kv("urgency", f"{record['urgency']:.2f} / 3", width=16)
    ui.kv("request time", f"{record['request_time']:.2f}s", width=16)

    ui._status(record["role"], record["action"].lower(), record["detail"], stream=sys.stdout)


def render_summary(records: list[dict[str, Any]]) -> None:
    """Render an aligned alert triage summary listing using ui.table."""
    ui.heading("incident triage summary", len(records))

    def action_color(action: str) -> str | None:
        if action == "Auto-Snoozed":
            return "71"  # ok (muted green)
        if action == "Page On-Call":
            return "167"  # err (muted red)
        if action == "Monitor Auto-Heal":
            return "179"  # warn (muted amber-yellow)
        return "110"  # info (muted blue)

    rows = [
        [
            r["id"],
            r["service"],
            r["domain"],
            f"{r['urgency']:.2f} / 3",
            f"{r['request_time']:.2f}s",
            r["action"],
        ]
        for r in records
    ]
    ui.table(rows, color=(5, action_color), dims=(1, 2, 3, 4))

    total_time = sum(r["request_time"] for r in records)
    ui.hint(f"{len(records)} incoming alerts triaged in {total_time:.2f}s · try next:")
    ui.command('python main3.py triage --id ALT-905 --service "auth-svc" --name "OomKilled" --payload "..."')


def triage_alerts(alerts: list[dict[str, Any]], is_json: bool) -> int:
    """Triage incoming alerts with TypeSafeClient, handling progress narration."""
    if not is_json:
        ui.heading("pager sentinel alert triage", len(alerts))
        ui.rule()

    adjudicated: list[dict[str, Any]] = []

    with TypeSafeClient() as client:
        for alert in alerts:
            t0 = time.monotonic()
            with ui.spinner(f"Triaging alert {alert.get('id')}: {alert.get('name')}"):
                case_input = {
                    "alert_name": alert.get("name", ""),
                    "service": alert.get("service", ""),
                    "source": alert.get("source", ""),
                    "payload": alert.get("payload", ""),
                }
                result = client.system_one(case_input, QUESTIONS)
            duration = time.monotonic() - t0

            record = format_record(alert, result, duration)
            adjudicated.append(record)

            if not is_json:
                render_alert(record)

    if is_json:
        print(json.dumps(adjudicated, indent=2), file=sys.stdout, flush=True)
    else:
        if len(adjudicated) > 1:
            ui.rule()
            render_summary(adjudicated)

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pager-sentinel",
        description="Pager Sentinel: AI production alert triager & incident commander powered by Jev.",
    )
    parser.add_argument("--no-color", action="store_true", help="Force colour off, keeping Unicode glyphs and rules intact")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output on stdout, quiet narration")
    parser.add_argument("--quiet", action="store_true", help="Suppress narration and spinners, keeping only essential output")
    parser.add_argument("--yes", action="store_true", help="Accept defaults for all prompts without blocking")

    subparsers = parser.add_subparsers(dest="subcommand")

    # 'inbox' subcommand
    inbox_parser = subparsers.add_parser("inbox", help="Triage active alert inbox")
    inbox_parser.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    inbox_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    inbox_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    inbox_parser.add_argument("--yes", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    # 'triage' subcommand
    triage_parser = subparsers.add_parser("triage", help="Triage an individual incoming alert payload")
    triage_parser.add_argument("--id", type=str, default="ALT-CUSTOM", help="Alert identifier")
    triage_parser.add_argument("--service", type=str, default="", help="Target service name")
    triage_parser.add_argument("--name", type=str, default="", help="Alert rule name")
    triage_parser.add_argument("--payload", type=str, default="", help="Alert payload or diagnostic message")
    triage_parser.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    triage_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    triage_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    triage_parser.add_argument("--yes", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

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

    if args.subcommand == "triage":
        alert_id = args.id
        service = args.service
        name = args.name
        payload = args.payload

        if not service:
            service = ui.prompt("affected service name", default="core-service")
        if not name:
            name = ui.prompt("alert rule name", default="UnexpectedErrorSpike")
        if not payload:
            payload = ui.prompt("alert description or telemetry payload")
            if not payload:
                raise ui.Cancelled("no alert payload provided")

        alert_data = {
            "id": alert_id,
            "service": service,
            "name": name,
            "source": "Manual Webhook",
            "payload": payload,
        }
        return triage_alerts([alert_data], is_json)

    # Default: triage standard inbox
    return triage_alerts(ALERTS, is_json)


def main() -> None:
    sys.exit(ui.run(cli_main, {TypeSafeError: 2}))


if __name__ == "__main__":
    main()
