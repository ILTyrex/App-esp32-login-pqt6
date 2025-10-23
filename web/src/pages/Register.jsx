import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../services/auth'

export default function Register(){
  const [name, setName] = useState('')
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [pass2, setPass2] = useState('')
  const [show, setShow] = useState(false)
  const navigate = useNavigate()

  async function submit(e){
    e.preventDefault()
  if(!user || !pass) return alert('Usuario y contraseña son requeridos')
    if(pass !== pass2) return alert('Las contraseñas no coinciden')
    try{
  await register(user, pass)
      alert('Usuario creado correctamente. Inicia sesión.')
      navigate('/login')
    }catch(err){
      const msg = err?.response?.data?.error || err?.response?.data?.msg || err?.message || 'Error'
      alert('Error creando usuario: ' + msg)
    }
  }

  return (
    <div className="login-page auth-page">
      <div className="auth-card">
        <div className="panel panel--side panel--side--left">
          <div className="panel-content panel-content--center">
            <h1 className="big">Welcome Back!</h1>
            <p className="muted">Enter your personal details to use all of site features</p>
            <Link to="/login"><button className="btn-ghost" style={{marginTop:20}}>SIGN IN</button></Link>
          </div>
        </div>

        <div className="panel panel--form">
          <div className="panel-content">
            <h2 className="title">Create Account</h2>
            <p className="muted">or use your email for registration</p>

            <form onSubmit={submit} className="form-grid">
              <div className="form-row">
                <input value={user} onChange={(e)=>setUser(e.target.value)} placeholder="Usuario" />
              </div>

              <div className="form-row">
                <div className="input-with-icon">
                  <input className="input-with-icon__input" type={show? 'text' : 'password'} value={pass} onChange={(e)=>setPass(e.target.value)} placeholder="Password" />
                  <button type="button" className="icon-btn icon-btn--inside" onClick={()=>setShow(s=>!s)} aria-label={show? 'Ocultar contraseña' : 'Mostrar contraseña'}>
                    {show ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="12" r="3" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-6 0-10-7-10-7 .96-1.7 2.4-3.34 4.2-4.8M9.88 9.88A3 3 0 0 0 14.12 14.12" stroke="#111" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/><path d="M1 1l22 22" stroke="#111" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    )}
                  </button>
                </div>
              </div>

              <div className="form-row">
                <input className="input-with-icon__input" type={show? 'text' : 'password'} value={pass2} onChange={(e)=>setPass2(e.target.value)} placeholder="Confirm Password" />
              </div>

              <div className="form-row">
                <button type="submit" className="btn-primary form-cta">SIGN UP</button>
              </div>
            </form>

            <div className="card-footer" style={{marginTop:12}}>
              <small>¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></small>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
