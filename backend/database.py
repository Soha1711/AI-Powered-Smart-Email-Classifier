import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.environ.get("DB_PATH", os.path.join(DB_DIR, "emails.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT NOT NULL,
            urgency TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_email(sender: str, subject: str, body: str, category: str, urgency: str):
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO emails (sender, subject, body, category, urgency) VALUES (?, ?, ?, ?, ?)',
        (sender, subject, body, category, urgency)
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    
    # Retrieve it so we get the exact timestamp
    row = conn.execute('SELECT * FROM emails WHERE id = ?', (inserted_id,)).fetchone()
    conn.close()
    return dict(row)

def get_all_emails():
    conn = get_db_connection()
    emails = conn.execute('SELECT * FROM emails ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(row) for row in emails]

def clear_all_emails():
    conn = get_db_connection()
    conn.execute('DELETE FROM emails')
    # Reset auto-increment
    conn.execute('DELETE FROM sqlite_sequence WHERE name="emails"')
    conn.commit()
    conn.close()
