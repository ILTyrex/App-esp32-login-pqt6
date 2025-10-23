import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login, register } from '../services/auth'

export default function Auth(){
  const [isSignUp, setIsSignUp] = useState(false)
  const [loginUser, setLoginUser] = useState('')
  const [loginPass, setLoginPass] = useState('')
  const [regUser, setRegUser] = useState('')
  const [regPass, setRegPass] = useState('')
  const [regPass2, setRegPass2] = useState('')
  const navigate = useNavigate()

  async function handleLogin(e){
    e.preventDefault()
    try{
      await login(loginUser, loginPass)
      navigate('/')
    }catch(err){
      alert('Error autenticando: ' + (err?.response?.data?.error || err?.message || 'desconocido'))
    }
  }

  async function handleRegister(e){
    e.preventDefault()
    if(!regUser || !regPass) return alert('Usuario y contraseña son requeridos')
    if(regPass !== regPass2) return alert('Las contraseñas no coinciden')
    try{
      await register(regUser, regPass)
      alert('Usuario creado correctamente. Inicia sesión.')
      setIsSignUp(false)
      setLoginUser(regUser)
    }catch(err){
      const msg = err?.response?.data?.error || err?.message || 'Error'
      alert('Error creando usuario: ' + msg)
    }
  }

  return (
    <div className={`container ${isSignUp ? 'active' : ''}`} id="container">
      <div className="form-container sign-up">
        <form onSubmit={handleRegister}>
          <h1>Create Account</h1>
          <span>or use your username for registration</span>
          <input value={regUser} onChange={(e)=>setRegUser(e.target.value)} type="text" placeholder="Usuario" />
          <input value={regPass} onChange={(e)=>setRegPass(e.target.value)} type="password" placeholder="Password" />
          <input value={regPass2} onChange={(e)=>setRegPass2(e.target.value)} type="password" placeholder="Confirm Password" />
          <button type="submit">Sign Up</button>
        </form>
      </div>

      <div className="form-container sign-in">
        <form onSubmit={handleLogin}>
          <h1>Sign In</h1>
          <span>or use your username and password</span>
          <input value={loginUser} onChange={(e)=>setLoginUser(e.target.value)} type="text" placeholder="Usuario" />
          <input value={loginPass} onChange={(e)=>setLoginPass(e.target.value)} type="password" placeholder="Password" />
          <button type="submit">Sign In</button>
        </form>
      </div>

      <div className="toggle-container">
        <div className="toggle">
          <div className="toggle-panel toggle-left">
            <h1>¡Bienvenido de nuevo!</h1>
            <p>Ingresa tus datos personales para usar todas las funciones del sitio</p>
            <button onClick={()=>setIsSignUp(false)} className="hidden" id="login">Sign In</button>
          </div>
          <div className="toggle-panel toggle-right">
            <h1>Hola, amigo!</h1>
            <p>Regístrate con tus datos personales para usar todas las funciones del sitio</p>
            <button onClick={()=>setIsSignUp(true)} className="hidden" id="register">Sign Up</button>
          </div>
        </div>
      </div>
    </div>
  )
}
