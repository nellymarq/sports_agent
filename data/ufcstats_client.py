"""
Thin wrapper around UFCStats HTML fetcher.
"""

from tools import _get_soup

def fetch(url: str):
    return _get_soup(url)
