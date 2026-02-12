# Token Tracker Dashboard 🎯

Multi-provider AI token usage monitoring dashboard with real-time analytics and cyberpunk aesthetics.

## Overview

Track OAuth accounts, API keys, and usage statistics across multiple AI providers from a single, beautiful web interface.

### Tracked Providers

**OAuth Providers:**
- Google Antigravity
- Gemini CLI
- Qwen Portal
- Claude Code

**API Keys:**
- Groq
- Gemini API
- OpenCode
- OpenRouter
- Anthropic (Claude)

## Versions

### 🚀 token-dashboard-nexus.py (Latest)
**Cyberpunk Terminal Theme** - Full-featured dashboard with real-time monitoring

**Features:**
- 📊 Real-time token usage tracking
- 🔐 OAuth account management
- 🎯 TPM/RPM limit monitoring
- 📈 Usage analytics (hourly, daily, weekly, monthly)
- 🎨 Cyberpunk grid aesthetic with ASCII avatars
- ⚡ Live uptime tracking
- 🎭 Provider status indicators
- 📱 Responsive design

**Design:**
- Neon cyan/green accents (#00d9ff, #00ff41)
- Grid background with glow effects
- Terminal-inspired typography (JetBrains Mono)
- Sharp edges, high contrast

### 📦 token-dashboard-v1.py (Previous)
**Original Implementation** - Earlier version, smaller codebase (951 lines)

## Installation

### Requirements

```bash
pip install flask
```

### Quick Start

```bash
# Run the dashboard
python3 token-dashboard-nexus.py

# Access in browser
open http://localhost:5000
```

### Data Sources

The dashboard reads from:
- `~/.config/opencode/antigravity-accounts.json` - OpenCode OAuth accounts
- `~/.openclaw/agents/main/agent/auth-profiles.json` - OpenClaw auth profiles
- `/tmp/litellm-full-env` - LiteLLM API keys
- `~/.openclaw/usage-stats.json` - Usage statistics

## Design Evolution

### Current: Cyberpunk Terminal
- Hard edges, grid patterns
- Neon colors (cyan, green, purple)
- ASCII art avatars
- Terminal aesthetic

### Planned: Glass Morphism (DESIGN-MERGE-PLAN.md)
- Soft translucent cards
- Backdrop blur effects
- Gradient backgrounds
- Indigo accent (#6366f1)
- iOS-inspired design language

See `DESIGN-MERGE-PLAN.md` for the glass morphism design specification.

## Features Deep Dive

### Token Monitoring
- Track TPM (Tokens Per Minute) and RPM (Requests Per Minute) limits
- Real-time usage across all providers
- Model-specific tracking

### Analytics Dashboard
- **Hourly**: Last 60 minutes
- **Daily**: Last 24 hours
- **Weekly**: Last 7 days
- **Monthly**: Last 30 days
- **All-time**: Complete history

### Provider Management
- Auto-detect OAuth accounts from config files
- API key validation and status checking
- Dashboard links for each provider
- Color-coded status indicators

### Model Tracking
- Per-model request counts
- Token consumption by model
- Multi-provider model support

## Development

### Project Structure

```
token-tracker/
├── token-dashboard-nexus.py    # Current version (cyberpunk)
├── token-dashboard-v1.py       # Previous version
├── DESIGN-MERGE-PLAN.md        # Glass morphism design spec
└── README.md                   # This file
```

### Running in Development

```bash
# With auto-reload
export FLASK_ENV=development
python3 token-dashboard-nexus.py
```

### Customization

Edit provider configurations in the script:
- `OAUTH_PROVIDERS` - OAuth provider limits and models
- `API_PROVIDERS` - API key provider details

## Architecture

**Stack:**
- Backend: Flask (Python 3)
- Frontend: Vanilla HTML/CSS/JavaScript
- Design: Single-file architecture (HTML embedded in Python)

**Why Single-File?**
- Rapid development and deployment
- No build process required
- Easy to modify and understand
- Self-contained distribution

## Browser Support

- Chrome 76+ (backdrop-filter support)
- Firefox 103+
- Safari 9+
- Edge (Chromium)

## Performance

- Lightweight: ~1200 lines of code
- No external dependencies (except Flask)
- Real-time updates without polling
- Optimized CSS animations (GPU-accelerated)

## Future Enhancements

- [ ] Apply glass morphism design from DESIGN-MERGE-PLAN.md
- [ ] Add theme switcher (cyberpunk ↔ glass)
- [ ] WebSocket support for live updates
- [ ] Export usage data (CSV/JSON)
- [ ] Historical charts (Chart.js integration)
- [ ] Multi-user support
- [ ] Authentication layer
- [ ] Docker deployment

## Contributing

Feel free to fork and customize for your own use case!

## License

MIT

---

**Built for monitoring AI provider usage across multiple platforms** 🤖
