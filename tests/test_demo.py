"""Developer-first demo, offline enforcement, isolation, and tamper tests."""
import html
import json
import re
import socket
from pathlib import Path
from cli.apl import main
from cli.commands import demo
from verifier.apl_verify import VerifyError, verify_receipt


def test_help_and_demo_artifacts(tmp_path: Path):
    assert main(["--help"]) == 0
    out = tmp_path / "apl-out"
    assert main(["demo", "--output", str(out)]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["assessment.md", "exposure.html", "receipt.json"]
    verify_receipt(json.loads((out / "receipt.json").read_text(encoding="utf-8")))
    assessment = (out / "assessment.md").read_text(encoding="utf-8")
    assert "Residual disclosure risk" in assessment and "Assessment method" in assessment
    assert main(["inspect", str(out)]) == 0


def test_demo_never_opens_external_socket(tmp_path: Path, monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("offline demo attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", reject)
    assert demo.run(str(tmp_path / "out")) == 0


def test_provider_panes_are_perspective_isolated(tmp_path: Path):
    out = tmp_path / "out"
    assert demo.run(str(out)) == 0
    page = (out / "exposure.html").read_text(encoding="utf-8")
    a = re.search(r'<section class="pane" id="mock_provider_a">(.*?)</section>', page, re.S).group(1)
    b = re.search(r'<section class="pane" id="mock_provider_b">(.*?)</section>', page, re.S).group(1)
    scenario = Path("examples/00_private_idea")
    payload_a = (scenario / "provider_a_payload.txt").read_text(encoding="utf-8").strip()
    payload_b = (scenario / "provider_b_payload.txt").read_text(encoding="utf-8").strip()
    local = json.loads((scenario / "local_only.json").read_text(encoding="utf-8"))
    assert html.escape(payload_a, quote=True) in a
    assert html.escape(payload_b, quote=True) not in a
    assert html.escape(payload_b, quote=True) in b
    assert html.escape(payload_a, quote=True) not in b
    for value in local.values():
        assert str(value) not in a and str(value) not in b


def test_break_receipt_preserves_original_and_fails_verification(tmp_path: Path):
    out = tmp_path / "out"
    assert demo.run(str(out)) == 0
    receipt = out / "receipt.json"
    original = receipt.read_bytes()
    assert main(["break-receipt", str(receipt)]) == 0
    assert receipt.read_bytes() == original
    tampered = json.loads((out / "receipt.tampered.json").read_text(encoding="utf-8"))
    try:
        verify_receipt(tampered)
    except VerifyError as exc:
        assert "receipt_hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered receipt verified")

def test_preview_and_run_accept_scenario_task_file(tmp_path: Path):
    task = "examples/00_private_idea/input.original.example.txt"
    assert main(["preview", task]) == 0
    assert main(["run", task, "--output", str(tmp_path / "run")]) == 0


def test_non_reference_scenario_shows_neutral_assessment(tmp_path: Path):
    out = tmp_path / "out"
    assert demo.run(str(out), "examples/01_private_code_context") == 0
    assessment = (out / "assessment.md").read_text(encoding="utf-8")
    assert "available only for the bundled reference scenario" in assessment
    assert "Recovered entities" not in assessment
    assert "developers and GitHub users" not in assessment
    page = (out / "exposure.html").read_text(encoding="utf-8")
    assert "developers and GitHub users" not in page
    assert "available only for the bundled reference scenario" in page
