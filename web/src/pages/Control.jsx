import React, { useEffect, useState } from 'react'
import { readState, writeState, createCommand, resetCounter } from '../services/device'
import { useNavigate } from 'react-router-dom'

export default function Control(){
  const [state, setState] = useState(readState())
  const [loadingIdx, setLoadingIdx] = useState(null)
  const navigate = useNavigate()

  useEffect(()=>{
    const id = setInterval(()=> setState(readState()), 800)
    return ()=>clearInterval(id)
  },[])

  async function onToggleLed(i){
    // optimistic update
    const cur = readState()
    const leds = [...cur.leds]
    leds[i] = !leds[i]
    writeState({leds})
    setState(readState())

    // send command to backend
    setLoadingIdx(i)
    try{
      const payload = { tipo: 'LED', detalle: `LED${i+1}`, accion: leds[i] ? 'ON' : 'OFF' }
      await createCommand(payload)
      // backend will record command and event
    }catch(err){
      // if not authorized, redirect to login
      if(err?.response?.status === 401){
        alert('Primero debes iniciar sesión para enviar comandos al dispositivo')
        navigate('/login')
        return
      }
      // rollback optimistic update on error
      const cur2 = readState()
      const leds2 = [...cur2.leds]
      leds2[i] = !leds2[i]
      writeState({leds: leds2})
      setState(readState())
      alert('Error enviando comando: ' + (err?.response?.data?.error || err?.message || 'desconocido'))
    }finally{
      setLoadingIdx(null)
    }
  }

  async function onConfirmReset(){
    if(window.confirm('¿Resetear el contador de obstáculos? Esta acción no se puede deshacer.')){
      try{
        await resetCounter()
        setState(readState())
      }catch(err){
        if(err?.response?.status === 401){
          alert('Debes iniciar sesión para resetear contador en el dispositivo')
          navigate('/login')
          return
        }
        alert('Error reseteando contador: ' + (err?.message || 'desconocido'))
      }
    }
  }

  return (
    <div>
      <div className="card">
        <h3>Control y Estado</h3>

        <div className="control-grid">
          {state.leds.map((l,i)=> (
            <div key={i} className="device-card">
              <div className="device-header">LED {i+1}</div>
              <div className="device-body">
                <div className={`led-indicator ${l ? 'on' : 'off'}`}></div>
                <div className="device-info">Estado: <strong>{l ? 'ON' : 'OFF'}</strong></div>
                <button className="btn-primary" onClick={()=>onToggleLed(i)} disabled={loadingIdx===i}>{loadingIdx===i ? '...' : 'Toggle'}</button>
              </div>
            </div>
          ))}

          <div className="device-card">
            <div className="device-header">Contador</div>
            <div className="device-body">
              <div className="device-info">Contador actual: <strong>{state.obstacleCount}</strong></div>
              <button className="btn-danger" onClick={onConfirmReset}>Reset contador</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
