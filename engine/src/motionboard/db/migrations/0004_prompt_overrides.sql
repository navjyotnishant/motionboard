-- Feature 003 corrective pass: generated prompt baselines are kept apart from creator-authored overrides.
-- shot.plate_prompt and shot.motion_prompt stay the effective text every renderer reads.
-- *_base is what the engine last generated; NULL means the shot was made before this migration and is settled
-- on first use (a stored prompt that differs from what the engine would generate is kept as authored).
-- *_authored = 1 marks an override the engine never rewrites. override_kept records, per part, the art direction
-- version at which the creator chose to keep an override after review.

ALTER TABLE shot ADD COLUMN plate_base TEXT;
ALTER TABLE shot ADD COLUMN motion_base TEXT;
ALTER TABLE shot ADD COLUMN plate_authored INTEGER NOT NULL DEFAULT 0;
ALTER TABLE shot ADD COLUMN motion_authored INTEGER NOT NULL DEFAULT 0;
ALTER TABLE shot ADD COLUMN override_kept TEXT NOT NULL DEFAULT '{}';
