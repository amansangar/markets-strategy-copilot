from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
import platform
import time
import urllib.request


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


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    display_command = [Path(part).name if Path(part).is_absolute() else part for part in command]
    print(f":: {' '.join(display_command)}")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(command, cwd=cwd, env=merged, check=True)


def stop_dev_servers() -> None:
    """Avoid reusing stale Next/Uvicorn dev servers after build steps."""
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
    node = node_cmd()
    python = python_cmd()
    test_db = ROOT / "apps" / "api" / "test_app.db"
    run([python, "-m", "pytest", "tests", "-q"], ROOT / "apps" / "api", {"DATABASE_URL": f"sqlite:///{test_db.as_posix()}"})
    run([node, "node_modules/eslint/bin/eslint.js", "app", "components", "lib", "tests", "--max-warnings=0"], ROOT / "apps" / "web")
    run([node, "node_modules/typescript/bin/tsc", "--noEmit"], ROOT / "apps" / "web")
    stop_dev_servers()
    clean_next_build()
    run([node, "node_modules/next/dist/bin/next", "build", "--webpack"], ROOT / "apps" / "web", {"NEXT_PUBLIC_API_BASE_URL": "http://127.0.0.1:8000"})
    stop_dev_servers()
    e2e_env = os.environ.copy()
    e2e_env["NEXT_PUBLIC_API_BASE_URL"] = "http://127.0.0.1:8000"
    e2e_env["PYTHON_EXECUTABLE"] = python
    e2e_db = ROOT / "artefacts" / "tmp" / f"check_e2e_{os.getpid()}.db"
    e2e_db.parent.mkdir(parents=True, exist_ok=True)
    e2e_env["DATABASE_URL"] = f"sqlite:///{e2e_db.as_posix()}"
    servers: list[tuple[subprocess.Popen[str], object, object]] = []
    try:
        servers.append(
            start_server(
                [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                ROOT / "apps" / "api",
                e2e_env,
                "check-api",
            )
        )
        wait_for_url("http://127.0.0.1:8000/api/v1/demo/briefing")
        servers.append(
            start_server(
                [node, "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3000"],
                ROOT / "apps" / "web",
                e2e_env,
                "check-web",
            )
        )
        wait_for_url("http://127.0.0.1:3000")
        playwright_env = e2e_env.copy()
        playwright_env["PLAYWRIGHT_MANAGED_SERVERS"] = "0"
        run(
            [node, playwright_cli(), "test", "--project=chromium-desktop"],
            ROOT / "apps" / "web",
            playwright_env,
        )
    finally:
        stop_servers(servers)
        stop_dev_servers()


if __name__ == "__main__":
    main()
