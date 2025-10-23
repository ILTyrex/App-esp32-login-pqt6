import axios from 'axios'

const DEFAULT_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

const api = axios.create({
  baseURL: DEFAULT_BASE,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 5000
})

export function setAuthToken(token){
  if(token){
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }else{
    delete api.defaults.headers.common['Authorization']
  }
}

export default api
