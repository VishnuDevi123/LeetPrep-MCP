# test_db.py (in project root)
"""quick script to print all saved rows from the local `problems` table."""

import sqlite3

# open the local project db file directly.
conn = sqlite3.connect("data/app_database.db")
cursor = conn.cursor()
# simple read to inspect current saved problems.
cursor.execute("SELECT * FROM problems")
rows = cursor.fetchall()

# print each row tuple for manual checking.
for row in rows:
    print(row)

# close connection so sqlite file handles are released cleanly.
conn.close()
