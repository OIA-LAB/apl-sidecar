# SPDX-License-Identifier: FSL-1.1-ALv2
"""Wheel-safe bundled resource and documented CLI parser tests."""
import json
from pathlib import Path

from cli import apl
from cli.commands import _common, _resources, _verifier_boot


def test_bundled_resources_work_without_source_tree(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_resources, "SOURCE_ROOT", tmp_path / "missing-source")
    scenario = _resources.bundled_scenario_path("00_private_idea")
    assert (scenario / "input.original.example.txt").is_file()
    assert (scenario / "masking_plan.yaml").is_file()
    playground = _resources.playground_root()
    assert (playground / "app" / "local_playground" / "index.html").is_file()
    policy = _common.load_policy_manifest()
    assert policy["policy_id"] == "apl-oss-demo-policy"


def test_packaged_public_key_fallback(monkeypatch, tmp_path: Path):
    # With the user key dir absent, the runtime bridge must still resolve the
    # packaged spec/ demo PUBLIC key so a fresh checkout verifies committed
    # receipts. (The verifier package itself never searches; the bridge does.)
    monkeypatch.setattr(_resources, "user_key_dir",
                        lambda: tmp_path / "missing")
    receipt = json.loads(Path("examples/00_private_idea/receipt.json").read_text(
        encoding="utf-8"))
    _verifier_boot.verify_receipt(receipt)


def test_documented_named_seat_commands_parse(monkeypatch):
    calls = []

    def fake_run(scenario, **kwargs):
        calls.append((scenario, kwargs))
        return 0

    monkeypatch.setattr(apl.cmd_run_live, "run", fake_run)
    assert apl.main([
        "run-live", "examples/00_private_idea",
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
        "run-live", "examples/00_private_idea",
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
