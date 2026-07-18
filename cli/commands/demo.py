# SPDX-License-Identifier: FSL-1.1-ALv2
"""One-command deterministic offline demo using canonical APL components."""
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path
from adapters.base import ProviderRequest
from adapters.mock import default_registry
from . import _common as c
from . import _resources
from . import _signing, run_mock, verify

DEFAULT_SCENARIO = _resources.bundled_scenario_path("00_private_idea")
REFERENCE_SCENARIO_ID = "00_private_idea"

NEUTRAL_ASSESSMENT = """# Exploratory Reconstruction Assessment

Assessment is available only for the bundled reference scenario. The receipt and verification results remain valid for this run.
"""


def _is_reference_scenario(paths: dict) -> bool:
    return paths["dir"].name == REFERENCE_SCENARIO_ID


def build_assessment(paths: dict, view: dict) -> str:
    if not _is_reference_scenario(paths):
        return NEUTRAL_ASSESSMENT
    local = c.load_local_only(paths)
    a = c.read_text(paths["payloads"]["mock_provider_a"])
    b = c.read_text(paths["payloads"]["mock_provider_b"])
    missing = "\n".join(f"- {name} (local-only field)" for name in sorted(local))
    return f"""# Exploratory Reconstruction Assessment

This is a fixed scenario assessment for demonstration only. It is not a secrecy proof or a calibrated attack benchmark.

## Recovered entities
- developers and GitHub users
- an early-stage privacy-sensitive developer tool

## Recovered relationships
- the tool targets developers who discover software through GitHub
- the product needs trust signals and a low-friction launch path

## Recovered objectives
- develop positioning and adoption guidance
- propose a developer-oriented README structure

## Missing context
{missing}

## Reconstruction signal
`MEDIUM` — what an observer of the disclosed fragments could plausibly infer: task category, audience, and objective. Fixed scenario value, not a calibrated probability.

## Residual disclosure risk
`MEDIUM` — what remains exposed after masking: named sensitive details stay local, but category-level intent is still visible to each provider.

## Measured disclosure volume
- Original task: approximately {c.estimated_tokens(c.read_text(paths['original']))} tokens ({view['original_chars']} normalized characters)
- Provider A: approximately {c.estimated_tokens(a)} tokens ({view['providers']['mock_provider_a']['chars']} normalized characters)
- Provider B: approximately {c.estimated_tokens(b)} tokens ({view['providers']['mock_provider_b']['chars']} normalized characters)
- Declared local-only values: approximately {sum(c.estimated_tokens(str(v)) for v in local.values())} tokens

Token figures use `ceil(normalized characters / 4)`. Canonical receipt exposure remains character based. Disclosure volume is not a privacy or reconstruction-risk percentage.

## Assessment method
The recovered entities, relationships, and objectives are fixed constants for the bundled demo scenario, not summaries derived from the disclosed text. No external provider, embedding model, or hidden classifier is used.
"""


def render_html(paths: dict, responses: dict[str, str], final_output: str,
                receipt: dict, assessment: str) -> str:
    def esc(value: str) -> str:
        return html.escape(value, quote=True)
    original = c.read_text(paths["original"])
    residual_risk = "MEDIUM" if _is_reference_scenario(paths) else "N/A"
    view = c.exposure_view(paths)
    local = json.dumps(c.load_local_only(paths), indent=2, ensure_ascii=False)
    cards = []
    for provider, label in (("mock_provider_a", "Provider A"), ("mock_provider_b", "Provider B")):
        payload = c.read_text(paths["payloads"][provider])
        metadata = json.dumps({"provider_id": provider, "mode": "offline-mock", "network": False}, indent=2)
        cards.append(f'''<section class="pane" id="{provider}"><h2>{label} View <b>SENT</b></h2><p>Only this provider's input, metadata, and output are shown in this perspective.</p><h3>Input · REDACTED</h3><pre>{esc(payload)}</pre><h3>Metadata · DERIVED</h3><pre>{esc(metadata)}</pre><h3>Output · RECEIVED</h3><pre>{esc(responses[provider])}</pre></section>''')
    provider_json = json.dumps({p: {"input": c.read_text(paths["payloads"][p]), "output": responses[p]} for p in c.PROVIDERS}, indent=2)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>APL Exposure Viewer</title><style>
body{{margin:auto;max-width:1100px;padding:32px;background:#f4f0e6;color:#14212b;font:16px/1.5 ui-monospace,monospace}}h1{{font-size:clamp(34px,7vw,68px);line-height:1}}section,.metric{{background:white;border:2px solid;padding:18px;margin:18px 0;box-shadow:5px 5px #14212b}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}nav{{display:flex;gap:8px;flex-wrap:wrap}}button{{padding:10px;border:2px solid;background:white;font:inherit}}button.on{{background:#14212b;color:white}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf0ed;padding:14px;border-left:6px solid #8dd3ff}}.pane{{display:none}}.pane.on{{display:block}}b{{background:#c9f27b;padding:2px 5px}}
</style></head><body><p>PRIVATE MODE FOR AI — EXPERIMENTAL</p><h1>Your prompt has a blast radius.</h1><p>See what leaves your machine, what stays local, and what this run can verify offline.</p>
<section><h2>Summary</h2><div class="metrics"><div class="metric">Original<br><b>~{c.estimated_tokens(original)} tokens</b><br>{view['original_chars']} chars</div><div class="metric">Provider A<br><b>~{c.estimated_tokens(c.read_text(paths['payloads']['mock_provider_a']))} tokens</b></div><div class="metric">Provider B<br><b>~{c.estimated_tokens(c.read_text(paths['payloads']['mock_provider_b']))} tokens</b></div><div class="metric">External providers<br><b>2 offline mocks</b></div><div class="metric">Receipt<br><b>VERIFIED</b></div><div class="metric">Residual disclosure risk<br><b>{residual_risk}</b></div></div></section>
<section><h2>Disclosure path</h2><pre>Original Task
├── LOCAL → local-only context
├── SENT → Provider A disclosure → response
├── SENT → Provider B disclosure → response
└── LOCAL → final stitch → final output</pre></section>
<nav><button class="on" data-id="full">Full Local View</button><button data-id="mock_provider_a">Provider A View</button><button data-id="mock_provider_b">Provider B View</button></nav>
<section class="pane on" id="full"><h2>Full Local View · LOCAL</h2><h3>Original task · ORIGINAL</h3><pre>{esc(original)}</pre><h3>Disclosure plan · DERIVED</h3><pre>{esc(c.read_text(paths['masking_plan']))}</pre><h3>Local-only context · LOCAL</h3><pre>{esc(local)}</pre><h3>Provider fragments and outputs · SENT</h3><pre>{esc(provider_json)}</pre><h3>Final stitch · LOCAL</h3><pre>{esc(final_output)}</pre><h3>Receipt · VERIFIED</h3><pre>{esc(json.dumps(receipt, indent=2, sort_keys=True))}</pre></section>{''.join(cards)}
<section><h2>Assessment · INFERRED</h2><pre>{esc(assessment)}</pre></section><script>document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.pane').forEach(x=>x.classList.remove('on'));document.querySelectorAll('button').forEach(x=>x.classList.remove('on'));document.getElementById(b.dataset.id).classList.add('on');b.classList.add('on')}})</script></body></html>'''


def run(output_dir: str = "apl-out", scenario_dir: str | None = None) -> int:
    paths = c.example_paths(scenario_dir or DEFAULT_SCENARIO)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    registry = default_registry()
    print("APL Sidecar Demo\n\nLoading local task...\nCreating controlled disclosures...")
    responses = {}
    for provider, label in (("mock_provider_a", "Mock Provider A"), ("mock_provider_b", "Mock Provider B")):
        adapter = registry.get(provider)
        if adapter.capabilities.network:
            print(f"Refusing network adapter: {provider}")
            return 1
        print(f"Sending fragment to {label}...")
        responses[provider] = adapter.complete(ProviderRequest(c.read_text(paths["payloads"][provider]), adapter.model, paths["dir"], {"mode": "offline-mock"})).text
    print("Reassembling locally...")
    final_output = c.read_text(paths["rehydrated"])
    view = c.exposure_view(paths)
    assessment = build_assessment(paths, view)
    assessment_path = output / "assessment.md"
    assessment_path.write_text(assessment, encoding="utf-8")
    print("Generating receipt...")
    body = run_mock.build_receipt_body(paths, responses)
    local_only = c.load_local_only(paths)
    body.update({
        "mode": "offline-mock",
        "original_task_sha256": c.text_sha256(c.read_text(paths["original"])),
        "original_task_token_estimate": c.estimated_tokens(c.read_text(paths["original"])),
        "local_only_token_estimate": sum(
            c.estimated_tokens(str(value)) for value in local_only.values()),
        "verification": {"algorithm": "Ed25519", "status": "verified"},
    })
    for event in body["provider_events"]:
        event["disclosed_token_estimate"] = c.estimated_tokens(
            c.read_text(paths["payloads"][event["provider_id"]]))
    body["run_artifacts"] = {"final_output_sha256": c.text_sha256(final_output), "assessment_sha256": hashlib.sha256(assessment.encode()).hexdigest()}
    key, key_id = _signing.ensure_local_keypair()
    receipt = _signing.sign_receipt(body, key, key_id)
    receipt_path = output / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Verifying receipt...")
    if verify.run([str(receipt_path)]) != 0:
        return 1
    exposure_path = output / "exposure.html"
    exposure_path.write_text(render_html(paths, responses, final_output, receipt, assessment), encoding="utf-8")
    print("\n[OK] Provider A view generated\n[OK] Provider B view generated\n[OK] Local stitch completed\n[OK] Receipt verified")
    print(f"\nOpen:\n{exposure_path}\n\nArtifacts:\n{receipt_path}\n{assessment_path}")
    return 0
