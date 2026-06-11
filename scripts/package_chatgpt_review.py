from __future__ import annotations

import fnmatch
import json
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "artefacts" / "review-packages"
FORBIDDEN_DIRS = {
    ".git",
    ".codex_tmp",
    "node_modules",
    ".next",
    ".venv",
    "venv",
    "env",
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
FORBIDDEN_FILES = [
    ".env",
    ".env.*",
    "*.zip",
    "*.db",
    "*.sqlite",
    "*.sqlite*",
    "*.sqlite3",
    "*.log",
    "*.pyc",
    "*.tsbuildinfo",
    "*.egg-info",
    "*.trace.zip",
    "*.webm",
    "*.mp4",
]
ROOT_FILES = {
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "DECISIONS.md",
    "Makefile",
    "README.md",
    "docker-compose.yml",
    "package.json",
}
SOURCE_DIRS = {"apps", "packages", "data", "docs", "scripts", "tests"}
EVIDENCE_FILES = {
    "artefacts/seeded_metrics.json",
    "artefacts/audit-log-extract.json",
    "artefacts/provider-health-demo.json",
    "artefacts/provider-health-live.json",
    "artefacts/strategy-benchmark-comparison.json",
    "artefacts/ablation-results.json",
    "artefacts/screenshot-validation.json",
    "artefacts/release-validation.json",
}


def _latest_final_screenshot_dir() -> Path:
    candidates = [
        path
        for path in (ROOT / "artefacts" / "screenshots").glob("final-current-fullpages-*")
        if path.is_dir()
    ]
    if not candidates:
        raise SystemExit("No final-current-fullpages screenshot folder exists. Run npm run screenshots:final first.")
    return max(candidates, key=lambda path: path.name)


def _sample_pdf_from_seeded_metrics() -> Path:
    seeded_path = ROOT / "artefacts" / "seeded_metrics.json"
    if not seeded_path.exists():
        raise SystemExit("artefacts/seeded_metrics.json is missing. Run python scripts/generate_artefacts.py first.")
    seeded = json.loads(seeded_path.read_text(encoding="utf-8"))
    report_path = Path(str(seeded.get("reportPath") or ""))
    if not report_path.parts:
        raise SystemExit("seeded_metrics.json does not reference a PDF report.")
    candidate = ROOT / report_path
    if not candidate.exists() or candidate.suffix.lower() != ".pdf":
        raise SystemExit(f"Referenced PDF does not exist: {candidate}")
    return candidate


def _is_forbidden(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.as_posix() == ".env.example":
        return False
    if set(rel.parts) & FORBIDDEN_DIRS:
        return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in FORBIDDEN_FILES)


def _include_source(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if _is_forbidden(path):
        return False
    if len(rel.parts) == 1 and rel.as_posix() in ROOT_FILES:
        return True
    if rel.parts and rel.parts[0] in SOURCE_DIRS:
        return True
    return False


def iter_review_files() -> list[Path]:
    files: set[Path] = set()
    latest_screenshots = _latest_final_screenshot_dir()
    sample_pdf = _sample_pdf_from_seeded_metrics()

    for path in ROOT.rglob("*"):
        if path.is_file() and _include_source(path):
            files.add(path)

    for rel_path in EVIDENCE_FILES:
        path = ROOT / rel_path
        if path.exists():
            files.add(path)

    files.add(sample_pdf)
    for path in latest_screenshots.rglob("*"):
        if path.is_file() and not _is_forbidden(path):
            files.add(path)

    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def validate_review_zip(archive: Path, latest_screenshots: Path, sample_pdf: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    bad = []
    for name in names:
        if name == ".env.example":
            continue
        rel = Path(name)
        if set(rel.parts) & FORBIDDEN_DIRS:
            bad.append(name)
        if any(fnmatch.fnmatch(rel.name, pattern) for pattern in FORBIDDEN_FILES):
            bad.append(name)
    if bad:
        raise SystemExit("Forbidden files found in ChatGPT review ZIP: " + ", ".join(bad[:20]))

    expected_screenshot_prefix = latest_screenshots.relative_to(ROOT).as_posix() + "/"
    screenshot_names = [name for name in names if name.startswith("artefacts/screenshots/")]
    if not screenshot_names or any(not name.startswith(expected_screenshot_prefix) for name in screenshot_names):
        raise SystemExit("Review ZIP must include only the latest final-current-fullpages screenshot folder.")
    if sample_pdf.relative_to(ROOT).as_posix() not in names:
        raise SystemExit("Review ZIP is missing the sample PDF referenced by seeded_metrics.json.")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT_DIR / f"markets-strategy-copilot-chatgpt-final-code-screenshots-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    latest_screenshots = _latest_final_screenshot_dir()
    sample_pdf = _sample_pdf_from_seeded_metrics()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in iter_review_files():
            zf.write(path, path.relative_to(ROOT))
    validate_review_zip(archive, latest_screenshots, sample_pdf)
    print(f"ChatGPT review package written to {archive}")


if __name__ == "__main__":
    main()
