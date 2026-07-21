# SPDX-License-Identifier: FSL-1.1-ALv2
"""Wheel-safe bundled resource and documented CLI parser tests."""
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from cli import apl
from cli.commands import _common, _resources

REPO = Path(__file__).resolve().parents[1]


def test_bundled_resources_work_without_source_tree(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_resources, "SOURCE_ROOT", tmp_path / "missing-source")
    scenario = _resources.bundled_scenario_path("00_private_matter")
    assert (scenario / "input.original.example.txt").is_file()
    assert (scenario / "masking_plan.yaml").is_file()
    playground = _resources.playground_root()
    assert (playground / "app" / "local_playground" / "index.html").is_file()
    policy = _common.load_policy_manifest()
    assert policy["policy_id"] == "apl-oss-demo-policy"


def test_packaged_public_key_fallback(tmp_path: Path):
    """MEASUREMENT-FLOOR gate (RC-2): the WHEEL — not the source tree — must
    carry every demo pubkey needed to verify the committed example receipts.

    The old version of this test read the SOURCE receipt+key from the repo cwd
    (`_source_checkout()` True), so it passed even when the wheel omitted the
    -02 key — the false-green that shipped the 0.2.1 bug. This version builds a
    wheel, installs it into a fresh venv, and runs `apl verify` (NO --pubkey)
    on every shipped example receipt from a NEUTRAL temp cwd with an empty
    APL_KEY_DIR — so the ONLY key source is the wheel. It also asserts
    `resources.files('spec')` lives under site-packages (no cwd shadow).

    Delegates to scripts/smoke_installed_wheel.py::measurement_floor so the CI
    smoke and this unit gate encode the exact same check from one source.
    """
    build = pytest.importorskip("build")  # noqa: F841
    # Build from an ISOLATED snapshot of the tracked tree, not REPO in place:
    # a stale in-tree build/lib/spec (left by a prior wheel build) is reused by
    # setuptools and would ship files the current package-data glob excludes —
    # a build-hygiene false-green. `git archive` yields exactly the committed
    # (staged) tree with no build artifacts. Falls back to REPO if git is
    # unavailable (with a fresh outdir; the caller's tmp_path is clean anyway).
    src = tmp_path / "src"
    listed = subprocess.run(
        ["git", "-C", str(REPO), "ls-files"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if listed.returncode == 0:
        import shutil
        for rel in listed.stdout.splitlines():
            rel = rel.strip()
            if not rel:
                continue
            source = REPO / rel
            if not source.is_file():
                continue  # e.g. a deleted-but-tracked path
            target = src / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        build_root = src  # tracked working-tree snapshot, no build/ artifacts
    else:
        build_root = REPO  # best-effort; tmp outdir keeps wheels isolated
    dist = tmp_path / "dist"
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", str(build_root),
         "--outdir", str(dist)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        pytest.skip(f"wheel build unavailable in this env:\n{proc.stdout}")
    wheels = sorted(dist.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"

    vdir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(vdir)
    if os.name == "nt":
        py = vdir / "Scripts" / "python.exe"
        apl_exe = vdir / "Scripts" / "apl.exe"
    else:
        py = vdir / "bin" / "python"
        apl_exe = vdir / "bin" / "apl"
    work = tmp_path / "neutral-work"   # NEVER the source tree
    work.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["APL_KEY_DIR"] = str(tmp_path / "empty-keys")

    install = subprocess.run(
        [str(py), "-m", "pip", "install", "-q", str(wheels[0])],
        cwd=work, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if install.returncode != 0:
        # No network to resolve apl-verifier, etc. — infra, not a real failure.
        pytest.skip(f"wheel install unavailable (offline?):\n{install.stdout}")

    # Reuse the exact CI measurement-floor check.
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import smoke_installed_wheel as smoke
    finally:
        sys.path.pop(0)
    smoke.measurement_floor(py, apl_exe, work, env)


def test_documented_named_seat_commands_parse(monkeypatch):
    calls = []

    def fake_run(scenario, **kwargs):
        calls.append((scenario, kwargs))
        return 0

    monkeypatch.setattr(apl.cmd_run_live, "run", fake_run)
    assert apl.main([
        "run-live", "examples/00_private_matter",
        "--seat", "mock_provider_a=anthropic",
        "--seat", "mock_provider_b=openai", "--yes",
    ]) == 0
    assert calls[-1][1]["seat_specs"] == [
        "mock_provider_a=anthropic", "mock_provider_b=openai"]
    assert apl.main([
        "run-live", "examples/02_market_entry_three_way",
        "--seat", "pricing=anthropic", "--seat", "channel=openai",
        "--seat", "risk=openai", "--yes",
    ]) == 0
    assert calls[-1][1]["seat_specs"] == [
        "pricing=anthropic", "channel=openai", "risk=openai"]
    assert apl.main([
        "run-live", "examples/02_market_entry_three_way",
        "--seat", "pricing=openai", "--seat", "channel=openai",
        "--seat", "risk=openai", "--yes",
    ]) == 0
    assert calls[-1][1]["seat_specs"] == [
        "pricing=openai", "channel=openai", "risk=openai"]
    assert apl.main([
        "run-live", "examples/00_private_matter",
        "--seat", "mock_provider_a=openai",
        "--seat", "mock_provider_b=openai", "--yes",
    ]) == 0
    assert calls[-1][1]["seat_specs"] == [
        "mock_provider_a=openai", "mock_provider_b=openai"]
    assert apl.main([
        "run-live", "examples/01_private_code_context",
        "--seat", "mock_provider_a=anthropic",
        "--seat", "mock_provider_b=openai",
        "--output", "apl-live-out-2",
        "--chain", "apl-live-out-1/receipt.live.json", "--yes",
    ]) == 0
    assert calls[-1][1]["chain"] == "apl-live-out-1/receipt.live.json"


def test_byok_docs_use_current_cli_syntax():
    text = Path("docs/byok_reference.md").read_text(encoding="utf-8")
    assert "--a " not in text and "--b " not in text
    assert "--seat mock_provider_a=anthropic" in text
    assert "--seat mock_provider_b=openai" in text
    assert "--seat pricing=anthropic" in text
    assert "APL_OPENAI_MODEL_MOCK_PROVIDER_B" in text

def test_release_workflow_reuses_smoked_distributions():
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    assert 'tags: ["v*"]' in workflow
    assert "id-token: write" in workflow
    assert "environment: pypi" in workflow
    # Dual-package pipeline: apl-verifier publishes before apl-sidecar.
    assert "verifier-build:" in workflow
    assert "verifier-publish:" in workflow
    assert "sidecar-build:" in workflow
    assert "sidecar-installed-wheel-smoke:" in workflow
    assert "sidecar-publish:" in workflow
    # Hard ordering gate: the sidecar only builds after the verifier is live,
    # because the sidecar installed-wheel smoke pip-resolves apl-verifier.
    assert "needs: verifier-publish" in workflow
    # Sidecar publish reuses the exact smoked distributions (no rebuild between
    # smoke and publish): smoke needs the build, publish needs the smoke.
    assert "needs: sidecar-build" in workflow
    assert "needs: sidecar-installed-wheel-smoke" in workflow
    assert "actions/upload-artifact@v4" in workflow
    # One download-artifact per: verifier-publish, sidecar smoke, sidecar-publish.
    assert workflow.count("actions/download-artifact@v4") == 3
    assert "python scripts/smoke_installed_wheel.py dist" in workflow
    assert "packages-dir: dist/" in workflow
    assert "packages-dir: dist-verifier/" in workflow
