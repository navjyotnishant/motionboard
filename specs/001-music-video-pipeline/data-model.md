# Data Model (shared by 001 engine and 002 Studio)

Feature 003 adds `art_direction`, `character_reference`, `critique`, `shot.creative` and `plate_request.refs`: see [specs/003-creative-direction-system/data-model.md](../003-creative-direction-system/data-model.md).

One SQLite file. IDs are text ULIDs. Times are ISO 8601 UTC text. Paths are absolute. The engine owns migrations; feature 002 adds no tables of its own beyond those marked (002).

## workspace_setting
| field | type | notes |
|---|---|---|
| key | text PK | e.g. `ltx_bin`, `projects_root`, `active_guard_profile` |
| value | text | JSON encoded |

## guard_profile
| field | type | notes |
|---|---|---|
| id | text PK | |
| name | text unique | safe, balanced, max, or custom |
| start_free_pct | int | must be > kill_free_pct |
| kill_free_pct | int | 1..50 |
| swap_ceiling_mb | int | >= 0 |
| poll_seconds | real | 0.5..10, default 2 |
| builtin | bool | builtin rows cannot be deleted |

## plate_adapter
| field | type | notes |
|---|---|---|
| id | text PK | |
| name | text unique | |
| kind | text | manual, command, http, handoff |
| config | text | JSON; may hold `key_file` or `key_env`, never a key |
| cost_per_image_usd | real | 0 for free |
| enabled | bool | |

## template
| field | type | notes |
|---|---|---|
| id | text PK | |
| name | text | Object World, Performance, Lyric Story, Two Lovers, Mood Loop, or saved |
| source | text | builtin (file in `templates/`) or user |
| body | text | YAML: rhythm rules, camera language, style lines, finishing theme |

## project
| field | type | notes |
|---|---|---|
| id | text PK | |
| title | text | |
| folder | text | project folder on disk |
| song_path | text | original audio |
| segment_start, segment_end | real | seconds in source song |
| lyrics | text | raw lyrics |
| idea | text | one paragraph |
| aspect | text | `9:16` or `16:9` |
| look | text | stylized or realistic |
| theme | text | JSON: fonts, colors, end card texts, artist, song, album, release note |
| template_id | text FK nullable | |
| concept_id | text FK nullable | chosen concept |
| video_backend | text | default `ltx23` |
| plate_adapter_id | text FK | |
| synthetic_people | bool | set true when look is realistic with people |
| created_at, updated_at | text | |

## song_analysis
| field | type | notes |
|---|---|---|
| project_id | text PK FK | |
| tempo_bpm | real | |
| beats | text | JSON array of seconds (segment time) |
| lines | text | JSON array of {start, end, text, source: aligned or beat} |
| loudness | text | JSON per frame RMS at 24 fps |
| waveform_peaks | text | JSON peaks for the Studio waveform |
| verified_vocal_alignment | bool | false when fell back to beat grid |

## concept (002 brainstorm, used by 001 draft)
| field | type | notes |
|---|---|---|
| id | text PK | |
| project_id | text FK | |
| title, premise, hero_image_idea | text | |
| sample_shots | text | JSON list of 3 |
| chosen | bool | at most one per project |

## character
| field | type | notes |
|---|---|---|
| id | text PK | |
| project_id | text FK | |
| name | text | |
| reference_image | text nullable | path |
| style_line | text | appended to prompts of shots that include this character |

## shot
| field | type | notes |
|---|---|---|
| id | text PK | |
| project_id | text FK | |
| ord | int | unique per project |
| start, end | real | segment seconds; end > start; no overlap with neighbours |
| frames | int | derived: rounded to backend frame rule |
| lyric | text | |
| visual | text | |
| action | text | one clear action |
| camera | text | |
| has_figure | bool | false selects the no figure style line |
| lip_sync | bool | requires has_figure |
| plate_prompt | text | |
| motion_prompt | text | |
| state | text | see state machine |
| dirty | bool | set when a field changes after a clip exists |

### Shot state machine
```
draft -> plate_requested -> plate_ready -> plate_approved
plate_approved -> clip_queued -> clip_rendering -> clip_ready -> clip_approved
any -> needs_redo (with note) -> plate_requested | clip_queued
clip_rendering -> clip_failed (guard stop or error) -> clip_queued
```
Editing visual or plate_prompt moves to `needs_redo` for plate; editing action, camera or motion_prompt after a clip moves to `needs_redo` for clip.

## asset_version
| field | type | notes |
|---|---|---|
| id | text PK | |
| shot_id | text FK | |
| kind | text | plate, clip, prompt |
| path | text nullable | file path (null for prompt) |
| text | text nullable | prompt text for kind prompt |
| source | text | adapter or backend name, or `upload` |
| cost_usd | real | |
| active | bool | one active per shot and kind |
| created_at | text | |

## plate_request
| field | type | notes |
|---|---|---|
| id | text PK | |
| shot_id | text FK | |
| adapter_id | text FK | |
| prompt | text | |
| reference_image | text nullable | |
| state | text | pending, approved_cost, running, done, failed |
| est_cost_usd | real | |
| result_asset_id | text FK nullable | |

## render_job
| field | type | notes |
|---|---|---|
| id | text PK | |
| project_id | text FK | |
| shot_id | text FK nullable | null for finish jobs |
| kind | text | clip, lipsync, vocals, finish |
| backend | text | |
| settings | text | JSON: width, height, frames, seed, fps |
| priority | int | queue order |
| state | text | queued, running, paused, done, failed, stopped |
| progress | real | 0..1 |
| sec_per_frame | real nullable | |
| stop_reason | text nullable | e.g. `guard: free 7% < 8%` |
| suggestion | text nullable | e.g. `try 448x800 or 65 frames` |
| log_path | text | |
| started_at, ended_at | text | |

## memory_sample
| field | type | notes |
|---|---|---|
| job_id | text FK | |
| at | text | |
| free_pct | int | |
| swap_mb | int | |
| rss_mb | int | job process group |

## fit_sample
| field | type | notes |
|---|---|---|
| backend, mode | text | |
| width, height, frames | int | |
| peak_used_gb | real | |
| sec_per_frame | real | |
| machine | text | chip and memory |

## stage_approval
| field | type | notes |
|---|---|---|
| project_id | text FK | |
| stage | text | storyboard, plates, clips, final |
| approved_at | text nullable | null means revoked |
| via | text | chat or studio |

## review_note
| field | type | notes |
|---|---|---|
| id | text PK | |
| asset_version_id | text FK | |
| decision | text | approve, reject, comment |
| text | text | |
| at | text | |

## delivery
| field | type | notes |
|---|---|---|
| project_id | text FK | |
| video_path, cover_path, metadata_path | text | |
| target_folder | text nullable | |
| post_time | text nullable | |
| verified | text | JSON report |

## change_event
| field | type | notes |
|---|---|---|
| seq | integer PK autoincrement | monotonic cursor for the Studio |
| at | text | |
| entity | text | table name |
| entity_id | text | |
| kind | text | insert, update, delete |
| actor | text | chat, studio, worker |

## Validation rules
- Shots of a project tile the segment with no gaps or overlaps; first start = 0, last end = segment length.
- `frames >= backend.min_frames`; shorter shots are merged or held (reported).
- `lip_sync` requires `has_figure` and a vocal line overlapping the shot.
- A gate can be approved only when every shot is in the matching approved state.
- Secrets never appear in any column; the repo layer rejects strings matching key patterns.
