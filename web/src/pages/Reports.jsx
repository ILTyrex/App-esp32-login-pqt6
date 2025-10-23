import React, { useEffect, useState } from 'react'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'
import { jsPDF } from 'jspdf'
import api from '../services/api'

export default function Reports(){
  const [events, setEvents] = useState([])

  useEffect(()=>{
    fetchEvents()
  },[])

  async function fetchEvents(){
    try{
      const res = await api.get('/events')
      setEvents(res.data)
    }catch(e){
      // fallback: show empty
      setEvents([])
    }
  }

  function exportExcel(){
    const rows = mapEventsToRows(events)
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Reporte')
    const wbout = XLSX.write(wb, {bookType:'xlsx', type:'array'})
    saveAs(new Blob([wbout]), 'reporte.xlsx')
  }

  function exportPDF(){
    const rows = mapEventsToRows(events)
    const doc = new jsPDF({orientation: 'landscape'})
    doc.setFontSize(12)
    doc.text('Reporte de Eventos', 10, 10)
    const startY = 20
    const lineHeight = 8
    let y = startY
    // header
    const header = ['id_evento','id_usuario','tipo_evento','detalle','origen','valor','origen_ip','fecha_hora']
    doc.setFontSize(9)
    doc.text(header.join(' | '), 10, y)
    y += lineHeight
    rows.forEach(r=>{
      const line = header.map(h=> (r[h] === null || r[h] === undefined) ? '' : String(r[h])).join(' | ')
      doc.text(line, 10, y)
      y += lineHeight
      if(y > 190){
        doc.addPage(); y = 20
      }
    })
    const blob = doc.output('blob')
    saveAs(blob, 'eventos.pdf')
  }

  // server CSV export removed — only Excel and PDF are supported client-side

  return (
    <div>
      <div className="card">
        <h3>Reportes</h3>
        <p>Exporta el conteo de obstáculos y su histórico (demo local).</p>
        <button onClick={exportExcel}>Exportar Excel</button>
  <button onClick={exportPDF} style={{marginLeft:8}}>Exportar PDF</button>
      </div>
    </div>
  )
}

// helper to map Evento.to_dict shape to flat rows
function mapEventsToRows(events){
  return events.map(e=>({
    id_evento: e.id_evento,
    id_usuario: e.id_usuario,
    tipo_evento: e.tipo_evento,
    detalle: e.detalle,
    origen: e.origen,
    valor: e.valor,
    origen_ip: e.origen_ip,
    fecha_hora: e.fecha_hora
  }))
}
