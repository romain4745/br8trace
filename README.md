# BR8Trace – Advanced OSINT & Satellite Intelligence Framework

![Status](https://img.shields.io/badge/status-active-brightgreen) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![License](https://img.shields.io/badge/license-Educational-orange)

<p align="center">
  <img src="https://github.com/user-attachments/assets/94d7a46f-4257-4f90-861b-6f9335f0c4a5" alt="BR8Trace Banner" width="800"/>
</p>

## 📡 Overview

BR8Trace is a comprehensive OSINT and satellite imagery analysis framework with a hacker-themed interface. It combines traditional OSINT capabilities (IP, email, phone, username intelligence) with advanced geospatial processing and dark web monitoring.

<p align="center">
  <img src="https://github.com/user-attachments/assets/cc9c6f4f-46dd-4ebb-bf30-b2fa3ee9d2ca" alt="Web UI Dashboard" width="800"/>
</p>

⚠️ **IMPORTANT**: BR8Trace is intended for **legal OSINT only**. See `LEGAL.md`.

---

## ✨ Features

### OSINT Intelligence
- **IP Intelligence**: WHOIS, geolocation, ISP/ASN, VPN/Proxy, blacklists
- **Email Intelligence**: Breach detection, domain reputation
- **Phone Intelligence**: Carrier detection, country code
- **Username Intelligence**: 100+ platforms (GitHub, Twitter, Instagram, LinkedIn, etc.)
- **Dark Web Scanner**: Tor-based .onion domain checking

### Satellite & Geospatial
- **Satellite Search**: Planet Labs API (PlanetScope, SkySat, RapidEye)
- **GeoTIFF Processing**: Clipping, merging, tiling, compression
- **Vegetation Analysis**: NDVI, NDWI index calculation
- **Raster to Vector**: Polygon extraction, shapefile smoothing

### Analysis & Reporting
- **Reputation Scoring**: 0-100 risk score
- **Timeline Builder**: Chronological event tracking
- **PDF Reports**: Professional investigation reports
- **JSON Export**: Machine-readable output

### User Interface
- Black background with neon green font (#00FF41)
- Matrix digital rain animation
- Animated scan progress with live console
- Blinking cursor effects
- CLI and Web interfaces

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB (optional)
- Tor (optional, for dark web)
- GDAL (for satellite processing)

### Installation

```bash
cd /path/to/BR8Trace
chmod +x setup.sh run.sh
./setup.sh
cp .env.example .env
# Edit .env with your API keys
