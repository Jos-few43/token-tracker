# Token Tracker Dashboard — NEXUS // TOKEN OS

Multi-provider AI token usage monitoring dashboard with real-time analytics, glass morphism design, and spend timeline charts.

## Overview

Track OAuth accounts, API keys, LiteLLM spend logs, and usage statistics across multiple AI providers from a single web interface.

### Tracked Providers

**OAuth Providers:**
- Google Antigravity
- Gemini CLI
- Qwen Portal
- Claude Code

**API Keys:**
- Groq
- Gemini API (Direct)
- OpenCode
- OpenRouter
- Anthropic (Claude)

## Features

- Real-time token usage tracking with 10-second auto-refresh
- OAuth account management with ASCII avatars and health bars
- TPM/RPM limit monitoring per provider
- LiteLLM spend log integration (`/spend/logs` endpoint)
- Per-model cost calculation (9 models + default pricing)
- Glass morphism UI: `backdrop-filter: blur(12px)`, radial gradient backgrounds
- Spend timeline chart (Chart.js) with hourly aggregation
- Usage analytics: hourly, 24h, 7d, 30d, all-time
- Graceful fallback when LiteLLM is unavailable

## Quick Start

### Local

```bash
pip install -r requirements.txt
python token_dashboard_nexus.py
# Dashboard at http://localhost:5056
```

### Docker

```bash
docker compose up
# Dashboard at http://localhost:5056
```

### Tests

```bash
python -m pytest tests/ -v
```

## Data Sources

- `~/.config/opencode/antigravity-accounts.json` — OpenCode OAuth accounts
- `~/.openclaw/agents/main/agent/auth-profiles.json` — OpenClaw auth profiles
- `/tmp/litellm-full-env` — LiteLLM API keys
- `~/.openclaw/usage-stats.json` — Local usage statistics
- `http://localhost:4000/spend/logs` — LiteLLM spend logs (live)

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard HTML |
| `GET /api/spend` | LiteLLM spend logs with cost calculation |
| `GET /api/spend?aggregate=hourly` | Hourly aggregated spend for charts |
| `GET /api/oauth` | OAuth account status |
| `GET /api/apikeys` | API key status |
| `GET /api/stats` | Usage statistics |

## Model Pricing (per million tokens)

| Model | Input | Output |
|---|---|---|
| claude-opus-4-6 | $15.00 | $75.00 |
| claude-sonnet-4-5 | $3.00 | $15.00 |
| claude-haiku-4-5 | $0.80 | $4.00 |
| gemini-3-flash | $0.10 | $0.40 |
| gemini-3-pro | $1.25 | $10.00 |
| gpt-oss-120b | $0.00 | $0.00 |
| llama-3.3-70b-versatile | $0.59 | $0.79 |
| deepseek-r1 | $0.55 | $2.19 |
| qwen-2.5-coder-32b | $0.20 | $0.20 |

## Project Structure

```
token-tracker/
├── token_dashboard_nexus.py   # Single-file Flask app (HTML/CSS/JS embedded)
├── token-dashboard-v1.py      # Previous version (reference only)
├── tests/
│   └── test_dashboard.py      # pytest test suite (7 tests)
├── requirements.txt            # Flask, requests, pytest
├── Dockerfile                  # python:3.12-slim, port 5056
├── docker-compose.yml          # With LiteLLM URL + config volume mounts
├── .dockerignore
├── DESIGN-MERGE-PLAN.md       # Glass morphism design spec (implemented)
└── README.md
```

## Architecture

- **Backend**: Flask (Python 3)
- **Frontend**: Vanilla HTML/CSS/JavaScript (embedded in Python f-string)
- **Charts**: Chart.js 4.4 (CDN)
- **Design**: Glass morphism — `rgba(20, 20, 25, 0.7)` + `backdrop-filter: blur(12px)`
- **Port**: 5056

## Browser Support

- Chrome 76+ (backdrop-filter)
- Firefox 103+
- Safari 9+
- Edge (Chromium)

## License

MIT
