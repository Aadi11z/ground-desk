const state = {
  config: null,
  session: null,
  user: null,
  workspaces: [],
  workspaceId: null,
  documents: [],
  selectedDocumentId: null,
};

const sessionStorageKey = "grounddesk-session";
const byId = (id) => document.getElementById(id);

function setHidden(id, hidden) {
  byId(id).hidden = hidden;
}

function authHeaders() {
  const headers = {};
  if (state.session?.access_token) {
    headers.Authorization = `Bearer ${state.session.access_token}`;
  }
  if (state.workspaceId) headers["X-Workspace-ID"] = state.workspaceId;
  return headers;
}

function showNotice(message, type = "error", target = "notice") {
  const notice = byId(target);
  notice.textContent = message;
  notice.className = `notice ${type}`;
  notice.hidden = false;
}

function clearNotice(target = "notice") {
  byId(target).hidden = true;
}

async function request(url, options = {}) {
  const headers = { ...authHeaders(), ...(options.headers || {}) };
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { message = (await response.json()).detail || message; } catch (_) { /* response was not JSON */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function persistSession(session) {
  state.session = session;
  localStorage.setItem(sessionStorageKey, JSON.stringify(session));
}

function clearSession() {
  state.session = null;
  state.user = null;
  state.workspaces = [];
  state.workspaceId = null;
  localStorage.removeItem(sessionStorageKey);
}

function selectAuthView(view) {
  document.querySelectorAll(".auth-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.authView === view);
  });
  byId("loginForm").hidden = view !== "login";
  byId("registerForm").hidden = view !== "register";
  clearNotice("authNotice");
}

function showAuthentication() {
  setHidden("authScreen", false);
  setHidden("onboardingScreen", true);
  setHidden("appShell", true);
  const demo = state.config?.auth_mode === "demo";
  byId("demoLogin").hidden = !demo;
  byId("loginForm").querySelectorAll("input, button[type=submit]").forEach((element) => {
    element.disabled = demo;
  });
  byId("registerForm").querySelectorAll("input, button[type=submit]").forEach((element) => {
    element.disabled = demo;
  });
  if (demo) {
    const user = state.config.demo_user;
    showNotice(
      `Local demo: continue as ${user.display_name} (${user.email}). Workspace registration is available when Supabase is configured.`,
      "success",
      "authNotice",
    );
  }
}

function showOnboarding({ additional = false } = {}) {
  setHidden("authScreen", true);
  setHidden("onboardingScreen", false);
  setHidden("appShell", true);
  byId("onboarding-title").textContent = additional
    ? "Create another company workspace."
    : "Create your first workspace.";
  byId("onboardingCancel").hidden = !additional;
  byId("onboardingLogout").hidden = additional;
  byId("onboardingName").value = state.user?.display_name || "";
  byId("onboardingOrganization").value = "";
  byId("onboardingWorkspace").value = "";
  clearNotice("onboardingNotice");
}

function enterProduct() {
  setHidden("authScreen", true);
  setHidden("onboardingScreen", true);
  setHidden("appShell", false);
  byId("profileName").textContent = state.user?.display_name || "GroundDesk user";
  byId("profileEmail").textContent = state.user?.email || "";
  byId("newWorkspaceButton").hidden = state.config?.auth_mode !== "supabase";
  renderWorkspaceSelect();
  selectView("ask");
  loadDocuments();
}

function renderWorkspaceSelect() {
  const select = byId("workspaceSelect");
  select.replaceChildren();
  state.workspaces.forEach((workspace) => {
    const option = document.createElement("option");
    option.value = workspace.id;
    option.textContent = workspace.name;
    option.selected = workspace.id === state.workspaceId;
    select.append(option);
  });
}

async function loadIdentity() {
  const identity = await request("/api/me");
  state.user = identity.user;
  state.workspaces = identity.workspaces;
  const savedWorkspace = localStorage.getItem("grounddesk-workspace");
  state.workspaceId = state.workspaces.some((workspace) => workspace.id === savedWorkspace)
    ? savedWorkspace
    : state.workspaces[0]?.id || null;
  if (!state.workspaceId) {
    showOnboarding();
    return;
  }
  enterProduct();
}

function authBaseUrl(path) {
  return `${state.config.supabase_url.replace(/\/$/, "")}${path}`;
}

async function supabaseAuth(path, body) {
  const response = await fetch(authBaseUrl(path), {
    method: "POST",
    headers: {
      apikey: state.config.supabase_publishable_key,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.msg || payload.error_description || payload.message || "Authentication failed.");
  return payload;
}

async function completeOnboarding({ displayName, organizationName, workspaceName }) {
  const result = await request("/api/onboarding", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      display_name: displayName || null,
      organization_name: organizationName,
      workspace_name: workspaceName,
    }),
  });
  await loadIdentity();
  state.workspaceId = result.workspace.id;
  localStorage.setItem("grounddesk-workspace", state.workspaceId);
  renderWorkspaceSelect();
  await loadDocuments();
  showNotice(`${result.workspace.name} is ready.`, "success");
}

function selectView(viewName) {
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === viewName);
  });
  if (viewName === "documents") loadDocuments();
  if (viewName === "history") loadHistory();
}

function renderDocuments() {
  const list = byId("documentList");
  list.replaceChildren();
  if (!state.documents.length) {
    list.textContent = "No documents yet.";
    return;
  }
  state.documents.forEach((documentRecord) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `document-item${documentRecord.document_id === state.selectedDocumentId ? " selected" : ""}`;
    const title = document.createElement("strong");
    title.textContent = documentRecord.title;
    const meta = document.createElement("small");
    meta.textContent = `${documentRecord.chunks_indexed} chunks · ${documentRecord.status}`;
    item.append(title, meta);
    item.addEventListener("click", () => previewDocument(documentRecord.document_id));
    list.append(item);
  });
}

async function loadDocuments() {
  clearNotice();
  try {
    state.documents = await request("/api/documents");
    renderDocuments();
  } catch (error) {
    showNotice(error.message);
  }
}

async function previewDocument(documentId) {
  clearNotice();
  try {
    const preview = await request(`/api/documents/${encodeURIComponent(documentId)}/preview`);
    state.selectedDocumentId = documentId;
    byId("documentPreview").textContent = preview.text || "No extracted text is available.";
    byId("previewMeta").textContent = `${preview.original_filename || preview.title}${preview.truncated ? " · preview shortened" : ""}`;
    renderDocuments();
  } catch (error) {
    showNotice(error.message);
  }
}

function addMessage(kind, label, text, citations = []) {
  const messages = byId("chatMessages");
  messages.querySelector(".empty-state")?.remove();
  const message = document.createElement("article");
  message.className = `message ${kind}`;
  const heading = document.createElement("strong");
  heading.textContent = label;
  const body = document.createElement("div");
  body.textContent = text;
  message.append(heading, body);
  if (citations.length) {
    const list = document.createElement("ul");
    list.className = "citations";
    citations.forEach((citation) => {
      const item = document.createElement("li");
      item.textContent = citation.title;
      list.append(item);
    });
    message.append(list);
  }
  messages.append(message);
  message.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

async function loadHistory() {
  const list = byId("historyList");
  list.replaceChildren();
  try {
    const history = await request("/api/history");
    if (!history.length) {
      list.textContent = "No conversations yet.";
      return;
    }
    history.forEach((entry) => {
      const item = document.createElement("article");
      item.className = "history-item";
      const question = document.createElement("strong");
      question.textContent = entry.question;
      const answer = document.createElement("p");
      answer.textContent = entry.answer;
      item.append(question, answer);
      list.append(item);
    });
  } catch (error) {
    showNotice(error.message);
  }
}

document.querySelectorAll(".auth-tab").forEach((button) => {
  button.addEventListener("click", () => selectAuthView(button.dataset.authView));
});
document.querySelectorAll(".nav-link").forEach((button) => {
  button.addEventListener("click", () => selectView(button.dataset.view));
});

byId("demoLogin").addEventListener("click", async () => {
  try {
    persistSession(await request("/api/auth/demo-session", { method: "POST" }));
    await loadIdentity();
  } catch (error) {
    showNotice(error.message, "error", "authNotice");
  }
});

byId("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const session = await supabaseAuth("/auth/v1/token?grant_type=password", {
      email: byId("loginEmail").value,
      password: byId("loginPassword").value,
    });
    persistSession(session);
    await loadIdentity();
  } catch (error) {
    showNotice(error.message, "error", "authNotice");
  }
});

byId("registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = {
    displayName: byId("registerName").value.trim(),
    email: byId("registerEmail").value.trim(),
    password: byId("registerPassword").value,
    organizationName: byId("organizationName").value.trim(),
    workspaceName: byId("workspaceName").value.trim(),
  };
  try {
    const response = await supabaseAuth("/auth/v1/signup", {
      email: values.email,
      password: values.password,
      data: { display_name: values.displayName },
      options: { emailRedirectTo: window.location.origin },
    });
    if (!response.access_token) {
      showNotice("Check your email to confirm your account, then log in to create the workspace.", "success", "authNotice");
      selectAuthView("login");
      return;
    }
    persistSession(response);
    await completeOnboarding(values);
  } catch (error) {
    showNotice(error.message, "error", "authNotice");
  }
});

byId("onboardingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await completeOnboarding({
      displayName: byId("onboardingName").value.trim(),
      organizationName: byId("onboardingOrganization").value.trim(),
      workspaceName: byId("onboardingWorkspace").value.trim(),
    });
  } catch (error) {
    showNotice(error.message, "error", "onboardingNotice");
  }
});

function logout() {
  clearSession();
  showAuthentication();
}

byId("logoutButton").addEventListener("click", logout);
byId("onboardingLogout").addEventListener("click", logout);
byId("onboardingCancel").addEventListener("click", enterProduct);
byId("newWorkspaceButton").addEventListener("click", () => {
  showOnboarding({ additional: true });
});
byId("workspaceSelect").addEventListener("change", (event) => {
  state.workspaceId = event.target.value;
  state.selectedDocumentId = null;
  localStorage.setItem("grounddesk-workspace", state.workspaceId);
  byId("documentPreview").textContent = "Select a document to view its extracted text.";
  byId("previewMeta").textContent = "";
  loadDocuments();
});
byId("refreshDocuments").addEventListener("click", loadDocuments);

byId("uploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = byId("documentFile").files[0];
  if (!file) return;
  clearNotice();
  const data = new FormData();
  data.append("file", file);
  try {
    const result = await request("/api/documents", { method: "POST", body: data });
    byId("uploadForm").reset();
    showNotice(`${file.name} indexed (${result.chunks_indexed} chunks).`, "success");
    await loadDocuments();
    await previewDocument(result.document_id);
  } catch (error) {
    showNotice(error.message);
  }
});

byId("chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = byId("question").value.trim();
  if (!question) return;
  clearNotice();
  addMessage("question", "You", question);
  byId("question").value = "";
  try {
    const answer = await request("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    addMessage(answer.needs_escalation ? "answer escalation" : "answer", answer.needs_escalation ? "Needs escalation" : "GroundDesk", answer.answer, answer.citations);
  } catch (error) {
    showNotice(error.message);
  }
});

async function initialize() {
  try {
    state.config = await fetch("/api/client-config").then((response) => response.json());
    const saved = localStorage.getItem(sessionStorageKey);
    if (!saved) {
      showAuthentication();
      return;
    }
    state.session = JSON.parse(saved);
    await loadIdentity();
  } catch (_) {
    clearSession();
    showAuthentication();
  }
}

initialize();
