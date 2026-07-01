import { useEffect, useState, type ChangeEvent } from "react";

import { isSessionExpiredMessage } from "../../api";
import {
  fetchAdditionalDocuments,
  getAdditionalDocumentErrorMessage,
  sortAdditionalDocuments,
  uploadAdditionalDocument,
  validateAdditionalDocumentFile,
  type WorkspaceAdditionalDocument,
} from "./workspaceAdditionalDocuments";

const ACCEPTED_DOCUMENT_TYPES = ".pdf,.txt,.md,.doc,.docx,.csv,.rtf";

export function useWorkspaceAdditionalDocuments({
  workspaceId,
  refreshKey = 0,
  onSessionExpired,
}: {
  workspaceId: string;
  refreshKey?: number;
  onSessionExpired: () => void;
}) {
  const [documents, setDocuments] = useState<WorkspaceAdditionalDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    void fetchAdditionalDocuments(workspaceId)
      .then((nextDocuments) => {
        if (!cancelled) {
          setDocuments(sortAdditionalDocuments(nextDocuments));
        }
      })
      .catch((caughtError) => {
        if (cancelled) {
          return;
        }
        const message = getAdditionalDocumentErrorMessage(caughtError);
        setError(message);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [onSessionExpired, refreshKey, workspaceId]);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    const validationError = validateAdditionalDocumentFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const document = await uploadAdditionalDocument(workspaceId, file);
      setDocuments((current) => sortAdditionalDocuments([...current, document]));
    } catch (caughtError) {
      const message = getAdditionalDocumentErrorMessage(caughtError);
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    } finally {
      setUploading(false);
    }
  }

  return {
    acceptedDocumentTypes: ACCEPTED_DOCUMENT_TYPES,
    documents,
    loading,
    uploading,
    error,
    setError,
    handleFileChange,
  };
}
