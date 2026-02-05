import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__),'..','..', 'data')
DB_PATH = os.path.join(DB_DIR, 'app_database.db')

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create problems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leetcode_id INTEGER UNIQUE,
            title TEXT,
            slug TEXT,
            difficulty TEXT,
            patterns TEXT,
            companies TEXT,
            created_at TEXT 
        )
    ''')
    # Create progress table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        leetcode_id INTEGER,
        status TEXT,
        time_taken_mins INTEGER,
        notes TEXT,
        created_at TEXT
    )
"""
    )

    conn.commit()
    conn.close()

    print("Database jas been initialized.")

def add_problem(leetcode_id: int, title: str, slug: str, difficulty: str,
                patterns: str, companies: str, created_at: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR IGNORE INTO problems (leetcode_id, title, slug, difficulty, patterns, companies, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (leetcode_id, title, slug, difficulty, patterns, companies, created_at))

    rows_affected = cursor.rowcount

    conn.commit()
    conn.close()

    if rows_affected > 0:
        return {"message": "Problem added successfully."}
    else:
        return {"message": "Problem already exists."}

from datetime import datetime  # Add at top


def track_progress(leetcode_id: int, status: str, time_taken_mins: int, notes: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    created_at = datetime.now().isoformat()  # Auto-generate timestamp

    cursor.execute(
        """
        INSERT INTO progress (leetcode_id, status, time_taken_mins, notes, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (leetcode_id, status, time_taken_mins, notes, created_at),
    )

    conn.commit()
    conn.close()

    return {"success": True, "message": f"Progress tracked for problem {leetcode_id}"}

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM problems WHERE status = 'solved'")
    solved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM problems WHERE status = 'attempted")
    attempted = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(time_taken_mins) FROM progress WHERE time_taken_mins > 0")
    avg_time = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(DISTINCT leetcode_id) FROM progress")
    unique_problems=  cursor.fetchone()[0]
    
    conn.close()
    
    return{
        "total_soled": solved,
        "total_attempted": attempted,
        "avg_time_mins": round(avg_time, 1),
        "unique_problems": unique_problems
    }
    
def get_weaknesses():
    conn = sqlite3.connect(DB_PATH)
    
    
if __name__ == "__main__":
    init_db()
