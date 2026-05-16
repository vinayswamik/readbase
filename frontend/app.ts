// This file is the frontend source of truth. TypeScript lets us describe the
// shapes of API responses, then the compiler turns this into static/app.js for
// the browser.

// Types aligned with the Python API: repo catalog, ask responses, and citation snippets.

// Labels chat bubbles as either the user question or the model reply.
type MessageRole = "user" | "assistant";

// Which repo is selected for Q&A and what the server reports as indexed.
interface AppState {
  repoId: string | null;
  repos: IndexedRepo[];
}

// One row from GET /api/repos (or shared fields on index responses).
interface IndexedRepo {
  repo_id: string;
  repo_url: string;
  file_count: number;
  chunk_count: number;
}

// POST /api/index success body: adds local clone path to IndexedRepo fields.
interface IndexResponse extends IndexedRepo {
  repo_path: string;
}

// GET /api/repos JSON envelope: { repos: [...] }.
interface ReposResponse {
  repos: IndexedRepo[];
}

// One retrieved chunk shown as a citation under an assistant message.
interface SourceMatch {
  score: number;
  id: string;
  path: string;
  start_line: number;
  end_line: number;
  text: string;
}

// POST /api/ask success: answer, backend mode string, and optional source list.
interface AskResponse {
  repo_id: string;
  question: string;
  answer: string;
  mode: string;
  sources: SourceMatch[];
}

// Optional API error field merged when parsing non-2xx or explicit error JSON.
interface ApiErrorResponse {
  error?: string;
}

// In-memory UI state shared across handlers (selection + last fetched repo list).
// This state is not saved to disk; the server owns the real indexes under .readbase/.
const state: AppState = {
  repoId: null,
  repos: [],
};

// Required DOM nodes: throws on startup if index.html and ids drift apart.
const indexForm = mustQuery<HTMLFormElement>("#indexForm");
const repoUrlInput = mustQuery<HTMLInputElement>("#repoUrl");
const refreshRepoInput = mustQuery<HTMLInputElement>("#refreshRepo");
const indexButton = mustQuery<HTMLButtonElement>("#indexButton");
const repoStatus = mustQuery<HTMLElement>("#repoStatus");
const repoList = mustQuery<HTMLElement>("#repoList");
const askForm = mustQuery<HTMLFormElement>("#askForm");
const questionInput = mustQuery<HTMLTextAreaElement>("#question");
const askButton = mustQuery<HTMLButtonElement>("#askButton");
const messages = mustQuery<HTMLElement>("#messages");
const llmMode = mustQuery<HTMLElement>("#llmMode");

// Clone or re-index a repo URL: POST /api/index, then refresh sidebar and ask controls.
indexForm.addEventListener("submit", async (event: SubmitEvent) => {
  // Browser forms normally reload the page. preventDefault keeps this as an
  // app-like interaction where JavaScript calls the backend with fetch().
  event.preventDefault();
  const repoUrl = repoUrlInput.value.trim();
  if (!repoUrl) return;

  // Disable the button during cloning/indexing so duplicate requests are less likely.
  setBusy(indexButton, true, "Indexing...");
  repoStatus.textContent = "Cloning and indexing repository. This can take a minute.";
  try {
    // Generic syntax: postJson<RequestShape, ResponseShape>(...). This lets
    // TypeScript check we pass and read the expected fields.
    const result = await postJson<
      { repo_url: string; refresh: boolean },
      IndexResponse
    >("/api/index", {
      repo_url: repoUrl,
      refresh: refreshRepoInput.checked,
    });
    state.repoId = result.repo_id;
    repoStatus.textContent = `${result.file_count} files indexed into ${result.chunk_count} chunks.`;
    await loadRepos();
    updateAskState();
  } catch (error) {
    repoStatus.textContent = getErrorMessage(error);
  } finally {
    setBusy(indexButton, false, "Index repository");
  }
});

// Ask against the selected repo: append user bubble, POST /api/ask, append assistant + sources.
askForm.addEventListener("submit", async (event: SubmitEvent) => {
  // Same form behavior as indexing: stay on the page and call our JSON API.
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || !state.repoId) return;

  // Optimistic UI: show the user's question immediately before the backend responds.
  appendMessage("user", question);
  questionInput.value = "";
  setBusy(askButton, true, "Thinking...");

  try {
    const result = await postJson<
      { repo_id: string; question: string; top_k: number },
      AskResponse
    >("/api/ask", {
      repo_id: state.repoId,
      question,
      top_k: 8,
    });
    llmMode.textContent = result.mode;
    // mode controls source rendering: full chunks for retrieval fallback,
    // compact citations when Anthropic produced the answer.
    appendMessage("assistant", result.answer, result.sources, result.mode);
  } catch (error) {
    appendMessage("assistant", getErrorMessage(error));
  } finally {
    setBusy(askButton, false, "Ask");
    updateAskState();
  }
});

// Re-evaluate whether Ask should be enabled whenever the question text changes.
questionInput.addEventListener("input", updateAskState);

// Fetch indexed repos from the server; default selection to first row if nothing picked yet.
async function loadRepos(): Promise<void> {
  try {
    const result = await fetchJson<ReposResponse>("/api/repos");
    state.repos = result.repos || [];
    if (!state.repoId && state.repos.length) {
      state.repoId = state.repos[0].repo_id;
    }
    renderRepos();
    updateAskState();
  } catch (error) {
    repoList.textContent = getErrorMessage(error);
  }
}

// Rebuild the sidebar repo buttons from state; clicking one updates selection and URL field.
function renderRepos(): void {
  repoList.innerHTML = "";
  if (!state.repos.length) {
    repoList.textContent = "No indexed repositories yet.";
    return;
  }

  for (const repo of state.repos) {
    // A button is used instead of a plain div so keyboard users can select repos.
    const button = document.createElement("button");
    button.type = "button";
    button.className = `repo-item${repo.repo_id === state.repoId ? " active" : ""}`;
    button.addEventListener("click", () => {
      state.repoId = repo.repo_id;
      repoUrlInput.value = repo.repo_url;
      repoStatus.textContent = `${repo.file_count} files indexed into ${repo.chunk_count} chunks.`;
      renderRepos();
      updateAskState();
    });

    const url = document.createElement("span");
    url.className = "repo-url";
    url.textContent = repo.repo_url;

    const meta = document.createElement("span");
    meta.className = "repo-meta";
    meta.textContent = `${repo.file_count} files, ${repo.chunk_count} chunks`;

    button.append(url, meta);
    repoList.append(button);
  }
}

// Append a chat row; assistant answers may attach up to four source previews below the text.
function appendMessage(
  role: MessageRole,
  text: string,
  sources: SourceMatch[] = [],
  mode = "retrieval",
): void {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const body = document.createElement("div");
  body.className = "message-body";
  // textContent is safer than innerHTML because model output should be displayed
  // as text, not executed/interpreted as HTML.
  body.textContent = text;

  if (sources.length) {
    const sourceList = document.createElement("div");
    sourceList.className = "sources";
    for (const source of sources.slice(0, 4)) {
      sourceList.append(renderSource(source, mode));
    }
    body.append(sourceList);
  }

  article.append(body);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

// Render one citation: path/line range + score; full snippet unless mode is compact Anthropic UI.
function renderSource(source: SourceMatch, mode: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = `source${mode === "anthropic" ? " compact" : ""}`;

  const title = document.createElement("div");
  title.className = "source-title";
  title.textContent = `${source.path}:${source.start_line}-${source.end_line} · score ${source.score}`;

  if (mode === "anthropic") {
    wrapper.append(title);
    return wrapper;
  }

  const pre = document.createElement("pre");
  pre.textContent = source.text;

  wrapper.append(title, pre);
  return wrapper;
}

// Ask stays disabled until a repo is selected and the question is non-empty.
function updateAskState(): void {
  askButton.disabled = !state.repoId || !questionInput.value.trim();
}

// During async work, lock the button and swap its label for progress text.
function setBusy(button: HTMLButtonElement, busy: boolean, label: string): void {
  button.disabled = busy;
  button.textContent = label;
}

// POST helper: JSON body, JSON parse, unified error handling via parseJsonResponse.
async function postJson<TRequest, TResponse>(
  url: string,
  body: TRequest,
): Promise<TResponse> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJsonResponse<TResponse>(response);
}

// GET helper: same parse path as POST for consistent error surfacing.
async function fetchJson<TResponse>(url: string): Promise<TResponse> {
  const response = await fetch(url);
  return parseJsonResponse<TResponse>(response);
}

// Read JSON and fail if HTTP not ok or server returned an { error } string in the body.
async function parseJsonResponse<TResponse>(response: Response): Promise<TResponse> {
  // We assume our own backend always returns JSON for API routes.
  const payload = (await response.json()) as TResponse & ApiErrorResponse;
  if (!response.ok || payload.error) {
    throw new Error(payload.error || `Request failed with ${response.status}`);
  }
  return payload;
}

// Typed querySelector that guarantees the element exists (startup invariant).
function mustQuery<T extends HTMLElement>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }
  return element;
}

// Turn thrown values from fetch/parse into a single string for status or chat bubbles.
function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error.";
}

// Initial load: populate sidebar from server so the page is usable without indexing first.
loadRepos();
