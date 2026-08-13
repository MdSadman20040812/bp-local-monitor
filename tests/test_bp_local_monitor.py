"""Tests for bp-local-monitor."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from bp_monitor.classifier import classify_bp, rolling_stats
from bp_monitor.schemas import BPSample, Classification
from bp_monitor.storage import load_csv, save_csv


def test_classify_normal():
    s = BPSample(timestamp="2026-08-13T08:00:00Z", systolic=115, diastolic=72)
    r = classify_bp(s)
    assert r.classification == Classification.NORMAL


def test_classify_stage1_systolic():
    s = BPSample(timestamp="2026-08-13T08:00:00Z", systolic=132, diastolic=78)
    r = classify_bp(s)
    assert r.classification == Classification.HYPERTENSION_STAGE_1


def test_classify_stage1_diastolic():
    s = BPSample(timestamp="2026-08-13T08:00:00Z", systolic=122, diastolic=85)
    r = classify_bp(s)
    assert r.classification == Classification.HYPERTENSION_STAGE_1


def test_classify_stage2():
    s = BPSample(timestamp="2026-08-13T08:00:00Z", systolic=145, diastolic=92)
    r = classify_bp(s)
    assert r.classification == Classification.HYPERTENSION_STAGE_2


def test_classify_crisis():
    s = BPSample(timestamp="2026-08-13T08:00:00Z", systolic=185, diastolic=115)
    r = classify_bp(s)
    assert r.classification == Classification.HYPERTENSIVE_CRISIS


def test_classify_low():
    s = BPSample(timestamp="2026-08-13T08:00:00Z", systolic=85, diastolic=55)
    r = classify_bp(s)
    assert r.classification == Classification.LOW


def test_diastolic_must_be_lt_systolic():
    with pytest.raises(Exception):
        BPSample(timestamp="2026-08-13T08:00:00Z", systolic=120, diastolic=120)


def test_csv_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "bp.csv"
        samples = [
            BPSample(timestamp="2026-08-13T08:00:00Z", systolic=120, diastolic=80, pulse=72, notes="morning", source="omron"),
            BPSample(timestamp="2026-08-13T20:00:00Z", systolic=135, diastolic=88, pulse=78, notes="evening"),
        ]
        save_csv(p, samples)
        loaded = load_csv(p)
        assert len(loaded) == 2
        assert loaded[0].systolic == 120
        assert loaded[1].pulse == 78
        assert loaded[0].notes == "morning"
        assert loaded[0].source == "omron"


def test_trend_statistics():
    samples = [
        BPSample(timestamp="2026-08-13T08:00:00Z", systolic=120, diastolic=80),
        BPSample(timestamp="2026-08-14T08:00:00Z", systolic=122, diastolic=82),
        BPSample(timestamp="2026-08-15T08:00:00Z", systolic=124, diastolic=84),
    ]
    trend = rolling_stats(samples, window_days=7)
    assert trend.sample_count == 3
    assert trend.mean_systolic == pytest.approx(122.0, abs=0.1)
    assert trend.pattern != "insufficient_data"


def test_trend_insufficient_data():
    trend = rolling_stats([], window_days=7)
    assert trend.sample_count == 0
    assert trend.pattern == "insufficient_data"


def test_agent_context_json_serializable():
    from bp_monitor.agent import AgentContext
    with tempfile.TemporaryDirectory() as tmp:
        csv_p = Path(tmp) / "bp_log.csv"
        log_p = Path(tmp) / "bp_agent_log.jsonl"
        samples = [
            BPSample(timestamp="2026-08-13T08:00:00Z", systolic=118, diastolic=76, pulse=68),
        ]
        save_csv(csv_p, samples)
        ctx = AgentContext(csv_p, log_p)
        ctx.refresh()
        data = ctx.to_dict()
        dumped = json.dumps(data)  # should not raise
        assert "tool" in dumped
        assert "agent_prompt_fragment" in dumped
