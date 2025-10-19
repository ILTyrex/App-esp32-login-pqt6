import React, { useEffect, useState } from 'react'
import { readState, toggleLed, resetCounter, reset } from '../services/device'

export default function Control(){
  const [state, setState] = useState(readState())

  useEffect(()=>{
    const id = setInterval(()=> setState(readState()), 800)
    return ()=>clearInterval(id)
  },[])

  function onToggleLed(i){
    toggleLed(i)
    setState(readState())
  }

  function onConfirmReset(){
    if(window.confirm('¿Resetear el contador de obstáculos? Esta acción no se puede deshacer.')){
      resetCounter()
      setState(readState())
    }
  }

  return (
    <div>
      <div className="card">
        <h3>Control y Estado</h3>

        <h3>Control y Estado</h3>

        <div className="control-grid">
          {state.leds.map((l,i)=> (
            <div key={i} className="device-card">
              <div className="device-header">LED {i+1}</div>
              <div className="device-body">
                <div className={`led-indicator ${l ? 'on' : 'off'}`}></div>
                <div className="device-info">Estado: <strong>{l ? 'ON' : 'OFF'}</strong></div>
                <button className="btn-primary" onClick={()=>onToggleLed(i)}>Toggle</button>
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
