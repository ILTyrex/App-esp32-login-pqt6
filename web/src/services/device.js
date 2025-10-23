import api from './api'

// keep previous local simulation as fallback
const KEY = 'device_state_v1'

function defaultState(){
  return {
    leds: [false, false, false],
    foco: false,
    sensor: false,
    obstacleCount: 0,
    lastUpdate: new Date().toISOString(),
    history: []
  }
}

export function readState(){
  try{
    const raw = localStorage.getItem(KEY)
    if(!raw) {
      const s = defaultState();
      localStorage.setItem(KEY, JSON.stringify(s));
      return s;
    }
    return JSON.parse(raw)
  }catch(e){
    const s = defaultState();
    localStorage.setItem(KEY, JSON.stringify(s));
    return s;
  }
}

export function writeState(updates){
  const cur = readState()
  const next = {...cur, ...updates, lastUpdate: new Date().toISOString()}
  if(updates.obstacleCount !== undefined && updates.obstacleCount !== cur.obstacleCount){
    next.history = (next.history || []).concat([{ts: new Date().toISOString(), obstacleCount: updates.obstacleCount}]).slice(-100)
  }
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function toggleLed(index){
  // optimistic local update
  const s = readState()
  const leds = [...s.leds]
  leds[index] = !leds[index]
  const updated = writeState({leds})
  // send event to backend (non-blocking)
  try{
    api.post('/events', { tipo_evento: leds[index] ? 'LED_ON' : 'LED_OFF', detalle: `LED${index+1}`, origen: 'APP', valor: leds[index] })
  }catch(e){
    // ignore network errors for now
  }
  return updated
}

export function setFoco(value){
  const updated = writeState({foco: !!value})
  try{ api.post('/events', { tipo_evento: value ? 'LED_ON' : 'LED_OFF', detalle: 'FOCO', origen: 'APP', valor: value }) }catch(e){}
  return updated
}

export function toggleSensor(){
  const s = readState()
  const newSensor = !s.sensor
  const updates = {sensor: newSensor}
  if(newSensor){
    updates.obstacleCount = (s.obstacleCount || 0) + 1
  }
  const updated = writeState(updates)
  try{ api.post('/events', { tipo_evento: newSensor ? 'SENSOR_BLOQUEADO' : 'SENSOR_LIBRE', detalle: 'SENSOR_IR', origen: 'APP', valor: newSensor }) }catch(e){}
  return updated
}

export function resetCounter(){
  const updated = writeState({obstacleCount: 0, history: []})
  try{ api.post('/events', { tipo_evento: 'RESET_CONTADOR', detalle: 'CONTADOR', origen: 'APP', valor: '0' }) }catch(e){}
  return updated
}

export function reset(){
  const s = defaultState()
  localStorage.setItem(KEY, JSON.stringify(s))
  return s
}

// backend operations for commands and exports
export async function createCommand(payload){
  // payload: { tipo, detalle, accion, device_id }
  try{
    const res = await api.post('/api/commands', payload)
    return res.data
  }catch(e){
    throw e
  }
}

export async function listCommands(device_id){
  try{
    const res = await api.get('/api/commands', { params: { device_id } })
    return res.data
  }catch(e){
    throw e
  }
}

export async function exportCSV(params){
  // params: { from, to, detalle }
  try{
    const res = await api.get('/export', { params, responseType: 'blob' })
    return res.data
  }catch(e){
    throw e
  }
}

