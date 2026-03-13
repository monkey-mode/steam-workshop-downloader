const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface WorkshopItem {
  workshop_id: string;
  title: string;
  description: string;
  app_id: string;
  file_size: number;
  size_human: string;
  subscriptions: number;
  favorited: number;
  tags: string[];
  preview_url: string;
  workshop_url: string;
}

export interface BrowseResponse {
  total: number;
  items: WorkshopItem[];
  has_api_key: boolean;
}

export interface StatusResponse {
  steamcmd: string | null;
  has_api_key: boolean;
}

export type SseEvent =
  | { type: "log"; line: string }
  | { type: "done"; path: string }
  | { type: "error"; line: string };

export async function browseWorkshop(params: {
  app_id: string;
  sort?: string;
  page?: number;
  count?: number;
  search?: string;
}): Promise<BrowseResponse> {
  const query = new URLSearchParams({
    app_id: params.app_id,
    sort: params.sort || "trend",
    page: String(params.page || 1),
    count: String(params.count || 20),
    search: params.search || "",
  });
  const res = await fetch(`${API_BASE}/api/browse?${query}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getItem(workshopId: string): Promise<WorkshopItem> {
  const res = await fetch(`${API_BASE}/api/item/${workshopId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Stream download events from the backend SSE endpoint.
 * Calls onEvent for each line of output, until done or error.
 */
export async function streamDownload(
  app_id: string,
  workshop_ids: string[],
  output_dir: string,
  username: string,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/download/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ app_id, workshop_ids, output_dir, username }),
    signal,
  });

  if (!res.ok) throw new Error(await res.text());
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        const event = JSON.parse(dataLine.slice(6)) as SseEvent;
        onEvent(event);
        if (event.type === "done" || event.type === "error") return;
      } catch {
        // ignore malformed lines
      }
    }
  }
}

export async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
