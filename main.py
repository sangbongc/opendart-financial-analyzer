import sqlite3

DART_DB_PATH = "data/dart.db"

conn = sqlite3.connect(DART_DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) dart_corporations")
count = cursor.fetchone()[0]

conn.close()

print("남은 기업 수:", count)