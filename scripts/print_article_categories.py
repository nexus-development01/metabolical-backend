import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "articles.db"

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("\nUnique categories and their counts:")
cursor.execute("SELECT categories, COUNT(*) FROM articles GROUP BY categories ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(row)

print("\nUnique subcategories and their counts:")
cursor.execute("SELECT subcategory, COUNT(*) FROM articles GROUP BY subcategory ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(row)

print("\nUnique tags (raw, not split):")
cursor.execute("SELECT tags FROM articles WHERE tags IS NOT NULL AND tags != '' LIMIT 100")
for row in cursor.fetchall():
    print(row[0])

conn.close()
