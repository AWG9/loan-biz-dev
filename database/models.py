import sqlite3
import os
from config import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            email TEXT UNIQUE,
            industry TEXT,
            prev_loan_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'prospect',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            loan_amount REAL NOT NULL,
            interest_rate REAL DEFAULT 0.08,
            term_months INTEGER DEFAULT 12,
            commission_rate REAL DEFAULT 0.02,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            duration_minutes INTEGER DEFAULT 0,
            outcome TEXT,
            notes TEXT,
            follow_up_date DATE,
            called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            template_name TEXT,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'draft',
            sent_at TIMESTAMP,
            replied INTEGER DEFAULT 0,
            reply_body TEXT,
            reply_received_at TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            follow_up_type TEXT,
            scheduled_date DATE NOT NULL,
            notes TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    conn.commit()
    conn.close()
    return True
