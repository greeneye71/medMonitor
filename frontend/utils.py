"""Utility helpers per i callback frontend."""

import requests

API_BASE = "http://localhost:8000"

def safe_get(path: str, timeout: int = 3):
    """GET con gestione errori. Returns (data, error_str)."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Backend non raggiungibile"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def safe_post(path: str, json=None, timeout: int = 5):
    """POST con gestione errori. Returns (data, error_str)."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Backend non raggiungibile"
    except Exception as e:
        return None, str(e)

def safe_delete(path: str, timeout: int = 5):
    """DELETE con gestione errori. Returns (data, error_str)."""
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Backend non raggiungibile"
    except Exception as e:
        return None, str(e)
