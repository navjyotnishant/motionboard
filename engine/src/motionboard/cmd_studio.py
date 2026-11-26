"""mb studio start|stop|status: run the Storyboard Studio on 127.0.0.1 only (002 T004).

First start installs the Node packages (npm ci) and builds the app (next build); later starts reuse the build
unless the Studio source changed. The session token is kept across restarts so open tabs keep working;
`mb studio start --new-session` or `mb studio stop --forget` replaces it.
"""

import os
import secrets
import shutil
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

import typer

from motionboard import config
from motionboard.cli import JsonOpt, app, run
from motionboard.report import MbError

studio_app = typer.Typer(no_args_is_help=True, help="Storyboard Studio (local web app)")
app.add_typer(studio_app, name="studio")

HOST = "127.0.0.1"


def studio_dir() -> Path:
    return config.repo_root() / "studio"


def _pid_file() -> Path:
    return config.home() / "studio.pid"


def _token_file() -> Path:
    return config.home() / "studio.token"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _running() -> tuple[int, int] | None:
    pf = _pid_file()
    if not pf.exists():
        return None
    try:
        pid, port = (int(x) for x in pf.read_text().split())
    except ValueError:
        return None
    return (pid, port) if _alive(pid) else None


def _newest(d: Path) -> float:
    return max((p.stat().st_mtime for p in d.rglob("*") if p.is_file()), default=0.0)


def _needs_build(sd: Path) -> bool:
    bid = sd / ".next" / "BUILD_ID"
    if not bid.exists():
        return True
    built = bid.stat().st_mtime
    return any(_newest(sd / x) > built for x in ("src", "public") if (sd / x).exists()) or \
        (sd / "package.json").stat().st_mtime > built


def _npm(args: list[str], sd: Path, log: Path) -> None:
    with log.open("a") as fh:
        r = subprocess.run(["npm", *args], cwd=sd, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        raise MbError("INTERNAL", f"npm {' '.join(args)} failed; see {log}")


def _wait_up(port: int, seconds: float = 40) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            urllib.request.urlopen(f"http://{HOST}:{port}/api/projects", timeout=2)
        except urllib.error.HTTPError:
            return True  # 403 without the cookie means the server answers
        except OSError:
            time.sleep(0.5)
            continue
        return True
    return False


@studio_app.command("start")
def studio_start(port: int = typer.Option(4317, "--port"), rebuild: bool = typer.Option(False, "--rebuild"),
                 no_open: bool = typer.Option(False, "--no-open", help="Do not open the browser"),
                 new_session: bool = typer.Option(False, "--new-session",
                                                  help="Make a new session token; open tabs must reopen"),
                 as_json: bool = JsonOpt) -> None:
    """Start the Studio and print its URL (with the session token)."""

    def go(conn, r):
        if _running():
            pid, p = _running()
            tok = _token_file().read_text().strip() if _token_file().exists() else ""
            r.data = {"url": f"http://{HOST}:{p}/?session={tok}", "pid": pid, "already_running": True}
            if not no_open and shutil.which("open"):
                subprocess.run(["open", r.data["url"]], check=False)
            return
        if not shutil.which("node") or not shutil.which("npm"):
            raise MbError("MISSING_TOOL", "Node 20 or later is needed for the Studio", hint="brew install node")
        sd = studio_dir()
        log = config.home() / "studio.log"
        log.write_text("")
        if not (sd / "node_modules").exists():
            _npm(["ci", "--no-audit", "--no-fund"], sd, log)
            r.verified.append("installed Studio packages (npm ci)")
        if rebuild or _needs_build(sd):
            _npm(["run", "build"], sd, log)
            r.verified.append("built the Studio (next build)")
        tf = _token_file()
        old = tf.read_text().strip() if tf.exists() else ""
        token = old if (old and not new_session) else secrets.token_urlsafe(24)
        tf.write_text(token)
        tf.chmod(0o600)
        r.verified.append("kept the session token, open tabs keep working" if token == old
                          else "new session token: reopen Studio tabs with mb studio open")
        env = {**os.environ, "MB_STUDIO_TOKEN": token, "PORT": str(port), "MB_HOME": str(config.home()),
               "MB_DB": str(config.db_path()), "MB_PROJECTS": str(config.projects_root()),
               "MB_REPO": str(config.repo_root()), "NODE_ENV": "production"}
        with log.open("a") as fh:
            proc = subprocess.Popen(["npx", "next", "start", "-H", HOST, "-p", str(port)], cwd=sd, env=env,
                                    stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        _pid_file().write_text(f"{proc.pid} {port}")
        if not _wait_up(port):
            raise MbError("INTERNAL", f"the Studio did not answer on port {port}; see {log}")
        r.verified.append(f"Studio answers on http://{HOST}:{port} (localhost only)")
        r.data = {"url": f"http://{HOST}:{port}/?session={token}", "pid": proc.pid, "log": str(log)}
        if not no_open:
            subprocess.run(["open", r.data["url"]], check=False) if shutil.which("open") else None
            r.verified.append("opened the Studio in your browser")
        r.next = "mb studio open to open it again; mb studio stop when done"

    run("mb studio start", as_json, go)


@studio_app.command("open")
def studio_open(as_json: bool = JsonOpt) -> None:
    """Open the running Studio in the browser (with its session link)."""

    def go(conn, r):
        cur = _running()
        if not cur or not _token_file().exists():
            raise MbError("NOT_FOUND", "the Studio is not running", hint="mb studio start")
        url = f"http://{HOST}:{cur[1]}/?session={_token_file().read_text().strip()}"
        if shutil.which("open"):
            subprocess.run(["open", url], check=False)
            r.verified.append("opened the Studio in your browser")
        r.data = {"url": url}

    run("mb studio open", as_json, go)


@studio_app.command("stop")
def studio_stop(forget: bool = typer.Option(False, "--forget", help="Also delete the session token"),
                as_json: bool = JsonOpt) -> None:
    """Stop the Studio. The session token is kept for the next start unless --forget."""

    def go(conn, r):
        cur = _running()
        if not cur:
            _pid_file().unlink(missing_ok=True)
            r.data = {"stopped": False, "reason": "not running"}
            return
        pid, _ = cur
        os.killpg(pid, signal.SIGTERM)
        for _ in range(20):
            if not _alive(pid):
                break
            time.sleep(0.25)
        else:
            os.killpg(pid, signal.SIGKILL)
        _pid_file().unlink(missing_ok=True)
        if forget:
            _token_file().unlink(missing_ok=True)
        r.data = {"stopped": True, "pid": pid}
        kept = "removed" if forget else "kept for the next start"
        r.verified.append(f"Studio process group stopped; session token {kept}")

    run("mb studio stop", as_json, go)


@studio_app.command("status")
def studio_status(as_json: bool = JsonOpt) -> None:
    """Is the Studio running, and where."""

    def go(conn, r):
        cur = _running()
        sd = studio_dir()
        r.data = {"running": bool(cur), "pid": cur[0] if cur else None,
                  "url": f"http://{HOST}:{cur[1]}/" if cur else None,
                  "installed": (sd / "node_modules").exists(), "built": (sd / ".next" / "BUILD_ID").exists()}

    run("mb studio status", as_json, go)
