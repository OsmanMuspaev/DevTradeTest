const BASE = '/api/users'

export async function getGithubLoginUrl() {
  const res = await fetch(`${BASE}/auth/github/login`)
  if (!res.ok) throw new Error('Failed to get GitHub login URL')
  return res.json()
}

export async function getMe(token) {
  const res = await fetch(`${BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    if (res.status === 401) throw new Error('Unauthorized')
    throw new Error('Failed to fetch user')
  }
  return res.json()
}