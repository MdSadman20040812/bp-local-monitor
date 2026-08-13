"""CLI for bp-local-monitor."""

from __future__ import annotations

import sys
from pathlib import Path

from bp_monitor.classifier import classify_bp, rolling_stats
from bp_monitor.dashboard import render_dashboard
from bp_monitor.schemas import BPSample, Classification
from bp_monitor.storage import load_csv, save_csv


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    csv_path = Path("bp_log.csv")
    log_path = Path("bp_agent_log.jsonl")

    # Parse optional csv path
    if argv and argv[0] in {"--file", "-f"}:
        csv_path = Path(argv[1])
        argv = argv[2:]

    if not argv:
        print("Usage: bp-local <add|list|trend|dashboard|log> [args...]")
        print("  --file <path>   alternate CSV path")
        return 0

    cmd = argv[0]

    if cmd == "add":
        if len(argv) < 4:
            print("Usage: bp-local add <timestamp> <systolic> <diastolic> [pulse] [notes]")
            return 1
        ts = argv[1]
        sys_val = int(argv[2])
        dia_val = int(argv[3])
        pulse = int(argv[4]) if len(argv) > 4 and argv[4].isdigit() else None
        notes = argv[5] if len(argv) > 5 else None

        try:
            sample = BPSample(timestamp=ts, systolic=sys_val, diastolic=dia_val, pulse=pulse, notes=notes)
        except Exception as e:
            print(f"Invalid sample: {e}")
            return 1

        samples = load_csv(csv_path)
        samples.append(sample)
        samples.sort(key=lambda s: s.timestamp)
        save_csv(csv_path, samples)

        reading = classify_bp(sample)
        print(f"Logged: {sys_val}/{dia_val} — {reading.classification_label}")
        return 0

    if cmd == "list":
        samples = load_csv(csv_path)
        if not samples:
            print("No readings yet.")
            return 0
        for s in samples[-20:]:
            r = classify_bp(s)
            print(f"{s.timestamp}  {s.systolic}/{s.diastolic}  {r.classification_label}")
        return 0

    if cmd == "trend":
        samples = load_csv(csv_path)
        trend = rolling_stats(samples)
        print(f"Window: {trend.window_days}d  Samples: {trend.sample_count}")
        print(f"Mean BP: {trend.mean_systolic}/{trend.mean_diastolic}")
        if trend.mean_pulse:
            print(f"Mean pulse: {trend.mean_pulse}")
        print(f"Std dev S/D: {trend.std_systolic}/{trend.std_diastolic}")
        if trend.morning_avg_systolic:
            print(f"Morning avg SBP: {trend.morning_avg_systolic}")
        if trend.evening_avg_systolic:
            print(f"Evening avg SBP: {trend.evening_avg_systolic}")
        print(f"Pattern: {trend.pattern}")
        return 0

    if cmd == "dashboard":
        samples = load_csv(csv_path)
        html = render_dashboard(samples)
        out = Path("bp_dashboard.html")
        out.write_text(html, encoding="utf-8")
        print(f"Dashboard written to {out}")
        return 0

    if cmd == "log":
        samples = load_csv(csv_path)
        if not samples:
            print("No readings to log.")
            return 0
        import json
        import datetime
        with log_path.open("a", encoding="utf-8") as f:
            for s in samples:
                r = classify_bp(s)
                entry = {
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "event": "reading_classified",
                    "reading_ts": s.timestamp,
                    "systolic": s.systolic,
                    "diastolic": s.diastolic,
                    "classification": r.classification.value,
                }
                f.write(json.dumps(entry) + "\n")
        print(f"Logged {len(samples)} readings to {log_path}")
        return 0

    if cmd == "agent-context":
        from bp_monitor.agent import main as agent_main
        return agent_main(["agent-context", "--file", str(csv_path)])

    if cmd == "agent-log":
        from bp_monitor.agent import main as agent_main
        return agent_main(["agent-log", "--file", str(csv_path)])

    if cmd == "agent-prompt":
        from bp_monitor.agent import main as agent_main
        return agent_main(["prompt"])

    print(f"Unknown command: {cmd}")
    return 1
