// Simulación de auth: en el futuro conectar con backend
const TOKEN_KEY = 'app_token'

export function loginMock(username, password) {
  // acepta cualquier credenciales para demo y guarda un token simulado
  const token = btoa(JSON.stringify({ username, exp: Date.now() + 1000 * 60 * 60 }))
  localStorage.setItem(TOKEN_KEY, token)
  return Promise.resolve({ token })
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
}

export function isAuthenticated() {
  const t = localStorage.getItem(TOKEN_KEY)
  if (!t) return false
  try {
    const payload = JSON.parse(atob(t))
    return payload.exp > Date.now()
  } catch (e) {
    return false
  }
}

export function getUser() {
  const t = localStorage.getItem(TOKEN_KEY)
  if (!t) return null
  try {
    return JSON.parse(atob(t))
  } catch (e) {
    return null
  }
}
