import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Auth from './pages/Auth'
import MainLayout from './pages/MainLayout'
import Dashboard from './pages/Dashboard'
import Control from './pages/Control'
import Reports from './pages/Reports'
import About from './pages/About'
import { isAuthenticated } from './services/auth'

function PrivateRoute({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
  <Route path="/login" element={<Auth />} />
  <Route path="/register" element={<Auth />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <MainLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="control" element={<Control />} />
        <Route path="reports" element={<Reports />} />
        <Route path="about" element={<About />} />
      </Route>
    </Routes>
  )
}
