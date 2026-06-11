from __future__ import annotations

import fnmatch
import os
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "artefacts" / "releases"

SOURCE_DIRS = {"apps", "packages", "data", "docs", "scripts", "tests"}
ROOT_FILES = {
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "DECISIONS.md",
    "Makefile",
    "README.md",
    "docker-compose.yml",
    "package.json",
    "package-lock.json",
}
ALLOWED_ARTEFACT_MARKERS = {
    "artefacts/.gitkeep",
    "artefacts/exports/.gitkeep",
}

FORBIDDEN_DIRS = {
    ".git",
    ".codex_tmp",
    "node_modules",
    ".next",
    "out",
    ".venv",
    "venv",
    "env",
    "postgres-data",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".cache",
    "dist",
    "build",
    "coverage",
    "htmlcov",
}
FORBIDDEN_DIR_PATTERNS = [
    "*.egg-info",
]
FORBIDDEN_FILE_PATTERNS = [
    ".env",
    ".env.*",
    ".coverage",
    "*.zip",
    "*.pem",
    "*.key",
    "*.db",
    "*.sqlite",
    "*.sqlite*",
    "*.sqlite3",
    "*.db-journal",
    "*.pyc",
    "*.log",
    "*.tsbuildinfo",
    "*.trace.zip",
    "*.webm",
    "*.mp4",
    "*.pdf",
    "*.png",
    "*.jpg",
    "*.jpeg",
]
FORBIDDEN_ARTEFACT_PREFIXES = (
    "artefacts/screenshots/",
    "artefacts/releases/",
    "artefacts/review-packages/",
    "artefacts/tmp/",
    "artefacts/playwright-results/",
    "artefacts/playwright-report/",
)
FORBIDDEN_ARTEFACT_FILES = {
    "artefacts/seeded_metrics.json",
    "artefacts/audit-log-extract.json",
    "artefacts/provider-health-demo.json",
    "artefacts/provider-health-live.json",
    "artefacts/strategy-benchmark-comparison.json",
    "artefacts/ablation-results.json",
    "artefacts/check-results.json",
    "artefacts/screenshot-validation.json",
    "artefacts/release-validation.json",
}


def _prepare_marker_folders() -> None:
    for rel_path in ALLOWED_ARTEFACT_MARKERS:
        path = ROOT / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")


def _is_forbidden(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    if rel_posix == ".env.example":
        return False
    if rel_posix in ALLOWED_ARTEFACT_MARKERS:
        return False
    if set(rel.parts) & FORBIDDEN_DIRS:
        return True
    if any(fnmatch.fnmatch(part, pattern) for part in rel.parts for pattern in FORBIDDEN_DIR_PATTERNS):
        return True
    if any(fnmatch.fnmatch(path.name, pattern) for pattern in FORBIDDEN_FILE_PATTERNS):
        return True
    if rel_posix in FORBIDDEN_ARTEFACT_FILES:
        return True
    if any(rel_posix == prefix.rstrip("/") or rel_posix.startswith(prefix) for prefix in FORBIDDEN_ARTEFACT_PREFIXES):
        return True
    if rel_posix == "apps/web/package-lock.json":
        return True
    return False


def _include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    if _is_forbidden(path):
        return False
    if rel_posix in ROOT_FILES or rel_posix in ALLOWED_ARTEFACT_MARKERS:
        return True
    return bool(rel.parts and rel.parts[0] in SOURCE_DIRS)


def iter_submission_files() -> list[Path]:
    _prepare_marker_folders()
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(ROOT):
        current = Path(current_root)
        dirnames[:] = [dirname for dirname in dirnames if not _is_forbidden(current / dirname)]
        for filename in filenames:
            path = current / filename
            if _include(path):
                files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def validate_zip(archive: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    bad: list[str] = []
    for name in names:
        rel = Path(name)
        if name == ".env.example":
            continue
        if set(rel.parts) & FORBIDDEN_DIRS:
            bad.append(name)
        if any(fnmatch.fnmatch(part, pattern) for part in rel.parts for pattern in FORBIDDEN_DIR_PATTERNS):
            bad.append(name)
        if any(fnmatch.fnmatch(rel.name, pattern) for pattern in FORBIDDEN_FILE_PATTERNS):
            bad.append(name)
        if name in FORBIDDEN_ARTEFACT_FILES:
            bad.append(name)
        if any(name == prefix.rstrip("/") or name.startswith(prefix) for prefix in FORBIDDEN_ARTEFACT_PREFIXES):
            bad.append(name)
    required = {".env.example", "README.md", "apps/api/pyproject.toml", "apps/web/package.json", "data/demo/policy.yml"}
    missing = sorted(required - names)
    if "artefacts/.gitkeep" not in names or "artefacts/exports/.gitkeep" not in names:
        missing.append("artefacts/.gitkeep and artefacts/exports/.gitkeep")
    if bad:
        raise SystemExit("Forbidden files found in source submission ZIP: " + ", ".join(sorted(set(bad))[:20]))
    if missing:
        raise SystemExit("Required source files missing from source submission ZIP: " + ", ".join(missing))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT_DIR / f"markets-strategy-copilot-source-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in iter_submission_files():
            zf.write(path, path.relative_to(ROOT))
    validate_zip(archive)
    print(f"Source submission package written to {archive}")


if __name__ == "__main__":
    main()
