from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[3]


def test_packaging_scripts_exclude_secrets_and_local_junk() -> None:
    ps1 = (ROOT / "scripts" / "package_release.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "scripts" / "package_release.sh").read_text(encoding="utf-8")
    packager = (ROOT / "scripts" / "package_release.py").read_text(encoding="utf-8")
    submission_packager = (ROOT / "scripts" / "package_submission.py").read_text(encoding="utf-8")
    required = [
        ".env",
        ".env.*",
        "*.zip",
        "*.egg-info",
        "*.tsbuildinfo",
        "node_modules",
        ".next",
        "*.db",
        ".pytest_cache",
        ".codex_tmp",
        "artefacts/playwright-results",
        "apps/web/package-lock.json",
        "artefacts/screenshots/exhaustive-ui-clicks-",
        "artefacts/exports/*.pdf",
        "artefacts/provider-health-demo.json",
        "artefacts/provider-health-live.json",
    ]
    for needle in required:
        assert needle in packager
    submission_required = [
        ".env",
        ".env.*",
        "*.zip",
        "*.egg-info",
        "*.tsbuildinfo",
        "node_modules",
        ".next",
        "*.db",
        ".pytest_cache",
        ".codex_tmp",
        "artefacts/playwright-results",
        "apps/web/package-lock.json",
        "artefacts/screenshots/",
        "artefacts/exports/.gitkeep",
        "artefacts/seeded_metrics.json",
        "artefacts/audit-log-extract.json",
        "artefacts/provider-health-demo.json",
        "artefacts/provider-health-live.json",
    ]
    for needle in submission_required:
        assert needle in submission_packager
    assert "scripts/package_release.py" in ps1
    assert "scripts/package_release.py" in sh


def test_python_package_release_excludes_forbidden_files() -> None:
    result = subprocess.run([sys.executable, "scripts/package_release.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    archive = Path(result.stdout.strip().split("Release package written to ")[-1])
    assert archive.exists()
    forbidden_parts = {"node_modules", ".next", ".git", ".pytest_cache", "__pycache__", ".codex_tmp"}
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert ".env.example" in names
    assert all(".env" != Path(name).name for name in names)
    assert all(not (set(Path(name).parts) & forbidden_parts) for name in names)
    assert all(not Path(name).name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
    assert "apps/web/package-lock.json" not in names
    assert all(not name.startswith("artefacts/playwright-results/") for name in names)
    assert all(not name.startswith("artefacts/playwright-report/") for name in names)
    assert all(not name.startswith("artefacts/screenshots/exhaustive-ui-clicks-") for name in names)


def test_python_package_submission_is_source_only() -> None:
    result = subprocess.run([sys.executable, "scripts/package_submission.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    archive = Path(result.stdout.strip().split("Source submission package written to ")[-1])
    assert archive.exists()
    forbidden_parts = {"node_modules", ".next", ".git", ".pytest_cache", "__pycache__", ".codex_tmp"}
    generated_artefacts = {
        "artefacts/seeded_metrics.json",
        "artefacts/audit-log-extract.json",
        "artefacts/provider-health-demo.json",
        "artefacts/provider-health-live.json",
        "artefacts/strategy-benchmark-comparison.json",
        "artefacts/ablation-results.json",
    }
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert ".env.example" in names
    assert "artefacts/.gitkeep" in names
    assert "artefacts/exports/.gitkeep" in names
    assert all(".env" != Path(name).name for name in names)
    assert all(not (set(Path(name).parts) & forbidden_parts) for name in names)
    assert all(not Path(name).name.endswith((".db", ".sqlite", ".sqlite3", ".pdf", ".png", ".jpg", ".jpeg", ".tsbuildinfo")) for name in names)
    assert all(not name.startswith("artefacts/screenshots/") for name in names)
    assert all(name not in generated_artefacts for name in names)
