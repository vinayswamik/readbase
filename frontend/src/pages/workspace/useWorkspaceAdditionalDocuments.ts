import { useEffect, useState, type ChangeEvent } from "react";

import { isSessionExpiredMessage } from "../../api";
import type { HierarchyAssignableUser } from "../../types";
import {
  deleteAdditionalDocument,
  fetchAdditionalDocuments,
  fetchDocumentAssignableUsers,
  getAdditionalDocumentErrorMessage,
  sortAdditionalDocuments,
  updateAdditionalDocumentAccess,
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
  const [assignableUsers, setAssignableUsers] = useState<HierarchyAssignableUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [managedDocument, setManagedDocument] = useState<WorkspaceAdditionalDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    void Promise.all([
      fetchAdditionalDocuments(workspaceId),
      fetchDocumentAssignableUsers(workspaceId),
    ])
      .then(([nextDocuments, nextAssignableUsers]) => {
        if (!cancelled) {
          setDocuments(sortAdditionalDocuments(nextDocuments));
          setAssignableUsers(nextAssignableUsers);
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

  async function handleSaveAccess(assignedUserIds: string[]) {
    if (!managedDocument) {
      return;
    }

    setMutating(true);
    setError(null);
    try {
      const updatedDocument = await updateAdditionalDocumentAccess(
        workspaceId,
        managedDocument.document_id,
        assignedUserIds,
      );
      setDocuments((current) =>
        sortAdditionalDocuments(
          current.map((entry) =>
            entry.document_id === updatedDocument.document_id ? updatedDocument : entry,
          ),
        ),
      );
      setManagedDocument(updatedDocument);
    } catch (caughtError) {
      const message = getAdditionalDocumentErrorMessage(caughtError);
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    } finally {
      setMutating(false);
    }
  }

  async function handleDeleteManagedDocument(): Promise<boolean> {
    if (!managedDocument) {
      return false;
    }

    setMutating(true);
    setError(null);
    try {
      await deleteAdditionalDocument(workspaceId, managedDocument.document_id);
      setDocuments((current) =>
        current.filter((entry) => entry.document_id !== managedDocument.document_id),
      );
      setManagedDocument(null);
      return true;
    } catch (caughtError) {
      const message = getAdditionalDocumentErrorMessage(caughtError);
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
      return false;
    } finally {
      setMutating(false);
    }
  }

  function clearManagedDocument() {
    setManagedDocument(null);
  }

  return {
    acceptedDocumentTypes: ACCEPTED_DOCUMENT_TYPES,
    documents,
    assignableUsers,
    loading,
    uploading,
    mutating,
    managedDocument,
    setManagedDocument,
    clearManagedDocument,
    error,
    setError,
    handleFileChange,
    handleSaveAccess,
    handleDeleteManagedDocument,
  };
}
