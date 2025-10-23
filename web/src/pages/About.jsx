import React from 'react'

export default function About(){
  return (
    <div className="about-page">
      <div className="card">
        <h3>Acerca de</h3>
        <p><strong>Proyecto:</strong> App ESP32 - Interfaz web</p>
        <div className="creators">
          <p><strong>Creadores:</strong></p>
          <ul>
            <li>Stiven Amorocho — realizó la app y el frontend</li>
            <li>Jose Angarita — realizó armamiento de circuito y base de datos</li>
            <li>Osvaldo Ospino — realizó armamiento de circuito y backend</li>
          </ul>
        </div>
        <p><strong>Contacto:</strong> <a href="mailto:amorochocordoba@gmail.com">amorochocordoba@gmail.com</a></p>
      </div>

      <div className="card project-description">
        <h4>Descripción del proyecto</h4>
        <p>
          Esta aplicación permite controlar y monitorear un dispositivo basado en ESP32
          desde una interfaz web y una aplicación de escritorio. Incluye autenticación
          de usuarios, almacenamiento de datos en una base de datos y comunicación con
          el microcontrolador para enviar comandos y recibir eventos en tiempo real.
        </p>
        <p>
          El objetivo es ofrecer una solución completa (hardware + backend + frontend)
          para proyectos IoT educativos y prototipos, facilitando la gestión de dispositivos,
          visualización de lecturas y el control remoto desde una interfaz moderna.
        </p>
      </div>
    </div>
  )
}
