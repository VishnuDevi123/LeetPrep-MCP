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
    
if __name__ == "__main__":
    init_db()