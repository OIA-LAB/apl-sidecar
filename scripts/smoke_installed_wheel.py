# SPDX-License-Identifier: FSL-1.1-ALv2
"""Smoke-test an installed APL wheel from an unrelated empty directory."""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import time
import urllib.request
import venv
from pathlib import Path


def run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f"$ {' '.join(command)}\n{result.stdout}")
    if result.returncode != 0:
        raise SystemExit(f"command failed with exit {result.returncode}")
    return result


def run_expect_fail(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    """The inverse gate: tamper detection must FAIL verification (nonzero)."""
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f"$ {' '.join(command)}  [expected to fail]\n{result.stdout}")
    if result.returncode == 0:
        raise SystemExit("tampered receipt VERIFIED — tamper detection is broken")


def measurement_floor(python: Path, apl: Path, work: Path,
                      env: dict[str, str]) -> None:
    """Wheel-only, neutral-cwd verify of every shipped example receipt.

    Asserts (a) `resources.files('spec')` lives under site-packages (no cwd
    shadow — the trap that shipped the 0.2.1 bug), and (b) every committed
    example `receipt.json` verifies with NO `--pubkey` (the runtime resolves
    the bundled demo key). APL_KEY_DIR is already an empty temp dir here, so
    the ONLY key source is the wheel. Fails loudly if a bundled key is missing.
    """
    # Discover the installed examples/ and assert spec/ is not cwd-shadowed.
    probe = subprocess.run(
        [str(python), "-c",
         "from importlib import resources;"
         "import examples, spec;"
         "assert 'site-packages' in str(resources.files('spec')),"
         "  'CWD SHADOW: spec=%s' % resources.files('spec');"
         "print(resources.files('examples'));"
         "print(resources.files('spec'))"],
        cwd=work, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f"$ python -c '<probe resources>'\n{probe.stdout}")
    if probe.returncode != 0:
        raise SystemExit("resource probe failed (cwd shadow or missing spec)")
    lines = [ln for ln in probe.stdout.splitlines() if ln.strip()]
    examples_root = Path(lines[-2])
    scenarios = sorted(
        d for d in examples_root.iterdir() if (d / "receipt.json").is_file())
    if not scenarios:
        raise SystemExit("no shipped example receipts found in the wheel")
    print(f"measurement floor over: {[s.name for s in scenarios]}")
    for scenario in scenarios:
        # Auto-resolve form (no --pubkey): the wheel must supply the key.
        run([str(apl), "verify", str(scenario / "receipt.json")], work, env)
        tampered = scenario / "tampered_receipt.example.json"
        if tampered.is_file():
            # Must fail for the RIGHT reason (hash/signature), i.e. the key
            # resolved and the content mismatch was detected — not a missing
            # key. run_expect_fail asserts nonzero; the key having resolved is
            # already proven by the untampered verify above passing.
            run_expect_fail([str(apl), "verify", str(tampered)], work, env)
    print("measurement floor passed: every shipped receipt verifies wheel-only.")


def find_wheel(path: Path) -> Path:
    if path.is_file() and path.suffix == ".whl":
        return path.resolve()
    wheels = sorted(path.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected exactly one wheel under {path}, found {len(wheels)}")
    return wheels[0].resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path, help="wheel file or directory containing one wheel")
    args = parser.parse_args()
    wheel = find_wheel(args.wheel)
    with tempfile.TemporaryDirectory(prefix="apl-wheel-smoke-") as temp_name:
        temp = Path(temp_name)
        environment = temp / "venv"
        work = temp / "empty-work"
        work.mkdir()
        venv.EnvBuilder(with_pip=True).create(environment)
        if os.name == "nt":
            python = environment / "Scripts" / "python.exe"
            apl = environment / "Scripts" / "apl.exe"
        else:
            python = environment / "bin" / "python"
            apl = environment / "bin" / "apl"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["APL_KEY_DIR"] = str(temp / "keys")
        run([str(python), "-m", "pip", "install", str(wheel)], work, env)
        run([str(apl), "--help"], work, env)
        run([str(apl), "demo"], work, env)
        output = work / "apl-out"
        expected = {"assessment.md", "exposure.html", "receipt.json"}
        actual = {item.name for item in output.iterdir()}
        if actual != expected:
            raise SystemExit(f"unexpected primary artifacts: {sorted(actual)}")
        run([str(apl), "inspect", "apl-out"], work, env)
        run([str(apl), "verify", "apl-out/receipt.json"], work, env)
        run([str(apl), "break-receipt", "apl-out/receipt.json"], work, env)
        # The wheel's core promise, exercised end-to-end: the packaged
        # verifier + packaged pubkey must REJECT the tampered copy.
        run_expect_fail([str(apl), "verify", "apl-out/receipt.tampered.json"],
                        work, env)

        # ---- measurement floor (RC-2): wheel-only verify of EVERY shipped
        # example receipt, from an empty cwd + empty APL_KEY_DIR, no --pubkey.
        # This is the check the 0.2.1 CI never ran: it exercises the COMMITTED
        # example fixtures (00 is signed by apl-oss-demo-key-02), so a missing
        # bundled pubkey (RC-1) is caught here, not masked by cwd shadow.
        measurement_floor(python, apl, work, env)

        server = subprocess.Popen(
            [str(apl), "playground", "--port", "18891"], cwd=work, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            body = None
            for _ in range(50):
                try:
                    with urllib.request.urlopen(
                            "http://127.0.0.1:18891/app/local_playground/",
                            timeout=0.5) as response:
                        body = response.read().decode("utf-8")
                    break
                except Exception:
                    if server.poll() is not None:
                        raise SystemExit("installed playground exited before serving")
                    time.sleep(0.1)
            if body is None or "APL Sidecar" not in body:
                raise SystemExit("installed playground did not serve its bundled index")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
        print("Installed-wheel onboarding and playground smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())