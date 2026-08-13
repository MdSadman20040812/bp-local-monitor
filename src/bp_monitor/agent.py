"""Agent-native interface for bp-local-monitor.

Agents can interact with the BP tool via three surfaces:
  1. JSON event log — append-only, append readings + classifications.
  2. State query  — deterministic JSON snapshot of all known readings.
  3. Prompt spec  — loadable system prompt fragment with domain context.

Designed for Hermes, Claude Code, OpenDevin, and any LLM agent that can:
  - read/write JSONL files
  - run shell commands
  - load system prompt fragments
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bp_monitor.classifier import classify_bp, rolling_stats
from bp_monitor.schemas import BPSample
from bp_monitor.storage import load_csv, save_csv

LOG_VERSION = "0.1.0"

AGENT_PROMPT_FRAGMENT = """\
You are a blood pressure monitoring assistant. You have access to the bp-local-monitor tool.

## How to use this tool
- `bp-local add <timestamp> <systolic> <diastolic> [pulse] [notes]` — add a reading
- `bp-local list` — show recent readings
- `bp-local trend` — show windowed statistics
- `bp-local dashboard` — generate HTML dashboard
- `bp-local agent-context` — output JSON state for reasoning
- `bp-local agent-log` — append all readings to JSONL event log

## Classification (AHA-aligned)
- Normal: SBP < 120 and DBP < 80
- Elevated: SBP 120–129 and DBP < 80
- Hypertension Stage 1: SBP 130–139 or DBP 80–89
- Hypertension Stage 2: SBP ≥ 140 or DBP ≥ 90
- Hypertensive crisis: SBP > 180 or DBP > 120 — advise emergency care

## Important constraints
- All data is local. Never upload. Never send to external APIs.
- This tool does not replace physician advice. Flag high readings as medical, not diagnostic.
- If the user mentions symptoms (headache, dizziness, chest pain), suggest medical evaluation.
- Timestamps should be ISO-8601 (2026-08-13T08:30:00Z).
"""


class AgentContext:
    """Agent-friendly state container."""

    def __init__(self, csv_path: Path, log_path: Path) -> None:
        self.csv_path = csv_path
        self.log_path = log_path
        self.samples: list[BPSample] = []
        self.trend = None
        self.readings: list[Any] = []
        self.last_updated: str = datetime.now(timezone.utc).isoformat()

    def refresh(self) -> None:
        self.samples = load_csv(self.csv_path)
        self.readings = [classify_bp(s).model_dump() for s in self.samples]
        self.trend = rolling_stats(self.samples).model_dump() if self.samples else None
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": "bp-local-monitor",
            "version": LOG_VERSION,
            "last_updated": self.last_updated,
            "sample_count": len(self.samples),
            "trend": self.trend,
            "readings": self.readings[-10:],  # last 10 for token efficiency
            "agent_prompt_fragment": AGENT_PROMPT_FRAGMENT,
            "constraints": {
                "no_external_uploads": True,
                "local_only": True,
                "does_not_replace_physician": True,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def log_reading(log_path: Path, sample: BPSample, reading: Any) -> None:
    """Append a classified reading to the JSONL agent log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": LOG_VERSION,
        "event": "reading_classified",
        "reading": sample.model_dump(),
        "classification": reading.model_dump(),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main(argv: list[str] | None = None) -> int:
    argv = argv or []
    csv_path = Path("bp_log.csv")
    log_path = Path("bp_agent_log.jsonl")

    if len(argv) > 1 and argv[0] in {"--file", "-f"}:
        csv_path = Path(argv[1])
        log_path = csv_path.parent / "bp_agent_log.jsonl"
        argv = argv[2:]

    cmd = argv[0] if argv else "help"

    if cmd == "agent-context":
        ctx = AgentContext(csv_path, log_path)
        ctx.refresh()
        print(ctx.to_json())
        return 0

    if cmd == "agent-log":
        from bp_monitor.classifier import classify_bp
        from bp_monitor.storage import load_csv
        samples = load_csv(csv_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            for s in samples:
                r = classify_bp(s)
                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": LOG_VERSION,
                    "event": "reading_classified",
                    "reading": s.model_dump(),
                    "classification": r.model_dump(),
                }
                f.write(json.dumps(entry) + "\n")
        print(f"Logged {len(samples)} readings to {log_path}")
        return 0

    if cmd == "prompt":
        print(AGENT_PROMPT_FRAGMENT)
        return 0

    if cmd == "help":
        print("bp-local-agent commands:")
        print("  agent-context   — JSON state snapshot for agents")
        print("  agent-log       — append readings to JSONL log")
        print("  prompt          — print agent prompt fragment")
        print("  --file <path>   — alternate CSV path")
        return 0

    print(f"Unknown command: {cmd}")
    return 1
