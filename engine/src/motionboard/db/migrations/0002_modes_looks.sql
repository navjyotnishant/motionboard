-- Storyboards combine a mode (story + animation pack) and a visual look (spec FR-017).
-- project.look stays the stylized/realistic switch; visual_look is the look slug.
ALTER TABLE project ADD COLUMN mode TEXT;
ALTER TABLE project ADD COLUMN visual_look TEXT;
