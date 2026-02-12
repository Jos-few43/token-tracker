#!/usr/bin/env python3
"""Multi-Account Token Dashboard - OAuth + API Keys + Statistics"""

from flask import Flask, jsonify
import json
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)

OPENCODE_ACCOUNTS = Path.home() / '.config/opencode/antigravity-accounts.json'
OPENCLAW_AUTH = Path.home() / '.openclaw/agents/main/agent/auth-profiles.json'
LITELLM_ENV = Path('/tmp/litellm-full-env')
USAGE_LOG = Path.home() / '.openclaw/usage-stats.json'

# OAuth quotas with models
OAUTH_PROVIDERS = {
    'google-antigravity': {
        'tpm': 4000000, 'rpm': 60,
        'models': ['claude-opus-4-6', 'claude-opus-4-6-thinking', 'claude-sonnet-4-5', 
                  'gemini-3-flash', 'gemini-3-pro', 'gpt-oss-120b']
    },
    'google-gemini-cli': {
        'tpm': 1000000, 'rpm': 15,
        'models': ['gemini-3-flash', 'gemini-3-pro', 'gemini-2.0-flash-exp', 
                  'gemini-2.0-flash-thinking-exp']
    },
    'qwen-portal': {
        'tpm': 100000, 'rpm': 10,
        'models': ['coder-model', 'vision-model']
    }
}

# API Keys with models and dashboard URLs
API_PROVIDERS = {
    'groq': {
        'tpm': 30000, 'rpm': 30, 'name': 'Groq',
        'models': ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
        'dashboardUrl': 'https://console.groq.com/keys'
    },
    'gemini': {
        'tpm': 1000000, 'rpm': 15, 'name': 'Gemini API (Direct)',
        'models': ['gemini-2.0-flash-exp', 'gemini-2.0-flash-thinking-exp'],
        'dashboardUrl': 'https://aistudio.google.com/apikey'
    },
    'opencode': {
        'tpm': 100000, 'rpm': 10, 'name': 'OpenCode',
        'models': ['kimi-k2.5-free', 'deepseek-r1-free'],
        'dashboardUrl': 'https://opencode.com/dashboard'
    },
    'openrouter': {
        'tpm': 200000, 'rpm': 20, 'name': 'OpenRouter',
        'models': ['qwen-2.5-coder-32b', 'deepseek-r1', 'llama-3.1-70b'],
        'dashboardUrl': 'https://openrouter.ai/settings/keys'
    }
}

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

def init_usage_log():
    """Initialize usage log if it doesn't exist"""
    if not USAGE_LOG.exists():
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG, 'w') as f:
            json.dump({'entries': [], 'created': datetime.now().isoformat()}, f)

def get_usage_stats():
    """Get usage statistics from log"""
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

    return stats

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

@app.route('/')
def dashboard():
    return '''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>API Nexus Dashboard</title>
<style>
:root {
  --background: #0a0a0c;
  --foreground: #f4f4f7;
  --card-bg: rgba(20, 20, 25, 0.7);
  --card-border: rgba(255, 255, 255, 0.1);
  --accent: #6366f1;
  --accent-glow: rgba(99, 102, 241, 0.3);
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --text-muted: #8e8e93;
  --glass-blur: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Inter', -apple-system, system-ui, sans-serif;
  background: var(--background);
  color: var(--foreground);
  padding: 20px;
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  background-image:
    radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%);
}
body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  background-image:
    radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 40% 20%, rgba(16, 185, 129, 0.02) 0%, transparent 40%);
  animation: floatBackground 20s ease-in-out infinite;
  z-index: 0;
}
@keyframes floatBackground {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(10px, -10px) scale(1.05); }
  66% { transform: translate(-10px, 10px) scale(0.95); }
}
.container { max-width: 1600px; margin: 0 auto; position: relative; z-index: 1; }
h1 {
  font-size: 2.8em;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #fff 0%, #a5a5a5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
  letter-spacing: -0.02em;
}
.subtitle { color: var(--text-muted); font-size: 1.1em; margin-bottom: 20px; font-weight: 400; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; flex-wrap: wrap; gap: 20px; }

.tabs { display: flex; gap: 10px; margin-bottom: 30px; border-bottom: 2px solid rgba(99, 102, 241, 0.2); flex-wrap: wrap; }
.tab {
  padding: 14px 28px; background: transparent; border: none; color: var(--text-muted); cursor: pointer;
  font-size: 1.1em; font-weight: 500; border-bottom: 3px solid transparent;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.tab::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), #8b5cf6);
  transform: translateX(-50%);
  transition: width 0.3s ease;
}
.tab:hover {
  color: var(--foreground);
  transform: translateY(-3px);
  text-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
}
.tab:hover::before { width: 100%; }
.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
  text-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
}
.tab-content { display: none; animation: fadeIn 0.4s ease-out; }
.tab-content.active { display: block; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.total-gauge-container {
  background: var(--card-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 40px;
  margin-bottom: 30px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
}
.gauge-title {
  font-size: 1.8em;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 30px;
}
.gauge { width: 100%; max-width: 700px; height: 220px; margin: 0 auto 25px; position: relative; }
.gauge-bg {
  width: 100%; height: 100%;
  background: linear-gradient(to right, var(--success) 0%, var(--warning) 50%, var(--error) 100%);
  border-radius: 120px; position: relative; overflow: hidden;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2), 0 0 40px rgba(99, 102, 241, 0.15);
  animation: gaugeGlow 3s ease-in-out infinite;
}
@keyframes gaugeGlow {
  0%, 100% { box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2), 0 0 40px rgba(99, 102, 241, 0.15); }
  50% { box-shadow: 0 4px 30px rgba(99, 102, 241, 0.4), 0 0 60px rgba(99, 102, 241, 0.25); }
}
.gauge-fill {
  position: absolute; right: 0; top: 0; bottom: 0;
  background: rgba(10, 10, 12, 0.85);
  backdrop-filter: blur(8px);
  border-radius: 120px;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
}
.gauge-label { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 3.5em; font-weight: bold; color: #fff; text-shadow: 2px 2px 8px rgba(0,0,0,0.6); z-index: 10; }
.gauge-subtitle { font-size: 1.15em; color: var(--text-muted); font-weight: 500; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px; }
.stat-card {
  background: var(--card-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 24px;
  position: relative;
  overflow: hidden;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.4s ease;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
}
.stat-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 20px 40px rgba(99, 102, 241, 0.25);
  border-color: rgba(99, 102, 241, 0.5);
}
.stat-card:hover::before {
  opacity: 1;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.1); opacity: 0.6; }
}
.stat-value {
  font-size: 2.8em;
  font-weight: bold;
  background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}
.stat-label { color: var(--text-muted); font-size: 0.95em; font-weight: 500; }

.accounts { display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 20px; }
.account {
  background: var(--card-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 24px;
  position: relative;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.4s ease, box-shadow 0.4s ease;
}
.account::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.15), transparent);
  transition: left 0.6s ease;
}
.account:hover {
  transform: translateY(-6px) scale(1.01);
  border-color: rgba(99, 102, 241, 0.6);
  box-shadow: 0 20px 50px rgba(99, 102, 241, 0.3), 0 0 30px rgba(99, 102, 241, 0.1);
}
.account:hover::after {
  left: 100%;
}
.account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid rgba(99, 102, 241, 0.2); }
.account-email { font-weight: 600; color: var(--accent); font-size: 1.1em; }
.badge { padding: 6px 14px; border-radius: 20px; font-size: 0.8em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.badge-active { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-limited { background: rgba(239, 68, 68, 0.15); color: var(--error); border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-configured { background: rgba(99, 102, 241, 0.15); color: var(--accent); border: 1px solid rgba(99, 102, 241, 0.3); }

.quota-section { margin: 15px 0; }
.quota-label { display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 8px; color: #8b949e; }
.quota-percent { font-weight: 600; }
.progress-bar { width: 100%; height: 28px; background: rgba(255, 255, 255, 0.05); border-radius: 14px; overflow: hidden; position: relative; box-shadow: inset 0 2px 6px rgba(0,0,0,0.3); }
.progress-fill { height: 100%; transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1), background 0.6s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 12px; font-size: 0.9em; font-weight: 700; color: #fff; text-shadow: 1px 1px 3px rgba(0,0,0,0.6); }

.account-details { font-size: 0.9em; margin-top: 15px; }
.detail-row { display: flex; justify-content: space-between; margin: 8px 0; }
.detail-label { color: #8b949e; }
.detail-value { font-weight: 500; }
.provider-tag { display: inline-block; padding: 6px 14px; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; font-size: 0.85em; font-weight: 600; margin-bottom: 12px; color: var(--accent); }
.error-count { color: var(--error); font-weight: 700; }
.time-until { color: var(--warning); font-weight: 700; }
.quota-info { font-size: 0.85em; color: var(--text-muted); margin-top: 12px; font-weight: 500; }
.key-display { font-family: 'SF Mono', 'Monaco', 'Courier New', monospace; font-size: 0.85em; color: #a5b4fc; background: rgba(99, 102, 241, 0.1); padding: 6px 10px; border-radius: 6px; border: 1px solid rgba(99, 102, 241, 0.2); }

.models-section { margin-top: 18px; padding-top: 18px; border-top: 1px solid rgba(99, 102, 241, 0.2); }
.models-title { font-size: 0.85em; color: var(--text-muted); margin-bottom: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.model-tag { display: inline-block; padding: 4px 10px; background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 6px; font-size: 0.75em; margin: 3px; color: #c4b5fd; font-weight: 500; }

.period-selector { display: flex; gap: 10px; margin-bottom: 20px; justify-content: center; }
.period-btn { padding: 10px 20px; background: #21262d; border: 1px solid #30363d; border-radius: 6px; color: #8b949e; cursor: pointer; transition: all 0.2s; }
.period-btn:hover { border-color: #58a6ff; color: #c9d1d9; }
.period-btn.active { background: #58a6ff; color: #fff; border-color: #58a6ff; }

.chart-container { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.chart-title { font-size: 1.2em; color: #58a6ff; margin-bottom: 15px; }
.provider-bar { margin: 15px 0; }
.provider-bar-label { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.9em; }
.provider-bar-fill { height: 30px; background: #238636; border-radius: 4px; display: flex; align-items: center; padding: 0 10px; color: #fff; font-weight: 600; }

.leaderboard { display: grid; gap: 14px; }
.leaderboard-item {
  background: var(--card-bg);
  backdrop-filter: blur(8px);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 18px;
  display: grid;
  grid-template-columns: 50px 1fr auto;
  gap: 18px;
  align-items: center;
  position: relative;
  overflow: hidden;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.4s ease;
}
.leaderboard-item::before {
  content: '';
  position: absolute;
  top: 50%;
  left: -100%;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  transition: left 0.6s ease;
}
.leaderboard-item:hover {
  transform: translateX(12px) scale(1.02);
  border-color: rgba(99, 102, 241, 0.6);
  box-shadow: 0 12px 36px rgba(99, 102, 241, 0.3);
}
.leaderboard-item:hover::before {
  left: 100%;
}
.leaderboard-item:first-child {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.05), var(--card-bg));
  border-color: rgba(255, 215, 0, 0.3);
}
.leaderboard-item:first-child:hover {
  box-shadow: 0 12px 36px rgba(255, 215, 0, 0.3), 0 0 40px rgba(255, 215, 0, 0.15);
}
.leaderboard-rank { font-size: 2em; font-weight: bold; text-align: center; color: var(--text-muted); }
.leaderboard-rank.rank-1 {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.leaderboard-rank.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.leaderboard-rank.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #e59866);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.leaderboard-info { min-width: 0; }
.leaderboard-model { font-size: 1.15em; font-weight: 700; color: var(--accent); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.leaderboard-details { font-size: 0.85em; color: var(--text-muted); font-weight: 500; }
.leaderboard-stats { text-align: right; }
.leaderboard-requests {
  font-size: 1.6em;
  font-weight: bold;
  background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.leaderboard-tokens { font-size: 0.85em; color: var(--text-muted); margin-top: 5px; font-weight: 500; }

.dashboard-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: linear-gradient(135deg, var(--accent), #8b5cf6);
  color: white !important;
  text-decoration: none !important;
  border-radius: 8px;
  font-size: 0.9em;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
  position: relative;
  z-index: 100;
  cursor: pointer !important;
  border: 1px solid rgba(255, 255, 255, 0.2);
  pointer-events: auto;
}
.dashboard-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}
.dashboard-link:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5), 0 0 30px rgba(99, 102, 241, 0.3);
}
.dashboard-link:hover::before {
  left: 100%;
}
.dashboard-link:active {
  transform: translateY(0) scale(0.98);
}
</style>
</head><body>
<div class="container">
<div class="header">
<div>
<h1>🔐 Multi-Account Token Dashboard</h1>
<div class="subtitle">Real-time monitoring • Usage statistics • Model tracking</div>
</div>
<div style="color: #8b949e; font-size: 0.9em;">Last update: <span id="last-update">-</span></div>
</div>

<div class="tabs">
<button class="tab active" onclick="switchTab('oauth')">🔑 OAuth (8)</button>
<button class="tab" onclick="switchTab('apikeys')">🗝️ API Keys (4)</button>
<button class="tab" onclick="switchTab('stats')">📊 Statistics</button>
</div>

<div id="oauth-tab" class="tab-content active">
<div class="total-gauge-container">
<div class="gauge-title">⛽ Total OAuth Capacity</div>
<div class="gauge"><div class="gauge-bg"><div class="gauge-fill" id="oauth-gauge-fill"></div><div class="gauge-label" id="oauth-gauge-label">--%</div></div></div>
<div class="gauge-subtitle" id="oauth-gauge-subtitle">-</div>
</div>
<div class="stats" id="oauth-stats"></div>
<div class="accounts" id="oauth-accounts"></div>
</div>

<div id="apikeys-tab" class="tab-content">
<div class="total-gauge-container">
<div class="gauge-title">🗝️ Total API Key Capacity</div>
<div class="gauge"><div class="gauge-bg"><div class="gauge-fill" id="api-gauge-fill"></div><div class="gauge-label" id="api-gauge-label">--%</div></div></div>
<div class="gauge-subtitle" id="api-gauge-subtitle">-</div>
</div>
<div class="stats" id="api-stats"></div>
<div class="accounts" id="api-accounts"></div>
</div>

<div id="stats-tab" class="tab-content">
<div class="period-selector">
<button class="period-btn active" onclick="selectPeriod('24h')">Last 24 Hours</button>
<button class="period-btn" onclick="selectPeriod('7d')">Last 7 Days</button>
<button class="period-btn" onclick="selectPeriod('30d')">Last 30 Days</button>
<button class="period-btn" onclick="selectPeriod('total')">All Time</button>
</div>
<div class="stats" id="stats-summary"></div>
<div class="chart-container">
<div class="chart-title">🏆 Model Usage Leaderboard</div>
<div id="model-leaderboard"></div>
</div>
<div class="chart-container">
<div class="chart-title">📈 Usage by Provider</div>
<div id="provider-chart"></div>
</div>
</div>

</div>

<script>
let currentPeriod = '24h';

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(tab + '-tab').classList.add('active');
}

function selectPeriod(period) {
  currentPeriod = period;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  loadStats();
}

function getProgressColor(percent) {
  if (percent < 50) return 'var(--success)';
  if (percent < 75) return 'var(--warning)';
  return 'var(--error)';
}

async function loadData() {
  const [oauth, apikeys] = await Promise.all([
    fetch('/api/oauth').then(r => r.json()),
    fetch('/api/apikeys').then(r => r.json())
  ]);
  renderOAuth(oauth);
  renderAPIKeys(apikeys);
  document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

async function loadStats() {
  const stats = await fetch('/api/stats').then(r => r.json());
  renderStats(stats);
}

function renderOAuth(data) {
  const totalPercent = data.totalUsagePercent;
  document.getElementById('oauth-gauge-fill').style.width = (100 - totalPercent) + '%';
  document.getElementById('oauth-gauge-label').textContent = totalPercent.toFixed(0) + '%';
  document.getElementById('oauth-gauge-subtitle').textContent = 
    `${data.stats.active} of ${data.stats.total} accounts • ${(data.totalQuota / 1000000).toFixed(1)}M TPM`;
  
  document.getElementById('oauth-stats').innerHTML = `
    <div class="stat-card"><div class="stat-value">${data.stats.total}</div><div class="stat-label">OAuth Accounts</div></div>
    <div class="stat-card"><div class="stat-value">${data.stats.active}</div><div class="stat-label">Active</div></div>
    <div class="stat-card"><div class="stat-value">${data.stats.limited}</div><div class="stat-label">Rate Limited</div></div>
    <div class="stat-card"><div class="stat-value">${(data.totalQuota / 1000000).toFixed(1)}M</div><div class="stat-label">Total TPM</div></div>
  `;
  
  let html = '';
  data.accounts.forEach(acc => {
    const used = acc.estimatedUsage;
    const avail = 100 - used;
    html += createAccountCard(acc, used, avail);
  });
  document.getElementById('oauth-accounts').innerHTML = html;
}

function renderAPIKeys(data) {
  const totalPercent = data.totalUsagePercent;
  document.getElementById('api-gauge-fill').style.width = (100 - totalPercent) + '%';
  document.getElementById('api-gauge-label').textContent = totalPercent.toFixed(0) + '%';
  document.getElementById('api-gauge-subtitle').textContent = 
    `${data.stats.configured} keys configured • ${(data.totalQuota / 1000).toFixed(0)}K TPM`;
  
  document.getElementById('api-stats').innerHTML = `
    <div class="stat-card"><div class="stat-value">${data.stats.total}</div><div class="stat-label">API Services</div></div>
    <div class="stat-card"><div class="stat-value">${data.stats.configured}</div><div class="stat-label">Configured</div></div>
    <div class="stat-card"><div class="stat-value">${data.stats.available}</div><div class="stat-label">Available</div></div>
    <div class="stat-card"><div class="stat-value">${(data.totalQuota / 1000).toFixed(0)}K</div><div class="stat-label">Total TPM</div></div>
  `;
  
  let html = '';
  data.keys.forEach(key => {
    const used = key.estimatedUsage;
    const avail = 100 - used;
    html += createAPIKeyCard(key, used, avail);
  });
  document.getElementById('api-accounts').innerHTML = html;
}

function renderStats(data) {
  const period = data[currentPeriod];

  // Summary stats - Safe: data from trusted backend API
  document.getElementById('stats-summary').innerHTML = `
    <div class="stat-card"><div class="stat-value">${period.requests.toLocaleString()}</div><div class="stat-label">Total Requests</div></div>
    <div class="stat-card"><div class="stat-value">${(period.tokens / 1000).toFixed(1)}K</div><div class="stat-label">Tokens Used</div></div>
    <div class="stat-card"><div class="stat-value">${Object.keys(period.providers).length}</div><div class="stat-label">Providers Used</div></div>
    <div class="stat-card"><div class="stat-value">${period.requests > 0 ? (period.tokens / period.requests).toFixed(0) : 0}</div><div class="stat-label">Avg Tokens/Request</div></div>
  `;

  // Model leaderboard - Safe: data from trusted local usage log
  let leaderboardHTML = '';
  const modelEntries = Object.entries(period.models || {})
    .map(([model, stats]) => ({model, ...stats}))
    .sort((a, b) => b.requests - a.requests)
    .slice(0, 10);

  if (modelEntries.length > 0) {
    modelEntries.forEach((item, index) => {
      const rank = index + 1;
      const rankClass = rank <= 3 ? `rank-${rank}` : '';
      const avgTokens = item.requests > 0 ? (item.tokens / item.requests).toFixed(0) : 0;
      leaderboardHTML += `
        <div class="leaderboard-item">
          <div class="leaderboard-rank ${rankClass}">#${rank}</div>
          <div class="leaderboard-info">
            <div class="leaderboard-model">${item.model}</div>
            <div class="leaderboard-details">${avgTokens} avg tokens/request</div>
          </div>
          <div class="leaderboard-stats">
            <div class="leaderboard-requests">${item.requests.toLocaleString()}</div>
            <div class="leaderboard-tokens">${(item.tokens / 1000).toFixed(1)}K tokens</div>
          </div>
        </div>
      `;
    });
  } else {
    leaderboardHTML = '<p style="color:#8b949e; text-align:center; padding: 40px;">No model usage data yet. Start using your APIs to see the leaderboard!</p>';
  }
  document.getElementById('model-leaderboard').innerHTML = leaderboardHTML;

  // Provider chart - Safe: data from trusted backend API
  let chartHTML = '';
  const maxRequests = Math.max(...Object.values(period.providers), 1);
  Object.entries(period.providers).sort((a,b) => b[1] - a[1]).forEach(([provider, count]) => {
    const width = (count / maxRequests) * 100;
    chartHTML += `
      <div class="provider-bar">
        <div class="provider-bar-label"><span>${provider}</span><span>${count} requests</span></div>
        <div class="provider-bar-fill" style="width: ${width}%">${count}</div>
      </div>
    `;
  });
  document.getElementById('provider-chart').innerHTML = chartHTML || '<p style="color:#8b949e; text-align:center;">No usage data yet</p>';
}

function createAccountCard(acc, used, avail) {
  const statusBadge = acc.isRateLimited ? 
    '<span class="badge badge-limited">RATE LIMITED</span>' :
    '<span class="badge badge-active">ACTIVE</span>';
  const barColor = getProgressColor(used);
  const resetInfo = acc.timeUntilReset ? 
    `<div class="detail-row"><span class="detail-label">Reset in:</span><span class="detail-value time-until">${acc.timeUntilReset}</span></div>` : '';
  const errorInfo = acc.errorCount > 0 ?
    `<div class="detail-row"><span class="detail-label">Errors:</span><span class="detail-value error-count">${acc.errorCount}</span></div>` : '';
  
  const modelsHTML = acc.models.map(m => `<span class="model-tag">${m}</span>`).join('');
  
  return `
    <div class="account">
      <div class="account-header">
        <div class="account-email">${acc.email}</div>
        ${statusBadge}
      </div>
      <div class="provider-tag">${acc.provider}</div>
      <div class="quota-section">
        <div class="quota-label"><span>Quota Available</span><span class="quota-percent">${avail.toFixed(0)}%</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width: ${used}%; background: ${barColor};">${used.toFixed(0)}% used</div></div>
        <div class="quota-info">${(acc.quota.tpm / 1000).toFixed(0)}K TPM • ${acc.quota.rpm} RPM</div>
      </div>
      <div class="account-details">
        <div class="detail-row"><span class="detail-label">Last Used:</span><span class="detail-value">${acc.lastUsed}</span></div>
        ${errorInfo}${resetInfo}
      </div>
      <div class="models-section">
        <div class="models-title">Available Models (${acc.models.length}):</div>
        ${modelsHTML}
      </div>
    </div>
  `;
}

function createAPIKeyCard(key, used, avail) {
  const statusBadge = key.configured ? 
    '<span class="badge badge-configured">CONFIGURED</span>' :
    '<span class="badge" style="background:#30363d">NOT SET</span>';
  const barColor = getProgressColor(used);
  
  const modelsHTML = key.models.map(m => `<span class="model-tag">${m}</span>`).join('');
  
  return `
    <div class="account">
      <div class="account-header">
        <div class="account-email">${key.name}</div>
        ${statusBadge}
      </div>
      <div class="provider-tag">${key.provider}</div>
      ${key.configured ? `
      <div class="quota-section">
        <div class="quota-label"><span>Quota Available</span><span class="quota-percent">${avail.toFixed(0)}%</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width: ${used}%; background: ${barColor};">${used.toFixed(0)}% used</div></div>
        <div class="quota-info">${(key.quota.tpm / 1000).toFixed(0)}K TPM • ${key.quota.rpm} RPM</div>
      </div>
      <div class="account-details">
        <div class="detail-row"><span class="detail-label">API Key:</span><span class="key-display">${key.keyMasked}</span></div>
        <div class="detail-row"><span class="detail-label">Status:</span><span class="detail-value" style="color:#238636">Ready</span></div>
      </div>
      <div class="models-section">
        <div class="models-title">Available Models (${key.models.length}):</div>
        ${modelsHTML}
      </div>
      ${key.dashboardUrl ? `
      <div style="margin-top: 15px;">
        <a href="${key.dashboardUrl}" target="_blank" rel="noopener noreferrer" class="dashboard-link" onclick="console.log('Link clicked!'); return true;">
          <span>🔗</span>
          <span>View API Dashboard</span>
          <span style="font-size: 0.7em;">↗</span>
        </a>
      </div>` : ''}
      ` : `
      <div class="account-details">
        <div class="detail-row"><span class="detail-label">Status:</span><span class="detail-value" style="color:#8b949e">No API key</span></div>
      </div>
      <div class="models-section">
        <div class="models-title">Available Models (${key.models.length}) when configured:</div>
        ${modelsHTML}
      </div>
      ${key.dashboardUrl ? `
      <div style="margin-top: 15px;">
        <a href="${key.dashboardUrl}" target="_blank" rel="noopener noreferrer" class="dashboard-link">
          <span>🔗</span>
          <span>Configure API Key</span>
          <span style="font-size: 0.7em;">↗</span>
        </a>
      </div>` : ''}
      `}
    </div>
  `;
}

setInterval(() => { loadData(); loadStats(); }, 10000);
loadData();
loadStats();
</script>
</body></html>'''

@app.route('/api/oauth')
def api_oauth():
    openclaw_data = read_json(OPENCLAW_AUTH)
    accounts = []
    total_quota = 0
    total_usage_sum = 0
    
    if openclaw_data:
        profiles = openclaw_data.get('profiles', {})
        usage = openclaw_data.get('usageStats', {})
        
        for key, profile in profiles.items():
            stats = usage.get(key, {})
            now_ms = int(datetime.now().timestamp() * 1000)
            cooldown = stats.get('cooldownUntil', 0)
            is_limited = cooldown > now_ms if cooldown else False
            
            provider = profile.get('provider', 'unknown')
            provider_info = OAUTH_PROVIDERS.get(provider, {'tpm': 100000, 'rpm': 10, 'models': []})
            total_quota += provider_info['tpm']
            
            last_used_ms = stats.get('lastUsed', 0)
            
            account_data = {
                'email': profile.get('email', key),
                'provider': provider,
                'isRateLimited': is_limited,
                'lastUsed': format_timestamp(last_used_ms),
                'lastUsedMs': last_used_ms,
                'errorCount': stats.get('errorCount', 0),
                'timeUntilReset': get_time_until(cooldown) if is_limited else None,
                'quota': {'tpm': provider_info['tpm'], 'rpm': provider_info['rpm']},
                'models': provider_info['models']
            }
            
            account_data['estimatedUsage'] = estimate_usage(account_data)
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
            'dashboardUrl': info.get('dashboardUrl', '')
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

if __name__ == '__main__':
    init_usage_log()
    print("🚀 Enhanced Dashboard: http://localhost:5555")
    print("📊 3 Pages: OAuth • API Keys • Statistics")
    print("🎯 Features: Models list • Usage tracking • Historical stats")
    print("🔄 Auto-refresh every 10 seconds")
    app.run(host='0.0.0.0', port=5555, debug=False)
