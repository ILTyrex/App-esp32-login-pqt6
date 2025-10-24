import React, { useEffect, useState } from 'react'
import { Chart, registerables } from 'chart.js'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import api from '../services/api'

Chart.register(...registerables)

export default function Dashboard(){
  const [events, setEvents] = useState([])

  useEffect(()=>{
    // poll events periodically
    fetchEvents()
    const id = setInterval(()=> fetchEvents(), 1000)
    return ()=>clearInterval(id)
  },[])

  async function fetchEvents(){
    try{
      // request a larger history
      const res = await api.get('/events', { params: { limit: 200 } })
      // server returns events in desc order; sort asc by fecha_hora
      const ev = Array.isArray(res.data) ? res.data.slice().sort((a,b)=> new Date(a.fecha_hora) - new Date(b.fecha_hora)) : []
      setEvents(ev)
    }catch(e){
      setEvents([])
    }
  }

  // derive indicators from events
  const lastByDetalle = {}
  events.forEach(ev => { lastByDetalle[ev.detalle] = ev })

  const leds = [1,2,3].map(i=>{
    const ev = lastByDetalle[`LED${i}`]
    if(!ev) return false
    // consider LED_ON / LED_OFF or valor 'ON'/'OFF'
    return ev.tipo_evento === 'LED_ON' || String(ev.valor).toUpperCase() === 'ON'
  })

  const ledsOnCount = leds.filter(Boolean).length
  const sensorEv = lastByDetalle['SENSOR_IR']
  const sensorOn = sensorEv ? (sensorEv.tipo_evento === 'SENSOR_BLOQUEADO' || String(sensorEv.valor).toLowerCase()==='true') : false

  // compute cumulative obstacle count and track counter evolution
  let obstacleCount = 0
  const historyPoints = [] // [{ts, obstacleCount}]
  const counterPoints = [] // [{ts, value}]
  const eventOrigins = { APP: 0, WEB: 0, CIRCUITO: 0 }

  events.forEach(ev=>{
    // Track event origins
    if (ev.origen) {
      eventOrigins[ev.origen] = (eventOrigins[ev.origen] || 0) + 1
    }

    // Track obstacle count
    if(ev.tipo_evento === 'CONTADOR_CAMBIO' && ev.detalle === 'CONTADOR') {
      // Usar el valor del contador directamente del circuito
      obstacleCount = parseInt(ev.valor) || obstacleCount
    } else if(ev.tipo_evento === 'SENSOR_BLOQUEADO' && ev.origen === 'WEB'){
      // Solo incrementar si el evento viene de la web
      obstacleCount += 1
    } else if(ev.tipo_evento === 'RESET_CONTADOR'){
      obstacleCount = 0
    }
    historyPoints.push({ ts: ev.fecha_hora, obstacleCount })

    // Track counter evolution
    if(ev.tipo_evento === 'CONTADOR_CAMBIO') {
      counterPoints.push({ ts: ev.fecha_hora, value: parseInt(ev.valor) || 0 })
    }
  })

  const indicators = [
    {label:'LEDs encendidos', value: ledsOnCount},
    {label:'Sensor', value: sensorOn ? 'Bloqueado' : 'Libre'},
    {label:'Obstáculos (cont.)', value: obstacleCount},
    {label:'Última actualización', value: events.length ? new Date(events[events.length-1].fecha_hora).toLocaleString('es-CO', { 
      hour12: true,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }) : '---'}
  ]

  const history = historyPoints.length ? historyPoints : [{ts: new Date().toISOString(), obstacleCount: 0}]
  const labels = history.map(h => new Date(h.ts).toLocaleTimeString('es-CO'))
  const lineData = { labels, datasets:[{label:'Obstáculos', data: history.map(h=>h.obstacleCount || 0), borderColor:'#1e90ff', tension:0.3}] }

  const barData = { labels: ['LEDs encendidos'], datasets:[{label:'LEDs', data:[ledsOnCount], backgroundColor:'#3b82f6'}] }
  const doughnutData = { labels:['Sensor Bloqueado','Sensor Libre'], datasets:[{data: sensorOn ? [1,0] : [0,1], backgroundColor:['#10b981','#ef4444']}] }
  
  // Nueva gráfica de dona para origen de eventos
  const eventOriginData = {
    labels: ['APP', 'WEB', 'CIRCUITO'],
    datasets: [{
      data: [eventOrigins.APP, eventOrigins.WEB, eventOrigins.CIRCUITO],
      backgroundColor: ['#f59e0b', '#3b82f6', '#10b981']
    }]
  }

  // Nueva gráfica de línea para evolución del contador
  const counterData = {
    labels: counterPoints.map(p => new Date(p.ts).toLocaleTimeString('es-CO')),
    datasets: [{
      label: 'Valor del Contador',
      data: counterPoints.map(p => p.value),
      borderColor: '#8b5cf6',
      tension: 0.3
    }]
  }

  return (
    <div>
      <div className="grid">
        {indicators.map((it)=> (
          <div className="card" key={it.label}>
            <h4>{it.label}</h4>
            <div style={{fontSize:28,fontWeight:700}}>{it.value}</div>
          </div>
        ))}
      </div>

      <div className="grid" style={{marginTop:16}}>
        <div className="card"><h4>Línea (histórico obstáculos)</h4><Line data={lineData} /></div>
        <div className="card"><h4>Barras (LEDs)</h4><Bar data={barData} /></div>
        <div className="card"><h4>Dona (sensor)</h4><Doughnut data={doughnutData} /></div>
        <div className="card"><h4>Origen de eventos</h4><Doughnut data={eventOriginData} /></div>
        <div className="card"><h4>Evolución del contador</h4><Line data={counterData} /></div>
      </div>
    </div>
  )
}
