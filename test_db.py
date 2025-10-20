import sqlite3

# Test SQLite database
conn = sqlite3.connect('backend/pdf_flashcards.db')
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('SQLite Tables:', [t[0] for t in tables])

# Check PDF count
cursor.execute('SELECT COUNT(*) FROM pdfs')
count = cursor.fetchone()[0]
print(f'SQLite PDFs: {count}')

conn.close()

# Test dual-repo configuration
from dotenv import load_dotenv
load_dotenv()

from backend.repo.dual_repo import DB_READ_PRIMARY, WRITE_SUPABASE, WRITE_SQLITE
print(f'Read Primary: {DB_READ_PRIMARY}')
print(f'Write SQLite: {WRITE_SQLITE}')
print(f'Write Supabase: {WRITE_SUPABASE}')

# Test Supabase configuration
from backend.db.supabase_engine import SUPABASE_ENABLED
print(f'Supabase Enabled: {SUPABASE_ENABLED}')
