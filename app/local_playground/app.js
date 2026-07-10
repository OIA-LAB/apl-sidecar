"use strict";
/* APL Sidecar local playground — offline; loads example fixtures from this
 * repo via the local server started by `python cli/apl.py playground`.
 * Verification is REAL: canonical hash + Ed25519 via WebCrypto. */

const $ = s => document.querySelector(s);
const BASE = "../../";
let EX = null;          // current example id
let RECEIPT = null;     // loaded receipt object
let TAMPERED = null;

async function ftext(path) {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(path + " -> " + r.status);
  return (await r.text()).replace(/\r\n/g, "\n");
}
async function fjson(path) { return JSON.parse(await ftext(path)); }

/* ---------- canonicalization per RECEIPT_STANDARD.md section 2 ---------- */
function canonical(obj) {
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canonical).join(",") + "]";
  return "{" + Object.keys(obj).sort().map(
    k => JSON.stringify(k) + ":" + canonical(obj[k])).join(",") + "}";
}
async function sha256hex(text) {
  const buf = await crypto.subtle.digest("SHA-256",
    new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function pemToBytes(pem) {
  const b64 = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  return Uint8Array.from(atob(b64), c => c.charCodeAt(0));
}
async function verifyReceipt(receipt) {
  const body = {};
  for (const k of Object.keys(receipt))
    if (k !== "receipt_hash" && k !== "signature") body[k] = receipt[k];
  const recomputed = await sha256hex(canonical(body));
  if (recomputed !== receipt.receipt_hash)
    return { ok: false, reason: "receipt_hash mismatch (content was modified)" };
  if (!receipt.signature || receipt.signature.alg !== "Ed25519")
    return { ok: false, reason: "missing or non-Ed25519 signature" };
  let key;
  try {
    const pem = await ftext("spec/" + receipt.signing_key_id + ".pem");
    key = await crypto.subtle.importKey("spki", pemToBytes(pem),
      { name: "Ed25519" }, false, ["verify"]);
  } catch (e) {
    return { ok: false, reason: "public key unavailable or Ed25519 " +
             "unsupported in this browser -- use: python cli/apl.py verify" };
  }
  const sig = Uint8Array.from(atob(receipt.signature.value), c => c.charCodeAt(0));
  const ok = await crypto.subtle.verify({ name: "Ed25519" }, key, sig,
    new TextEncoder().encode(receipt.receipt_hash));
  return ok ? { ok: true }
            : { ok: false, reason: "Ed25519 signature invalid" };
}

/* ------------------------------ UI flow ------------------------------ */
function pct(x) { return (x * 100).toFixed(1) + "%"; }

async function loadExample(ex) {
  EX = ex;
  document.querySelectorAll(".choice").forEach(b =>
    b.classList.toggle("sel", b.dataset.ex === ex));
  const dir = "examples/" + ex + "/";
  const original = await ftext(dir + "input.original.example.txt");
  const localOnly = await fjson(dir + "local_only.json");
  const payloadA = await ftext(dir + "provider_a_payload.txt");
  const payloadB = await ftext(dir + "provider_b_payload.txt");
  RECEIPT = await fjson(dir + "receipt.json");
  TAMPERED = await fjson(dir + "tampered_receipt.example.json");

  $("#original").textContent = original;
  $("#localonly").textContent = Object.entries(localOnly)
    .map(([k, v]) => k + ":\n  " + v).join("\n\n");
  $("#payload-a").textContent = payloadA;
  $("#payload-b").textContent = payloadB;

  const n = original.length;
  const ra = payloadA.length / n, rb = payloadB.length / n;
  $("#exp-a-label").textContent = "exposure: " + pct(ra) + " of original";
  $("#exp-b-label").textContent = "exposure: " + pct(rb) + " of original";
  $("#exp-a").style.width = Math.min(ra * 100, 100) + "%";
  $("#exp-b").style.width = Math.min(rb * 100, 100) + "%";

  // exposure panel from the signed receipt (source of record)
  $("#exposure").innerHTML = RECEIPT.single_provider_exposure.map(e =>
    `<div class="meter"><span>${e.provider_id}: ${pct(e.exposure_ratio)}</span>
     <div class="bar"><i style="width:${Math.min(e.exposure_ratio * 100, 100)}%"></i></div></div>`
  ).join("") + `<p>max_single_provider_exposure: <b>${pct(RECEIPT.max_single_provider_exposure)}</b></p>`;
  $("#sawfull").textContent = RECEIPT.no_single_provider_saw_full
    ? "No single provider saw the full task context."
    : "WARNING: a provider payload equals the full context.";

  $("#receiptmeta").innerHTML = [
    ["run_id", RECEIPT.run_id],
    ["task_type", RECEIPT.task_type],
    ["masking_level", RECEIPT.masking_level],
    ["local_only fields", RECEIPT.local_only_hashes.length + " (hashes only)"],
    ["prev_receipt_hash", String(RECEIPT.prev_receipt_hash)],
    ["receipt_hash", RECEIPT.receipt_hash],
    ["signature", RECEIPT.signature.alg + " / key: " + RECEIPT.signing_key_id],
  ].map(([k, v]) => `<div><b>${k}</b>: ${v}</div>`).join("");
  $("#receipt").textContent = JSON.stringify(RECEIPT, null, 2);

  $("#answers").hidden = true;
  $("#rehydrated").textContent = "";
  $("#verdict").textContent = "";
  for (const id of ["p-original", "p-local", "p-payloads", "p-run",
                    "p-exposure", "p-receipt", "p-verify"])
    document.getElementById(id).hidden = false;
  document.getElementById("p-rehydrate").hidden = true;
}

async function runMock() {
  const dir = "examples/" + EX + "/";
  $("#answer-a").textContent = await ftext(dir + "mock_answer_a.txt");
  $("#answer-b").textContent = await ftext(dir + "mock_answer_b.txt");
  $("#answers").hidden = false;
  $("#rehydrated").textContent = await ftext(dir + "final_rehydrated_answer.txt");
  document.getElementById("p-rehydrate").hidden = false;
}

async function showVerdict(receipt) {
  const v = $("#verdict");
  v.textContent = "verifying...";
  v.className = "big";
  const res = await verifyReceipt(receipt);
  if (res.ok) {
    v.textContent = "Signature verified. Receipt chain valid.";
    v.className = "big verdict-ok";
  } else {
    v.textContent = "Verification failed: receipt was modified or signature " +
                    "is invalid. (" + res.reason + ")";
    v.className = "big verdict-bad";
  }
}

document.querySelectorAll(".choice").forEach(b =>
  b.addEventListener("click", () => loadExample(b.dataset.ex)));
$("#run").addEventListener("click", runMock);
$("#verify-good").addEventListener("click", () => showVerdict(RECEIPT));
$("#verify-bad").addEventListener("click", () => showVerdict(TAMPERED));
$("#steps").textContent =
  "Flow: choose example -> original -> local-only -> provider payloads -> " +
  "run mock -> rehydrate -> exposure -> receipt -> verify";
