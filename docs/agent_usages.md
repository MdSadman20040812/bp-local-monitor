agent_usages = [
    ("Hermes Agent", """
Hermes can use bp-local via the shell tool. The agent-context command
returns a JSON state snapshot that Hermes can reason over without loading
the full file list. Example flow:

1. Run: bp-local agent-context --file /path/to/bp_log.csv
2. Hermes parses the JSON output, identifies patterns, and can suggest
   lifestyle or medical escalation based on the deterministic thresholds.
3. Hermes can add new readings with: bp-local add <timestamp> <sys> <dia> [pulse] [notes]
4. Hermes can generate a fresh dashboard with: bp-local dashboard --file ...
5. Hermes can read the prompt fragment with: bp-local prompt
   and self-configure its monitoring behavior from the spec.
    """),
    ("Claude Code / OpenDevin", """
Any terminal-based agent that can run shell commands and read/write files
can interact with bp-local via the JSONL event log or the agent-context
snapshot. The JSONL format is line-delimited JSON — easy to stream, filter,
and append.

Example workflow for Claude Code:
1. Run: bp-local agent-log --file project/bp/bp_log.csv
2. Claude Code reads bp_agent_log.jsonl and reasons over recent classifications.
3. Claude Code can call bp-local add to log new readings.
4. Claude Code can call bp-local dashboard to regenerate the HTML dashboard
   and present it to the user via a preview tool.
    """),
    ("Custom scripts / automation", """
The Python API is importable: from bp_monitor import classify_bp, rolling_stats.
This allows custom dashboards, alerting scripts, or integration into larger
health toolchains. All data stays local; no API keys or external calls are needed.
    """),
]
