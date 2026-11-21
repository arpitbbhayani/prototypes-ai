"""Pydantic data models for parallel subagents and synthesis."""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Finding(BaseModel):
    title: str = Field(description="Succinct title of the issue")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        description="Severity classification: CRITICAL, HIGH, MEDIUM, LOW, or INFO"
    )
    location: str = Field(description="Line number range or function/symbol name")
    description: str = Field(description="1-2 sentences explaining the problem and consequence")
    remediation: str = Field(description="Specific actionable fix")


class SubagentOutput(BaseModel):
    """Schema returned directly by each specialized subagent LLM call."""
    summary: str = Field(description="Brief 1-line summary of domain assessment")
    findings: list[Finding] = Field(description="List of detected findings in this specialist domain")


class SubagentReport(BaseModel):
    """Runtime wrapper around subagent output containing execution metadata."""
    agent_id: str
    agent_name: str
    domain: str
    summary: str
    findings: list[Finding]
    latency_seconds: float


class SynthesizedOutput(BaseModel):
    """Schema returned by the Lead Synthesizer LLM call."""
    verdict: Literal["APPROVE", "REQUEST_CHANGES", "NEEDS_DISCUSSION"] = Field(
        description="Overall pull request / code review verdict"
    )
    risk_score: int = Field(
        description="Aggregated risk score between 0 (pristine) and 100 (critical vulnerabilities)"
    )
    executive_summary: str = Field(description="High-level 2-3 sentence executive synthesis for the engineering team")
    top_action_items: list[str] = Field(description="Prioritized list of top 3-5 immediate action items")
    consolidated_findings: list[Finding] = Field(description="Deduplicated and cross-correlated key findings")


class ReviewRunResult(BaseModel):
    """Full execution result containing subagent reports and lead synthesis."""
    target_path: str
    model_name: str
    execution_mode: Literal["parallel", "serial"] = Field(
        description="How the specialist subagents were scheduled: parallel or serial"
    )
    subagent_reports: list[SubagentReport]
    synthesis: SynthesizedOutput
    subagents_wall_time: float = Field(
        description="Wall-clock seconds for Phase 1 (all specialist subagents)"
    )
    subagents_serial_sum: float = Field(
        description="Sum of individual subagent latencies in seconds"
    )
    synthesis_time: float = Field(
        description="Wall-clock seconds for Phase 2 (sequential lead synthesizer)"
    )
    speedup_ratio: float = Field(
        description="subagents_serial_sum / subagents_wall_time"
    )
