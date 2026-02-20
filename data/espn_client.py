"""
Thin wrappers around ESPN helper functions from tools.py.
These allow future modularization without changing tool behavior.
"""

from tools import (
    _get_json,
    _get_soup,
    _espn_scoreboard_json,
    _espn_standings_json,
    _espn_news_json,
)

def scoreboard(sport: str, league: str):
    return _espn_scoreboard_json(sport, league)

def standings(sport: str, league: str):
    return _espn_standings_json(sport, league)

def news(sport: str, league: str = None):
    return _espn_news_json(sport, league)
