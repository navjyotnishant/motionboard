# Memory guard

Every heavy job (clip renders, command adapters, vocal separation, animation renders) runs under a guard that samples free memory and swap every few seconds and stops the job before the machine runs out.

## Presets

| Preset | Start floor (free %) | Kill floor (free %) | Swap growth ceiling | Use |
|---|---|---|---|---|
| safe | 45 | 12 | 2 GB | other apps open |
| balanced (default) | 35 | 8 | 4 GB | normal use |
| max | 25 | 6 | 8 GB | nothing else running |

- **Start floor**: a job waits until free memory is at least this.
- **Kill floor**: the job is stopped (SIGTERM, then SIGKILL after 5 s) when free memory drops below this.
- **Swap growth ceiling**: measured from the swap in use when the job starts, so existing swap does not block work.

```bash
mb guard                          # list presets and the active one
mb guard --set safe
mb guard --create tight --start 60 --kill 20 --swap 1024
```

The guard is never loosened silently. A stopped job reports `GUARD_STOPPED` with the reason and a suggestion (fewer frames, smaller size, close apps).

## Fit check

Before a clip is queued, the fit check (also `mb fit --width W --height H --frames N`) estimates its peak memory from the backend profile and your own past renders, adds 15%, and compares it with the memory you can use above the kill floor. A shot that will not fit is refused with the largest frame count that would.
