import { useRef, useState, type ChangeEvent, type PointerEvent as ReactPointerEvent, type ReactNode, type RefObject, type SyntheticEvent } from "react";

import chartIconMarkup from "../assets/icons/chart.svg?raw";

import type { ChatMessage, IndexedRepo, SourceMatch } from "../types";

export function WorkspaceChatBox({
  messages,
  question,
  asking,
  canAsk,
  selectedRepo,
  messageEndRef,
  onQuestionChange,
  onSubmit,
  graphOpen,
  onToggleGraph,
  acceptedDocumentTypes,
  onUploadDocument,
  children,
}: {
  messages: ChatMessage[];
  question: string;
  asking: boolean;
  canAsk: boolean;
  selectedRepo: IndexedRepo | null;
  messageEndRef: RefObject<HTMLDivElement | null>;
  onQuestionChange: (question: string) => void;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  graphOpen: boolean;
  onToggleGraph: () => void;
  acceptedDocumentTypes: string;
  onUploadDocument: (event: ChangeEvent<HTMLInputElement>) => void;
  children?: ReactNode;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [togglePressed, setTogglePressed] = useState(false);
  const toggleEngagedRef = useRef(false);

  function handleAddSourcesClick() {
    fileInputRef.current?.click();
  }

  return (
    <section className="chat-panel" aria-label="Ask workspace">
      <div className="chat-panel-body">
        <div className="overlay-messages">
          {messages.length ? (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          ) : (
            <article className="message assistant">
              <div className="message-body empty-message">No questions yet.</div>
            </article>
          )}
          <div ref={messageEndRef} />
        </div>
        {children}
      </div>
      <form className="chat-panel-bar" onSubmit={onSubmit}>
        <div className="chat-panel-bar-actions">
          <button
            type="button"
            className="secondary-action-button"
            aria-label="History"
            title="History"
          >
            <HistoryIcon />
          </button>
          <button
            type="button"
            className="secondary-action-button"
            aria-label="Add sources"
            title="Add sources"
            onClick={handleAddSourcesClick}
          >
            <PlusIcon />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptedDocumentTypes}
            multiple
            hidden
            onChange={onUploadDocument}
          />
        </div>
        <div className="chat-panel-bar-input">
          <textarea
            rows={2}
            value={question}
            placeholder={selectedRepo ? `Ask about ${repoLabel(selectedRepo)}` : "Ask across workspace sources"}
            required
            onChange={(event) => onQuestionChange(event.target.value)}
          />
          <button type="submit" disabled={!canAsk} className="primary-button">
            {asking ? "Thinking..." : "Ask"}
          </button>
        </div>
        <button
          type="button"
          className={`chat-panel-bar-toggle${togglePressed ? " is-pressed" : ""}`}
          onPointerDown={(event) => {
            if (event.button !== 0) {
              return;
            }
            toggleEngagedRef.current = true;
            setTogglePressed(true);
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerUp={(event) => {
            if (event.button !== 0) {
              return;
            }
            const engaged = toggleEngagedRef.current;
            toggleEngagedRef.current = false;
            setTogglePressed(false);
            if (!engaged) {
              return;
            }
            event.preventDefault();
            onToggleGraph();
          }}
          onPointerCancel={() => {
            toggleEngagedRef.current = false;
            setTogglePressed(false);
          }}
          aria-pressed={graphOpen}
          aria-label="Chart"
          data-tooltip="Chart"
        >
          <ChartIcon />
        </button>
      </form>
    </section>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="message-body">
        {message.text}
        <SourceList sources={message.sources || []} mode={message.mode || "retrieval"} />
      </div>
    </article>
  );
}

function SourceList({ sources, mode }: { sources: SourceMatch[]; mode: string }) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="sources">
      {sources.slice(0, 4).map((source) => (
        <div
          key={source.id}
          className={`source${mode === "anthropic" ? " compact" : ""}`}
        >
          <div className="source-title">
            {source.source_type === "jira" && source.issue_key ? `${source.issue_key} · ` : ""}
            {source.source_type === "slack" && source.channel_name ? `#${source.channel_name} · ` : ""}
            {source.path}:{source.start_line}-{source.end_line} · score{" "}
            {formatScore(source.score)}
          </div>
          {mode !== "anthropic" ? <pre>{source.text}</pre> : null}
        </div>
      ))}
    </div>
  );
}

function repoLabel(repo: IndexedRepo): string {
  return repo.repo_url.replace(/^https?:\/\/github\.com\//, "");
}

function formatScore(score: number): string {
  return Number.isFinite(score) ? score.toFixed(3) : String(score);
}

function HistoryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" focusable="false" aria-hidden="true">
      <path
        d="M12 8v4l3 2"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3.05 11A9 9 0 1 1 6 18.7"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3 4v4h4"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" focusable="false" aria-hidden="true">
      <path
        d="M12 5v14M5 12h14"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChartIcon() {
  return (
    <span
      className="chat-panel-bar-toggle-icon"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: chartIconMarkup }}
    />
  );
}
