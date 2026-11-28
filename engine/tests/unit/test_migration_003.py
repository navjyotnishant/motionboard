"""Migration 0003 on a database made before feature 003 (FR-010, FR-025): old references stay usable."""

import json
import shutil

from typer.testing import CliRunner

from motionboard.cli import app
from motionboard.db.connection import connect, current_version, latest_version, migrate

runner = CliRunner()


def mb(*args):
    return json.loads(runner.invoke(app, [*args, "--json"]).stdout)


def test_old_database_keeps_references_and_work(mb_home, fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("MB_BACKEND", "stub")
    # Build a schema-2 database by hand, as a pre-003 install left it.
    conn = connect()
    migrate(conn, target=2)
    assert current_version(conn) == 2
    ref = tmp_path / "legacy-her.png"
    shutil.copy(fixtures_dir / "plates" / "shot-01.png", ref)
    folder = tmp_path / "projects" / "legacy"
    (folder / "plates").mkdir(parents=True)
    conn.execute("INSERT INTO project(id, title, folder, aspect, created_at, updated_at, segment_start, segment_end) "
                 "VALUES ('P1LEGACY', 'Legacy', ?, '9:16', 'x', 'x', 0, 4)", (str(folder),))
    conn.execute("INSERT INTO character(id, project_id, name, reference_image, style_line) "
                 "VALUES ('C1HER', 'P1LEGACY', 'HER', ?, 'a red paper woman')", (str(ref),))
    conn.execute("INSERT INTO character(id, project_id, name, reference_image, style_line) "
                 "VALUES ('C2HIM', 'P1LEGACY', 'HIM', NULL, '')")
    conn.execute("INSERT INTO shot(id, project_id, ord, start, \"end\", lyric, visual, action, camera, has_figure, "
                 "state, updated_at) VALUES ('S1', 'P1LEGACY', 1, 0, 4, 'l', 'HER waits', 'she waits', 'still', 1, "
                 "'plate_approved', 'x')")
    conn.execute("INSERT INTO shot_character VALUES ('S1', 'C1HER')")
    conn.execute("INSERT INTO stage_approval VALUES ('P1LEGACY', 'storyboard', '2026-11-01', 'chat')")
    conn.close()

    conn = connect()
    applied = migrate(conn)
    assert applied == ["0003_creative_direction.sql", "0004_prompt_overrides.sql"]
    assert current_version(conn) == latest_version()
    refs = [dict(r) for r in conn.execute("SELECT * FROM character_reference")]
    assert len(refs) == 1
    assert refs[0]["character_id"] == "C1HER" and refs[0]["path"] == str(ref)
    assert refs[0]["is_primary"] == 1 and refs[0]["purpose"] == "other"
    assert conn.execute("SELECT reference_image FROM character WHERE id = 'C1HER'").fetchone()[0] == str(ref)
    shot = dict(conn.execute("SELECT * FROM shot WHERE id = 'S1'").fetchone())
    assert shot["creative"] == "{}" and shot["state"] == "plate_approved"
    assert conn.execute("SELECT approved_at FROM stage_approval").fetchone()[0] == "2026-11-01"
    conn.close()

    # The CLI still lists the character with its old reference, now as the primary.
    chars = {c["name"]: c for c in mb("character", "list", "-p", "P1LEGACY")["data"]["characters"]}
    assert chars["HER"]["reference_image"] == str(ref)
    assert [(r["path"], r["primary"]) for r in chars["HER"]["references"]] == [(str(ref), True)]
    assert chars["HIM"]["references"] == []
    # No Bible: nothing new blocks the project.
    assert mb("art", "history", "-p", "P1LEGACY")["data"]["versions"] == []
