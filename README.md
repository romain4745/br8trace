# BR8Trace – Advanced OSINT & Satellite Intelligence Framework



## 📡 Overview

BR8Trace is a comprehensive OSINT and satellite imagery analysis framework with a hacker-themed interface. It combines traditional OSINT capabilities (IP, email, phone, username intelligence) with advanced geospatial processing and dark web monitoring.


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
