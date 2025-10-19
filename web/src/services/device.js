// Servicio simple para simular el estado del dispositivo (ESP32) en localStorage
const KEY = 'device_state_v1'

function defaultState(){
  return {
    leds: [false, false, false],
    foco: false,
    sensor: false, // true cuando hay obstáculo
    obstacleCount: 0,
    lastUpdate: new Date().toISOString(),
    history: [] // array de {ts, obstacleCount}
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
  // if obstacleCount changed, push history point
  if(updates.obstacleCount !== undefined && updates.obstacleCount !== cur.obstacleCount){
    next.history = (next.history || []).concat([{ts: new Date().toISOString(), obstacleCount: updates.obstacleCount}]).slice(-100)
  }
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function toggleLed(index){
  const s = readState()
  const leds = [...s.leds]
  leds[index] = !leds[index]
  return writeState({leds})
}

export function setFoco(value){
  return writeState({foco: !!value})
}

export function toggleSensor(){
  const s = readState()
  const newSensor = !s.sensor
  const updates = {sensor: newSensor}
  if(newSensor){
    updates.obstacleCount = (s.obstacleCount || 0) + 1
  }
  return writeState(updates)
}

export function resetCounter(){
  const s = readState()
  return writeState({obstacleCount: 0, history: []})
}

export function reset(){
  const s = defaultState()
  localStorage.setItem(KEY, JSON.stringify(s))
  return s
}
