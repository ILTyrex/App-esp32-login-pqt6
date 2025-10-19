import React from 'react'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'
import { readState } from '../services/device'

export default function Reports(){
  const st = readState()
  const sampleData = [
    {ts:new Date().toISOString(), metric:'obstacleCount', value: st.obstacleCount},
    ...st.history.slice(-10).map(h=>({ts:h.ts, metric:'obstacleCount', value:h.obstacleCount}))
  ]

  function exportExcel(){
    const ws = XLSX.utils.json_to_sheet(sampleData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Reporte')
    const wbout = XLSX.write(wb, {bookType:'xlsx', type:'array'})
    saveAs(new Blob([wbout]), 'reporte.xlsx')
  }

  function exportPDF(){
    const content = `Reporte\n\n${sampleData.map(d=>`${d.ts} ${d.metric} ${d.value}`).join('\n')}`
    const blob = new Blob([content], {type:'text/plain'})
    saveAs(blob, 'reporte.txt')
  }

  return (
    <div>
      <div className="card">
        <h3>Reportes</h3>
        <p>Exporta el conteo de obstáculos y su histórico (demo local).</p>
        <button onClick={exportExcel}>Exportar Excel</button>
        <button onClick={exportPDF} style={{marginLeft:8}}>Exportar (txt placeholder para PDF)</button>
      </div>
    </div>
  )
}
