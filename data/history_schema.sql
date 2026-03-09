-- data/history_schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS fighters (
    fighter_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    nickname TEXT,
    height TEXT,
    reach TEXT,
    stance TEXT,
    dob TEXT,
    country TEXT,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS fights (
    fight_id TEXT PRIMARY KEY,
    fighter_id TEXT NOT NULL,
    opponent_id TEXT NOT NULL,
    event_id TEXT,
    event_name TEXT,
    date TEXT,
    weight_class TEXT,
    result TEXT,
    method TEXT,
    round INTEGER,
    time TEXT,
    source TEXT NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (fighter_id) REFERENCES fighters(fighter_id),
    FOREIGN KEY (opponent_id) REFERENCES fighters(fighter_id)
);

CREATE INDEX IF NOT EXISTS idx_fights_fighter ON fights(fighter_id);
CREATE INDEX IF NOT EXISTS idx_fights_opponent ON fights(opponent_id);
CREATE INDEX IF NOT EXISTS idx_fights_event ON fights(event_id);
