import React, { useEffect, useState } from "react";
import { Chart, registerables } from "chart.js";
import { Line, Bar, Doughnut } from "react-chartjs-2";
import api from "../services/api";

Chart.register(...registerables);

// Función para convertir UTC a hora local de Colombia
function toColombiaTime(utcDate) {
  const date = new Date(utcDate);
  // Colombia está en UTC-5
  date.setHours(date.getHours() - 5);
  return date;
}

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    // poll events periodically
    fetchEvents();
    const id = setInterval(() => fetchEvents(), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    function handleResize() {
      setWindowWidth(window.innerWidth);
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  async function fetchEvents() {
    try {
      // request a larger history
      const res = await api.get("/events", { params: { limit: 200 } });
      // server returns events in desc order; sort asc by fecha_hora
      const ev = Array.isArray(res.data)
        ? res.data
            .slice()
            .sort((a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora))
        : [];
      setEvents(ev);
    } catch (e) {
      setEvents([]);
    }
  }

  // derive indicators from events
  const lastByDetalle = {};
  events.forEach((ev) => {
    lastByDetalle[ev.detalle] = ev;
  });

  const leds = [1, 2, 3, 4].map((i) => {
    const ev = lastByDetalle[`LED${i}`];
    if (!ev) return false;
    // consider LED_ON / LED_OFF or valor 'ON'/'OFF'
    return (
      ev.tipo_evento === "LED_ON" || String(ev.valor).toUpperCase() === "ON"
    );
  });

  const ledsOnCount = leds.filter(Boolean).length;
  const sensorEv = lastByDetalle["SENSOR_IR"];
  const sensorOn = sensorEv
    ? sensorEv.tipo_evento === "SENSOR_BLOQUEADO" ||
      String(sensorEv.valor).toLowerCase() === "true"
    : false;

  // compute cumulative obstacle count and track counter evolution
  let obstacleCount = 0;
  const historyPoints = []; // [{ts, obstacleCount}]
  const counterPoints = []; // [{ts, value}]
  const eventOrigins = { APP: 0, WEB: 0, CIRCUITO: 0 };

  events.forEach((ev) => {
    // Track event origins
    if (ev.origen) {
      eventOrigins[ev.origen] = (eventOrigins[ev.origen] || 0) + 1;
    }

    // Track obstacle count
    if (ev.tipo_evento === "CONTADOR_CAMBIO" && ev.detalle === "CONTADOR") {
      // Usar el valor del contador directamente del circuito
      obstacleCount = parseInt(ev.valor) || obstacleCount;
    } else if (ev.tipo_evento === "SENSOR_BLOQUEADO" && ev.origen === "WEB") {
      // Solo incrementar si el evento viene de la web
      obstacleCount += 1;
    } else if (ev.tipo_evento === "RESET_CONTADOR") {
      obstacleCount = 0;
    }
    historyPoints.push({ ts: ev.fecha_hora, obstacleCount });

    // Track counter evolution
    if (ev.tipo_evento === "CONTADOR_CAMBIO") {
      counterPoints.push({ ts: ev.fecha_hora, value: parseInt(ev.valor) || 0 });
    }
  });

  // Indicadores: tarjeta con contador total de eventos registrados
  const indicators = [
    { label: "LEDs encendidos", value: ledsOnCount },
    { label: "Sensor", value: sensorOn ? "Bloqueado" : "Libre" },
    { label: "Obstáculos (cont.)", value: obstacleCount },
    { label: "Eventos registrados", value: events.length },
  ];

  const history = historyPoints.length
    ? historyPoints
    : [{ ts: new Date().toISOString(), obstacleCount: 0 }];
  // Mostrar solo la fecha en las etiquetas del eje X (sin hora)
  const labels = history.map((h) =>
    toColombiaTime(h.ts).toLocaleDateString("es-CO")
  );
  const lineData = {
    labels,
    datasets: [
      {
        label: "Obstáculos",
        data: history.map((h) => h.obstacleCount || 0),
        borderColor: "#1e90ff",
        tension: 0.3,
      },
    ],
  };

  const barData = {
    labels: ["LEDs encendidos"],
    datasets: [
      { label: "LEDs", data: [ledsOnCount], backgroundColor: "#3b82f6" },
    ],
  };
  const doughnutData = {
    labels: ["Sensor Bloqueado", "Sensor Libre"],
    datasets: [
      {
        data: sensorOn ? [1, 0] : [0, 1],
        backgroundColor: ["#10b981", "#ef4444"],
      },
    ],
  };

  // Nueva gráfica de dona para origen de eventos
  const eventOriginData = {
    labels: ["APP", "WEB", "CIRCUITO"],
    datasets: [
      {
        data: [eventOrigins.APP, eventOrigins.WEB, eventOrigins.CIRCUITO],
        backgroundColor: ["#f59e0b", "#3b82f6", "#10b981"],
      },
    ],
  };

  // Nueva gráfica de línea para evolución del contador
  const counterData = {
    labels: counterPoints.map((p) =>
      toColombiaTime(p.ts).toLocaleTimeString("es-CO")
    ),
    datasets: [
      {
        label: "Valor del Contador",
        data: counterPoints.map((p) => p.value),
        borderColor: "#8b5cf6",
        tension: 0.3,
      },
    ],
  };

  // Estilos base para las grillas
  const gridBaseStyle = { display: 'grid', gap: '16px', width: '100%' }
  
  // Media queries aplicadas con condición de ventana
  const isWideScreen = window.innerWidth >= 1200
  const isMediumScreen = window.innerWidth >= 768 && window.innerWidth < 1200
  
  const topGridStyle = {
    ...gridBaseStyle,
    gridTemplateColumns: isWideScreen ? 'repeat(3, 1fr)' : (isMediumScreen ? 'repeat(2, 1fr)' : '1fr'),
    marginBottom: '16px'
  }
  
  const bottomGridStyle = {
    ...gridBaseStyle,
    gridTemplateColumns: isWideScreen || isMediumScreen ? 'repeat(2, 1fr)' : '1fr',
    marginTop: '16px'
  }
  
  // Altura base para las tarjetas según el viewport
  const chartBaseHeight = Math.min(window.innerHeight * 0.45, 420)
  const cardBaseStyle = {
    display: 'flex',
    flexDirection: 'column',
    height: chartBaseHeight,
    minHeight: '300px',
    overflow: 'hidden'
  }
  
  // Opciones comunes para todos los gráficos
  const chartOptions = {
    maintainAspectRatio: false,
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          boxWidth: 12,
          padding: 8
        }
      }
    }
  }
  
  // Opciones específicas para gráficos tipo dona
  const doughnutOptions = {
    ...chartOptions,
    cutout: '65%',
    plugins: {
      ...chartOptions.plugins,
      legend: {
        ...chartOptions.plugins.legend,
        position: 'right'
      }
    }
  }

  return (
    <div>
      <div className="grid">
        {indicators.map((it) => (
          <div className="card" key={it.label}>
            <h4>{it.label}</h4>
            {it.content ? (
              it.content
            ) : (
              <div style={{ fontSize: 28, fontWeight: 700 }}>{it.value}</div>
            )}
          </div>
        ))}
      </div>

      {/* Top row: 3 charts */}
      <div style={topGridStyle}>
        <div className="card" style={cardBaseStyle}>
          <h4>Línea (histórico obstáculos)</h4>
          <div style={{ flex: 1, minHeight: 0 }}>
            <Line data={lineData} options={chartOptions} />
          </div>
        </div>

        <div className="card" style={cardBaseStyle}>
          <h4>Barras (LEDs)</h4>
          <div style={{ flex: 1, minHeight: 0 }}>
            <Bar data={barData} options={chartOptions} />
          </div>
        </div>

        <div className="card" style={cardBaseStyle}>
          <h4>Dona (sensor)</h4>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Doughnut data={doughnutData} options={doughnutOptions} />
          </div>
        </div>
      </div>

      {/* Bottom row: 2 charts */}
      <div style={bottomGridStyle}>
        <div className="card" style={cardBaseStyle}>
          <h4>Origen de eventos</h4>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Doughnut data={eventOriginData} options={doughnutOptions} />
          </div>
        </div>

        <div className="card" style={cardBaseStyle}>
          <h4>Evolución del contador</h4>
          <div style={{ flex: 1, minHeight: 0 }}>
            <Line data={counterData} options={chartOptions} />
          </div>
        </div>
      </div>
    </div>
  );
}
