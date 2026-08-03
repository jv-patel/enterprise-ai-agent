const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

interface ApiOptions extends RequestInit {
  userId?: string;
}

interface ApiErrorBody {
  error?: { code?: string; message?: string };
}

export class ApiError extends Error {
  code?: string;
  status: number;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { userId, headers, ...rest } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(userId ? { "X-User-Id": userId } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const body: ApiErrorBody | null = await response.json().catch(() => null);
    throw new ApiError(
      body?.error?.message || `Request failed with status ${response.status}`,
      response.status,
      body?.error?.code
    );
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.blob()) as unknown as T;
}
