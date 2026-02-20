"""
Thin wrapper around balldontlie JSON fetcher.
"""

from tools import _get_json

def fetch(url: str, params=None):
    return _get_json(url, params=params)
