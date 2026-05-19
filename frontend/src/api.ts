interface ApiErrorPayload {
  error?: string;
  detail?: string | Array<{ msg?: string }>;
}

const REQUEST_TIMEOUT_MS = 6_000;

export async function postJson<TRequest, TResponse>(
  url: string,
  body?: TRequest,
): Promise<TResponse> {
  const hasBody = typeof body !== "undefined";
  const response = await fetchWithTimeout(url, {
    method: "POST",
    credentials: "include",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    body: hasBody ? JSON.stringify(body) : undefined,
  });
  return parseJsonResponse<TResponse>(response);
}

export async function patchJson<TRequest, TResponse>(
  url: string,
  body: TRequest,
): Promise<TResponse> {
  const response = await fetchWithTimeout(url, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJsonResponse<TResponse>(response);
}

export async function fetchJson<TResponse>(url: string): Promise<TResponse> {
  const response = await fetchWithTimeout(url, { credentials: "include" });
  return parseJsonResponse<TResponse>(response);
}

export async function deleteJson<TResponse>(url: string): Promise<TResponse> {
  const response = await fetchWithTimeout(url, {
    method: "DELETE",
    credentials: "include",
  });
  return parseJsonResponse<TResponse>(response);
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error.";
}

export function isSessionExpiredMessage(message: string): boolean {
  const normalizedMessage = message.toLowerCase();
  return (
    normalizedMessage.includes("session expired") ||
    normalizedMessage.includes("authentication required")
  );
}

async function parseJsonResponse<TResponse>(
  response: Response,
): Promise<TResponse> {
  const payload = (await response.json()) as TResponse & ApiErrorPayload;

  if (!response.ok || payload.error || payload.detail) {
    throw new Error(getApiErrorMessage(payload, response.status));
  }

  return payload;
}

async function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "Cannot reach backend right now. Start the server and refresh the page.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function getApiErrorMessage(payload: ApiErrorPayload, status: number): string {
  if (payload.error) {
    return payload.error;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    const messages = payload.detail
      .map((item) => item.msg)
      .filter((message): message is string => Boolean(message));
    if (messages.length) {
      return messages.join(", ");
    }
  }

  return `Request failed with ${status}`;
}
