"""Interview-ready product demo page for GroundDesk."""

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
    .hidden { display: none !important; }
    .access-panel, .thread-panel {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 16px;
      padding: 12px;
    }
    .access-panel { display: grid; gap: 9px; }
    .access-title { font-weight: 850; font-size: 13px; color: #334155; }
    .access-meta { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .access-panel input, .access-panel select { padding: 10px 11px; border-radius: 12px; }
    .access-actions { display: flex; gap: 8px; }
    .access-actions button { flex: 1; }
    select {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 12px;
      padding: 10px;
      outline: none;
    }
    .threads { display: grid; gap: 7px; max-height: 258px; overflow-y: auto; margin-top: 9px; }
    .thread {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 9px;
      cursor: pointer;
    }
    .thread:hover, .thread.active { border-color: #93c5fd; background: #eff6ff; }
    .thread-question { font-size: 12px; font-weight: 750; line-height: 1.35; color: #334155; }
    .thread-meta { font-size: 11px; color: var(--muted); margin-top: 4px; }
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
    .benchmark {
      border: 1px solid #bfdbfe;
      background: #eff6ff;
      border-radius: 16px;
      padding: 12px;
    }
    .benchmark-name { color: #1e3a8a; font-size: 12px; font-weight: 850; }
    .benchmark-value { font-size: 26px; font-weight: 950; color: var(--brand-dark); letter-spacing: -.045em; margin-top: 7px; }
    .benchmark-meta { color: #475569; font-size: 12px; line-height: 1.5; margin-top: 5px; }
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
    .feedback {
      margin-top: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .feedback button {
      border: 1px solid var(--line);
      background: #fff;
      color: #334155;
      padding: 8px 11px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 750;
    }
    .feedback button:hover { border-color: #93c5fd; background: #eff6ff; }
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
      </div>

      <div>
        <div class="section-title">Access</div>
        <div class="access-panel" id="demoAccess">
          <div class="access-title">Public demo</div>
          <div class="access-meta">This session is restricted to the bundled demo workspace.</div>
        </div>
        <form class="access-panel hidden" id="signInPanel">
          <div class="access-title">Team sign in</div>
          <div class="access-meta">Use your organization account to access its knowledge base.</div>
          <input type="email" id="email" autocomplete="email" placeholder="Work email" required>
          <input type="password" id="password" autocomplete="current-password" placeholder="Password" required>
          <button class="primary-btn" id="signInBtn" type="submit">Sign in</button>
          <div class="access-meta" id="authStatus"></div>
        </form>
        <div class="access-panel hidden" id="userPanel">
          <div class="access-title" id="userEmail">Signed in</div>
          <label class="access-meta" for="workspaceSelect">Workspace</label>
          <select id="workspaceSelect"></select>
          <div class="access-actions">
            <button class="secondary-btn" id="signOutBtn">Sign out</button>
          </div>
        </div>
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

      <div class="hidden" id="historyPanel">
        <div class="section-title">My recent questions</div>
        <div class="thread-panel">
          <button class="secondary-btn" id="newThreadBtn" style="width:100%">New question thread</button>
          <div class="threads" id="history"><div class="empty">No saved conversations yet.</div></div>
        </div>
      </div>

      <div>
        <div class="section-title">Measured retrieval</div>
        <div class="benchmark">
          <div class="benchmark-name" id="benchmarkName">Loading benchmark report…</div>
          <div class="benchmark-value" id="benchmarkValue">—</div>
          <div class="benchmark-meta" id="benchmarkMeta"></div>
          <div class="benchmark-meta" id="benchmarkGemini"></div>
        </div>
      </div>

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
          <div class="workspace">Workspace: <span id="workspaceName">demo</span></div>
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
              <span class="metric" id="confidence">Evidence support: —</span>
              <span class="metric" id="escalation">Escalation: —</span>
              <span class="metric" id="trace">Trace: —</span>
            </div>
            <div class="feedback hidden" id="feedbackPanel">
              <span class="help">Was this grounded answer useful?</span>
              <button id="feedbackUp">Helpful</button>
              <button id="feedbackDown">Needs review</button>
              <span class="help" id="feedbackStatus"></span>
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
    const SESSION_KEY = "grounddesk.supabase.session";
    const state = {
      config: {auth_mode: "demo", default_workspace_id: "demo"},
      workspaceId: "demo",
      session: null,
      user: null,
      conversationId: null,
      lastTraceId: null,
      history: []
    };
    let lastHealth = {documents: 0, chunks: 0};
    const el = id => document.getElementById(id);
    const setText = (id, value) => { el(id).textContent = value; };
    const isTeamMode = () => state.config.auth_mode === "supabase";

    async function headers(includeJson = false) {
      const result = {"X-Workspace-ID": state.workspaceId};
      if (includeJson) result["Content-Type"] = "application/json";
      if (isTeamMode()) {
        const active = await ensureSession();
        if (!active) throw new Error("Sign in to access your workspace.");
        result["Authorization"] = `Bearer ${state.session.access_token}`;
      }
      return result;
    }

    function saveSession(payload) {
      state.session = {
        access_token: payload.access_token,
        refresh_token: payload.refresh_token,
        expires_at_ms: payload.expires_at
          ? Number(payload.expires_at) * 1000
          : Date.now() + Number(payload.expires_in || 3600) * 1000
      };
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(state.session));
    }

    function clearSession() {
      state.session = null;
      state.user = null;
      state.conversationId = null;
      state.lastTraceId = null;
      state.history = [];
      sessionStorage.removeItem(SESSION_KEY);
    }

    async function ensureSession() {
      if (!state.session || !state.session.access_token) return false;
      if (Date.now() < Number(state.session.expires_at_ms || 0) - 60000) return true;
      if (!state.session.refresh_token) {
        await signOut(false);
        return false;
      }
      try {
        const res = await fetch(`${state.config.supabase_url}/auth/v1/token?grant_type=refresh_token`, {
          method: "POST",
          headers: {"Content-Type": "application/json", "apikey": state.config.supabase_publishable_key},
          body: JSON.stringify({refresh_token: state.session.refresh_token})
        });
        if (!res.ok) throw new Error("Session expired.");
        saveSession(await res.json());
        return true;
      } catch {
        await signOut(false);
        return false;
      }
    }

    function renderSamples() {
      el("samples").innerHTML = samples.map(q => `<button class="sample">${escapeHtml(q)}</button>`).join("");
      document.querySelectorAll(".sample").forEach(node => node.addEventListener("click", () => {
        el("question").value = node.textContent;
        ask();
      }));
    }

    async function loadClientConfig() {
      const res = await fetch("/api/client-config", {cache: "no-store"});
      if (!res.ok) throw new Error("Could not load application configuration.");
      state.config = await res.json();
      state.workspaceId = state.config.default_workspace_id || "demo";
      setText("workspaceName", state.workspaceId);

      if (!isTeamMode()) {
        el("demoAccess").classList.remove("hidden");
        el("signInPanel").classList.add("hidden");
        el("userPanel").classList.add("hidden");
        el("historyPanel").classList.add("hidden");
        return;
      }

      el("demoAccess").classList.add("hidden");
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) {
        try { state.session = JSON.parse(saved); } catch { clearSession(); }
      }
      if (state.session && await ensureSession()) {
        try {
          await loadWorkspaces();
          return;
        } catch {
          clearSession();
        }
      }
      renderSignedOut();
    }

    function renderSignedOut(message = "") {
      el("signInPanel").classList.remove("hidden");
      el("userPanel").classList.add("hidden");
      el("historyPanel").classList.add("hidden");
      el("askBtn").disabled = true;
      setText("authStatus", message);
      el("documents").innerHTML = `<div class="empty">Sign in to view workspace documents.</div>`;
    }

    async function signIn(event) {
      event.preventDefault();
      el("signInBtn").disabled = true;
      setText("authStatus", "Signing in…");
      try {
        const res = await fetch(`${state.config.supabase_url}/auth/v1/token?grant_type=password`, {
          method: "POST",
          headers: {"Content-Type": "application/json", "apikey": state.config.supabase_publishable_key},
          body: JSON.stringify({email: el("email").value.trim(), password: el("password").value})
        });
        const payload = await res.json();
        if (!res.ok) throw new Error(payload.error_description || payload.msg || "Sign-in failed.");
        saveSession(payload);
        await loadWorkspaces();
        await refreshWorkspaceData();
      } catch (err) {
        clearSession();
        renderSignedOut(err.message);
      } finally {
        el("signInBtn").disabled = false;
      }
    }

    async function signOut(revoke = true) {
      if (revoke && state.session && state.session.access_token) {
        fetch(`${state.config.supabase_url}/auth/v1/logout`, {
          method: "POST",
          headers: {"apikey": state.config.supabase_publishable_key, "Authorization": `Bearer ${state.session.access_token}`}
        }).catch(() => {});
      }
      clearSession();
      renderSignedOut("Signed out.");
      resetAnswer();
    }

    async function loadWorkspaces() {
      const res = await fetch("/api/me/workspaces", {headers: await headers(), cache: "no-store"});
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not resolve workspace membership.");
      state.user = data;
      const workspaces = data.workspaces || [];
      if (!workspaces.length) throw new Error("This account has no GroundDesk workspace membership.");
      if (!workspaces.some(item => item.id === state.workspaceId)) state.workspaceId = workspaces[0].id;
      el("workspaceSelect").innerHTML = workspaces.map(
        item => `<option value="${escapeHtml(item.id)}" ${item.id === state.workspaceId ? "selected" : ""}>${escapeHtml(item.name)} (${escapeHtml(item.role)})</option>`
      ).join("");
      setText("userEmail", data.email || "Signed-in user");
      setText("workspaceName", state.workspaceId);
      el("signInPanel").classList.add("hidden");
      el("userPanel").classList.remove("hidden");
      el("historyPanel").classList.remove("hidden");
      el("askBtn").disabled = false;
    }

    async function loadHealth() {
      try {
        const res = await fetch("/api/health", {cache: "no-store"});
        const data = await res.json();
        lastHealth = data;
        setText("status", data.status || "ok");
        setText("docCount", isTeamMode() ? "Private" : (data.documents ?? "—"));
        setText("chunkCount", isTeamMode() ? "Private" : (data.chunks ?? "—"));
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
      if (isTeamMode() && !state.session) return;
      try {
        const res = await fetch("/api/documents", {headers: await headers(), cache: "no-store"});
        const docs = await res.json();
        if (!res.ok) throw new Error(docs.detail || "Could not load documents.");
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

    async function loadHistory() {
      if (!isTeamMode() || !state.session) return;
      try {
        const res = await fetch("/api/history", {headers: await headers(), cache: "no-store"});
        const history = await res.json();
        if (!res.ok) throw new Error(history.detail || "Could not load history.");
        state.history = Array.isArray(history) ? history : [];
        const latestThreads = [];
        const seen = new Set();
        state.history.forEach(item => {
          if (!seen.has(item.conversation_id)) {
            seen.add(item.conversation_id);
            latestThreads.push(item);
          }
        });
        if (!latestThreads.length) {
          el("history").innerHTML = `<div class="empty">No saved conversations yet.</div>`;
          return;
        }
        el("history").innerHTML = latestThreads.map(item => `
          <div class="thread ${item.conversation_id === state.conversationId ? "active" : ""}" data-conversation="${escapeHtml(item.conversation_id)}">
            <div class="thread-question">${escapeHtml(item.question || "Question")}</div>
            <div class="thread-meta">${item.needs_escalation ? "Escalated for review" : "Grounded answer returned"}</div>
          </div>`).join("");
        document.querySelectorAll(".thread").forEach(node => node.addEventListener("click", () => selectThread(node.dataset.conversation)));
      } catch (err) {
        el("history").innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
      }
    }

    function selectThread(conversationId) {
      const item = state.history.find(row => row.conversation_id === conversationId);
      if (!item) return;
      state.conversationId = conversationId;
      state.lastTraceId = item.trace_id;
      el("question").value = item.question || "";
      renderResponse(item);
      loadHistory();
    }

    function newThread() {
      state.conversationId = null;
      state.lastTraceId = null;
      el("question").value = "";
      resetAnswer();
      if (isTeamMode()) loadHistory();
    }

    async function loadBenchmark() {
      try {
        const res = await fetch("/api/benchmark/summary", {cache: "no-store"});
        const report = await res.json();
        if (!report.available || !report.reports || !report.reports.length) {
          el("benchmarkName").textContent = "No vetted report shipped";
          el("benchmarkValue").textContent = "—";
          el("benchmarkMeta").textContent = "Run the labelled benchmark and commit its reviewed report.";
          el("benchmarkGemini").textContent = "";
          return;
        }
        const full = report.reports.find(item => item.dataset && item.dataset.name === "nfcorpus") || report.reports[0];
        const preferred = full.runs.find(run => String(run.strategy).startsWith("hybrid")) || full.runs[0];
        const metrics = preferred.metrics || {};
        const hitRate = Math.round(Number(metrics["success@5"] || 0) * 1000) / 10;
        const mrr = Number(metrics["mrr@10"] || 0).toFixed(3);
        const dataset = full.dataset || {};
        el("benchmarkName").textContent = `${dataset.name || "Benchmark"} · ${preferred.strategy}`;
        el("benchmarkValue").textContent = `${hitRate}% hit@5`;
        el("benchmarkMeta").textContent = `${dataset.documents || "—"} docs · ${dataset.evaluated_queries || "—"} labelled queries · MRR@10 ${mrr}. Retrieval only; not answer accuracy.`;
        const gemini = report.reports.find(item => item.dataset && String(item.dataset.name).includes("gemini_slice"));
        if (gemini) {
          const geminiRun = gemini.runs.find(run => String(run.strategy).startsWith("hybrid")) || gemini.runs[0];
          const geminiHitRate = Math.round(Number(geminiRun.metrics["success@5"] || 0) * 1000) / 10;
          el("benchmarkGemini").textContent = `Gemini Embedding 2 verified on controlled slice: ${gemini.dataset.documents} docs · ${gemini.dataset.evaluated_queries} labelled queries · ${geminiHitRate}% hit@5.`;
        } else {
          el("benchmarkGemini").textContent = "";
        }
      } catch {
        el("benchmarkName").textContent = "Benchmark report unavailable";
        el("benchmarkValue").textContent = "—";
        el("benchmarkMeta").textContent = "";
        el("benchmarkGemini").textContent = "";
      }
    }

    async function ask() {
      if (isTeamMode() && !state.session) {
        setText("authStatus", "Sign in before asking questions in a team workspace.");
        return;
      }
      const question = el("question").value.trim();
      if (!question) return;
      el("askBtn").disabled = true;
      el("answer").textContent = "Retrieving evidence from Qdrant and generating an evidence-constrained answer…";
      el("citations").className = "empty";
      el("citations").textContent = "Retrieving citations…";
      try {
        const res = await fetch("/api/chat", {
          method:"POST",
          headers: await headers(true),
          body: JSON.stringify({
            question,
            conversation_id: state.conversationId,
            top_k: 5,
            draft_ticket_reply: el("ticket").checked
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        state.conversationId = data.conversation_id || state.conversationId;
        state.lastTraceId = data.trace_id;
        renderResponse(data);
        if (isTeamMode()) await loadHistory();
      } catch (err) {
        el("answer").textContent = `Error: ${err.message}`;
        el("citations").className = "empty";
        el("citations").textContent = "No citations returned.";
      } finally {
        el("askBtn").disabled = false;
      }
    }

    function renderResponse(data) {
      el("answer").textContent = cleanAnswer(data.answer || "No answer returned.");
      const evidenceLabels = {
        supported: "supported",
        limited: "limited",
        insufficient: "not found",
        clarification_needed: "needs clarification",
        unassessed: "unassessed"
      };
      const evidenceStatus = data.evidence_status || (data.needs_escalation ? "limited" : "supported");
      el("confidence").textContent = `Evidence support: ${evidenceLabels[evidenceStatus] || evidenceStatus}`;
      el("confidence").className = `metric ${evidenceStatus === "supported" && !data.needs_escalation ? "good" : "warn"}`;
      el("escalation").textContent = `Escalation: ${data.needs_escalation ? "yes" : "no"}`;
      el("escalation").className = `metric ${data.needs_escalation ? "warn" : "good"}`;
      el("trace").textContent = `Trace: ${data.trace_id || "—"}`;
      el("ticketReply").textContent = data.suggested_ticket_reply || "No support reply requested.";
      el("feedbackPanel").classList.remove("hidden");
      setText("feedbackStatus", "");
      if (data.citations && data.citations.length) {
        el("citations").className = "";
        el("citations").innerHTML = data.citations.map((c, i) => `<div class="citation"><div class="citation-title"><span>[${i + 1}] ${escapeHtml(c.title)}</span><span class="score">rank score ${Number(c.score || 0).toFixed(2)}</span></div><div class="snippet">${escapeHtml(c.snippet || "")}</div></div>`).join("");
      } else {
        el("citations").className = "empty";
        el("citations").textContent = "No citations returned. GroundDesk should escalate this instead of inventing an answer.";
      }
    }

    function resetAnswer() {
      el("answer").textContent = "Ready for a support question.";
      el("citations").className = "empty";
      el("citations").textContent = "Citations appear after generation.";
      el("ticketReply").textContent = "A paste-ready reply appears here when enabled.";
      setText("confidence", "Evidence support: —");
      setText("escalation", "Escalation: —");
      setText("trace", "Trace: —");
      el("feedbackPanel").classList.add("hidden");
    }

    async function sendFeedback(rating, feedbackType) {
      if (!state.lastTraceId) return;
      try {
        const res = await fetch("/api/feedback", {
          method: "POST",
          headers: await headers(true),
          body: JSON.stringify({trace_id: state.lastTraceId, rating, feedback_type: feedbackType})
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Feedback was not saved.");
        setText("feedbackStatus", "Feedback saved.");
      } catch (err) {
        setText("feedbackStatus", err.message);
      }
    }

    async function refreshWorkspaceData() {
      await loadDocuments();
      if (isTeamMode()) await loadHistory();
    }

    async function refreshAll() {
      await loadHealth();
      await loadBenchmark();
      if (!isTeamMode() || state.session) await refreshWorkspaceData();
    }
    function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c])); }
    function cleanAnswer(value) { return String(value).replace(/\{?\s*chunk_id\s*:\s*[^}\s]+(?:\s*\})?/gi, "").replace(/\s+([.,;:!?])/g, "$1").replace(/[ \t]{2,}/g, " ").trim(); }

    async function initialize() {
      renderSamples();
      try {
        await loadClientConfig();
      } catch (err) {
        el("healthAlert").style.display = "block";
        el("healthAlert").textContent = err.message;
      }
      await refreshAll();
    }

    initialize();
    setInterval(refreshAll, 15000);
    el("askBtn").addEventListener("click", ask);
    el("refreshBtn").addEventListener("click", refreshAll);
    el("signInPanel").addEventListener("submit", signIn);
    el("signOutBtn").addEventListener("click", () => signOut(true));
    el("workspaceSelect").addEventListener("change", async event => {
      state.workspaceId = event.target.value;
      state.conversationId = null;
      state.lastTraceId = null;
      setText("workspaceName", state.workspaceId);
      resetAnswer();
      await refreshWorkspaceData();
    });
    el("newThreadBtn").addEventListener("click", newThread);
    el("feedbackUp").addEventListener("click", () => sendFeedback(5, "helpful"));
    el("feedbackDown").addEventListener("click", () => sendFeedback(1, "needs_review"));
  </script>
</body>
</html>"""
