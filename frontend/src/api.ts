interface ApiErrorPayload {
  error?: string;
  detail?: string | Array<{ msg?: string }>;
}

export async function postJson<TRequest, TResponse>(
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

export async function fetchJson<TResponse>(url: string): Promise<TResponse> {
  const response = await fetch(url);
  return parseJsonResponse<TResponse>(response);
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error.";
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
