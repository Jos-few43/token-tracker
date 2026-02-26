#!/usr/bin/env python3
"""NEXUS // TOKEN OS - Cyberpunk Terminal Dashboard"""

from flask import Flask, jsonify
import json
from datetime import datetime, timedelta
from pathlib import Path
import time
import requests as http_requests

app = Flask(__name__)

LITELLM_URL = 'http://localhost:4000'
OPENCODE_ACCOUNTS = Path.home() / '.config/opencode/antigravity-accounts.json'
OPENCLAW_AUTH = Path.home() / '.openclaw/agents/main/agent/auth-profiles.json'
LITELLM_ENV = Path('/tmp/litellm-full-env')
USAGE_LOG = Path.home() / '.openclaw/usage-stats.json'
START_TIME = time.time()

# OAuth providers with ASCII avatars
OAUTH_PROVIDERS = {
    'google-antigravity': {
        'tpm': 4000000, 'rpm': 60,
        'models': ['claude-opus-4-6', 'claude-opus-4-6-thinking', 'claude-sonnet-4-5',
                  'gemini-3-flash', 'gemini-3-pro', 'gpt-oss-120b'],
        'avatar': '(○ᴗ○)',
        'color': '#00ff41'
    },
    'google-gemini-cli': {
        'tpm': 1000000, 'rpm': 15,
        'models': ['gemini-3-flash', 'gemini-3-pro', 'gemini-2.0-flash-exp',
                  'gemini-2.0-flash-thinking-exp'],
        'avatar': '(○◡○)',
        'color': '#00d9ff'
    },
    'qwen-portal': {
        'tpm': 100000, 'rpm': 10,
        'models': ['coder-model', 'vision-model'],
        'avatar': '(○‿○)',
        'color': '#ff6b35'
    },
    'claude-code': {
        'tpm': 4000000, 'rpm': 50,
        'models': ['claude-opus-4-6', 'claude-sonnet-4-5', 'claude-haiku-4-5'],
        'avatar': '(◕‿◕✿)',
        'color': '#a78bfa'
    }
}

# API Keys with ASCII avatars and dashboard URLs
API_PROVIDERS = {
    'groq': {
        'tpm': 30000, 'rpm': 30, 'name': 'Groq',
        'models': ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
        'dashboardUrl': 'https://console.groq.com/keys',
        'avatar': '(◕‿◕)',
        'color': '#ff6b35'
    },
    'gemini': {
        'tpm': 1000000, 'rpm': 15, 'name': 'Gemini API (Direct)',
        'models': ['gemini-2.0-flash-exp', 'gemini-2.0-flash-thinking-exp'],
        'dashboardUrl': 'https://aistudio.google.com/apikey',
        'avatar': '(◕‿◕✿)',
        'color': '#00d9ff'
    },
    'opencode': {
        'tpm': 100000, 'rpm': 10, 'name': 'OpenCode',
        'models': ['kimi-k2.5-free', 'deepseek-r1-free'],
        'dashboardUrl': 'https://opencode.com/dashboard',
        'avatar': '(⌐■_■)',
        'color': '#00ff41'
    },
    'openrouter': {
        'tpm': 200000, 'rpm': 20, 'name': 'OpenRouter',
        'models': ['qwen-2.5-coder-32b', 'deepseek-r1', 'llama-3.1-70b'],
        'dashboardUrl': 'https://openrouter.ai/settings/keys',
        'avatar': '(◉‿◉)',
        'color': '#a78bfa'
    },
    'anthropic': {
        'tpm': 4000000, 'rpm': 50, 'name': 'Claude (Anthropic API)',
        'models': ['claude-opus-4-6', 'claude-sonnet-4-5', 'claude-haiku-4-5'],
        'dashboardUrl': 'https://console.anthropic.com/settings/keys',
        'avatar': '(◕ᴗ◕✿)',
        'color': '#8b5cf6'
    }
}

# Pricing per million tokens (input, output) in USD
MODEL_PRICING = {
    'claude-opus-4-6':           (15.0, 75.0),
    'claude-sonnet-4-5':         (3.0, 15.0),
    'claude-haiku-4-5':          (0.80, 4.0),
    'gemini-3-flash':            (0.10, 0.40),
    'gemini-3-pro':              (1.25, 10.0),
    'gpt-oss-120b':              (0.0, 0.0),
    'llama-3.3-70b-versatile':   (0.59, 0.79),
    'deepseek-r1':               (0.55, 2.19),
    'qwen-2.5-coder-32b':        (0.20, 0.20),
}
DEFAULT_PRICING = (1.0, 3.0)

def calculate_cost(model, prompt_tokens=0, completion_tokens=0):
    """Calculate cost in USD for a given model and token counts"""
    input_rate, output_rate = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000

def read_json(filepath):
    try:
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
    except:
        pass
    return None

def read_env_file():
    keys = {}
    try:
        if LITELLM_ENV.exists():
            with open(LITELLM_ENV) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if 'API_KEY' in key:
                            keys[key] = value
    except:
        pass
    return keys

def mask_key(key):
    if not key or len(key) < 8:
        return '***'
    return f"{key[:8]}...{key[-4:]}"

def format_timestamp(ts_ms):
    if not ts_ms or ts_ms == 0:
        return "Never"
    try:
        return datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "Invalid"

def get_time_until(ts_ms):
    if not ts_ms:
        return None
    try:
        now = datetime.now()
        target = datetime.fromtimestamp(ts_ms / 1000)
        if target < now:
            return "Expired"
        delta = target - now
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return f"{int(delta.total_seconds() / 60)}m"
        elif hours < 24:
            return f"{int(hours)}h {int((delta.total_seconds() % 3600) / 60)}m"
        else:
            days = int(hours / 24)
            remaining_hours = int(hours % 24)
            return f"{days}d {remaining_hours}h"
    except:
        return None

def estimate_usage(account):
    if account['isRateLimited']:
        return 95 + (account['errorCount'] % 5)
    error_factor = min(account['errorCount'] * 15, 60)
    if account.get('lastUsedMs') and account['lastUsedMs'] > 0:
        now_ms = int(datetime.now().timestamp() * 1000)
        hours_since = (now_ms - account['lastUsedMs']) / (1000 * 3600)
        if hours_since < 1:
            recency_factor = 30
        elif hours_since < 24:
            recency_factor = 15
        else:
            recency_factor = 5
    else:
        recency_factor = 0
    return min(error_factor + recency_factor, 85)

def init_usage_log():
    """Initialize usage log if it doesn't exist"""
    if not USAGE_LOG.exists():
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG, 'w') as f:
            json.dump({'entries': [], 'created': datetime.now().isoformat()}, f)

def get_usage_stats():
    """Get usage statistics from log with model tracking"""
    init_usage_log()
    data = read_json(USAGE_LOG) or {'entries': []}

    now = datetime.now()
    periods = {
        '24h': now - timedelta(hours=24),
        '7d': now - timedelta(days=7),
        '30d': now - timedelta(days=30)
    }

    stats = {
        'total': {'requests': 0, 'tokens': 0, 'providers': {}, 'models': {}},
        '24h': {'requests': 0, 'tokens': 0, 'providers': {}, 'models': {}},
        '7d': {'requests': 0, 'tokens': 0, 'providers': {}, 'models': {}},
        '30d': {'requests': 0, 'tokens': 0, 'providers': {}, 'models': {}}
    }

    for entry in data.get('entries', []):
        try:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            provider = entry['provider']
            model = entry.get('model', 'unknown')
            tokens = entry.get('tokens', 0)

            # All-time
            stats['total']['requests'] += 1
            stats['total']['tokens'] += tokens
            stats['total']['providers'][provider] = stats['total']['providers'].get(provider, 0) + 1

            # Model tracking
            if model not in stats['total']['models']:
                stats['total']['models'][model] = {'requests': 0, 'tokens': 0}
            stats['total']['models'][model]['requests'] += 1
            stats['total']['models'][model]['tokens'] += tokens

            # Time periods
            for period, cutoff in periods.items():
                if timestamp >= cutoff:
                    stats[period]['requests'] += 1
                    stats[period]['tokens'] += tokens
                    stats[period]['providers'][provider] = stats[period]['providers'].get(provider, 0) + 1

                    # Model tracking for period
                    if model not in stats[period]['models']:
                        stats[period]['models'][model] = {'requests': 0, 'tokens': 0}
                    stats[period]['models'][model]['requests'] += 1
                    stats[period]['models'][model]['tokens'] += tokens
        except:
            continue

    return stats

@app.route('/api/spend')
def api_spend():
    entries = []
    source = 'local'
    try:
        resp = http_requests.get(f'{LITELLM_URL}/spend/logs', timeout=5)
        if resp.status_code == 200:
            source = 'litellm'
            raw = resp.json()
            for entry in (raw if isinstance(raw, list) else raw.get('data', [])):
                entries.append({
                    'timestamp': entry.get('startTime', ''),
                    'model': entry.get('model', 'unknown'),
                    'spend': entry.get('spend', 0),
                    'total_tokens': entry.get('total_tokens', 0),
                    'prompt_tokens': entry.get('prompt_tokens', 0),
                    'completion_tokens': entry.get('completion_tokens', 0),
                    'cost': calculate_cost(
                        entry.get('model', 'unknown'),
                        entry.get('prompt_tokens', 0),
                        entry.get('completion_tokens', 0)
                    ),
                })
    except (http_requests.ConnectionError, http_requests.Timeout):
        data = read_json(USAGE_LOG) or {'entries': []}
        for entry in data.get('entries', []):
            entries.append({
                'timestamp': entry.get('timestamp', ''),
                'model': entry.get('model', 'unknown'),
                'spend': 0,
                'total_tokens': entry.get('tokens', 0),
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'cost': calculate_cost(
                    entry.get('model', 'unknown'),
                    0,
                    0
                ),
            })
    return jsonify({'entries': entries, 'source': source})

@app.route('/')
def index():
    oauth_data = read_json(OPENCODE_ACCOUNTS) or {}
    oauth_accounts = oauth_data.get('accounts', [])

    openclaw_data = read_json(OPENCLAW_AUTH) or {}
    openclaw_profiles = openclaw_data.get('profiles', [])

    api_keys = read_env_file()

    usage_stats = get_usage_stats()
    uptime = int(time.time() - START_TIME)

    # Serialize providers to JSON for JavaScript
    oauth_providers_json = json.dumps(OAUTH_PROVIDERS)
    api_providers_json = json.dumps(API_PROVIDERS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS // TOKEN OS</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0d1a;
            --bg-secondary: #0f1322;
            --bg-tertiary: #141829;
            --border-glow: #00d9ff;
            --border-dim: #1a2332;
            --accent-cyan: #00d9ff;
            --accent-green: #00ff41;
            --accent-red: #ff3366;
            --accent-yellow: #ffd700;
            --accent-purple: #a78bfa;
            --text-primary: #e0e7ff;
            --text-secondary: #94a3b8;
            --text-dim: #64748b;
            --status-online: #00ff41;
            --status-limited: #ff3366;
            --status-idle: #ffd700;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            line-height: 1.6;
            overflow-x: hidden;
        }}

        /* Cyberpunk grid background */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(0deg, transparent 24%, rgba(0, 217, 255, .05) 25%, rgba(0, 217, 255, .05) 26%, transparent 27%, transparent 74%, rgba(0, 217, 255, .05) 75%, rgba(0, 217, 255, .05) 76%, transparent 77%, transparent),
                linear-gradient(90deg, transparent 24%, rgba(0, 217, 255, .05) 25%, rgba(0, 217, 255, .05) 26%, transparent 27%, transparent 74%, rgba(0, 217, 255, .05) 75%, rgba(0, 217, 255, .05) 76%, transparent 77%, transparent);
            background-size: 50px 50px;
            opacity: 0.3;
            z-index: 0;
            pointer-events: none;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }}

        /* Header */
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--border-dim);
            margin-bottom: 30px;
            position: relative;
        }}

        .header h1 {{
            font-size: 36px;
            font-weight: 700;
            letter-spacing: 4px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 30px rgba(0, 217, 255, 0.3);
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        /* System status bar */
        .system-status {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-dim);
            border-radius: 4px;
            margin-bottom: 25px;
            font-size: 11px;
        }}

        .system-status .status-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .system-status .status-item .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--status-online);
            box-shadow: 0 0 10px var(--status-online);
            animation: pulse 2s ease-in-out infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}

        /* Tiles */
        .tile {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-dim);
            border-radius: 6px;
            margin-bottom: 20px;
            overflow: hidden;
            transition: all 0.3s ease;
        }}

        .tile:hover {{
            border-color: var(--border-glow);
            box-shadow: 0 0 20px rgba(0, 217, 255, 0.2);
        }}

        .tile-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border-dim);
        }}

        .tile-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: var(--accent-cyan);
        }}

        .tile-icon {{
            font-size: 14px;
        }}

        .tile-controls {{
            display: flex;
            gap: 10px;
            color: var(--text-dim);
        }}

        .tile-btn {{
            cursor: pointer;
            transition: color 0.2s;
        }}

        .tile-btn:hover {{
            color: var(--accent-cyan);
        }}

        .tile-body {{
            padding: 20px;
        }}

        /* Pet card */
        .pet-card {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border-dim);
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
            position: relative;
            transition: all 0.3s ease;
        }}

        .pet-card:hover {{
            border-color: var(--border-glow);
            transform: translateY(-2px);
        }}

        .pet-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }}

        .pet-avatar {{
            font-size: 32px;
            line-height: 1;
            animation: float 3s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-5px); }}
        }}

        .pet-info {{
            flex: 1;
        }}

        .pet-name {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }}

        .pet-type {{
            font-size: 10px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .pet-status {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .status-online {{
            background: rgba(0, 255, 65, 0.15);
            color: var(--status-online);
            border: 1px solid var(--status-online);
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
        }}

        .status-limited {{
            background: rgba(255, 51, 102, 0.15);
            color: var(--status-limited);
            border: 1px solid var(--status-limited);
        }}

        .status-idle {{
            background: rgba(255, 215, 0, 0.15);
            color: var(--status-idle);
            border: 1px solid var(--status-idle);
        }}

        /* Health bar */
        .health-bar {{
            margin: 15px 0;
        }}

        .health-label {{
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            color: var(--text-dim);
            margin-bottom: 6px;
        }}

        .health-track {{
            height: 6px;
            background: var(--bg-primary);
            border-radius: 3px;
            overflow: hidden;
            position: relative;
        }}

        .health-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
            border-radius: 3px;
            position: relative;
            transition: width 0.3s ease;
        }}

        .health-fill::after {{
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 30%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3));
            animation: shimmer 2s ease-in-out infinite;
        }}

        @keyframes shimmer {{
            0%, 100% {{ opacity: 0; }}
            50% {{ opacity: 1; }}
        }}

        /* Pet stats */
        .pet-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 8px;
            background: var(--bg-primary);
            border-radius: 3px;
            font-size: 11px;
        }}

        .stat-label {{
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-value {{
            color: var(--accent-cyan);
            font-weight: 600;
        }}

        /* Models list */
        .models-list {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border-dim);
        }}

        .models-label {{
            font-size: 10px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}

        .model-tag {{
            display: inline-block;
            padding: 4px 8px;
            margin: 3px 3px 3px 0;
            background: var(--bg-primary);
            border: 1px solid var(--border-dim);
            border-radius: 3px;
            font-size: 10px;
            color: var(--text-secondary);
            transition: all 0.2s;
        }}

        .model-tag:hover {{
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }}

        /* Dashboard link */
        .dashboard-link {{
            display: inline-block;
            margin-top: 10px;
            padding: 6px 12px;
            background: var(--bg-primary);
            border: 1px solid var(--border-glow);
            border-radius: 3px;
            color: var(--accent-cyan);
            text-decoration: none;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            transition: all 0.3s;
            cursor: pointer;
            position: relative;
            z-index: 10;
        }}

        .dashboard-link:hover {{
            background: var(--accent-cyan);
            color: var(--bg-primary);
            box-shadow: 0 0 15px rgba(0, 217, 255, 0.5);
            transform: translateY(-2px);
        }}

        /* Memory pool */
        .memory-pool {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 20px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-dim);
            border-radius: 6px;
            margin-top: 30px;
        }}

        .pool-label {{
            font-size: 11px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .pool-dots {{
            flex: 1;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .pool-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }}

        .pool-dot:nth-child(4n+1) {{
            background: var(--accent-cyan);
            box-shadow: 0 0 10px var(--accent-cyan);
        }}

        .pool-dot:nth-child(4n+2) {{
            background: var(--accent-green);
            box-shadow: 0 0 10px var(--accent-green);
            animation-delay: 0.5s;
        }}

        .pool-dot:nth-child(4n+3) {{
            background: var(--accent-purple);
            box-shadow: 0 0 10px var(--accent-purple);
            animation-delay: 1s;
        }}

        .pool-dot:nth-child(4n) {{
            background: var(--accent-yellow);
            box-shadow: 0 0 10px var(--accent-yellow);
            animation-delay: 1.5s;
        }}

        /* Stats grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}

        .stat-card {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border-dim);
            border-radius: 4px;
            padding: 15px;
            text-align: center;
        }}

        .stat-card-label {{
            font-size: 10px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}

        .stat-card-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--accent-cyan);
        }}

        /* Auto-refresh indicator */
        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .refreshing {{
            animation: spin 1s linear infinite;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>NEXUS // TOKEN OS</h1>
            <div class="subtitle">Multi-Account Token Management System</div>
        </div>

        <!-- System Status -->
        <div class="system-status">
            <div class="status-item">
                <div class="dot"></div>
                <span>SYSTEM ONLINE</span>
            </div>
            <div class="status-item">
                <span id="uptime">UPTIME: {uptime}s</span>
            </div>
            <div class="status-item">
                <span id="clock">00:00:00</span>
            </div>
        </div>

        <!-- OAuth Tile -->
        <div class="tile">
            <div class="tile-header">
                <div class="tile-title">
                    <span class="tile-icon">⚡</span>
                    <span>OAUTH NODE</span>
                </div>
                <div class="tile-controls">
                    <span class="tile-btn">◐</span>
                    <span class="tile-btn">×</span>
                </div>
            </div>
            <div class="tile-body" id="oauth-container">
                <!-- OAuth accounts will be rendered here -->
            </div>
        </div>

        <!-- API Tile -->
        <div class="tile">
            <div class="tile-header">
                <div class="tile-title">
                    <span class="tile-icon">🔑</span>
                    <span>API NODE</span>
                </div>
                <div class="tile-controls">
                    <span class="tile-btn">◐</span>
                    <span class="tile-btn">×</span>
                </div>
            </div>
            <div class="tile-body" id="api-container">
                <!-- API keys will be rendered here -->
            </div>
        </div>

        <!-- Statistics Tile -->
        <div class="tile">
            <div class="tile-header">
                <div class="tile-title">
                    <span class="tile-icon">📊</span>
                    <span>STATISTICS</span>
                </div>
                <div class="tile-controls">
                    <span class="tile-btn">◐</span>
                    <span class="tile-btn">×</span>
                </div>
            </div>
            <div class="tile-body" id="stats-container">
                <!-- Statistics will be rendered here -->
            </div>
        </div>

        <!-- Memory Pool -->
        <div class="memory-pool">
            <div class="pool-label">MEMORY POOL</div>
            <div class="pool-dots">
                {' '.join([f'<div class="pool-dot"></div>' for _ in range(40)])}
            </div>
        </div>
    </div>

    <script>
        // OAuth providers config
        const oauthProviders = {oauth_providers_json};
        const apiProviders = {api_providers_json};

        // Update clock
        function updateClock() {{
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('clock').textContent = `${{hours}}:${{minutes}}:${{seconds}}`;
        }}
        setInterval(updateClock, 1000);
        updateClock();

        // Update uptime
        let startTime = {START_TIME};
        function updateUptime() {{
            const uptime = Math.floor(Date.now()/1000 - startTime);
            document.getElementById('uptime').textContent = `UPTIME: ${{uptime}}s`;
        }}
        setInterval(updateUptime, 1000);

        // Render OAuth accounts
        function renderOAuthAccounts(data) {{
            const container = document.getElementById('oauth-container');
            const accounts = data.accounts || [];

            if (accounts.length === 0) {{
                container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 20px;">No OAuth accounts configured</div>';
                return;
            }}

            container.innerHTML = accounts.map(account => {{
                const percentage = account.estimatedUsage || 0;
                const status = account.isRateLimited ? 'limited' : (percentage > 80 ? 'idle' : 'online');
                const statusText = {{
                    'online': 'ONLINE',
                    'limited': 'LIMITED',
                    'idle': 'IDLE'
                }}[status];

                const resetInfo = account.timeUntilReset ?
                    `<div class="stat">
                        <span class="stat-label">RESET IN</span>
                        <span class="stat-value">${{account.timeUntilReset}}</span>
                    </div>` : '';

                return `
                    <div class="pet-card">
                        <div class="pet-header">
                            <div class="pet-avatar" style="color: ${{account.color || '#00d9ff'}}">${{account.avatar || '(○‿○)'}}</div>
                            <div class="pet-info">
                                <div class="pet-name">${{account.email}}</div>
                                <div class="pet-type">${{account.provider}}</div>
                            </div>
                            <div class="pet-status status-${{status}}">${{statusText}}</div>
                        </div>

                        <div class="health-bar">
                            <div class="health-label">
                                <span>${{account.tokensLast24h > 0 ? 'TOKENS (24H)' : 'HEALTH'}}</span>
                                <span>${{account.tokensLast24h > 0 ? account.tokensLast24h.toLocaleString() + ' / ' + account.dailyQuota.toLocaleString() : percentage.toFixed(0) + '% Est.'}}</span>
                            </div>
                            <div class="health-track">
                                <div class="health-fill" style="width: ${{percentage}}%; background: linear-gradient(90deg, ${{account.color || '#00d9ff'}}, var(--accent-green))"></div>
                            </div>
                        </div>

                        <div class="pet-stats">
                            <div class="stat">
                                <span class="stat-label">TPM</span>
                                <span class="stat-value">${{account.quota?.tpm?.toLocaleString() || 'N/A'}}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">RPM</span>
                                <span class="stat-value">${{account.quota?.rpm || 'N/A'}}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">ERRORS</span>
                                <span class="stat-value">${{account.errorCount || 0}}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">${{account.tokensLast24h > 0 ? 'USAGE' : 'LAST USED'}}</span>
                                <span class="stat-value" style="font-size: 9px;">${{account.tokensLast24h > 0 ? percentage.toFixed(1) + '%' : (account.lastUsed || 'Never')}}</span>
                            </div>
                        </div>

                        ${{resetInfo}}

                        ${{account.models && account.models.length > 0 ? `
                            <div class="models-list">
                                <div class="models-label">Available Models (${{account.models.length}})</div>
                                <div>
                                    ${{account.models.map(m => `<span class="model-tag">${{m}}</span>`).join('')}}
                                </div>
                            </div>
                        ` : ''}}
                    </div>
                `;
            }}).join('');
        }}

        // Render API keys
        function renderAPIKeys(data) {{
            const container = document.getElementById('api-container');
            const keys = data.keys || [];

            if (keys.length === 0) {{
                container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 20px;">No API keys configured</div>';
                return;
            }}

            container.innerHTML = keys.map(key => {{
                const status = key.configured ? 'online' : 'idle';
                const statusText = key.configured ? 'ACTIVE' : 'NOT SET';
                const percentage = key.estimatedUsage || 0;

                return `
                    <div class="pet-card">
                        <div class="pet-header">
                            <div class="pet-avatar" style="color: ${{key.color || '#00d9ff'}}">${{key.avatar || '(⌐■_■)'}}</div>
                            <div class="pet-info">
                                <div class="pet-name">${{key.name}}</div>
                                <div class="pet-type">${{key.provider}}</div>
                            </div>
                            <div class="pet-status status-${{status}}">${{statusText}}</div>
                        </div>

                        ${{key.configured ? `
                            <div class="health-bar">
                                <div class="health-label">
                                    <span>USAGE</span>
                                    <span>${{percentage.toFixed(0)}}%</span>
                                </div>
                                <div class="health-track">
                                    <div class="health-fill" style="width: ${{percentage}}%; background: linear-gradient(90deg, ${{key.color || '#00d9ff'}}, var(--accent-green))"></div>
                                </div>
                            </div>
                        ` : ''}}

                        <div class="pet-stats">
                            <div class="stat">
                                <span class="stat-label">TPM</span>
                                <span class="stat-value">${{key.quota?.tpm?.toLocaleString() || 'N/A'}}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">RPM</span>
                                <span class="stat-value">${{key.quota?.rpm || 'N/A'}}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">KEY</span>
                                <span class="stat-value" style="font-size: 9px;">${{key.keyMasked}}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">STATUS</span>
                                <span class="stat-value">${{key.configured ? 'Ready' : 'Inactive'}}</span>
                            </div>
                        </div>

                        ${{key.models && key.models.length > 0 ? `
                            <div class="models-list">
                                <div class="models-label">Available Models (${{key.models.length}})</div>
                                <div>
                                    ${{key.models.map(m => `<span class="model-tag">${{m}}</span>`).join('')}}
                                </div>
                            </div>
                        ` : ''}}

                        ${{key.dashboardUrl ? `
                            <a href="${{key.dashboardUrl}}" target="_blank" rel="noopener noreferrer" class="dashboard-link">
                                ➜ ${{key.configured ? 'OPEN DASHBOARD' : 'CONFIGURE KEY'}}
                            </a>
                        ` : ''}}
                    </div>
                `;
            }}).join('');
        }}

        // Render statistics
        function renderStatistics(stats) {{
            const container = document.getElementById('stats-container');

            const totalStats = stats.total || {{}};
            const stats24h = stats['24h'] || {{}};
            const stats7d = stats['7d'] || {{}};
            const stats30d = stats['30d'] || {{}};

            const html = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-card-label">TOTAL REQUESTS</div>
                        <div class="stat-card-value">${{(totalStats.requests || 0).toLocaleString()}}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">TOTAL TOKENS</div>
                        <div class="stat-card-value">${{(totalStats.tokens || 0).toLocaleString()}}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">24H REQUESTS</div>
                        <div class="stat-card-value">${{(stats24h.requests || 0).toLocaleString()}}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">24H TOKENS</div>
                        <div class="stat-card-value">${{(stats24h.tokens || 0).toLocaleString()}}</div>
                    </div>
                </div>

                <div style="margin-top: 20px;">
                    <div class="models-label">PROVIDER USAGE (ALL TIME)</div>
                    ${{Object.entries(totalStats.providers || {{}}).map(([provider, requests]) => `
                        <div class="stat" style="margin-bottom: 8px;">
                            <span class="stat-label">${{provider}}</span>
                            <span class="stat-value">${{requests}} requests</span>
                        </div>
                    `).join('') || '<div style="color: var(--text-dim); padding: 10px;">No usage data yet</div>'}}
                </div>

                ${{Object.keys(totalStats.models || {{}}).length > 0 ? `
                    <div style="margin-top: 20px;">
                        <div class="models-label">MODEL LEADERBOARD (ALL TIME)</div>
                        ${{Object.entries(totalStats.models || {{}})
                            .sort((a, b) => b[1].tokens - a[1].tokens)
                            .slice(0, 10)
                            .map(([model, data]) => `
                            <div class="pet-card" style="margin-bottom: 10px;">
                                <div class="pet-header">
                                    <div class="pet-avatar">🤖</div>
                                    <div class="pet-info">
                                        <div class="pet-name">${{model}}</div>
                                        <div class="pet-type">${{data.requests}} requests • ${{data.tokens.toLocaleString()}} tokens</div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}}
                    </div>
                ` : ''}}
            `;

            container.innerHTML = html;
        }}

        // Fetch and render data
        async function fetchData() {{
            try {{
                const [oauthResp, apikeysResp, statsResp] = await Promise.all([
                    fetch('/api/oauth'),
                    fetch('/api/apikeys'),
                    fetch('/api/stats')
                ]);

                const oauthData = await oauthResp.json();
                const apikeysData = await apikeysResp.json();
                const statsData = await statsResp.json();

                renderOAuthAccounts(oauthData);
                renderAPIKeys(apikeysData);
                renderStatistics(statsData);
            }} catch (error) {{
                console.error('Error fetching data:', error);
            }}
        }}

        // Auto-refresh every 10 seconds
        fetchData();
        setInterval(fetchData, 10000);
    </script>
</body>
</html>"""

@app.route('/api/oauth')
def api_oauth():
    openclaw_data = read_json(OPENCLAW_AUTH)
    accounts = []
    total_quota = 0
    total_usage_sum = 0

    # Get actual token usage per account from usage log (24 hours)
    usage_log_data = read_json(USAGE_LOG) or {'entries': []}
    now = datetime.now()
    one_day_ago = now - timedelta(hours=24)

    tokens_per_account = {}
    for entry in usage_log_data.get('entries', []):
        try:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time >= one_day_ago:  # Last 24 hours usage
                email = entry.get('email', 'unknown')
                if email and email != 'unknown':  # Only count entries with valid email
                    tokens = entry.get('tokens', 0)
                    tokens_per_account[email] = tokens_per_account.get(email, 0) + tokens
        except:
            continue

    if openclaw_data:
        profiles = openclaw_data.get('profiles', {})
        usage = openclaw_data.get('usageStats', {})

        for key, profile in profiles.items():
            stats = usage.get(key, {})
            now_ms = int(datetime.now().timestamp() * 1000)
            cooldown = stats.get('cooldownUntil', 0)
            is_limited = cooldown > now_ms if cooldown else False

            provider = profile.get('provider', 'unknown')
            provider_info = OAUTH_PROVIDERS.get(provider, {'tpm': 100000, 'rpm': 10, 'models': [], 'avatar': '(○‿○)', 'color': '#00d9ff'})
            total_quota += provider_info['tpm']

            last_used_ms = stats.get('lastUsed', 0)
            email = profile.get('email', key)

            # Calculate real usage: tokens in last 24h / (TPM * 60 * 24)
            tokens_last_24h = tokens_per_account.get(email, 0)
            daily_quota = provider_info['tpm'] * 60 * 24  # TPM × 1440 minutes (24 hours)
            actual_usage_pct = min((tokens_last_24h / daily_quota) * 100, 100) if daily_quota > 0 else 0

            account_data = {
                'email': email,
                'provider': provider,
                'isRateLimited': is_limited,
                'lastUsed': format_timestamp(last_used_ms),
                'lastUsedMs': last_used_ms,
                'errorCount': stats.get('errorCount', 0),
                'timeUntilReset': get_time_until(cooldown) if is_limited else None,
                'quota': {'tpm': provider_info['tpm'], 'rpm': provider_info['rpm']},
                'models': provider_info['models'],
                'avatar': provider_info.get('avatar', '(○‿○)'),
                'color': provider_info.get('color', '#00d9ff'),
                'tokensLast24h': tokens_last_24h,
                'dailyQuota': daily_quota,
                'actualUsage': actual_usage_pct
            }

            # Use actual usage if available, otherwise estimate
            account_data['estimatedUsage'] = actual_usage_pct if tokens_last_24h > 0 else estimate_usage(account_data)
            total_usage_sum += account_data['estimatedUsage']
            accounts.append(account_data)

    accounts.sort(key=lambda x: (x['provider'], x['email']))
    total = len(accounts)
    active = sum(1 for a in accounts if not a['isRateLimited'])

    return jsonify({
        'accounts': accounts,
        'stats': {'total': total, 'active': active, 'limited': total - active},
        'totalQuota': total_quota,
        'totalUsagePercent': total_usage_sum / total if total > 0 else 0
    })

@app.route('/api/apikeys')
def api_apikeys():
    env_keys = read_env_file()
    keys = []
    total_quota = 0
    configured_count = 0

    for provider, info in API_PROVIDERS.items():
        env_var = f"{provider.upper().replace('-', '_')}_API_KEY"
        api_key = env_keys.get(env_var)

        is_configured = bool(api_key)
        if is_configured:
            configured_count += 1
            total_quota += info['tpm']

        estimated_usage = 20 if is_configured else 0

        keys.append({
            'provider': provider,
            'name': info['name'],
            'configured': is_configured,
            'keyMasked': mask_key(api_key) if api_key else 'Not set',
            'quota': {'tpm': info['tpm'], 'rpm': info['rpm']},
            'estimatedUsage': estimated_usage,
            'models': info['models'],
            'dashboardUrl': info.get('dashboardUrl', ''),
            'avatar': info.get('avatar', '(⌐■_■)'),
            'color': info.get('color', '#00d9ff')
        })

    total_usage = sum(k['estimatedUsage'] for k in keys) / len(keys) if keys else 0

    return jsonify({
        'keys': keys,
        'stats': {'total': len(keys), 'configured': configured_count, 'available': configured_count},
        'totalQuota': total_quota,
        'totalUsagePercent': total_usage
    })

@app.route('/api/stats')
def api_stats():
    return jsonify(get_usage_stats())

@app.route('/api/data')
def get_data():
    """Legacy endpoint for compatibility"""
    oauth_resp = api_oauth()
    apikeys_resp = api_apikeys()
    stats_resp = api_stats()

    return jsonify({
        'oauth_accounts': oauth_resp.json['accounts'],
        'api_keys': apikeys_resp.json['keys'],
        'usage_stats': stats_resp.json,
        'uptime': int(time.time() - START_TIME)
    })

if __name__ == '__main__':
    print('🚀 NEXUS // TOKEN OS')
    print('📊 Cyberpunk Terminal Dashboard')
    print('🎯 Features: ASCII Pets • Health Bars • Real-time Stats')
    print('🔄 Auto-refresh every 10 seconds')
    print(f'⚡ Dashboard: http://localhost:5555')
    app.run(host='0.0.0.0', port=5555)
