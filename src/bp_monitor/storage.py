"""CSV storage — fully self-contained, no external dependencies."""

from __future__ import annotations

import csv
from pathlib import Path

from bp_monitor.schemas import BPSample

FIELDS = ["timestamp", "systolic", "diastolic", "pulse", "notes", "source"]


def save_csv(path: Path, samples: list[BPSample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for s in samples:
            writer.writerow({
                "timestamp": s.timestamp,
                "systolic": s.systolic,
                "diastolic": s.diastolic,
                "pulse": s.pulse or "",
                "notes": s.notes or "",
                "source": s.source or "manual",
            })


def load_csv(path: Path) -> list[BPSample]:
    if not path.exists():
        return []
    samples: list[BPSample] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pulse = int(row["pulse"]) if row.get("pulse", "").strip() else None
            notes = row.get("notes", "").strip() or None
            source = row.get("source", "manual").strip() or "manual"
            samples.append(
                BPSample(
                    timestamp=row["timestamp"],
                    systolic=int(row["systolic"]),
                    diastolic=int(row["diastolic"]),
                    pulse=pulse,
                    notes=notes,
                    source=source,
                )
            )
    return samples
