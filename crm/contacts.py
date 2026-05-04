import csv
from database.models import get_conn


def add_contact(name, company="", phone="", email="", industry="", prev_loan_amount=0, notes=""):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO contacts (name, company, phone, email, industry, prev_loan_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, company, phone, email, industry, prev_loan_amount, notes))
        conn.commit()
        contact_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return contact_id
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()


def get_all_contacts(status=None):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE status=? ORDER BY updated_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM contacts ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contact(contact_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_contact_status(contact_id, status):
    conn = get_conn()
    conn.execute(
        "UPDATE contacts SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, contact_id)
    )
    conn.commit()
    conn.close()


def import_from_csv(filepath):
    """
    Expected CSV columns: name, company, phone, email, industry, prev_loan_amount, notes
    Returns (imported_count, skipped_count, errors)
    """
    imported, skipped, errors = 0, 0, []
    conn = get_conn()
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO contacts
                    (name, company, phone, email, industry, prev_loan_amount, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("name", "").strip(),
                    row.get("company", "").strip(),
                    row.get("phone", "").strip(),
                    row.get("email", "").strip().lower(),
                    row.get("industry", "").strip(),
                    float(row.get("prev_loan_amount", 0) or 0),
                    row.get("notes", "").strip(),
                ))
                if conn.execute("SELECT changes()").fetchone()[0]:
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f"Row {row}: {e}")
    conn.commit()
    conn.close()
    return imported, skipped, errors


def get_contacts_due_followup():
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*, f.follow_up_type, f.scheduled_date, f.id as followup_id
        FROM contacts c
        JOIN follow_ups f ON c.id = f.contact_id
        WHERE f.completed = 0 AND f.scheduled_date <= date('now')
        ORDER BY f.scheduled_date ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_contacts(query):
    conn = get_conn()
    like = f"%{query}%"
    rows = conn.execute("""
        SELECT * FROM contacts
        WHERE name LIKE ? OR company LIKE ? OR email LIKE ? OR industry LIKE ?
        ORDER BY name
    """, (like, like, like, like)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
