# Contract: Guard and fit check

```python
def fit(backend, mode, width, height, frames, profile) -> FitResult
# FitResult: fits: bool, est_peak_gb, available_gb, margin_pct, est_seconds, suggestions: list[str]

def run_guarded(cmd: list[str], profile: GuardProfile, job_id: str, on_sample) -> GuardOutcome
# GuardOutcome: exit_code, stopped: bool, stop_reason: str | None, peak_used_gb
```

Behaviour:
1. Wait (up to 10 min, reporting) until free percent >= `start_free_pct`.
2. Start the command in a new process group.
3. Every `poll_seconds`: read free percent, swap used, group RSS; write a `memory_sample` row.
4. If free < `kill_free_pct` or swap > `swap_ceiling_mb`: SIGTERM the group, SIGKILL after 5 s, set `stop_reason` and a `suggestion` (smaller size or fewer frames, from the fit profile).
5. On success append a `fit_sample` row with measured peak.

Builtin presets:

| name | start_free_pct | kill_free_pct | swap_ceiling_mb |
|---|---|---|---|
| safe | 45 | 12 | 2048 |
| balanced | 35 | 8 | 4096 |
| max | 25 | 6 | 8192 |

The active preset is printed at the start of every job. Presets are never changed silently; changing needs `mb guard --set` or a Studio setting change.
