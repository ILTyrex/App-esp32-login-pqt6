import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../services/auth'

export default function Register(){
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
    <div className="login-page">
      <div className="login-box card">
        <div className="card-header">
          <h2>Crear cuenta</h2>
          <div className="muted">Registra un nuevo usuario para acceder al panel</div>
        </div>

        <form onSubmit={submit} className="form-grid">
          <div className="form-row">
            <label>Usuario</label>
            <input value={user} onChange={(e)=>setUser(e.target.value)} placeholder="usuario" />
          </div>

          <div className="form-row">
            <label>Contraseña</label>
            <div className="input-with-icon">
              <input className="input-with-icon__input" type={show? 'text' : 'password'} value={pass} onChange={(e)=>setPass(e.target.value)} placeholder="contraseña" />
              <button type="button" className="icon-btn icon-btn--inside" onClick={()=>setShow(s=>!s)} aria-label={show? 'Ocultar contraseña' : 'Mostrar contraseña'}>
                {show ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" stroke="#1e90ff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="12" r="3" stroke="#1e90ff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-6 0-10-7-10-7 .96-1.7 2.4-3.34 4.2-4.8M9.88 9.88A3 3 0 0 0 14.12 14.12" stroke="#111" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/><path d="M1 1l22 22" stroke="#111" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                )}
              </button>
            </div>
          </div>

          <div className="form-row">
            <label>Confirmar contraseña</label>
            <div className="input-with-icon">
              <input className="input-with-icon__input" type={show? 'text' : 'password'} value={pass2} onChange={(e)=>setPass2(e.target.value)} placeholder="repite la contraseña" />
              <div style={{width:36}} />
            </div>
          </div>

          <div className="form-row">
            <button type="submit" className="btn-primary">Registrar</button>
          </div>
        </form>

        <div className="card-footer">
          <small>¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></small>
        </div>
      </div>
    </div>
  )
}
