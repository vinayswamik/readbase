import { useRef, type ChangeEvent } from "react";

import type { WorkspaceAdditionalDocument } from "./workspaceAdditionalDocuments";

export function WorkspaceAdditionalDocumentsSection({
  documents,
  loading,
  uploading,
  error,
  acceptedDocumentTypes,
  onFileChange,
}: {
  documents: WorkspaceAdditionalDocument[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
  acceptedDocumentTypes: string;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleAddClick() {
    if (uploading) {
      return;
    }
    fileInputRef.current?.click();
  }

  return (
    <section
      className="workspace-sources-documents"
      aria-labelledby="workspace-sources-documents-heading"
    >
      <div className="workspace-sources-documents-header">
        <h3 id="workspace-sources-documents-heading">Additional documents</h3>
        <button
          type="button"
          className="workspace-sources-documents-add"
          aria-label="Upload document"
          disabled={uploading}
          onClick={handleAddClick}
        >
          <PlusIcon />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="workspace-sources-documents-input"
          accept={acceptedDocumentTypes}
          aria-hidden="true"
          tabIndex={-1}
          onChange={(event) => void onFileChange(event)}
        />
      </div>
      {error ? (
        <p className="workspace-sources-documents-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="workspace-sources-documents-list" aria-busy={loading || uploading}>
        {loading ? (
          <p className="workspace-sources-documents-empty">Loading documents...</p>
        ) : documents.length === 0 ? (
          <p className="workspace-sources-documents-empty">
            Upload PDFs, notes, or specs to include them in workspace answers.
          </p>
        ) : (
          <div className="workspace-sources-documents-rows">
            {documents.map((document) => (
              <section
                className="workspace-sources-holder workspace-sources-document-holder"
                key={document.document_id}
              >
                <div className="workspace-sources-holder-header">
                  <div className="workspace-sources-holder-leading">
                    <DocumentRowIcon />
                    <span className="workspace-sources-holder-name" title={document.name}>
                      {document.name}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="home-connection-state connected workspace-sources-manage"
                    aria-label={`Manage ${document.name}`}
                    disabled={uploading}
                  >
                    <span>Manage</span>
                    <span className="home-manage-arrow" aria-hidden="true">
                      <svg viewBox="0 0 16 16" focusable="false">
                        <path d="M5 4h7v7" />
                        <path d="m4 12 8-8" />
                      </svg>
                    </span>
                  </button>
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M12 5v14M5 12h14"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

function DocumentRowIcon() {
  return (
    <span className="workspace-sources-document-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path
          d="M8 4.5h5.2L17 8.3V19.5A1.5 1.5 0 0 1 15.5 21h-9A1.5 1.5 0 0 1 5 19.5v-15A1.5 1.5 0 0 1 6.5 3H8v1.5z"
          fill="none"
          stroke="currentColor"
          strokeLinejoin="round"
          strokeWidth="1.75"
        />
        <path
          d="M13 4.5V9h4.5"
          fill="none"
          stroke="currentColor"
          strokeLinejoin="round"
          strokeWidth="1.75"
        />
      </svg>
    </span>
  );
}
