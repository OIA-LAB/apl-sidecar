"use strict";
/* APL Sidecar local playground — offline; loads example fixtures from this
 * repo via the local server started by `apl playground`.
 * Three-act narrative: problem -> mechanism -> proof.
 * Bilingual: default English, `?lang=zh` for Traditional Chinese (UI chrome
 * only — the example fixtures themselves are English evidence artifacts).
 * Verification is REAL: canonical hash + Ed25519 via WebCrypto. */

const $ = s => document.querySelector(s);
const BASE = "../../";
const LANG = new URLSearchParams(location.search).get("lang") === "zh" ? "zh" : "en";
let EX = null, RECEIPT = null, TAMPERED = null;

/* ------------------------------- i18n ------------------------------- */
const I18N = {
  en: {
    // dynamic strings only — English static text lives in the HTML
    verifying: "verifying in your browser...",
    verdictOk: "✓ Signature verified. Receipt chain valid.",
    verdictOkSub: "Recomputed the canonical hash and checked the Ed25519 " +
                  "signature with WebCrypto — locally, just now.",
    verdictFail: "✗ Verification failed: receipt was modified or signature is invalid.",
    tamperNote: " — this copy differs from the real receipt by one number.",
    ofOriginal: p => `<b>${p}</b> of the original`,
    sees: (name, p) => `${name} sees <b>${p}</b>`,
    goodConsequence: (worst, n) =>
      `Worst single provider: ${worst} of the characters — and none of the ` +
      `${n} sensitive fields. No single provider saw the full task context.`,
    sumLocal: n => `${n} fields — only their SHA-256 fingerprints enter the receipt.`,
    chars: n => ` (${n.toLocaleString()} characters)`,
    fieldsOnly: n => `${n} (fingerprints only)`,
  },
  zh: {
    kicker: "APL Sidecar · 本機遊樂場 · 離線 · 免金鑰 · 零網路",
    hook: "AI 的無痕模式。",
    lead: "開無痕視窗，藏不住你的 prompt 洩漏了什麼：整包貼進一個 AI 對話框，" +
          "<b>那家供應商就看到了 100%</b>。APL 以最小暴露開場——" +
          "<b>沒有任何一家看得到全貌</b>——並簽發一張可驗證的收據。",
    tryWith: "選個場景試：",
    ex00: "機密併購案",
    ex01: "私有 repo 與 bug",
    skip: "直接跳到證明 ↓",
    withoutTitle: "不用 APL",
    withoutSub: "平常的做法：整包貼進同一個對話框",
    withoutMeter: "單一供應商看到你任務的 <b>100%</b>",
    withTitle: "用 APL",
    withSub: "同一個任務，切分後——機密欄位不出機器",
    act2Title: "切分是怎麼發生的",
    act2Sub: "五步，全在你的機器上。想看原文就展開卡片，不想看讀一行摘要就夠。",
    c1Title: "完整任務",
    tagSensitive: "敏感",
    c1Details: "顯示原始輸入（機密部分已標紅）",
    c2Title: "機密欄位進本機保險箱",
    tagNever: "永不出境",
    c2Details: "顯示 local-only 欄位原值",
    c3Title: "每家供應商只拿到一片抽象切片",
    c3Line: "兩個有用、答得出來的問題——但機密已經抽掉。",
    aSees: "供應商 A 看到",
    bSees: "供應商 B 看到",
    aDetails: "顯示 payload A",
    bDetails: "顯示 payload B",
    c4Title: "供應商作答",
    tagMock: "mock · 離線",
    c4Line: "以 fixture 回應代替真模型——零網路、零金鑰。",
    runBtn: "執行 mock providers",
    ansA: "Mock 回答 A",
    ansB: "Mock 回答 B",
    c5Title: "你的機器把真正的答案拼回來",
    tagRehydrate: "本機重組",
    c5Line: "泛用建議＋你的保險箱＝一份沒有任何供應商看過的完整方案。",
    c5Details: "顯示重組後的完整答案",
    act3Title: "憑什麼相信這些？",
    act3Sub: "因為每次執行都簽發收據：誰看了什麼、看了多少、留在本機的欄位指紋——" +
             "Ed25519 簽章。下面的驗證<b>就在你的瀏覽器裡現場計算</b>（WebCrypto）。" +
             "這是數學，不是動畫。",
    btnGood: "驗證收據",
    btnBad: "驗證「被竄改」的副本",
    hint: "被竄改的副本只差<b>一個數字</b>。這就夠了。",
    receiptDetails: "完整收據 JSON",
    footer: "所有範例內容皆為虛構（範例本文為英文證物，不翻譯）。P0 採用人工引導遮罩與" +
            "策展 payload——自動語意切分是 roadmap 項目，不是 P0 宣稱。APL 呈現的是" +
            "<b>什麼離開了本機</b>；不宣稱零洩漏、不宣稱供應商不留存、不宣稱匿名。",
    verifying: "正在你的瀏覽器裡驗證…",
    verdictOk: "✓ 簽章驗證通過。收據鏈有效。",
    verdictOkSub: "剛剛在本機用 WebCrypto 重算 canonical hash 並驗 Ed25519 簽章。",
    verdictFail: "✗ 驗證失敗：收據已被修改或簽章無效。",
    tamperNote: "——這份副本與真收據只差一個數字。",
    ofOriginal: p => `原文的 <b>${p}</b>`,
    sees: (name, p) => `${name} 看到 <b>${p}</b>`,
    goodConsequence: (worst, n) =>
      `最壞的單一供應商也只拿到 ${worst} 的字元——而且 ${n} 個機密欄位一個都沒拿到。` +
      `沒有任何一家看到完整任務。`,
    sumLocal: n => `${n} 個欄位——收據裡只有它們的 SHA-256 指紋。`,
    chars: n => `（${n.toLocaleString()} 字元）`,
    fieldsOnly: n => `${n}（僅指紋）`,
  },
};
const T = I18N[LANG];

const STORY = {
  en: {
    "00_private_matter": {
      bad: "The provider now holds the parties' real identities, the deal " +
           "codename, the price terms, the board's posture, and the deal " +
           "red flags. In one paste.",
      sumOriginal: "Deal counsel's full working matter file for a confidential M&A matter.",
      sumA: "A codename-level request-list task — no real names, no terms, no posture.",
      sumB: "A codename-level cover-note task — no parties, no price, no red flags.",
    },
    "01_private_code_context": {
      bad: "The provider now holds your repo tree, a committed API key, a " +
           "customer name, and your competitive roadmap. In one paste.",
      sumOriginal: "Full repo working context: tree, code, an embedded key, " +
                   "customer and roadmap notes.",
      sumA: "A minimal bug repro — a 10-line snippet and one error, nothing else.",
      sumB: "A generic API-documentation task — no codebase, no internals.",
    },
  },
  zh: {
    "00_private_matter": {
      bad: "那家供應商現在握有雙方真實身分、交易代號、價格條件、董事會的談判" +
           "姿態、還有交易的紅旗風險。一次貼上，全部奉上。",
      sumOriginal: "承辦律師一份機密併購案的完整工作卷宗。",
      sumA: "一個代號層級的清單整理任務——沒有真實名稱、沒有條件、沒有姿態。",
      sumB: "一個代號層級的函件草擬任務——沒有當事人、沒有價格、沒有紅旗。",
    },
    "01_private_code_context": {
      bad: "那家供應商現在握有你的 repo 樹、一把誤 commit 的 API key、客戶名稱、" +
           "還有你的競爭 roadmap。一次貼上，全部奉上。",
      sumOriginal: "完整 repo 工作情境：檔案樹、程式碼、內嵌金鑰、客戶與 roadmap 註記。",
      sumA: "最小 bug 重現——10 行片段加一條錯誤訊息，其他什麼都沒有。",
      sumB: "一個泛用的 API 文件任務——沒有 codebase、沒有內部細節。",
    },
  },
};

function applyLang() {
  document.documentElement.lang = LANG === "zh" ? "zh-Hant" : "en";
  // language switch (present in both languages)
  const here = location.pathname;
  $("#langswitch").innerHTML = LANG === "zh"
    ? ` · <a href="${here}">EN</a> / <b>中文</b>`
    : ` · <b>EN</b> / <a href="${here}?lang=zh">中文</a>`;
  if (LANG === "en") return;  // English static text is already in the HTML
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    if (I18N.zh[key]) el.textContent = I18N.zh[key];
  });
  document.querySelectorAll("[data-i18n-html]").forEach(el => {
    const key = el.dataset.i18nHtml;
    if (I18N.zh[key]) el.innerHTML = I18N.zh[key];
  });
}

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
             "unsupported in this browser -- use: apl verify" };
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
  const OPEN = "@@APL_MARK@@", CLOSE = "@@APL_END@@"; // survive esc()'d text
  let html = esc(text);
  for (const t of tokens) {
    const re = new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
    html = html.replace(re, m => OPEN + m + CLOSE);
  }
  return html.replaceAll(OPEN, "<mark>").replaceAll(CLOSE, "</mark>");
}

/* ------------------------------ UI flow ------------------------------ */
const pct = x => (x * 100).toFixed(1) + "%";

function meterHTML(label, ratio) {
  return `<div class="meter"><span>${T.sees(esc(label), pct(ratio))}</span>
    <div class="bar"><i style="width:${Math.min(ratio * 100, 100)}%"></i></div></div>`;
}

async function loadExample(ex) {
  EX = ex;
  document.querySelectorAll(".choice").forEach(b =>
    b.classList.toggle("sel", b.dataset.ex === ex));
  const story = STORY[LANG][ex];
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
    T.goodConsequence(pct(worst), RECEIPT.local_only_hashes.length);
  $("#compare").hidden = false;

  /* ---- Act 2: the mechanism ---- */
  const tokens = sensitiveTokens(localOnly);
  $("#sum-original").textContent = story.sumOriginal + T.chars(original.length);
  $("#original").innerHTML = highlight(original, tokens);
  $("#sum-local").textContent = T.sumLocal(Object.keys(localOnly).length);
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
  $("#exp-a-label").innerHTML = T.ofOriginal(pct(ra));
  $("#exp-b-label").innerHTML = T.ofOriginal(pct(rb));
  $("#exp-a").style.width = Math.min(ra * 100, 100) + "%";
  $("#exp-b").style.width = Math.min(rb * 100, 100) + "%";
  $("#answers").hidden = true;
  $("#c-rehydrate").hidden = true;

  /* ---- Act 3: the proof ---- */
  $("#receiptmeta").innerHTML = [
    ["task", RECEIPT.task_type],
    ["masking_level", RECEIPT.masking_level],
    ["local_only_fields", T.fieldsOnly(RECEIPT.local_only_hashes.length)],
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
  card.textContent = T.verifying;
  const res = await verifyReceipt(receipt);
  if (res.ok) {
    card.className = "verdict-card ok";
    card.innerHTML = T.verdictOk + "<small>" + T.verdictOkSub + "</small>";
  } else {
    card.className = "verdict-card fail";
    card.innerHTML = T.verdictFail + "<small>" + esc(res.reason) +
      (tampered ? T.tamperNote : "") + "</small>";
  }
}

/* ---------- friendly failure banner (a trust product must not fail
 * silently; the classic cause is a stale cached app.js vs fresh HTML) ---- */
function showErrorBanner(detail) {
  if ($("#apl-error-banner")) return;
  const div = document.createElement("div");
  div.id = "apl-error-banner";
  div.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99;" +
    "background:#b3261e;color:#fff;padding:10px 16px;font-size:14px;text-align:center";
  div.textContent = (LANG === "zh"
    ? "頁面載入出了問題——請按 Ctrl+F5 強制重新整理（通常是瀏覽器快取了舊版檔案）。"
    : "Something failed to load — press Ctrl+F5 to hard-refresh " +
      "(a stale cached file is the usual culprit).") +
    (detail ? "  [" + detail + "]" : "");
  document.body.prepend(div);
}
window.addEventListener("error", e => showErrorBanner(e.message));
window.addEventListener("unhandledrejection", e =>
  showErrorBanner(String(e.reason).slice(0, 120)));

document.querySelectorAll(".choice").forEach(b =>
  b.addEventListener("click", () => loadExample(b.dataset.ex)
    .catch(err => showErrorBanner(String(err).slice(0, 120)))));
$("#run").addEventListener("click", runMock);
$("#verify-good").addEventListener("click", () => showVerdict(RECEIPT, false));
$("#verify-bad").addEventListener("click", () => showVerdict(TAMPERED, true));

/* first paint: apply language, never show an empty stage */
applyLang();
loadExample("00_private_matter").catch(err =>
  showErrorBanner(String(err).slice(0, 120)));
