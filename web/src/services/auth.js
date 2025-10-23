import api, { setAuthToken } from './api'

const TOKEN_KEY = 'app_token'
const USER_KEY = 'app_user'

async function login(username, password){
  try{
    const res = await api.post('/auth/login', { usuario: username, contrasena: password })
    const token = res.data.access_token
    const user = res.data.usuario
    if(token){
      localStorage.setItem(TOKEN_KEY, token)
      setAuthToken(token)
    }
    if(user){
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    }
    return { token, user }
  }catch(e){
    // rethrow for UI to handle
    throw e
  }
}

async function register(username, password){
  try{
    const res = await api.post('/auth/register', { usuario: username, contrasena: password })
    return res.data
  }catch(e){
    throw e
  }
}

function logout(){
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  setAuthToken(null)
}

function isAuthenticated(){
  const t = localStorage.getItem(TOKEN_KEY)
  return !!t
}

function getUser(){
  const raw = localStorage.getItem(USER_KEY)
  if(!raw) return null
  try{
    const u = JSON.parse(raw)
    // normalize backend shape { usuario: 'name' } to { username }
    if(u){
      const normalized = { ...u }
      if(u.usuario && !u.username){
        normalized.username = u.usuario
      }
      return normalized
    }
    return null
  }catch(e){
    return null
  }
}

async function me(){
  try{
    const res = await api.get('/auth/me')
    return res.data
  }catch(e){
    throw e
  }
}

export { login, register, logout, isAuthenticated, getUser, me }

