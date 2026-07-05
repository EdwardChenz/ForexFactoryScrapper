---
title: ForexFactory Scrapper
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# ForexFactory Scrapper

A Flask-based API for scraping Forex Factory economic calendar data.

## API Endpoints

- `GET /` - Welcome page
- `GET /api/forex/daily?day=1&month=1&year=2024` - Get daily forex data
- `GET /api/helper/health` - Health check
- `GET /api/swagger` - API documentation