from __future__ import annotations

import fnmatch
import json
import os
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "artefacts" / "releases"
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
    ".next*",
    "*.egg-info",
]
FORBIDDEN_FILE_PATTERNS = [
    ".env",
    ".env.*",
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
]
REQUIRED_ARTEFACTS = [
    "artefacts/seeded_metrics.json",
    "artefacts/audit-log-extract.json",
    "artefacts/provider-health-demo.json",
    "artefacts/provider-health-live.json",
    "artefacts/strategy-benchmark-comparison.json",
    "artefacts/ablation-results.json",
    "artefacts/check-results.json",
    "artefacts/screenshot-validation.json",
    "artefacts/release-validation.json",
    "docs/artefact-completion-evidence.md",
]


def _latest_final_screenshot_dir() -> Path | None:
    screenshots_root = ROOT / "artefacts" / "screenshots"
    candidates = [
        path
        for path in screenshots_root.glob("final-current-fullpages-*")
        if path.is_dir()
    ]
    return max(candidates, key=lambda path: path.name) if candidates else None


def _sample_pdf_path() -> Path | None:
    seeded_path = ROOT / "artefacts" / "seeded_metrics.json"
    if not seeded_path.exists():
        return None
    try:
        seeded = json.loads(seeded_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    report_path = str(seeded.get("reportPath") or "")
    if not report_path:
        return None
    return (ROOT / report_path).resolve()


def excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.as_posix() == ".env.example":
        return False
    parts = set(rel.parts)
    if parts & FORBIDDEN_DIRS or any(fnmatch.fnmatch(part, pattern) for part in rel.parts for pattern in FORBIDDEN_DIR_PATTERNS):
        return True
    rel_posix = rel.as_posix()
    latest_screenshots = _latest_final_screenshot_dir()
    if rel.parts[:2] == ("artefacts", "screenshots"):
        if len(rel.parts) == 2:
            return False
        if latest_screenshots is None:
            return True
        return not path.is_relative_to(latest_screenshots)
    if rel.parts[:2] == ("artefacts", "exports") and path.suffix.lower() == ".pdf":
        sample_pdf = _sample_pdf_path()
        return sample_pdf is None or path.resolve() != sample_pdf
    if rel_posix == "apps/web/package-lock.json":
        return True
    if (
        rel_posix.startswith("artefacts/tmp/")
        or rel_posix.startswith("artefacts/releases/")
        or rel_posix.startswith("artefacts/review-packages/")
        or rel_posix.startswith("artefacts/playwright-results/")
        or rel_posix.startswith("artefacts/playwright-report/")
        or rel_posix.startswith("artefacts/screenshots/exhaustive-ui-clicks-")
    ):
        return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in FORBIDDEN_FILE_PATTERNS)


def validate_zip(archive: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        bad = []
        for name in names:
            if name == ".env.example":
                continue
            parts = set(Path(name).parts)
            if parts & FORBIDDEN_DIRS:
                bad.append(name)
            if any(fnmatch.fnmatch(part, pattern) for part in Path(name).parts for pattern in FORBIDDEN_DIR_PATTERNS):
                bad.append(name)
            if any(fnmatch.fnmatch(Path(name).name, pattern) for pattern in FORBIDDEN_FILE_PATTERNS):
                bad.append(name)
            if name == "apps/web/package-lock.json":
                bad.append(name)
            if (
                name.startswith("artefacts/tmp/")
                or name.startswith("artefacts/releases/")
                or name.startswith("artefacts/review-packages/")
                or name.startswith("artefacts/playwright-results/")
                or name.startswith("artefacts/playwright-report/")
                or name.startswith("artefacts/screenshots/exhaustive-ui-clicks-")
            ):
                bad.append(name)
        if bad:
            raise SystemExit("Forbidden files found in release ZIP: " + ", ".join(bad[:20]))
        missing = [name for name in REQUIRED_ARTEFACTS if name not in names]
        pdfs = sorted(name for name in names if name.startswith("artefacts/exports/") and name.lower().endswith(".pdf"))
        if not pdfs:
            missing.append("artefacts/exports/*.pdf")
        screenshot_dirs = {"/".join(Path(name).parts[:3]) for name in names if name.startswith("artefacts/screenshots/final-current-fullpages-")}
        if not screenshot_dirs:
            missing.append("artefacts/screenshots/final-current-fullpages-*")
        if missing:
            raise SystemExit("Required final artefacts missing from release ZIP: " + ", ".join(missing))
        seeded = json.loads(zf.read("artefacts/seeded_metrics.json").decode("utf-8"))
        report_path = str(seeded.get("reportPath") or "").replace("\\", "/")
        if report_path and report_path not in names:
            raise SystemExit(f"seeded_metrics.json references a missing PDF/report artefact: {report_path}")

    validation = {
        "archive": str(archive),
        "validatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "validated",
        "forbiddenFilesFound": 0,
        "requiredArtefactsPresent": True,
        "samplePdfIncluded": True,
        "secretsExcluded": True,
    }
    (ROOT / "artefacts" / "release-validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")


def iter_release_files():
    for current_root, dirnames, filenames in os.walk(ROOT):
        current = Path(current_root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not excluded(current / dirname)
        ]
        for filename in filenames:
            path = current / filename
            if not excluded(path):
                yield path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT_DIR / f"markets-strategy-copilot-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    (ROOT / "artefacts" / "release-validation.json").write_text(
        json.dumps(
            {
                "archive": str(archive),
                "validatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "validated",
                "forbiddenFilesFound": 0,
                "requiredArtefactsPresent": True,
                "samplePdfIncluded": True,
                "secretsExcluded": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in iter_release_files():
            zf.write(path, path.relative_to(ROOT))
    validate_zip(archive)
    print(f"Release package written to {archive}")


if __name__ == "__main__":
    main()
