const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

function buildUrl(path) {
  return new URL(`${DEFAULT_BASE_URL}/api/ai${path}`, window.location.origin).toString()
}

function getAuthHeaders() {
  try {
    const token = localStorage.getItem('devtrade_token')
    if (token) {
      return { Authorization: `Bearer ${token}` }
    }
  } catch {
    // localStorage недоступен (например, в SSR)
  }
  return {}
}

async function parseJson(res) {
  const text = await res.text().catch(() => '')
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export async function listChats({ signal } = {}) {
  const res = await fetch(buildUrl('/chats'), {
    signal,
    cache: 'no-store',
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error((await res.text().catch(() => '')) || `HTTP ${res.status}`)
  const json = await res.json()
  return Array.isArray(json?.data) ? json.data : []
}

export async function createChat({ name, signal } = {}) {
  const res = await fetch(buildUrl('/chats'), {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error((await res.text().catch(() => '')) || `HTTP ${res.status}`)
  return await res.json()
}

export async function renameChat(chatId, { name, signal } = {}) {
  const res = await fetch(buildUrl(`/chats/${encodeURIComponent(chatId)}/rename`), {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error((await res.text().catch(() => '')) || `HTTP ${res.status}`)
  return await res.json()
}

export async function deleteChat(chatId, { signal } = {}) {
  const res = await fetch(buildUrl(`/chats/${encodeURIComponent(chatId)}`), {
    method: 'DELETE',
    signal,
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error((await res.text().catch(() => '')) || `HTTP ${res.status}`)
  return await res.json()
}

export async function listMessages(chatId, { signal } = {}) {
  const res = await fetch(buildUrl(`/chats/${encodeURIComponent(chatId)}/messages`), {
    signal,
    cache: 'no-store',
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error((await res.text().catch(() => '')) || `HTTP ${res.status}`)
  const json = await res.json()
  return {
    chat: json?.chat ?? null,
    messages: Array.isArray(json?.data) ? json.data : [],
  }
}

export async function sendMessage(chatId, { content, signal } = {}) {
  const res = await fetch(buildUrl(`/chats/${encodeURIComponent(chatId)}/messages`), {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) {
    const data = await parseJson(res)
    throw new Error((data && (data.detail || data.error || data.message)) || `HTTP ${res.status}`)
  }
  return await res.json()
}

export async function submitStrategy({ title, language = 'python', code, signal } = {}) {
  const res = await fetch(buildUrl('/strategies/submit'), {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ title, language, code }),
  })
  if (!res.ok) {
    const data = await parseJson(res)
    throw new Error((data && (data.detail || data.error || data.message)) || `HTTP ${res.status}`)
  }
  return await res.json()
}