-- Motionboard schema v1. Owned by the engine (constitution VIII). See specs/001-music-video-pipeline/data-model.md

CREATE TABLE workspace_setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE guard_profile (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    start_free_pct  INTEGER NOT NULL CHECK (start_free_pct BETWEEN 1 AND 99),
    kill_free_pct   INTEGER NOT NULL CHECK (kill_free_pct BETWEEN 1 AND 50),
    swap_ceiling_mb INTEGER NOT NULL CHECK (swap_ceiling_mb >= 0),
    poll_seconds    REAL NOT NULL DEFAULT 2 CHECK (poll_seconds BETWEEN 0.5 AND 10),
    builtin         INTEGER NOT NULL DEFAULT 0,
    CHECK (start_free_pct > kill_free_pct)
);

CREATE TABLE plate_adapter (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL UNIQUE,
    kind               TEXT NOT NULL CHECK (kind IN ('manual', 'command', 'http', 'handoff')),
    config             TEXT NOT NULL DEFAULT '{}',
    cost_per_image_usd REAL NOT NULL DEFAULT 0,
    enabled            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE template (
    id     TEXT PRIMARY KEY,
    name   TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL CHECK (source IN ('builtin', 'user')),
    body   TEXT NOT NULL
);

CREATE TABLE project (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    folder           TEXT NOT NULL UNIQUE,
    song_path        TEXT,
    segment_start    REAL,
    segment_end      REAL,
    lyrics           TEXT NOT NULL DEFAULT '',
    idea             TEXT NOT NULL DEFAULT '',
    aspect           TEXT NOT NULL CHECK (aspect IN ('9:16', '16:9')),
    look             TEXT NOT NULL DEFAULT 'stylized' CHECK (look IN ('stylized', 'realistic')),
    theme            TEXT NOT NULL DEFAULT '{}',
    template_id      TEXT REFERENCES template(id),
    concept_id       TEXT,
    video_backend    TEXT NOT NULL DEFAULT 'ltx23',
    plate_adapter_id TEXT REFERENCES plate_adapter(id),
    synthetic_people INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE song_analysis (
    project_id               TEXT PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
    tempo_bpm                REAL,
    beats                    TEXT NOT NULL DEFAULT '[]',
    lines                    TEXT NOT NULL DEFAULT '[]',
    loudness                 TEXT NOT NULL DEFAULT '[]',
    waveform_peaks           TEXT NOT NULL DEFAULT '[]',
    verified_vocal_alignment INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE concept (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    premise         TEXT NOT NULL DEFAULT '',
    hero_image_idea TEXT NOT NULL DEFAULT '',
    sample_shots    TEXT NOT NULL DEFAULT '[]',
    chosen          INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX concept_one_chosen ON concept(project_id) WHERE chosen = 1;

CREATE TABLE character (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    reference_image TEXT,
    style_line      TEXT NOT NULL DEFAULT '',
    UNIQUE (project_id, name)
);

CREATE TABLE shot (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    ord           INTEGER NOT NULL,
    start         REAL NOT NULL,
    "end"         REAL NOT NULL,
    frames        INTEGER NOT NULL DEFAULT 0,
    lyric         TEXT NOT NULL DEFAULT '',
    visual        TEXT NOT NULL DEFAULT '',
    action        TEXT NOT NULL DEFAULT '',
    camera        TEXT NOT NULL DEFAULT '',
    has_figure    INTEGER NOT NULL DEFAULT 0,
    lip_sync      INTEGER NOT NULL DEFAULT 0,
    plate_prompt  TEXT NOT NULL DEFAULT '',
    motion_prompt TEXT NOT NULL DEFAULT '',
    state         TEXT NOT NULL DEFAULT 'draft' CHECK (state IN (
        'draft', 'plate_requested', 'plate_ready', 'plate_approved',
        'clip_queued', 'clip_rendering', 'clip_ready', 'clip_approved',
        'clip_failed', 'needs_redo')),
    dirty         INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT NOT NULL,
    UNIQUE (project_id, ord),
    CHECK ("end" > start),
    CHECK (lip_sync = 0 OR has_figure = 1)
);

CREATE TABLE shot_character (
    shot_id      TEXT NOT NULL REFERENCES shot(id) ON DELETE CASCADE,
    character_id TEXT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    PRIMARY KEY (shot_id, character_id)
);

CREATE TABLE asset_version (
    id         TEXT PRIMARY KEY,
    shot_id    TEXT NOT NULL REFERENCES shot(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN ('plate', 'clip', 'prompt')),
    path       TEXT,
    text       TEXT,
    source     TEXT NOT NULL,
    cost_usd   REAL NOT NULL DEFAULT 0,
    active     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX asset_one_active ON asset_version(shot_id, kind) WHERE active = 1;

CREATE TABLE plate_request (
    id                TEXT PRIMARY KEY,
    shot_id           TEXT NOT NULL REFERENCES shot(id) ON DELETE CASCADE,
    adapter_id        TEXT NOT NULL REFERENCES plate_adapter(id),
    prompt            TEXT NOT NULL,
    reference_image   TEXT,
    state             TEXT NOT NULL DEFAULT 'pending'
                      CHECK (state IN ('pending', 'approved_cost', 'running', 'done', 'failed')),
    est_cost_usd      REAL NOT NULL DEFAULT 0,
    result_asset_id   TEXT REFERENCES asset_version(id),
    created_at        TEXT NOT NULL
);

CREATE TABLE render_job (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    shot_id       TEXT REFERENCES shot(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL CHECK (kind IN ('clip', 'lipsync', 'vocals', 'finish', 'plate')),
    backend       TEXT NOT NULL,
    settings      TEXT NOT NULL DEFAULT '{}',
    priority      INTEGER NOT NULL DEFAULT 0,
    state         TEXT NOT NULL DEFAULT 'queued'
                  CHECK (state IN ('queued', 'running', 'paused', 'done', 'failed', 'stopped')),
    progress      REAL NOT NULL DEFAULT 0,
    sec_per_frame REAL,
    stop_reason   TEXT,
    suggestion    TEXT,
    log_path      TEXT,
    created_at    TEXT NOT NULL,
    started_at    TEXT,
    ended_at      TEXT
);
CREATE INDEX render_job_queue ON render_job(state, priority, created_at);

CREATE TABLE memory_sample (
    job_id   TEXT NOT NULL REFERENCES render_job(id) ON DELETE CASCADE,
    at       TEXT NOT NULL,
    free_pct INTEGER NOT NULL,
    swap_mb  INTEGER NOT NULL,
    rss_mb   INTEGER NOT NULL
);
CREATE INDEX memory_sample_job ON memory_sample(job_id, at);

CREATE TABLE fit_sample (
    backend       TEXT NOT NULL,
    mode          TEXT NOT NULL,
    width         INTEGER NOT NULL,
    height        INTEGER NOT NULL,
    frames        INTEGER NOT NULL,
    peak_used_gb  REAL NOT NULL,
    sec_per_frame REAL,
    machine       TEXT NOT NULL,
    at            TEXT NOT NULL
);

CREATE TABLE stage_approval (
    project_id  TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    stage       TEXT NOT NULL CHECK (stage IN ('storyboard', 'plates', 'clips', 'final')),
    approved_at TEXT,
    via         TEXT NOT NULL CHECK (via IN ('chat', 'studio')),
    PRIMARY KEY (project_id, stage)
);

CREATE TABLE review_note (
    id               TEXT PRIMARY KEY,
    asset_version_id TEXT NOT NULL REFERENCES asset_version(id) ON DELETE CASCADE,
    decision         TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'comment')),
    text             TEXT NOT NULL DEFAULT '',
    at               TEXT NOT NULL
);

CREATE TABLE delivery (
    project_id    TEXT PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
    video_path    TEXT,
    cover_path    TEXT,
    metadata_path TEXT,
    target_folder TEXT,
    post_time     TEXT,
    verified      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE change_event (
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT NOT NULL,
    entity    TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    kind      TEXT NOT NULL CHECK (kind IN ('insert', 'update', 'delete')),
    actor     TEXT NOT NULL CHECK (actor IN ('chat', 'studio', 'worker'))
);
