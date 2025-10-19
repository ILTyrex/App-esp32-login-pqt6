import React from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { logout, getUser } from '../services/auth'

export default function MainLayout(){
  const navigate = useNavigate()
  const user = getUser()

  function doLogout(){
    logout();
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h3>Dashboard</h3>
        <div style={{marginBottom:20}}>Usuario: {user?.username || '---'}</div>
        <NavLink className="nav-link" to="/">Inicio</NavLink>
        <NavLink className="nav-link" to="/control">Control</NavLink>
        <NavLink className="nav-link" to="/reports">Reportes</NavLink>
        <NavLink className="nav-link" to="/about">Acerca de</NavLink>
        <div style={{marginTop:20}}>
          <button onClick={doLogout}>Cerrar sesión</button>
        </div>
      </aside>
      <main className="content">
        <div className="topbar">
          <h2>App ESP32 - Panel</h2>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
