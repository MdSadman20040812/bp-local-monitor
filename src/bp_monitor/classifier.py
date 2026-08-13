"""Deterministic BP classification and pattern detection."""

from __future__ import annotations

from statistics import mean, stdev
from typing import Optional

from .schemas import BPSample, BPReading, Classification, TrendSummary

# AHA / ESC-aligned thresholds
# Order: crisis -> stage2 -> stage1 -> elevated -> low -> normal


def classify_bp(sample: BPSample) -> BPReading:
    """Classify a single BP reading using AHA/ESC thresholds."""
    sys = sample.systolic
    dia = sample.diastolic

    # Hypertensive crisis: SBP > 180 or DBP > 120
    if sys >= 180 or dia >= 120:
        return BPReading(
            sample=sample,
            classification=Classification.HYPERTENSIVE_CRISIS,
            classification_label="Hypertensive crisis — seek emergency care",
            derived_metrics={},
        )

    # Stage 2: SBP >= 140 or DBP >= 90
    if sys >= 140 or dia >= 90:
        return BPReading(
            sample=sample,
            classification=Classification.HYPERTENSION_STAGE_2,
            classification_label="Hypertension Stage 2 — prompt medical review",
            derived_metrics={},
        )

    # Stage 1: SBP >= 130 or DBP >= 80
    if sys >= 130 or dia >= 80:
        return BPReading(
            sample=sample,
            classification=Classification.HYPERTENSION_STAGE_1,
            classification_label="Hypertension Stage 1 — discuss with physician",
            derived_metrics={},
        )

    # Elevated: SBP >= 120, DBP < 80
    if sys >= 120:
        return BPReading(
            sample=sample,
            classification=Classification.ELEVATED,
            classification_label="Elevated — lifestyle review warranted",
            derived_metrics={},
        )

    # Low: SBP < 90 or DBP < 60
    if sys < 90 or dia < 60:
        return BPReading(
            sample=sample,
            classification=Classification.LOW,
            classification_label="Low BP — consider evaluation if symptomatic",
            derived_metrics={},
        )

    # Normal
    derived: dict = {}
    if sample.pulse is not None:
        derived["pulse_status"] = (
            "elevated" if sample.pulse > 100 else
            "low" if sample.pulse < 50 else
            "normal"
        )

    return BPReading(
        sample=sample,
        classification=Classification.NORMAL,
        classification_label="Normal",
        derived_metrics=derived,
    )


MORNING_HOURS = range(6, 12)  # 06:00-11:59
EVENING_HOURS = range(18, 23)  # 18:00-22:59


def rolling_stats(samples: list[BPSample], window_days: int = 7) -> TrendSummary:
    """Compute deterministic windowed statistics."""
    if not samples:
        return TrendSummary(
            window_days=window_days,
            sample_count=0,
            mean_systolic=0.0,
            mean_diastolic=0.0,
            mean_pulse=None,
            std_systolic=0.0,
            std_diastolic=0.0,
        )

    sys_vals = [s.systolic for s in samples]
    dia_vals = [s.diastolic for s in samples]
    pulse_vals = [s.pulse for s in samples if s.pulse is not None]

    # Split by time of day
    morning_sys = [
        s.systolic for s in samples
        if s.timestamp[11:13].isdigit() and int(s.timestamp[11:13]) in MORNING_HOURS
    ]
    evening_sys = [
        s.systolic for s in samples
        if s.timestamp[11:13].isdigit() and int(s.timestamp[11:13]) in EVENING_HOURS
    ]

    mean_sys = mean(sys_vals)
    mean_dia = mean(dia_vals)
    mean_pulse = mean(pulse_vals) if pulse_vals else None
    std_sys = stdev(sys_vals) if len(sys_vals) > 1 else 0.0
    std_dia = stdev(dia_vals) if len(dia_vals) > 1 else 0.0

    pattern = detect_pattern(samples, mean_sys, morning_sys, evening_sys)

    return TrendSummary(
        window_days=window_days,
        sample_count=len(samples),
        mean_systolic=round(mean_sys, 1),
        mean_diastolic=round(mean_dia, 1),
        mean_pulse=round(mean_pulse, 1) if mean_pulse is not None else None,
        std_systolic=round(std_sys, 1),
        std_diastolic=round(std_dia, 1),
        morning_avg_systolic=round(mean(morning_sys), 1) if morning_sys else None,
        evening_avg_systolic=round(mean(evening_sys), 1) if evening_sys else None,
        pattern=pattern,
    )


def detect_pattern(
    samples: list[BPSample],
    mean_sys: float,
    morning_sys: list[int],
    evening_sys: list[int],
) -> str:
    """Detect known BP patterns (non-dipping, nocturnal elevation, etc.)."""
    if len(samples) < 3:
        return "insufficient_data"

    patterns_found: list[str] = []

    # Non-dipping: nighttime SBP drop < 10% from daytime
    if morning_sys and evening_sys:
        morning_avg = mean(morning_sys)
        evening_avg = mean(evening_sys)
        if morning_avg > evening_avg:
            drop_pct = ((morning_avg - evening_avg) / morning_avg) * 100
            if drop_pct < 10:
                patterns_found.append("non-dipping")

    # Nocturnal elevation: overall mean high
    if mean_sys >= 140:
        patterns_found.append("nocturnal_elevation")

    # High variability
    if len(samples) > 1:
        sys_vals = [s.systolic for s in samples]
        cv = (stdev(sys_vals) / mean_sys) * 100
        if cv > 15:
            patterns_found.append("high_variability")

    # Isolated elevation
    high_count = sum(1 for s in samples if s.systolic >= 130)
    if high_count / len(samples) >= 0.5:
        patterns_found.append("frequent_elevation")

    if not patterns_found:
        if mean_sys >= 130:
            patterns_found.append("persistent_elevation")
        else:
            patterns_found.append("stable")

    return ", ".join(patterns_found)
