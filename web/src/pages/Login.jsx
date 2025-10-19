import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginMock } from '../services/auth'

export default function Login() {
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    await loginMock(user, pass)
    navigate('/')
  }

  return (
    <div className="login-box card">
      <h2>Iniciar sesión</h2>
      <form onSubmit={submit}>
        <label>Usuario</label>
        <input value={user} onChange={(e)=>setUser(e.target.value)} />
        <label>Contraseña</label>
        <input type="password" value={pass} onChange={(e)=>setPass(e.target.value)} />
        <button type="submit">Entrar</button>
      </form>
    </div>
  )
}
