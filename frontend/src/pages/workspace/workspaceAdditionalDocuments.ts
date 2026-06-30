import { deleteJson, fetchJson, getErrorMessage, patchJson, postJson } from "../../api";
import type { HierarchyAssignableUser, HierarchyGraphResponse } from "../../types";

export type WorkspaceAdditionalDocument = {
  document_id: string;
  name: string;
  created_at: string;
  uploaded_by_user_id: string | null;
  assigned_user_ids: string[];
};

export type WorkspaceAdditionalDocumentsResponse = {
  documents: WorkspaceAdditionalDocument[];
};

export type UpdateAdditionalDocumentAccessRequest = {
  assigned_user_ids: string[];
};

const ALLOWED_EXTENSIONS = new Set([
  ".pdf",
  ".txt",
  ".md",
  ".doc",
  ".docx",
  ".csv",
  ".rtf",
]);
const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;

export function validateAdditionalDocumentFile(file: File): string | null {
  const trimmedName = file.name.trim();
  if (!trimmedName) {
    return "Choose a document to upload.";
  }
  const extension = trimmedName.includes(".")
    ? trimmedName.slice(trimmedName.lastIndexOf(".")).toLowerCase()
    : "";
  if (!ALLOWED_EXTENSIONS.has(extension)) {
    return "Upload a PDF, text, Markdown, Word, CSV, or RTF file.";
  }
  if (file.size <= 0) {
    return "The selected file is empty.";
  }
  if (file.size > MAX_DOCUMENT_BYTES) {
    return "Documents must be 10 MB or smaller.";
  }
  return null;
}

export async function fetchAdditionalDocuments(
  workspaceId: string,
): Promise<WorkspaceAdditionalDocument[]> {
  const response = await fetchJson<WorkspaceAdditionalDocumentsResponse>(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/documents`,
  );
  return response.documents.map(normalizeAdditionalDocument);
}

export async function fetchDocumentAssignableUsers(
  workspaceId: string,
): Promise<HierarchyAssignableUser[]> {
  const response = await fetchJson<HierarchyGraphResponse>(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/graph`,
  );
  return response.assignable_users ?? [];
}

export async function uploadAdditionalDocument(
  workspaceId: string,
  file: File,
): Promise<WorkspaceAdditionalDocument> {
  const validationError = validateAdditionalDocumentFile(file);
  if (validationError) {
    throw new Error(validationError);
  }

  const response = await postJson<{ name: string }, { document: WorkspaceAdditionalDocument }>(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/documents`,
    { name: file.name.trim() },
  );
  return normalizeAdditionalDocument(response.document);
}

export async function updateAdditionalDocumentAccess(
  workspaceId: string,
  documentId: string,
  assignedUserIds: string[],
): Promise<WorkspaceAdditionalDocument> {
  const response = await patchJson<
    UpdateAdditionalDocumentAccessRequest,
    { document: WorkspaceAdditionalDocument }
  >(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/documents/${encodeURIComponent(documentId)}`,
    { assigned_user_ids: assignedUserIds },
  );
  return normalizeAdditionalDocument(response.document);
}

export async function deleteAdditionalDocument(
  workspaceId: string,
  documentId: string,
): Promise<void> {
  await deleteJson<{ document_id: string }>(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/documents/${encodeURIComponent(documentId)}`,
  );
}

export function normalizeAdditionalDocument(
  document: WorkspaceAdditionalDocument,
): WorkspaceAdditionalDocument {
  return {
    ...document,
    uploaded_by_user_id: document.uploaded_by_user_id ?? null,
    assigned_user_ids: Array.isArray(document.assigned_user_ids) ? document.assigned_user_ids : [],
  };
}

export function sortAdditionalDocuments(
  documents: WorkspaceAdditionalDocument[],
): WorkspaceAdditionalDocument[] {
  return [...documents].sort((left, right) =>
    left.name.localeCompare(right.name, undefined, { sensitivity: "base" }),
  );
}

export function formatDocumentUploadedAt(createdAt: string): string {
  const parsed = new Date(createdAt);
  if (Number.isNaN(parsed.getTime())) {
    return createdAt;
  }
  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function getAdditionalDocumentErrorMessage(error: unknown): string {
  return getErrorMessage(error) || "Document action failed.";
}
