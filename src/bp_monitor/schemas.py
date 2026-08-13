"""Data contracts for bp_local_monitor.

All timestamps are ISO-8601 UTC strings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Classification(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HYPERTENSION_STAGE_1 = "hypertension_stage_1"
    HYPERTENSION_STAGE_2 = "hypertension_stage_2"
    HYPERTENSIVE_CRISIS = "hypertensive_crisis"
    LOW = "low"


class BPSample(BaseModel):
    """Single validated BP measurement."""

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    systolic: int = Field(..., ge=50, le=300)
    diastolic: int = Field(..., ge=30, le=200)
    pulse: Optional[int] = Field(default=None, ge=20, le=250)
    notes: Optional[str] = Field(default=None, max_length=500)
    source: Optional[str] = Field(default="manual", description="manual, omron, etc.")

    @field_validator("timestamp")
    @classmethod
    def validate_iso8601(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid ISO-8601 timestamp: {v}")
        return v

    @field_validator("diastolic")
    @classmethod
    def check_dia_lt_sys(cls, v: int, info) -> int:
        if "systolic" in info.data and v >= info.data["systolic"]:
            raise ValueError("diastolic must be less than systolic")
        return v


class BPReading(BaseModel):
    """Classified reading with context."""

    sample: BPSample
    classification: Classification
    classification_label: str = Field(...)
    derived_metrics: dict = Field(default_factory=dict)


class TrendSummary(BaseModel):
    """Aggregate statistics over a window."""

    window_days: int
    sample_count: int
    mean_systolic: float
    mean_diastolic: float
    mean_pulse: Optional[float]
    std_systolic: float
    std_diastolic: float
    morning_avg_systolic: Optional[float] = None
    evening_avg_systolic: Optional[float] = None
    pattern: str = "insufficient_data"
