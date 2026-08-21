import {
  useEffect,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from "react";

import {
  askQuestion,
  getDocuments,
  uploadDocument,
} from "../api";
import type { DocumentRecord, Identity } from "../types";
import { Notice } from "./Notice";

type Screen = "ask" | "documents";
type ProductScreenProps = {
  identity: Identity;
  workspaceId: string;
  setWorkspaceId: Dispatch<SetStateAction<string>>;
  accessToken: string;
  onLogout: () => void;
  notice: string | null;
  setNotice: Dispatch<SetStateAction<string | null>>;
};

const screens: Array<{ id: Screen; label: string }> = [
  { id: "ask", label: "Ask" },
  { id: "documents", label: "Documents" },
];

export function ProductScreen(props: ProductScreenProps) {
  const { accessToken, workspaceId, setNotice } = props;
  const [screen, setScreen] = useState<Screen>("ask");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);

  useEffect(() => {
    if (screen === "documents") {
      getDocuments(accessToken, workspaceId).then(setDocuments).catch(showError);
    }

    function showError(error: Error) {
      setNotice(error.message);
    }
  }, [accessToken, screen, setNotice, workspaceId]);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await askQuestion(accessToken, workspaceId, question);
      setAnswer(response.answer);
      setQuestion("");
    } catch (error) {
      setNotice(errorMessage(error, "Unable to answer."));
    }
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = new FormData(event.currentTarget).get("file");
    if (!(file instanceof File)) return;

    try {
      await uploadDocument(accessToken, workspaceId, file);
      event.currentTarget.reset();
      setDocuments(await getDocuments(accessToken, workspaceId));
    } catch (error) {
      setNotice(errorMessage(error, "Unable to upload the document."));
    }
  }

  return (
    <main className="shell">
      <Sidebar {...props} screen={screen} setScreen={setScreen} />
      <section className="content">
        <Notice value={props.notice} />
        {screen === "ask" && (
          <AskPanel
            answer={answer}
            question={question}
            setQuestion={setQuestion}
            onSubmit={submitQuestion}
          />
        )}
        {screen === "documents" && (
          <DocumentsPanel
            documents={documents}
            onUpload={submitUpload}
          />
        )}
      </section>
    </main>
  );
}

type SidebarProps = Pick<
  ProductScreenProps,
  "identity" | "workspaceId" | "setWorkspaceId" | "onLogout"
> & {
  screen: Screen;
  setScreen: Dispatch<SetStateAction<Screen>>;
};

function Sidebar({
  identity,
  workspaceId,
  setWorkspaceId,
  screen,
  setScreen,
  onLogout,
}: SidebarProps) {
  return (
    <aside>
      <div className="brand">
        <i />GroundDesk
      </div>
      <small>{identity.user.display_name ?? identity.user.email}</small>
      <select
        value={workspaceId}
        onChange={(event) => setWorkspaceId(event.target.value)}
      >
        {identity.workspaces.map((workspace) => (
          <option value={workspace.id} key={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </select>
      <nav>
        {screens.map(({ id, label }) => (
          <button
            className={screen === id ? "active" : ""}
            onClick={() => setScreen(id)}
            key={id}
          >
            {label}
          </button>
        ))}
      </nav>
      <button className="plain" onClick={onLogout}>
        Log out
      </button>
    </aside>
  );
}

type AskPanelProps = {
  answer: string | null;
  question: string;
  setQuestion: Dispatch<SetStateAction<string>>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

function AskPanel({ answer, question, setQuestion, onSubmit }: AskPanelProps) {
  return (
    <>
      <p className="eyebrow">Support assistant</p>
      <h1>Ask your documents</h1>
      {answer && <article className="panel">{answer}</article>}
      <form className="form" onSubmit={onSubmit}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about your documents…"
          required
        />
        <button className="primary">Send question</button>
      </form>
    </>
  );
}

type DocumentsPanelProps = {
  documents: DocumentRecord[];
  onUpload: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

function DocumentsPanel({
  documents,
  onUpload,
}: DocumentsPanelProps) {
  return (
    <>
      <p className="eyebrow">Knowledge base</p>
      <h1>Documents</h1>
      <form className="form" onSubmit={onUpload}>
        <input
          name="file"
          type="file"
          accept=".md,.markdown,.txt,.pdf"
          required
        />
        <button className="primary">Upload document</button>
      </form>
      {documents.map((document) => (
        <article className="panel" key={document.document_id}>
          <strong>{document.title}</strong>
          <small>
            {document.chunks_indexed} chunks · {document.status}
          </small>
        </article>
      ))}
    </>
  );
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
