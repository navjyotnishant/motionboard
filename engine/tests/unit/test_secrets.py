import pytest

from motionboard.db import repo
from motionboard.db.connection import open_db
from motionboard.report import Report, redact

FAKE_KEYS = [
    "sk-ant-api03-" + "a" * 40,
    "sk-" + "B" * 40,
    "ghp_" + "c" * 36,
    "hf_" + "d" * 34,
    "AKIA" + "E" * 16,
    "api_key = " + "f" * 32,
]


@pytest.fixture
def conn(mb_home):
    c = open_db()
    yield c
    c.close()


@pytest.mark.parametrize("key", FAKE_KEYS)
def test_repo_refuses_secret_values(conn, key):
    with pytest.raises(repo.SecretValueError):
        repo.insert(conn, "plate_adapter", {"name": "x", "kind": "http", "config": {"token": key}}, "chat")
    with pytest.raises(repo.SecretValueError):
        repo.set_setting(conn, "something", key, "chat")
    assert repo.find(conn, "plate_adapter") == []


def test_repo_allows_key_references(conn):
    cfg = {"key_file": "~/.navaan-assets/meta_api_key", "key_env": "MUSE_API_KEY"}
    rid = repo.insert(conn, "plate_adapter", {"name": "muse", "kind": "http", "config": cfg}, "chat")
    assert repo.get(conn, "plate_adapter", rid)["name"] == "muse"


@pytest.mark.parametrize("key", FAKE_KEYS)
def test_reports_redact_secrets(key):
    r = Report(command="mb test", data={"echo": f"value {key} end"})
    assert key not in r.to_json()
    assert key not in r.to_text()
    assert "[REDACTED]" in r.to_json()


def test_redact_bearer_header():
    assert "abc123" not in redact("Authorization: Bearer abc123")
