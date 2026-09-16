"""
connector/store.py

In-memory store for dashboard data.
Holds the last 50 scheduler runs with their decisions and incident results.
"""

# Holds the last 50 pipeline run results
pipeline_runs: list = []

MAX_RUNS = 50


def save_run(run: dict):
    pipeline_runs.insert(0, run)
    if len(pipeline_runs) > MAX_RUNS:
        pipeline_runs.pop()
