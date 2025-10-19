import React, { useEffect, useState } from 'react'
import { Chart, registerables } from 'chart.js'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import { readState } from '../services/device'

Chart.register(...registerables)

export default function Dashboard(){
  const [state, setState] = useState(readState())

  useEffect(()=>{
    const id = setInterval(()=> setState(readState()), 800)
    return ()=>clearInterval(id)
  },[])

  const indicators = [
    {label:'Actuadores ON', value: state.leds.filter(Boolean).length},
    {label:'Foco', value: state.foco ? 'ON' : 'OFF'},
    {label:'Obstáculos (cont.)', value: state.obstacleCount},
    {label:'Última actualización', value: new Date(state.lastUpdate).toLocaleString()}
  ]

  const labels = state.history.map((h,i)=> new Date(h.ts).toLocaleTimeString())
  const lineData = {
    labels: labels.length? labels : ['-'],
    datasets:[{label:'Obstáculos', data: state.history.map(h=>h.obstacleCount), borderColor:'#1e90ff', tension:0.3}]
  }

  const barData = {labels: ['Leds on'], datasets:[{label:'Actuadores', data:[state.leds.filter(Boolean).length], backgroundColor:'#3b82f6'}]}

  const doughnutData = {labels:['Foco ON','Foco OFF'], datasets:[{data: state.foco ? [1,0] : [0,1], backgroundColor:['#10b981','#ef4444']}]}

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
        <div className="card"><h4>Linea (histórico obstáculos)</h4><Line data={lineData} /></div>
        <div className="card"><h4>Barras (actuadores)</h4><Bar data={barData} /></div>
        <div className="card"><h4>Dona (foco)</h4><Doughnut data={doughnutData} /></div>
        <div className="card"><h4>Mini Linea</h4><Line data={lineData} /></div>
        <div className="card"><h4>Mini Barra</h4><Bar data={barData} /></div>
      </div>
    </div>
  )
}
