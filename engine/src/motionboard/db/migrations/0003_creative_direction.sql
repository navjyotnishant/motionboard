-- Feature 003: creative direction. See specs/003-creative-direction-system/data-model.md
-- Art Direction Bible versions, several references per character, shot creative context, critiques.

CREATE TABLE art_direction (
    id           TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    version      INTEGER NOT NULL CHECK (version >= 1),
    profile      TEXT NOT NULL CHECK (profile IN ('compact', 'full')),
    status       TEXT NOT NULL CHECK (status IN ('draft', 'in_review', 'approved', 'superseded')),
    body         TEXT NOT NULL DEFAULT '{}',
    note         TEXT NOT NULL DEFAULT '',
    based_on     TEXT REFERENCES art_direction(id) ON DELETE SET NULL,
    impact       TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    created_via  TEXT NOT NULL DEFAULT 'chat' CHECK (created_via IN ('chat', 'studio', 'worker')),
    approved_at  TEXT,
    approved_via TEXT CHECK (approved_via IN ('chat', 'studio')),
    UNIQUE (project_id, version)
);
CREATE UNIQUE INDEX art_direction_one_approved ON art_direction(project_id) WHERE status = 'approved';
CREATE UNIQUE INDEX art_direction_one_open ON art_direction(project_id) WHERE status IN ('draft', 'in_review');

CREATE TABLE character_reference (
    id           TEXT PRIMARY KEY,
    character_id TEXT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    path         TEXT NOT NULL,
    purpose      TEXT NOT NULL DEFAULT 'other'
                 CHECK (purpose IN ('face', 'silhouette', 'costume', 'material', 'detail', 'turnaround', 'other')),
    description  TEXT NOT NULL DEFAULT '',
    is_primary   INTEGER NOT NULL DEFAULT 0,
    ord          INTEGER NOT NULL DEFAULT 0,
    meta         TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL
);
CREATE UNIQUE INDEX character_reference_one_primary ON character_reference(character_id) WHERE is_primary = 1;
CREATE INDEX character_reference_order ON character_reference(character_id, ord);

-- Existing single references become each character's primary reference. The file does not move.
INSERT INTO character_reference (id, character_id, path, purpose, description, is_primary, ord, meta, created_at)
SELECT 'R' || upper(hex(randomblob(12))), id, reference_image, 'other', '', 1, 0, '{}',
       strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
FROM character
WHERE reference_image IS NOT NULL AND reference_image != '';

ALTER TABLE shot ADD COLUMN creative TEXT NOT NULL DEFAULT '{}';

ALTER TABLE plate_request ADD COLUMN refs TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plate_request ADD COLUMN refs_dropped TEXT NOT NULL DEFAULT '[]';

CREATE TABLE critique (
    id               TEXT PRIMARY KEY,
    project_id       TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    stage            TEXT NOT NULL CHECK (stage IN ('concept', 'art_direction', 'plate', 'rough_cut')),
    role             TEXT NOT NULL CHECK (role IN ('director', 'production_designer', 'cinematographer', 'editor',
                                                   'emotion_editor', 'creator')),
    verdict          TEXT NOT NULL CHECK (verdict IN ('ready', 'revise', 'blocked')),
    summary          TEXT NOT NULL DEFAULT '',
    findings         TEXT NOT NULL DEFAULT '[]',
    checked          TEXT NOT NULL DEFAULT '[]',
    not_checked      TEXT NOT NULL DEFAULT '[]',
    art_direction_id TEXT REFERENCES art_direction(id) ON DELETE SET NULL,
    created_at       TEXT NOT NULL,
    resolved_at      TEXT
);
CREATE INDEX critique_by_project ON critique(project_id, stage, created_at);
