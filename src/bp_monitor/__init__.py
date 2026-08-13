"""bp_local_monitor — deterministic blood pressure monitoring, no cloud."""

__version__ = "0.1.0"

from .schemas import BPSample, BPReading, TrendSummary
from .classifier import classify_bp, rolling_stats, detect_pattern
from .dashboard import render_dashboard

__all__ = [
    "BPSample",
    "BPReading",
    "TrendSummary",
    "classify_bp",
    "rolling_stats",
    "detect_pattern",
    "render_dashboard",
]
