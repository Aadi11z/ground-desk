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
      --bg: #eef2f7;
      --bg-2: #f8fafc;
      --panel: #ffffff;
      --panel-2: #f8fafc;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --brand: #2563eb;
      --brand-dark: #1d4ed8;
      --green: #067647;
      --amber: #b45309;
      --red: #b42318;
      --shadow: 0 20px 60px rgba(15, 23, 42, 0.10);
      --radius: 22px;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(37,99,235,.14), transparent 34rem),
        radial-gradient(circle at 80% 0%, rgba(14,165,233,.14), transparent 30rem),
        linear-gradient(180deg, var(--bg-2), var(--bg));
      color: var(--ink);
    }
    a { color: inherit; text-decoration: none; }
    button, textarea, input { font: inherit; }
    button { border: 0; cursor: pointer; }
    .shell {
      width: min(1400px, calc(100vw - 36px));
      margin: 22px auto;
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      gap: 18px;
    }
    .sidebar, .card {
      background: rgba(255,255,255,.88);
      border: 1px solid rgba(226,232,240,.95);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
      border-radius: var(--radius);
    }
    .sidebar {
      min-height: calc(100vh - 44px);
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      position: sticky;
      top: 22px;
    }
    .brand { display: flex; align-items: center; gap: 12px; padding-bottom: 6px; }
    .logo {
      width: 44px; height: 44px; border-radius: 14px;
      display: grid; place-items: center;
      background: linear-gradient(135deg, #2563eb, #0f172a);
      color: #fff; font-weight: 900; letter-spacing: -.04em;
      box-shadow: 0 10px 28px rgba(37,99,235,.25);
    }
    .brand-title { font-size: 21px; font-weight: 900; letter-spacing: -.055em; }
    .brand-subtitle { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .navlinks { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .navlinks a, .secondary-btn {
      text-align: center;
      border: 1px solid var(--line);
      border-radius: 13px;
      background: var(--panel-2);
      padding: 10px;
      font-size: 13px;
      font-weight: 750;
      color: #334155;
    }
    .section-title {
      margin: 4px 0 10px;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .12em;
      font-weight: 850;
    }
    .status-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
    .status-tile {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: #fff;
      padding: 12px;
    }
    .status-value { font-size: 22px; font-weight: 900; letter-spacing: -.04em; }
    .status-label { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .pill {
      display: inline-flex; align-items: center; gap: 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 10px;
      color: #475569;
      background: #fff;
      font-size: 12px;
      font-weight: 700;
    }
    .dot { width: 8px; height: 8px; border-radius: 99px; background: var(--green); }
    .dot.warn { background: var(--amber); }
    .doc-list { display: grid; gap: 9px; }
    .doc {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 15px;
      padding: 11px;
    }
    .doc-head { display: flex; justify-content: space-between; gap: 10px; font-weight: 850; font-size: 13px; }
    .doc-meta { color: var(--muted); font-size: 12px; line-height: 1.45; margin-top: 5px; }
    details { border-top: 1px solid var(--line); padding-top: 14px; }
    summary { cursor: pointer; font-weight: 850; font-size: 13px; }
    .upload { display: grid; gap: 9px; margin-top: 12px; }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 15px;
      padding: 13px 14px;
      outline: none;
    }
    input:focus, textarea:focus { border-color: #93c5fd; box-shadow: 0 0 0 4px rgba(37,99,235,.12); }
    .main { display: flex; flex-direction: column; gap: 18px; }
    .hero {
      padding: 28px 30px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 24px;
      align-items: end;
    }
    h1 { margin: 0; font-size: clamp(34px, 4vw, 56px); line-height: .98; letter-spacing: -.075em; max-width: 820px; }
    .lead { margin: 14px 0 0; color: var(--muted); font-size: 16px; line-height: 1.6; max-width: 760px; }
    .stack-badges { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .workspace { color: var(--muted); font-size: 12px; margin-top: 10px; text-align: right; }
    .workbench { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(360px, .7fr); gap: 18px; }
    .card-head {
      padding: 17px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid var(--line);
    }
    .card-title { font-weight: 900; letter-spacing: -.025em; }
    .card-subtitle { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .card-body { padding: 18px; }
    .samples { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; margin-bottom: 13px; }
    .sample {
      text-align: left;
      border: 1px solid var(--line);
      background: #f8fafc;
      color: #334155;
      border-radius: 14px;
      padding: 10px 11px;
      font-size: 13px;
      font-weight: 650;
    }
    .sample:hover { border-color: #93c5fd; color: var(--brand-dark); background: #eff6ff; }
    textarea { min-height: 120px; resize: vertical; line-height: 1.55; }
    .controls { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
    .checkbox { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    .checkbox input { width: auto; }
    .primary-btn {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #fff;
      border-radius: 14px;
      padding: 12px 16px;
      font-weight: 900;
      box-shadow: 0 10px 24px rgba(37,99,235,.22);
    }
    .primary-btn:hover { filter: brightness(.97); }
    .primary-btn:disabled, .secondary-btn:disabled { opacity: .65; cursor: wait; }
    .answer {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 18px;
      padding: 17px;
      line-height: 1.65;
      min-height: 152px;
      white-space: pre-wrap;
    }
    .label { margin: 18px 0 8px; color: #334155; font-size: 13px; font-weight: 900; }
    .metrics { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 11px; }
    .metric { border-radius: 999px; padding: 8px 11px; background: #f1f5f9; color: #475569; font-size: 12px; font-weight: 800; }
    .metric.good { background: #ecfdf3; color: var(--green); }
    .metric.warn { background: #fffbeb; color: var(--amber); }
    .citation {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 16px;
      padding: 13px;
      margin-bottom: 10px;
    }
    .citation-title { display: flex; justify-content: space-between; gap: 12px; font-weight: 900; font-size: 13px; margin-bottom: 7px; }
    .snippet, .help, .empty { color: var(--muted); font-size: 13px; line-height: 1.5; }
    .score { color: var(--brand-dark); white-space: nowrap; }
    .alert {
      display: none;
      border: 1px solid #fed7aa;
      background: #fff7ed;
      color: #9a3412;
      border-radius: 15px;
      padding: 12px;
      margin-top: 12px;
      font-size: 13px;
      line-height: 1.45;
    }
    .kb-empty-issue {
      border: 1px solid #fed7aa;
      background: #fff7ed;
      color: #9a3412;
      border-radius: 15px;
      padding: 12px;
      font-size: 13px;
      line-height: 1.45;
    }
    @media (max-width: 1100px) {
      .shell { grid-template-columns: 1fr; }
      .sidebar { position: static; min-height: auto; }
      .workbench, .hero { grid-template-columns: 1fr; }
      .stack-badges, .workspace { justify-content: flex-start; text-align: left; }
    }
    @media (max-width: 650px) {
      .shell { width: min(100vw - 20px, 1400px); margin: 10px auto; }
      .samples, .status-grid { grid-template-columns: 1fr; }
      h1 { font-size: 36px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">GD</div>
        <div>
          <div class="brand-title">GroundDesk</div>
          <div class="brand-subtitle">Evidence-grounded support intelligence</div>
        </div>
      </div>

      <div class="navlinks">
        <a href="/docs" target="_blank">OpenAPI</a>
        <a href="/demo" target="_blank">Gradio</a>
      </div>

      <div>
        <div class="section-title">System health</div>
        <div class="status-grid">
          <div class="status-tile"><div class="status-value" id="docCount">—</div><div class="status-label">Documents</div></div>
          <div class="status-tile"><div class="status-value" id="chunkCount">—</div><div class="status-label">Chunks</div></div>
        </div>
        <div style="margin-top:10px"><span class="pill"><span class="dot" id="statusDot"></span>Status: <span id="status">loading</span></span></div>
        <div class="alert" id="healthAlert"></div>
      </div>

      <div>
        <div class="section-title">Knowledge base</div>
        <div id="documents" class="doc-list"><div class="empty">Loading documents…</div></div>
      </div>

      <details>
        <summary>Admin ingestion</summary>
        <p class="help">Optional for the demo. Upload Markdown, TXT, or PDF to index it into Qdrant for the demo workspace.</p>
        <div class="upload">
          <input type="file" id="file" accept=".pdf,.md,.markdown,.txt">
          <input type="password" id="adminKey" placeholder="Admin key, if configured">
          <button class="secondary-btn" id="uploadBtn">Index document</button>
          <div class="help" id="uploadStatus"></div>
        </div>
      </details>
    </aside>

    <main class="main">
      <section class="card hero">
        <div>
          <h1>Support answers with receipts.</h1>
          <p class="lead">Ask a customer-support question. GroundDesk searches Qdrant, generates a Gemini answer constrained to retrieved evidence, returns citations, and flags cases that need escalation.</p>
        </div>
        <div>
          <div class="stack-badges">
            <span class="pill">Vector DB: Qdrant</span>
            <span class="pill">Generation: Gemini</span>
            <span class="pill">Embeddings: <span id="embedding">—</span></span>
          </div>
          <div class="workspace">Workspace: demo</div>
        </div>
      </section>

      <section class="workbench">
        <div class="card">
          <div class="card-head">
            <div><div class="card-title">Support copilot</div><div class="card-subtitle">Grounded answer generation</div></div>
            <button class="primary-btn" id="askBtn">Ask GroundDesk</button>
          </div>
          <div class="card-body">
            <div class="samples" id="samples"></div>
            <textarea id="question">How long do password reset emails take?</textarea>
            <div class="controls">
              <label class="checkbox"><input id="ticket" type="checkbox" checked> Include suggested support reply</label>
              <span class="help">If evidence is weak, the response should escalate instead of guessing.</span>
            </div>

            <div class="label">Grounded answer</div>
            <div class="answer" id="answer">Ready for a support question.</div>
            <div class="metrics">
              <span class="metric" id="confidence">Confidence: —</span>
              <span class="metric" id="escalation">Escalation: —</span>
              <span class="metric" id="trace">Trace: —</span>
            </div>

            <div class="label">Suggested support reply</div>
            <div class="answer" id="ticketReply" style="min-height:84px">A paste-ready reply appears here when enabled.</div>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <div><div class="card-title">Evidence</div><div class="card-subtitle">Retrieved source chunks</div></div>
            <button class="secondary-btn" id="refreshBtn">Refresh</button>
          </div>
          <div class="card-body">
            <div id="citations" class="empty">Citations appear after generation.</div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const samples = [
      "How long do password reset emails take?",
      "Can I export invoices from the billing page?",
      "What should I do if SSO users cannot sign in?",
      "Can you configure my payroll software?"
    ];
    const workspaceId = "demo";
    let lastHealth = {documents: 0, chunks: 0};
    const el = id => document.getElementById(id);
    const setText = (id, value) => { el(id).textContent = value; };
    const jsonHeaders = extra => ({"Content-Type":"application/json", "X-Workspace-ID": workspaceId, ...(extra || {})});

    function renderSamples() {
      el("samples").innerHTML = samples.map(q => `<button class="sample">${escapeHtml(q)}</button>`).join("");
      document.querySelectorAll(".sample").forEach(node => node.addEventListener("click", () => {
        el("question").value = node.textContent;
        ask();
      }));
    }

    async function loadHealth() {
      try {
        const res = await fetch("/api/health", {cache: "no-store"});
        const data = await res.json();
        lastHealth = data;
        setText("status", data.status || "ok");
        setText("docCount", data.documents ?? "—");
        setText("chunkCount", data.chunks ?? "—");
        setText("embedding", data.embedding_model || "—");
        el("statusDot").className = `dot ${data.status === "ok" ? "" : "warn"}`;
        if (data.status !== "ok" || data.startup_error) {
          el("healthAlert").style.display = "block";
          el("healthAlert").textContent = data.startup_error || "System is degraded. Check deployment logs.";
        } else {
          el("healthAlert").style.display = "none";
        }
      } catch {
        setText("status", "offline");
        el("statusDot").className = "dot warn";
      }
    }

    async function loadDocuments() {
      try {
        const res = await fetch("/api/documents", {headers: {"X-Workspace-ID": workspaceId}, cache: "no-store"});
        const docs = await res.json();
        if (!Array.isArray(docs) || !docs.length) {
          if ((lastHealth.chunks || 0) > 0) {
            el("documents").innerHTML = `<div class="kb-empty-issue">Qdrant has ${lastHealth.chunks} chunk(s), but this app build is not exposing document manifests yet. Redeploy the latest backend patch, then refresh.</div>`;
          } else {
            el("documents").innerHTML = `<div class="empty">No documents indexed yet. Startup indexing may still be running.</div>`;
          }
          return;
        }
        el("documents").innerHTML = docs.map(doc => `<div class="doc"><div class="doc-head"><span>${escapeHtml(doc.title)}</span><span>${doc.chunks_indexed}</span></div><div class="doc-meta">${escapeHtml(doc.source)} · ${escapeHtml(doc.status)} · ${escapeHtml(doc.source_type)}</div></div>`).join("");
      } catch {
        el("documents").innerHTML = `<div class="empty">Could not load documents.</div>`;
      }
    }

    async function ask() {
      const question = el("question").value.trim();
      if (!question) return;
      el("askBtn").disabled = true;
      el("answer").textContent = "Retrieving evidence from Qdrant and generating an evidence-constrained answer…";
      el("citations").className = "empty";
      el("citations").textContent = "Retrieving citations…";
      try {
        const res = await fetch("/api/chat", {
          method:"POST",
          headers:jsonHeaders(),
          body: JSON.stringify({question, top_k: 5, draft_ticket_reply: el("ticket").checked})
        });
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
          el("citations").innerHTML = data.citations.map((c, i) => `<div class="citation"><div class="citation-title"><span>[${i + 1}] ${escapeHtml(c.title)}</span><span class="score">score ${Number(c.score || 0).toFixed(2)}</span></div><div class="snippet">${escapeHtml(c.snippet || "")}</div></div>`).join("");
        } else {
          el("citations").className = "empty";
          el("citations").textContent = "No citations returned. GroundDesk should escalate this instead of inventing an answer.";
        }
      } catch (err) {
        el("answer").textContent = `Error: ${err.message}`;
        el("citations").className = "empty";
        el("citations").textContent = "No citations returned.";
      } finally {
        el("askBtn").disabled = false;
      }
    }

    async function upload() {
      const file = el("file").files[0];
      if (!file) { el("uploadStatus").textContent = "Choose a file first."; return; }
      const body = new FormData();
      body.append("file", file);
      const extra = {"X-Workspace-ID": workspaceId};
      const key = el("adminKey").value.trim();
      if (key) extra["X-Admin-API-Key"] = key;
      el("uploadBtn").disabled = true;
      el("uploadStatus").textContent = "Indexing document into Qdrant…";
      try {
        const res = await fetch("/api/documents", {method:"POST", headers:extra, body});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");
        el("uploadStatus").textContent = `${data.status}: ${data.chunks_indexed} chunks indexed.`;
        await refreshAll();
      } catch (err) {
        el("uploadStatus").textContent = `Upload failed: ${err.message}`;
      } finally {
        el("uploadBtn").disabled = false;
      }
    }

    async function refreshAll() {
      await loadHealth();
      await loadDocuments();
    }
    function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c])); }
    function cleanAnswer(value) { return String(value).replace(/\{?\s*chunk_id\s*:\s*[^}\s]+(?:\s*\})?/gi, "").replace(/\s+([.,;:!?])/g, "$1").replace(/[ \t]{2,}/g, " ").trim(); }

    renderSamples();
    refreshAll();
    setInterval(refreshAll, 15000);
    el("askBtn").addEventListener("click", ask);
    el("refreshBtn").addEventListener("click", refreshAll);
    el("uploadBtn").addEventListener("click", upload);
  </script>
</body>
</html>'''
