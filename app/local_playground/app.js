"use strict";
/* APL Sidecar local playground — offline; loads example fixtures from this
 * repo via the local server started by `python cli/apl.py playground`.
 * Three-act narrative: problem -> mechanism -> proof.
 * Verification is REAL: canonical hash + Ed25519 via WebCrypto. */

const $ = s => document.querySelector(s);
const BASE = "../../";
let EX = null, RECEIPT = null, TAMPERED = null;

const STORY = {
  "00_private_idea": {
    bad: "The provider now holds your product name, mechanism, pricing, " +
         "go-to-market channel, and your do-not-disclose note. In one paste.",
    sumOriginal: "A founder's full working notes for an unannounced startup idea.",
    sumA: "A generic positioning question — no name, no differentiator, no pricing.",
    sumB: "A README-structure task — no idea, no business model.",
  },
  "01_private_code_context": {
    bad: "The provider now holds your repo tree, a committed API key, a " +
         "customer name, and your competitive roadmap. In one paste.",
    sumOriginal: "Full repo working context: tree, code, an embedded key, " +
                 "customer and roadmap notes.",
    sumA: "A minimal bug repro — a 10-line snippet and one error, nothing else.",
    sumB: "A generic API-documentation task — no codebase, no internals.",
  },
};

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
  return ok ? { ok: true } : { ok: false, reason: "Ed25519 signature invalid" };
}

/* ------------------- sensitive-token highlighting ------------------- */
const esc = t => String(t ?? "").replace(/[&<>"]/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function sensitiveTokens(localOnly) {
  const stop = new Set(["with", "from", "that", "this", "their", "before",
    "which", "believed", "signed", "local", "receipt", "value", "notes",
    "customer", "internal", "product", "market", "strategy", "developers",
    "startups", "founders", "tools", "sync", "engine", "pilot", "sites"]);
  const toks = new Set();
  for (const v of Object.values(localOnly)) {
    for (const t of String(v).split(/[^A-Za-z0-9._$/-]+/)) {
      if (t.length >= 5 && !stop.has(t.toLowerCase()) && /[A-Za-z]/.test(t))
        toks.add(t);
    }
  }
  return [...toks].sort((a, b) => b.length - a.length);
}
function highlight(text, tokens) {
  let html = esc(text);
  for (const t of tokens) {
    const re = new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
    html = html.replace(re, m => "@@APL_MARK@@" + m + "@@APL_END@@");
  }
  return html.replaceAll("@@APL_MARK@@", "<mark>").replaceAll("@@APL_END@@", "</mark>");
}

/* ------------------------------ UI flow ------------------------------ */
const pct = x => (x * 100).toFixed(1) + "%";

function meterHTML(label, ratio) {
  return `<div class="meter"><span>${esc(label)} sees <b>${pct(ratio)}</b></span>
    <div class="bar"><i style="width:${Math.min(ratio * 100, 100)}%"></i></div></div>`;
}

async function loadExample(ex) {
  EX = ex;
  document.querySelectorAll(".choice").forEach(b =>
    b.classList.toggle("sel", b.dataset.ex === ex));
  const story = STORY[ex];
  const dir = "examples/" + ex + "/";
  const original = await ftext(dir + "input.original.example.txt");
  const localOnly = await fjson(dir + "local_only.json");
  const payloadA = await ftext(dir + "provider_a_payload.txt");
  const payloadB = await ftext(dir + "provider_b_payload.txt");
  RECEIPT = await fjson(dir + "receipt.json");
  TAMPERED = await fjson(dir + "tampered_receipt.example.json");

  /* ---- Act 1: the comparison ---- */
  $("#bad-consequence").textContent = story.bad;
  const worst = RECEIPT.max_single_provider_exposure;
  $("#good-meters").innerHTML = RECEIPT.single_provider_exposure.map(e =>
    meterHTML(e.provider_id.replace("mock_", ""), e.exposure_ratio)).join("");
  $("#good-consequence").textContent =
    `Worst single provider: ${pct(worst)} of the characters — and none of the ` +
    `${RECEIPT.local_only_hashes.length} sensitive fields. ` +
    `No single provider saw the full task context.`;
  $("#compare").hidden = false;

  /* ---- Act 2: the mechanism ---- */
  const tokens = sensitiveTokens(localOnly);
  $("#sum-original").textContent = story.sumOriginal +
    ` (${original.length.toLocaleString()} characters)`;
  $("#original").innerHTML = highlight(original, tokens);
  $("#sum-local").textContent =
    `${Object.keys(localOnly).length} fields — only their SHA-256 fingerprints ` +
    `enter the receipt.`;
  $("#vault").innerHTML = Object.keys(localOnly).map(
    k => `<span>🔒 ${esc(k)}</span>`).join("");
  $("#localonly").textContent = Object.entries(localOnly)
    .map(([k, v]) => k + ":\n  " + v).join("\n\n");
  $("#sum-a").textContent = story.sumA;
  $("#sum-b").textContent = story.sumB;
  $("#payload-a").textContent = payloadA;
  $("#payload-b").textContent = payloadB;
  const n = original.length;
  const ra = payloadA.length / n, rb = payloadB.length / n;
  $("#exp-a-label").innerHTML = `<b>${pct(ra)}</b> of the original`;
  $("#exp-b-label").innerHTML = `<b>${pct(rb)}</b> of the original`;
  $("#exp-a").style.width = Math.min(ra * 100, 100) + "%";
  $("#exp-b").style.width = Math.min(rb * 100, 100) + "%";
  $("#answers").hidden = true;
  $("#c-rehydrate").hidden = true;

  /* ---- Act 3: the proof ---- */
  $("#receiptmeta").innerHTML = [
    ["task", RECEIPT.task_type],
    ["masking_level", RECEIPT.masking_level],
    ["local-only fields", RECEIPT.local_only_hashes.length + " (fingerprints only)"],
    ["receipt_hash", RECEIPT.receipt_hash],
    ["signature", RECEIPT.signature.alg + " / key: " + RECEIPT.signing_key_id],
  ].map(([k, v]) => `<div><b>${esc(k)}</b>: ${esc(String(v))}</div>`).join("");
  $("#receipt").textContent = JSON.stringify(RECEIPT, null, 2);
  const card = $("#verdict-card");
  card.hidden = true; card.className = "verdict-card";

  $("#act2").hidden = false;
  $("#act3").hidden = false;
}

async function runMock() {
  const dir = "examples/" + EX + "/";
  $("#answer-a").textContent = await ftext(dir + "mock_answer_a.txt");
  $("#answer-b").textContent = await ftext(dir + "mock_answer_b.txt");
  $("#answers").hidden = false;
  $("#rehydrated").textContent = await ftext(dir + "final_rehydrated_answer.txt");
  $("#c-rehydrate").hidden = false;
  $("#c-rehydrate").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function showVerdict(receipt, tampered) {
  const card = $("#verdict-card");
  card.hidden = false;
  card.className = "verdict-card";
  card.textContent = "verifying in your browser...";
  const res = await verifyReceipt(receipt);
  if (res.ok) {
    card.className = "verdict-card ok";
    card.innerHTML = "✓ Signature verified. Receipt chain valid." +
      "<small>Recomputed the canonical hash and checked the Ed25519 signature " +
      "with WebCrypto — locally, just now.</small>";
  } else {
    card.className = "verdict-card fail";
    card.innerHTML = "✗ Verification failed: receipt was modified or signature " +
      "is invalid.<small>" + esc(res.reason) +
      (tampered ? " — this copy differs from the real receipt by one number." : "") +
      "</small>";
  }
}

document.querySelectorAll(".choice").forEach(b =>
  b.addEventListener("click", () => loadExample(b.dataset.ex)));
$("#run").addEventListener("click", runMock);
$("#verify-good").addEventListener("click", () => showVerdict(RECEIPT, false));
$("#verify-bad").addEventListener("click", () => showVerdict(TAMPERED, true));

/* first paint: never show an empty stage */
loadExample("00_private_idea");
