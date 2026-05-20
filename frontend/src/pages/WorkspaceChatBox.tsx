import type { FormEvent, RefObject } from "react";

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
  onClose,
}: {
  messages: ChatMessage[];
  question: string;
  asking: boolean;
  canAsk: boolean;
  selectedRepo: IndexedRepo | null;
  messageEndRef: RefObject<HTMLDivElement | null>;
  onQuestionChange: (question: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
}) {
  return (
    <section className="chat-overlay" aria-label="Ask workspace">
      <header className="chat-overlay-header">
        <div>
          <h2>Ask</h2>
          <p>{selectedRepo ? repoLabel(selectedRepo) : "Select a repository first"}</p>
        </div>
        <button type="button" className="secondary-action-button" onClick={onClose}>
          Close
        </button>
      </header>
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
      <form className="ask-form overlay-ask-form" onSubmit={onSubmit}>
        <textarea
          rows={2}
          value={question}
          placeholder={selectedRepo ? `Ask about ${repoLabel(selectedRepo)}` : "Select a repository first"}
          required
          onChange={(event) => onQuestionChange(event.target.value)}
        />
        <button type="submit" disabled={!canAsk} className="primary-button">
          {asking ? "Thinking..." : "Ask"}
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
