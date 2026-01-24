# test_db.py (in project root)
import sqlite3

conn = sqlite3.connect('data/app_database.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM problems")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()