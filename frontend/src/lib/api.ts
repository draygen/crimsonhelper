const BASE = ''  // proxied via Vite in dev; same origin in prod

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function del(path: string): Promise<void> {
  await fetch(`${BASE}${path}`, { method: 'DELETE' })
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface Quest {
  id: number
  title: string
  description?: string
  zone?: string
  npc_name?: string
  status: string
  screenshot_id?: number
  captured_at: string
}

export interface Screenshot {
  id: number
  filename: string
  thumbnail?: string
  category: string
  ocr_text?: string
  zone?: string
  captured_at: string
}

export interface LootEntry {
  id: number
  item_name: string
  quantity: number
  zone?: string
  screenshot_id?: number
  captured_at: string
}

export interface NPC {
  id: number
  name: string
  zone?: string
  dialogue?: string
  screenshot_id?: number
  first_seen: string
  last_seen: string
}

export interface Status {
  ocr_available: boolean
  voice_active: boolean
  voice_available: boolean
  collab_enabled: boolean
  hotkey: string
  game_running: boolean
  game_process: string
}

export interface YTGuide {
  search_url: string
  api_available: boolean
  results: { title: string; url: string; channel: string; thumbnail: string }[]
}

// ── API calls ──────────────────────────────────────────────────────────────────

export const api = {
  status: () => get<Status>('/api/status'),

  quests: {
    list:   (params?: Record<string, string>) =>
      get<Quest[]>(`/api/quests?${new URLSearchParams(params).toString()}`),
    get:    (id: number) => get<Quest>(`/api/quests/${id}`),
    delete: (id: number) => del(`/api/quests/${id}`),
    status: (id: number, status: string) =>
      patch(`/api/quests/${id}/status?status=${status}`),
    guide:  (id: number) => get<YTGuide>(`/api/quests/${id}/guide`),
  },

  screenshots: {
    list:   (params?: Record<string, string>) =>
      get<Screenshot[]>(`/api/screenshots?${new URLSearchParams(params).toString()}`),
    delete: (id: number) => del(`/api/screenshots/${id}`),
    url:    (filename: string) => `/screenshots/${filename}`,
    thumb:  (filename: string) => `/screenshots/${filename}`,
  },

  loot: {
    list:    (params?: Record<string, string>) =>
      get<LootEntry[]>(`/api/loot?${new URLSearchParams(params).toString()}`),
    summary: () => get<{ item_name: string; total: number }[]>('/api/loot/summary'),
    guide:   (item: string) => get<YTGuide>(`/api/loot/guide?item=${encodeURIComponent(item)}`),
    delete:  (id: number) => del(`/api/loot/${id}`),
  },

  npcs: {
    list:   (params?: Record<string, string>) =>
      get<NPC[]>(`/api/npcs?${new URLSearchParams(params).toString()}`),
    count:  () => get<{ count: number }>('/api/npcs/count'),
    delete: (id: number) => del(`/api/npcs/${id}`),
  },

  capture: () => post<{ ok: boolean }>('/api/capture'),

  collab: {
    status: () => get('/api/collab/status'),
    inbox:  () => get<{ messages: unknown[] }>('/api/collab/inbox'),
    task:   (description: string, priority = 'normal') =>
      post<unknown>(`/api/collab/task?description=${encodeURIComponent(description)}&priority=${priority}`),
  },
}
