const TOKEN_KEY = 'oligolab_token'
const USER_KEY = 'oligolab_user'

export interface AuthUser {
  username: string
  display_name: string
  department: string
  email: string
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}
export function setUser(u: AuthUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(u))
}
export function clearUser(): void {
  localStorage.removeItem(USER_KEY)
}

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const p = parts[1]
    return JSON.parse(atob(p.replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  const token = getToken()
  if (!token) return false
  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return false
  return Date.now() < (payload.exp as number) * 1000
}

export function logout(): void {
  clearToken()
  clearUser()
}
