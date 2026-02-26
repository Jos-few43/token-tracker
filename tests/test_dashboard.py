import pytest
import json
import sys
import os

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
