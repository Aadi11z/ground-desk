"""Interview-ready product demo page for GroundDesk."""

from __future__ import annotations


def demo_product_html() -> str:
    return r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GroundDesk</title>
  <style>
    :root {
      --bg: #f7f8fb;
      --surface: #ffffff;
      --surface-2: #f2f5f9;
      --ink: #101828;
      --muted: #667085;
      --line: #e4e7ec;
      --brand: #1d4ed8;
      --brand-2: #0f172a;
      --green: #067647;
      --amber: #b54708;
      --red: #b42318;
      --shadow: 0 18px 48px rgba(16, 24, 40, 0.08);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); min-height: 100vh; }
    .topbar { height: 72px; background: var(--surface); border-bottom: 1px solid var(--line); display: flex; align-items: center; }
    .container { width: min(1180px, calc(100vw - 32px)); margin: 0 auto; }
    .nav { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    .brand { display: flex; align-items: center; gap: 12px; }
    .logo { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; color: #fff; font-weight: 800; background: linear-gradient(135deg, #1d4ed8, #0f172a); }
    .brand-title { font-weight: 800; letter-spacing: -0.04em; font-size: 19px; }
    .brand-subtitle { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .navlinks { display: flex; gap: 10px; align-items: center; }
    a { color: var(--brand); text-decoration: none; font-weight: 700; font-size: 13px; }
    .badge-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
    .badge { border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: 7px 10px; color: var(--muted); font-size: 12px; }
    .badge strong { color: var(--ink); }
    .hero { padding: 38px 0 24px; }
    .hero-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 24px; align-items: end; }
    h1 { font-size: clamp(34px, 5vw, 58px); line-height: 0.98; letter-spacing: -0.075em; margin: 0; max-width: 760px; }
    .lead { color: var(--muted); font-size: 17px; line-height: 1.6; margin: 16px 0 0; max-width: 720px; }
    .proof { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .proof-card { background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 14px; box-shadow: 0 8px 28px rgba(16,24,40,.04); }
    .proof-num { font-size: 23px; font-weight: 850; letter-spacing: -0.04em; }
    .proof-label { color: var(--muted); font-size: 12px; margin-top: 4px; }
    .main { display: grid; grid-template-columns: minmax(0, 1.45fr) 360px; gap: 18px; padding-bottom: 46px; }
    .panel { background: var(--surface); border: 1px solid var(--line); border-radius: 22px; box-shadow: var(--shadow); overflow: hidden; }
    .panel-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid var(--line); gap: 12px; }
    .panel-title { font-size: 14px; font-weight: 800; letter-spacing: -0.01em; }
    .panel-body { padding: 18px; }
    .samples { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-bottom: 14px; }
    .sample { text-align: left; background: var(--surface-2); color: #344054; border: 1px solid #e7ebf2; border-radius: 13px; padding: 10px 11px; font-size: 13px; cursor: pointer; }
    .sample:hover { border-color: #bcd0ff; color: var(--brand); }
    textarea, input { width: 100%; border: 1px solid var(--line); border-radius: 14px; padding: 13px 14px; font: inherit; color: var(--ink); background: #fff; outline: none; }
    textarea { min-height: 116px; resize: vertical; line-height: 1.5; }
    textarea:focus, input:focus { border-color: #8bb4ff; box-shadow: 0 0 0 4px rgba(29,78,216,.11); }
    .controls { display: flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
    .checkbox { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    .checkbox input { width: auto; }
    button { border: 0; border-radius: 13px; background: var(--brand); color: #fff; padding: 11px 15px; font-weight: 800; cursor: pointer; }
    button:hover { background: #1644bd; }
    button.secondary { background: var(--surface-2); color: var(--ink); border: 1px solid var(--line); }
    button.secondary:hover { background: #e9eef6; }
    button:disabled { opacity: .6; cursor: wait; }
    .answer { border: 1px solid var(--line); background: #fcfcfd; border-radius: 16px; padding: 16px; line-height: 1.62; min-height: 156px; white-space: pre-wrap; }
    .section-label { margin: 18px 0 8px; font-size: 12px; color: var(--muted); font-weight: 800; text-transform: uppercase; letter-spacing: .08em; }
    .metrics { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .metric { border-radius: 999px; padding: 7px 10px; background: var(--surface-2); color: var(--muted); font-size: 12px; }
    .metric.good { background: #ecfdf3; color: var(--green); }
    .metric.warn { background: #fffaeb; color: var(--amber); }
    .citation, .doc { border: 1px solid var(--line); background: #fff; border-radius: 15px; padding: 13px; margin-bottom: 10px; }
    .citation-title, .doc-title { display: flex; justify-content: space-between; gap: 10px; font-weight: 800; font-size: 13px; margin-bottom: 6px; }
    .snippet, .doc-meta, .help { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .score { color: var(--brand); white-space: nowrap; }
    .empty { color: var(--muted); font-size: 14px; padding: 8px 0; }
    .upload { display: grid; gap: 10px; margin-top: 10px; }
    .alert { border: 1px solid #fedf89; color: #93370d; background: #fffaeb; border-radius: 14px; padding: 11px 12px; font-size: 13px; display: none; margin-top: 12px; }
    @media (max-width: 980px) { .hero-grid, .main { grid-template-columns: 1fr; } .proof { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 650px) { .samples, .proof { grid-template-columns: 1fr; } .nav { align-items: flex-start; flex-direction: column; } }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="container nav">
      <div class="brand">
        <div class="logo">GD</div>
        <div><div class="brand-title">GroundDesk</div><div class="brand-subtitle">RAG support copilot</div></div>
      </div>
      <div class="navlinks"><a href="/docs" target="_blank">API Docs</a><a href="/demo" target="_blank">Admin UI</a></div>
    </div>
  </div>

  <section class="container hero">
    <div class="hero-grid">
      <div>
        <h1>Answer support questions from trusted company knowledge.</h1>
        <p class="lead">GroundDesk retrieves evidence from Qdrant, asks Gemini to answer only from that evidence, cites the source chunks, and escalates when documentation is insufficient.</p>
        <div class="badge-row">
          <span class="badge">Status: <strong id="status">loading</strong></span>
          <span class="badge">Embedding: <strong id="embedding">—</strong></span>
        </div>
        <div class="alert" id="healthAlert"></div>
      </div>
      <div class="proof">
        <div class="proof-card"><div class="proof-num" id="docCount">—</div><div class="proof-label">documents indexed</div></div>
        <div class="proof-card"><div class="proof-num" id="chunkCount">—</div><div class="proof-label">evidence chunks</div></div>
        <div class="proof-card"><div class="proof-num">RAG</div><div class="proof-label">Qdrant + Gemini</div></div>
      </div>
    </div>
  </section>

  <main class="container main">
    <section class="panel">
      <div class="panel-head"><div class="panel-title">Ask GroundDesk</div><button id="askBtn">Generate answer</button></div>
      <div class="panel-body">
        <div class="samples" id="samples"></div>
        <textarea id="question">How long do password reset emails take?</textarea>
        <div class="controls"><label class="checkbox"><input id="ticket" type="checkbox" checked> Draft support reply</label><span class="help">Answers are constrained to retrieved evidence.</span></div>
        <div class="section-label">Grounded answer</div>
        <div class="answer" id="answer">Ready for a support question.</div>
        <div class="metrics"><span class="metric" id="confidence">Confidence: —</span><span class="metric" id="escalation">Escalation: —</span><span class="metric" id="trace">Trace: —</span></div>
        <div class="section-label">Citations</div>
        <div id="citations" class="empty">Citations appear after generation.</div>
        <div class="section-label">Suggested support reply</div>
        <div class="answer" id="ticketReply" style="min-height:80px">A paste-ready reply appears here when enabled.</div>
      </div>
    </section>

    <aside class="panel">
      <div class="panel-head"><div class="panel-title">Knowledge base</div><button class="secondary" id="refreshBtn">Refresh</button></div>
      <div class="panel-body">
        <div id="documents" class="empty">Loading documents…</div>
        <div class="section-label">Live ingestion</div>
        <p class="help">Optional for the interview. Upload Markdown, TXT, or PDF to show a new document being embedded and stored in Qdrant.</p>
        <div class="upload"><input type="file" id="file" accept=".pdf,.md,.markdown,.txt"><input type="password" id="adminKey" placeholder="Admin key if configured"><button class="secondary" id="uploadBtn">Index document</button><div class="help" id="uploadStatus"></div></div>
      </div>
    </aside>
  </main>

  <script>
    const samples = [
      "How long do password reset emails take?",
      "Can I export invoices from the billing page?",
      "What should I do if SSO users cannot sign in?",
      "Can you configure my payroll software?"
    ];
    const workspaceId = "demo";
    const el = id => document.getElementById(id);
    const setText = (id, value) => { el(id).textContent = value; };
    const headers = extra => ({"Content-Type":"application/json", "X-Workspace-ID": workspaceId, ...(extra || {})});

    function renderSamples() {
      el("samples").innerHTML = samples.map(q => `<button class="sample">${escapeHtml(q)}</button>`).join("");
      document.querySelectorAll(".sample").forEach(node => node.addEventListener("click", () => { el("question").value = node.textContent; ask(); }));
    }

    async function loadHealth() {
      try {
        const res = await fetch("/api/health");
        const data = await res.json();
        setText("status", data.status || "ok");
        setText("docCount", data.documents ?? "—");
        setText("chunkCount", data.chunks ?? "—");
        setText("embedding", data.embedding_model || "—");
        if (data.status !== "ok" || data.startup_error) {
          el("healthAlert").style.display = "block";
          el("healthAlert").textContent = data.startup_error || "System is degraded. Check deployment logs.";
        } else {
          el("healthAlert").style.display = "none";
        }
      } catch { setText("status", "offline"); }
    }

    async function loadDocuments() {
      try {
        const res = await fetch("/api/documents", {headers: {"X-Workspace-ID": workspaceId}});
        const docs = await res.json();
        if (!Array.isArray(docs) || !docs.length) {
          el("documents").className = "empty";
          el("documents").textContent = "No documents indexed yet. Refresh after startup indexing completes.";
          return;
        }
        el("documents").className = "";
        el("documents").innerHTML = docs.map(doc => `<div class="doc"><div class="doc-title"><span>${escapeHtml(doc.title)}</span><span>${doc.chunks_indexed} chunk${doc.chunks_indexed === 1 ? "" : "s"}</span></div><div class="doc-meta">${escapeHtml(doc.source)} · ${escapeHtml(doc.status)}</div></div>`).join("");
      } catch { el("documents").textContent = "Could not load documents."; }
    }

    async function ask() {
      const question = el("question").value.trim();
      if (!question) return;
      el("askBtn").disabled = true;
      el("answer").textContent = "Retrieving evidence from Qdrant and generating answer…";
      el("citations").className = "empty";
      el("citations").textContent = "Loading citations…";
      try {
        const res = await fetch("/api/chat", {method:"POST", headers:headers(), body: JSON.stringify({question, top_k: 5, draft_ticket_reply: el("ticket").checked})});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        el("answer").textContent = cleanAnswer(data.answer || "No answer returned.");
        const confidence = Math.round((data.confidence || 0) * 100);
        el("confidence").textContent = `Confidence: ${confidence}%`;
        el("confidence").className = `metric ${confidence >= 60 ? "good" : "warn"}`;
        el("escalation").textContent = `Escalation: ${data.needs_escalation ? "yes" : "no"}`;
        el("escalation").className = `metric ${data.needs_escalation ? "warn" : "good"}`;
        el("trace").textContent = `Trace: ${data.trace_id}`;
        el("ticketReply").textContent = data.suggested_ticket_reply || "No support reply requested.";
        if (data.citations && data.citations.length) {
          el("citations").className = "";
          el("citations").innerHTML = data.citations.map((c, i) => `<div class="citation"><div class="citation-title"><span>[${i + 1}] ${escapeHtml(c.title)}</span><span class="score">${Number(c.score || 0).toFixed(2)}</span></div><div class="snippet">${escapeHtml(c.snippet || "")}</div></div>`).join("");
        } else {
          el("citations").className = "empty";
          el("citations").textContent = "No citations returned. This should usually escalate.";
        }
      } catch (err) {
        el("answer").textContent = `Error: ${err.message}`;
        el("citations").textContent = "No citations.";
      } finally { el("askBtn").disabled = false; }
    }

    async function upload() {
      const file = el("file").files[0];
      if (!file) { el("uploadStatus").textContent = "Choose a file first."; return; }
      const body = new FormData(); body.append("file", file);
      const extra = {"X-Workspace-ID": workspaceId};
      const key = el("adminKey").value.trim(); if (key) extra["X-Admin-API-Key"] = key;
      el("uploadBtn").disabled = true; el("uploadStatus").textContent = "Indexing document…";
      try {
        const res = await fetch("/api/documents", {method:"POST", headers:extra, body});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");
        el("uploadStatus").textContent = `${data.status}: ${data.chunks_indexed} chunks indexed.`;
        await loadHealth(); await loadDocuments();
      } catch (err) { el("uploadStatus").textContent = `Upload failed: ${err.message}`; }
      finally { el("uploadBtn").disabled = false; }
    }

    function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c])); }
    function cleanAnswer(value) { return String(value).replace(/\{?\s*chunk_id\s*:\s*[^}\s]+(?:\s*\})?/gi, "").replace(/\s+([.,;:!?])/g, "$1").replace(/[ \t]{2,}/g, " ").trim(); }

    renderSamples(); loadHealth(); loadDocuments();
    el("askBtn").addEventListener("click", ask);
    el("refreshBtn").addEventListener("click", () => { loadHealth(); loadDocuments(); });
    el("uploadBtn").addEventListener("click", upload);
  </script>
</body>
</html>'''
