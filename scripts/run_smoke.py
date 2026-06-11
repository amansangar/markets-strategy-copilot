from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def node_cmd() -> str:
    return shutil.which("node") or "node"


def python_cmd() -> str:
    return shutil.which("python") or shutil.which("python3") or sys.executable


def playwright_cli() -> str:
    candidates = [
        ROOT / "node_modules" / "@playwright" / "test" / "cli.js",
        ROOT / "apps" / "web" / "node_modules" / "@playwright" / "test" / "cli.js",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def stop_dev_servers() -> None:
    if platform.system().lower() != "windows":
        return
    # Port-based cleanup is more reliable than matching Windows command lines:
    # stale Next servers can otherwise serve old hashed chunks after a rebuild.
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "$pids = Get-NetTCPConnection -LocalPort 3000,8000 -State Listen -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique; "
            "foreach ($pid in $pids) { if ($pid -and $pid -ne $PID) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } }",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    query = subprocess.run(
        ["wmic", "process", "get", "ProcessId,CommandLine", "/format:list"],
        capture_output=True,
        text=True,
        check=False,
    )
    command_line = ""
    for raw_line in query.stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("CommandLine="):
            command_line = line.removeprefix("CommandLine=")
            continue
        if not line.startswith("ProcessId="):
            continue
        process_id = line.removeprefix("ProcessId=").strip()
        if process_id and (("uvicorn app.main:app" in command_line) or ("next" in command_line and "node.exe" in command_line.lower())):
            subprocess.run(["taskkill", "/F", "/PID", process_id], check=False, capture_output=True, text=True)
        command_line = ""


def clean_next_build() -> None:
    target = (ROOT / "apps" / "web" / ".next").resolve()
    web_root = (ROOT / "apps" / "web").resolve()
    if not target.exists():
        return
    if web_root not in target.parents:
        raise RuntimeError(f"Refusing to clean unexpected path: {target}")
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            shutil.rmtree(target)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(2)
    stale_target = web_root / f".next.stale.{int(time.time())}"
    try:
        target.rename(stale_target)
        return
    except OSError as exc:
        raise RuntimeError(f"Unable to clean or rotate {target}: {last_error or exc}") from exc


def wait_for_url(url: str, timeout_seconds: float = 240.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "not checked"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status < 500:
                    return
                last_error = f"HTTP {response.status}"
        except Exception as exc:  # noqa: BLE001 - startup probes should keep retrying.
            last_error = str(exc)
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def warm_smoke_paths(mode: str) -> None:
    """Prime deterministic read-heavy routes before the browser suite starts."""
    urls = [
        "http://127.0.0.1:8000/api/v1/demo/briefing",
        f"http://127.0.0.1:8000/api/v1/dashboard?mode={mode}&symbol=SPY",
        f"http://127.0.0.1:8000/api/v1/assets/SPY?mode={mode}",
        f"http://127.0.0.1:8000/api/v1/scanner?mode={mode}",
        f"http://127.0.0.1:8000/api/v1/portfolio?mode={mode}",
        "http://127.0.0.1:8000/api/v1/workspace",
    ]
    for url in urls:
        wait_for_url(url, timeout_seconds=300.0)


def start_server(command: list[str], cwd: Path, env: dict[str, str], name: str) -> tuple[subprocess.Popen[str], object, object]:
    log_dir = ROOT / "artefacts" / "tmp"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / f"{name}.out.log").open("w", encoding="utf-8")
    stderr = (log_dir / f"{name}.err.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        text=True,
    )
    return process, stdout, stderr


def stop_servers(processes: list[tuple[subprocess.Popen[str], object, object]]) -> None:
    for process, _, _ in processes:
        if process.poll() is None:
            process.terminate()
    for process, _, _ in processes:
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
    for _, stdout, stderr in processes:
        stdout.close()
        stderr.close()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"
    playwright_args = sys.argv[2:]
    python = python_cmd()
    env = os.environ.copy()
    env["MARKETS_TEST_MODE"] = mode
    env["NEXT_PUBLIC_API_BASE_URL"] = "http://127.0.0.1:8000"
    env["PYTHON_EXECUTABLE"] = python
    smoke_db = ROOT / "artefacts" / "tmp" / f"smoke_{os.getpid()}.db"
    smoke_db.parent.mkdir(parents=True, exist_ok=True)
    env["DATABASE_URL"] = f"sqlite:///{smoke_db.as_posix()}"
    stop_dev_servers()
    clean_next_build()
    subprocess.run(
        [node_cmd(), "node_modules/next/dist/bin/next", "build", "--webpack"],
        cwd=ROOT / "apps" / "web",
        env=env,
        check=True,
    )
    servers: list[tuple[subprocess.Popen[str], object, object]] = []
    try:
        servers.append(
            start_server(
                [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                ROOT / "apps" / "api",
                env,
                "smoke-api",
            )
        )
        wait_for_url("http://127.0.0.1:8000/api/v1/demo/briefing")
        warm_smoke_paths(mode)
        servers.append(
            start_server(
                [node_cmd(), "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3000"],
                ROOT / "apps" / "web",
                env,
                "smoke-web",
            )
        )
        wait_for_url("http://127.0.0.1:3000")
        playwright_env = env.copy()
        playwright_env["PLAYWRIGHT_MANAGED_SERVERS"] = "0"
        subprocess.run(
            [node_cmd(), playwright_cli(), "test", "--project=chromium-desktop", *playwright_args],
            cwd=ROOT / "apps" / "web",
            env=playwright_env,
            check=True,
        )
    finally:
        stop_servers(servers)
        stop_dev_servers()


if __name__ == "__main__":
    main()
