import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from token_dashboard_nexus import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_returns_html(client):
    """Smoke test: dashboard renders without crashing"""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'NEXUS' in rv.data

def test_fetch_litellm_spend_returns_list(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"startTime": "2026-02-26T10:00:00", "model": "claude-sonnet-4-5",
         "spend": 0.003, "total_tokens": 1500, "api_key": "sk-***"}
    ]
    with patch('token_dashboard_nexus.http_requests.get', return_value=mock_response):
        rv = client.get('/api/spend')
        data = json.loads(rv.data)
        assert rv.status_code == 200
        assert 'entries' in data
        assert len(data['entries']) >= 1
        assert data['entries'][0]['model'] == 'claude-sonnet-4-5'
        assert data['source'] == 'litellm'

def test_fetch_litellm_spend_fallback_on_error(client):
    with patch('token_dashboard_nexus.http_requests.get', side_effect=requests.ConnectionError):
        rv = client.get('/api/spend')
        data = json.loads(rv.data)
        assert rv.status_code == 200
        assert 'entries' in data
        assert data['source'] == 'local'

def test_cost_calculation():
    from token_dashboard_nexus import calculate_cost
    # Claude Sonnet: $3/M input, $15/M output
    cost = calculate_cost('claude-sonnet-4-5', prompt_tokens=1000, completion_tokens=500)
    expected = (1000 * 3.0 + 500 * 15.0) / 1_000_000  # = 0.0105
    assert abs(cost - expected) < 0.0001

def test_cost_unknown_model():
    from token_dashboard_nexus import calculate_cost
    cost = calculate_cost('unknown-model', prompt_tokens=1000, completion_tokens=500)
    assert cost > 0  # uses default rate (1.0, 3.0)
    expected = (1000 * 1.0 + 500 * 3.0) / 1_000_000
    assert abs(cost - expected) < 0.0001
