"""Interview-ready product demo page.

This is intentionally a small server-rendered single page app. It keeps the demo
deployable as one FastAPI service while making the product feel less like a
developer/admin console than the Gradio interface.
"""

from __future__ import annotations


def demo_product_html() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GroundDesk</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f3ee;
      --panel: rgba(255, 255, 255, 0.86);
      --panel-strong: #ffffff;
      --ink: #171717;
      --muted: #65605a;
      --line: rgba(23, 23, 23, 0.11);
      --brand: #2457ff;
      --brand-dark: #183fc4;
      --good: #0c7c45;
      --warn: #a15c00;
      --bad: #b42318;
      --shadow: 0 20px 60px rgba(37, 41, 46, 0.12);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(36, 87, 255, 0.13), transparent 34rem),
        radial-gradient(circle at 80% 0%, rgba(17, 138, 99, 0.13), transparent 30rem),
        var(--bg);
      color: var(--ink);
      min-height: 100vh;
    }
    .shell { width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 48px; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      margin-bottom: 22px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .mark {
      width: 42px; height: 42px; border-radius: 14px;
      display: grid; place-items: center;
      background: linear-gradient(145deg, #2457ff, #102a83);
      color: white; font-weight: 800; letter-spacing: -0.05em;
      box-shadow: var(--shadow);
    }
    h1 { margin: 0; font-size: 22px; letter-spacing: -0.04em; }
    .tagline { margin: 3px 0 0; color: var(--muted); font-size: 14px; }
    .statusbar { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .pill {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 999px;
      padding: 8px 11px;
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }
    .pill strong { color: var(--ink); }
    .hero {
      background: rgba(255,255,255,0.68);
      border: 1px solid var(--line);
      border-radius: 30px;
      padding: 26px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
      margin-bottom: 18px;
    }
    .hero h2 { margin: 0 0 8px; font-size: clamp(30px, 5vw, 58px); line-height: 0.95; letter-spacing: -0.075em; }
    .hero p { margin: 0; color: var(--muted); max-width: 760px; font-size: 17px; line-height: 1.55; }
    .grid { display: grid; grid-template-columns: 1.45fr 0.9fr; gap: 18px; align-items: start; }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .card-head {
      padding: 17px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .card h3 { margin: 0; font-size: 15px; letter-spacing: -0.02em; }
    .card-body { padding: 18px; }
    textarea, input {
      width: 100%;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      color: var(--ink);
      border-radius: 16px;
      padding: 14px 15px;
      outline: none;
      font: inherit;
    }
    textarea { resize: vertical; min-height: 128px; line-height: 1.45; }
    textarea:focus, input:focus { border-color: rgba(36, 87, 255, 0.48); box-shadow: 0 0 0 4px rgba(36, 87, 255, 0.11); }
    button {
      border: 0;
      background: var(--brand);
      color: white;
      border-radius: 999px;
      padding: 11px 16px;
      font-weight: 700;
      cursor: pointer;
      transition: transform .12s ease, background .12s ease;
    }
    button:hover { background: var(--brand-dark); transform: translateY(-1px); }
    button.secondary { background: #eee9df; color: var(--ink); }
    button.secondary:hover { background: #e4ddd0; }
    button:disabled { opacity: .55; cursor: wait; transform: none; }
    .actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
    .sample-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
    .sample {
      background: #f0ede6;
      color: #393530;
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 12px;
      cursor: pointer;
      border: 1px solid transparent;
    }
    .sample:hover { border-color: rgba(36, 87, 255, .25); color: var(--brand-dark); }
    .answer {
      white-space: pre-wrap;
      line-height: 1.6;
      background: #fbfaf7;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      min-height: 168px;
    }
    .meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .metric { font-size: 12px; padding: 7px 9px; border-radius: 999px; background: #f2eee7; color: var(--muted); }
    .metric.good { color: var(--good); background: #eaf7ef; }
    .metric.warn { color: var(--warn); background: #fff4df; }
    .citation, .doc {
      border: 1px solid var(--line);
      background: #fbfaf7;
      border-radius: 16px;
      padding: 13px;
      margin-bottom: 10px;
    }
    .citation-title, .doc-title { font-weight: 750; font-size: 13px; margin-bottom: 6px; }
    .snippet, .doc-meta { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .empty { color: var(--muted); font-size: 14px; padding: 8px 0; }
    .upload {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }
    .small { font-size: 12px; color: var(--muted); line-height: 1.45; }
    .links { display: flex; gap: 8px; flex-wrap: wrap; }
    a { color: var(--brand-dark); text-decoration: none; font-weight: 650; }
    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      .statusbar { justify-content: flex-start; }
      .grid { grid-template-columns: 1fr; }
      .hero { border-radius: 24px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand">
        <div class="mark">GD</div>
        <div>
          <h1>GroundDesk</h1>
          <p class="tagline">Evidence-grounded support intelligence</p>
        </div>
      </div>
      <div class="statusbar">
        <span class="pill">Status: <strong id="status">loading</strong></span>
        <span class="pill">Docs: <strong id="docCount">—</strong></span>
        <span class="pill">Chunks: <strong id="chunkCount">—</strong></span>
        <span class="pill">Embeddings: <strong id="embedding">—</strong></span>
      </div>
    </header>

    <section class="hero">
      <h2>Customer answers, grounded in your support docs.</h2>
      <p>Ask a support question. GroundDesk retrieves the most relevant evidence from Qdrant, asks Gemini to answer only from that evidence, and returns citations plus escalation signals.</p>
    </section>

    <main class="grid">
      <section class="card">
        <div class="card-head">
          <h3>Support Copilot</h3>
          <div class="links">
            <a href="/docs" target="_blank">API docs</a>
            <a href="/demo" target="_blank">Admin demo</a>
          </div>
        </div>
        <div class="card-body">
          <div class="sample-row" id="samples"></div>
          <textarea id="question" placeholder="Ask a customer support question...">How long do password reset emails take?</textarea>
          <div class="actions">
            <label class="small"><input id="ticket" type="checkbox" checked style="width:auto;margin-right:6px;"> Draft customer reply</label>
            <button id="askBtn">Ask GroundDesk</button>
          </div>
          <div style="height:14px"></div>
          <div class="answer" id="answer">Ready for a question.</div>
          <div class="meta">
            <span class="metric" id="confidence">Confidence: —</span>
            <span class="metric" id="escalation">Escalation: —</span>
            <span class="metric" id="trace">Trace: —</span>
          </div>
          <div style="height:18px"></div>
          <h3>Citations</h3>
          <div id="citations" class="empty">Citations will appear here after an answer.</div>
          <div style="height:18px"></div>
          <h3>Suggested customer reply</h3>
          <div class="answer" id="ticketReply" style="min-height:80px;">Enable “Draft customer reply” before asking.</div>
        </div>
      </section>

      <aside class="card">
        <div class="card-head">
          <h3>Knowledge Base</h3>
          <button class="secondary" id="refreshBtn">Refresh</button>
        </div>
        <div class="card-body">
          <div id="documents" class="empty">Loading documents…</div>
          <div style="height:18px"></div>
          <h3>Optional upload</h3>
          <p class="small">For interviews, the bundled docs are enough. Upload is here if you want to show live ingestion into Qdrant.</p>
          <div class="upload">
            <input type="file" id="file" accept=".pdf,.md,.markdown,.txt" />
            <input type="password" id="adminKey" placeholder="Admin key, only if configured" />
            <button class="secondary" id="uploadBtn">Index document</button>
            <div id="uploadStatus" class="small"></div>
          </div>
        </div>
      </aside>
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

    function el(id) { return document.getElementById(id); }
    function setText(id, value) { el(id).textContent = value; }
    function headers(extra = {}) {
      return {"Content-Type": "application/json", "X-Workspace-ID": workspaceId, ...extra};
    }

    function renderSamples() {
      el("samples").innerHTML = samples.map(q => `<span class="sample">${q}</span>`).join("");
      [...document.querySelectorAll(".sample")].forEach(node => {
        node.addEventListener("click", () => {
          el("question").value = node.textContent;
          ask();
        });
      });
    }

    async function loadHealth() {
      try {
        const res = await fetch("/api/health");
        const data = await res.json();
        setText("status", data.status || "ok");
        setText("docCount", data.documents ?? "—");
        setText("chunkCount", data.chunks ?? "—");
        setText("embedding", data.embedding_model || "—");
      } catch {
        setText("status", "offline");
      }
    }

    async function loadDocuments() {
      try {
        const res = await fetch("/api/documents", {headers: {"X-Workspace-ID": workspaceId}});
        const docs = await res.json();
        setText("docCount", docs.length);
        if (!docs.length) {
          el("documents").className = "empty";
          el("documents").textContent = "No documents indexed yet.";
          return;
        }
        el("documents").className = "";
        el("documents").innerHTML = docs.map(doc => `
          <div class="doc">
            <div class="doc-title">${escapeHtml(doc.title)}</div>
            <div class="doc-meta">${escapeHtml(doc.source)} · ${doc.chunks_indexed} chunk${doc.chunks_indexed === 1 ? "" : "s"} · ${doc.status}</div>
          </div>
        `).join("");
      } catch (err) {
        el("documents").className = "empty";
        el("documents").textContent = "Could not load documents.";
      }
    }

    async function ask() {
      const question = el("question").value.trim();
      if (!question) return;
      el("askBtn").disabled = true;
      el("answer").textContent = "Retrieving evidence and generating answer…";
      el("citations").className = "empty";
      el("citations").textContent = "Loading citations…";
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: headers(),
          body: JSON.stringify({
            question,
            top_k: 5,
            draft_ticket_reply: el("ticket").checked
          })
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
        el("ticketReply").textContent = data.suggested_ticket_reply || "No ticket reply requested.";
        if (data.citations && data.citations.length) {
          el("citations").className = "";
          el("citations").innerHTML = data.citations.map((c, i) => `
            <div class="citation">
              <div class="citation-title">[${i + 1}] ${escapeHtml(c.title)} · score ${Number(c.score || 0).toFixed(2)}</div>
              <div class="snippet">${escapeHtml(c.snippet || "")}</div>
            </div>
          `).join("");
        } else {
          el("citations").className = "empty";
          el("citations").textContent = "No citations returned. This should usually escalate.";
        }
      } catch (err) {
        el("answer").textContent = `Error: ${err.message}`;
        el("citations").textContent = "No citations.";
      } finally {
        el("askBtn").disabled = false;
      }
    }

    async function upload() {
      const file = el("file").files[0];
      if (!file) {
        el("uploadStatus").textContent = "Choose a file first.";
        return;
      }
      const body = new FormData();
      body.append("file", file);
      const extra = {"X-Workspace-ID": workspaceId};
      const adminKey = el("adminKey").value.trim();
      if (adminKey) extra["X-Admin-API-Key"] = adminKey;
      el("uploadBtn").disabled = true;
      el("uploadStatus").textContent = "Indexing document…";
      try {
        const res = await fetch("/api/documents", {method: "POST", headers: extra, body});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");
        el("uploadStatus").textContent = `${data.status}: ${data.chunks_indexed} chunks indexed.`;
        await loadHealth();
        await loadDocuments();
      } catch (err) {
        el("uploadStatus").textContent = `Upload failed: ${err.message}`;
      } finally {
        el("uploadBtn").disabled = false;
      }
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;"
      }[c]));
    }

    function cleanAnswer(value) {
      return String(value)
        .replace(/\{?\s*chunk_id\s*:\s*[^}\s]+(?:\s*\})?/gi, "")
        .replace(/\s+([.,;:!?])/g, "$1")
        .replace(/[ \t]{2,}/g, " ")
        .trim();
    }

    renderSamples();
    loadHealth();
    loadDocuments();
    el("askBtn").addEventListener("click", ask);
    el("refreshBtn").addEventListener("click", () => { loadHealth(); loadDocuments(); });
    el("uploadBtn").addEventListener("click", upload);
  </script>
</body>
</html>"""
