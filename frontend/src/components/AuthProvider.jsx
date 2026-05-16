import { useState, useCallback, useEffect } from 'react'
import { AuthContext } from './AuthContext.js'
import { getMe } from '../services/auth.js'

const TOKEN_KEY = 'devtrade_token'

function getStoredToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

function setStoredToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* ignore */ }
}

function parseTokenFromUrl() {
  const params = new URLSearchParams(window.location.search)
  return params.get('token')
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async (token) => {
    try {
      const data = await getMe(token)
      setUser(data)
      setStoredToken(token)
    } catch {
      setUser(null)
      setStoredToken(null)
    }
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    setStoredToken(null)
  }, [])

  useEffect(() => {
    let cancelled = false

    const init = async () => {
      const tokenFromUrl = parseTokenFromUrl()
      if (tokenFromUrl) {
        await fetchUser(tokenFromUrl)
        window.history.replaceState({}, '', '/')
        if (!cancelled) setLoading(false)
        return
      }

      const stored = getStoredToken()
      if (stored) {
        await fetchUser(stored)
      }

      if (!cancelled) setLoading(false)
    }

    init()
    return () => { cancelled = true }
  }, [fetchUser])

  const value = {
    user,
    loading,
    logout,
    fetchUser,
    isAuthenticated: !!user,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}