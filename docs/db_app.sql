-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 21-10-2025 a las 20:00:00
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
 /*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
 /*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
 /*!40101 SET NAMES utf8mb4 */;

-- --------------------------------------------------------
-- BASE DE DATOS: db_app
-- --------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `db_app` 
  DEFAULT CHARACTER SET utf8mb4 
  COLLATE utf8mb4_general_ci;
USE `db_app`;

-- --------------------------------------------------------
-- TABLA: usuarios
-- --------------------------------------------------------
CREATE TABLE `usuarios` (
  `id_usuario` int(11) NOT NULL AUTO_INCREMENT,
  `usuario` varchar(100) NOT NULL,
  `contrasena` varchar(255) NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `activo` tinyint(1) DEFAULT 1,
  `rol` enum('ADMIN','USER') NOT NULL DEFAULT 'USER',
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `usuario` (`usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- TABLA: eventos
-- --------------------------------------------------------
CREATE TABLE `eventos` (
  `id_evento` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `tipo_evento` enum('LED_ON','LED_OFF','SENSOR_BLOQUEADO','SENSOR_LIBRE','RESET_CONTADOR','CONTADOR_CAMBIO','LOGIN') NOT NULL,
  `detalle` enum('LED1','LED2','LED3','LED4','SENSOR_IR','CONTADOR','LOGIN_USER') NOT NULL,
  `origen` enum('APP','WEB','CIRCUITO') NOT NULL,
  `origen_ip` varchar(45) DEFAULT NULL,
  `valor` varchar(50) NOT NULL,
  `fecha_hora` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_evento`),
  KEY `id_usuario` (`id_usuario`),
  KEY `idx_usuario_fecha` (`id_usuario`, `fecha_hora`),
  CONSTRAINT `fk_eventos_usuario` FOREIGN KEY (`id_usuario`) 
    REFERENCES `usuarios` (`id_usuario`) 
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- TABLA: historialexportado
-- --------------------------------------------------------
CREATE TABLE `historialexportado` (
  `id_exportacion` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `formato` enum('CSV','PDF') NOT NULL,
  `fecha_exportacion` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_exportacion`),
  KEY `id_usuario` (`id_usuario`),
  CONSTRAINT `fk_historial_usuario` FOREIGN KEY (`id_usuario`) 
    REFERENCES `usuarios` (`id_usuario`) 
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- TABLA: dispositivos
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `dispositivos` (
  `id_dispositivo` int(11) NOT NULL AUTO_INCREMENT,
  `device_id` varchar(255) NOT NULL UNIQUE,
  `nombre` varchar(100) DEFAULT NULL,
  `token_device` varchar(255) DEFAULT NULL,
  `last_seen` timestamp NULL DEFAULT NULL,
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_dispositivo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- TABLA: commands
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `commands` (
  `id_command` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `device_id` varchar(100) DEFAULT NULL,
  `tipo` enum('LED','MOTOR','SYSTEM') NOT NULL,
  `detalle` varchar(50) NOT NULL,
  `accion` enum('ON','OFF','STATUS','SHOW_USER') NOT NULL,
  `enviada` tinyint(1) NOT NULL DEFAULT 0,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_command`),
  CONSTRAINT `fk_commands_usuario` FOREIGN KEY (`id_usuario`) 
    REFERENCES `usuarios`(`id_usuario`) 
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- TABLA: estados_actuales
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `estados_actuales` (
  `id_estado` int(11) NOT NULL AUTO_INCREMENT,
  `device_id` varchar(100) DEFAULT NULL,
  `detalle` varchar(50) NOT NULL,
  `valor` varchar(20) NOT NULL,
  `fecha_actualizacion` timestamp NOT NULL 
      DEFAULT current_timestamp() 
      ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
 /*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
 /*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
