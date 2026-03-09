# cli/init_history_db.py

import os
from data.history_client import HistoryDB, DB_PATH

def main():
    os.makedirs("data", exist_ok=True)

    db = HistoryDB(DB_PATH)
    db.init_schema()

    print(f"[history-db] Initialized at {DB_PATH}")

if __name__ == "__main__":
    main()
