"""Self-contained HTML dashboard generator — zero external JS/CSS dependencies."""

from __future__ import annotations

from datetime import datetime

from bp_monitor.classifier import classify_bp, rolling_stats
from bp_monitor.schemas import BPSample


def render_dashboard(samples: list[BPSample]) -> str:
    """Return a single-file HTML dashboard string."""
    readings = [classify_bp(s) for s in samples]
    trend = rolling_stats(samples)

    # Build chart data
    chart_data_points: list[dict] = []
    for s, r in zip(samples, readings):
        chart_data_points.append(
            {
                "ts": s.timestamp,
                "sys": s.systolic,
                "dia": s.diastolic,
                "pulse": s.pulse,
                "cls": r.classification.value,
            }
        )

    chart_json = _to_json(chart_data_points)

    # Pattern colors
    pattern_colors = {
        "normal": "#2ecc71",
        "elevated": "#f1c40f",
        "hypertension_stage_1": "#e67e22",
        "hypertension_stage_2": "#e74c3c",
        "hypertensive_crisis": "#8e0000",
        "low": "#3498db",
    }

    reading_rows = ""
    for r in reversed(readings[-50:]):
        color = pattern_colors.get(r.classification.value, "#95a5a6")
        pulse_td = f"<td>{r.sample.pulse}</td>" if r.sample.pulse else "<td>—</td>"
        notes_td = f"<td class='notes'>{_esc(r.sample.notes or '')}</td>" if r.sample.notes else ""
        reading_rows += f"""
            <tr class="reading-row" data-cls="{r.classification.value}">
              <td>{_esc(r.sample.timestamp)}</td>
              <td class="sys">{r.sample.systolic}</td>
              <td class="dia">{r.sample.diastolic}</td>
              {pulse_td}
              <td class="cls-badge" style="background:{color}22;color:{color}">{_esc(r.classification_label)}</td>
              {notes_td}
            </tr>"""

    pattern_html = ", ".join(trend.pattern.split(", ")) if trend.pattern else "—"

    # Trend insight
    insights = _build_insights(trend, pattern_colors)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BP Local Monitor</title>
<style>
  :root {{
    --bg: #0f1115;
    --surface: #161920;
    --border: #252830;
    --text: #e6e8ee;
    --muted: #8b8f9a;
    --accent: #60a5fa;
    --sys: #f87171;
    --dia: #34d399;
    --pulse: #a78bfa;
    --ok: #2ecc71;
    --warn: #f1c40f;
    --danger: #e74c3c;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0;
    background: var(--bg); color: var(--text);
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  header {{
    padding: 24px 32px;
    border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
  }}
  header h1 {{ font-size: 18px; font-weight: 600; margin: 0; }}
  header .subtitle {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  main {{ padding: 24px 32px; max-width: 1200px; }}
  .stats-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin-bottom: 24px;
  }}
  .stat-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px;
  }}
  .stat-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }}
  .stat-value {{ font-size: 22px; font-weight: 700; margin-top: 6px; }}
  .stat-value.sys {{ color: var(--sys); }}
  .stat-value.dia {{ color: var(--dia); }}
  .stat-value.pulse {{ color: var(--pulse); }}
  .chart-wrap {{ margin: 24px 0; }}
  .chart-wrap h2 {{ font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 12px; }}
  canvas {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; width: 100%; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }}
  tr:hover td {{ background: var(--surface); }}
  .cls-badge {{ border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; display: inline-block; }}
  .notes {{ color: var(--muted); font-style: italic; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .insights {{ margin-top: 24px; padding: 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }}
  .insights h3 {{ margin: 0 0 8px; font-size: 13px; color: var(--accent); }}
  .insights ul {{ margin: 0; padding-left: 18px; color: var(--muted); font-size: 13px; }}
  .insights li {{ margin: 4px 0; }}
  .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--muted); font-size: 11px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>BP Local Monitor</h1>
    <div class="subtitle">No cloud · No login · All data stays on this machine</div>
  </div>
  <div style="text-align:right; color:var(--muted); font-size:12px;">
    Generated {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}
  </div>
</header>
<main>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Mean Systolic</div>
      <div class="stat-value sys">{trend.mean_systolic}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Mean Diastolic</div>
      <div class="stat-value dia">{trend.mean_diastolic}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Mean Pulse</div>
      <div class="stat-value pulse">{trend.mean_pulse if trend.mean_pulse is not None else '—'}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Std Dev S / D</div>
      <div class="stat-value">{trend.std_systolic} / {trend.std_diastolic}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Samples</div>
      <div class="stat-value">{trend.sample_count}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Pattern</div>
      <div class="stat-value" style="font-size:14px;">{_esc(pattern_html)}</div>
    </div>
  </div>

  <div class="chart-wrap">
    <h2>Blood Pressure Trend</h2>
    <canvas id="chart" height="280"></canvas>
  </div>

  <h2 style="font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; margin-bottom:8px;">Recent Readings</h2>
  <table>
    <thead>
      <tr>
        <th>Timestamp</th>
        <th>Systolic</th>
        <th>Diastolic</th>
        <th>Pulse</th>
        <th>Classification</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>
      {reading_rows}
    </tbody>
  </table>

  <div class="insights">
    <h3>Pattern Insights</h3>
    <ul>
      {insights}
    </ul>
  </div>

  <div class="footer">
    bp-local-monitor v0.1.0 — Open-source, MIT license. No data leaves this machine.
  </div>
</main>
<script>
(function(){{
  const data = {chart_json};
  const canvas = document.getElementById('chart');
  if (!canvas || !data.length) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth * (window.devicePixelRatio || 1);
  const H = canvas.height = 280 * (window.devicePixelRatio || 1);
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  const w = canvas.clientWidth;
  const h = 280;

  const pad = {{ top: 20, right: 20, bottom: 30, left: 40 }};
  const cw = w - pad.left - pad.right;
  const ch = h - pad.top - pad.bottom;

  const sysVals = data.map(d => d.sys);
  const diaVals = data.map(d => d.dia);
  const allVals = [...sysVals, ...diaVals];
  const yMin = Math.max(30, Math.floor(Math.min(...allVals) / 10) * 10 - 10);
  const yMax = Math.min(220, Math.ceil(Math.max(...allVals) / 10) * 10 + 10);

  const xFor = i => pad.left + (i / Math.max(1, data.length - 1)) * cw;
  const yFor = v => pad.top + ch - ((v - yMin) / (yMax - yMin)) * ch;

  function grid() {{
    ctx.strokeStyle = '#252830'; ctx.lineWidth = 1;
    for (let v = yMin; v <= yMax; v += 20) {{
      const y = yFor(v);
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
      ctx.fillStyle = '#8b8f9a'; ctx.font = '10px ui-monospace';
      ctx.textAlign = 'right'; ctx.fillText(v, pad.left - 6, y + 3);
    }}
    // threshold lines
    ctx.strokeStyle = '#f1c40f44'; ctx.setLineDash([4,4]);
    [120, 140, 180].forEach(v => {{
      const y = yFor(v);
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    }});
    ctx.setLineDash([]);
  }}

  function drawLines(color, key) {{
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.lineJoin = 'round';
    ctx.beginPath();
    data.forEach((d, i) => {{
      const x = xFor(i), y = yFor(d[key]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }});
    ctx.stroke();
  }}

  function drawDots(color, key) {{
    ctx.fillStyle = color;
    data.forEach((d, i) => {{
      ctx.beginPath(); ctx.arc(xFor(i), yFor(d[key]), 3, 0, Math.PI * 2); ctx.fill();
    }});
  }}

  grid();
  drawLines('#f87171', 'sys');
  drawDots('#f87171', 'sys');
  drawLines('#34d399', 'dia');
  drawDots('#34d399', 'dia');

  // legend
  ctx.font = '11px ui-monospace';
  ctx.fillStyle = '#f87171'; ctx.fillText('Systolic', pad.left, h - 8);
  ctx.fillStyle = '#34d399'; ctx.fillText('Diastolic', pad.left + 90, h - 8);
}})();
</script>
</body>
</html>"""
    return html


def _to_json(obj):
    import json
    return json.dumps(obj)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_insights(trend, colors: dict) -> str:
    items: list[str] = []
    if trend.morning_avg_systolic and trend.evening_avg_systolic:
        drop = ((trend.morning_avg_systolic - trend.evening_avg_systolic) / trend.morning_avg_systolic) * 100
        if drop < 10:
            items.append(
                f"<span style='color:{colors.get('hypertension_stage_2','#e74c3c')}'>Non-dipping pattern detected</span> — "
                f"nighttime SBP drop is only {drop:.0f}% (target ≥ 10%). "
                "Common causes: sleep disruption, sinusitis-related apnea, irregular medication timing."
            )
        else:
            items.append(
                f"Normal dipper — nighttime SBP drops {drop:.0f}%. "
                "This is the expected pattern."
            )
    if trend.mean_systolic >= 140:
        items.append("Overall mean systolic ≥ 140 mmHg suggests sustained hypertension. Continue monitoring and share with your physician.")
    elif trend.mean_systolic >= 130:
        items.append("Mean systolic is in the elevated range (130–139). Lifestyle review is warranted.")
    else:
        items.append("Mean systolic is within normal range. Continue routine monitoring.")

    items.append(
        f"Standard deviation: SBP σ={trend.std_systolic}, DBP σ={trend.std_diastolic}. "
        "Lower σ indicates more stable readings."
    )

    if not items:
        items.append("Collect more readings to generate personalized insights.")
    return "\n".join(f"<li>{item}</li>" for item in items)
