import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, type CurrentUser } from '@/lib/api'

type AuthState = {
  user: CurrentUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Resets to logged-out state without an API call -- for when a request
   * elsewhere discovers the session already expired server-side. */
  invalidate: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const u = await api.login(email, password)
    setUser(u)
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    const u = await api.register(email, password)
    setUser(u)
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const invalidate = useCallback(() => setUser(null), [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, invalidate }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
