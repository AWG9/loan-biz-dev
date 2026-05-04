from database.models import get_conn
from config import DEFAULT_COMMISSION_RATE
from datetime import datetime, timedelta


PIPELINE_STAGES = ["prospect", "contacted", "interested", "proposal_sent", "negotiating", "closed_won", "closed_lost"]


def add_deal(contact_id, loan_amount, interest_rate=0.08, term_months=12,
             commission_rate=None, notes=""):
    rate = commission_rate if commission_rate is not None else DEFAULT_COMMISSION_RATE
    conn = get_conn()
    conn.execute("""
        INSERT INTO deals (contact_id, loan_amount, interest_rate, term_months, commission_rate, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (contact_id, loan_amount, interest_rate, term_months, rate, notes))
    conn.commit()
    deal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "UPDATE contacts SET status='interested', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (contact_id,)
    )
    conn.commit()
    conn.close()
    return deal_id


def close_deal(deal_id, won=True):
    status = "closed_won" if won else "closed_lost"
    conn = get_conn()
    conn.execute("""
        UPDATE deals SET status=?, closed_at=CURRENT_TIMESTAMP WHERE id=?
    """, (status, deal_id))
    deal = conn.execute("SELECT * FROM deals WHERE id=?", (deal_id,)).fetchone()
    if deal:
        conn.execute(
            "UPDATE contacts SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, deal["contact_id"])
        )
    conn.commit()
    conn.close()


def get_all_deals(status=None):
    conn = get_conn()
    if status:
        rows = conn.execute("""
            SELECT d.*, c.name as contact_name, c.company
            FROM deals d JOIN contacts c ON d.contact_id = c.id
            WHERE d.status=? ORDER BY d.created_at DESC
        """, (status,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT d.*, c.name as contact_name, c.company
            FROM deals d JOIN contacts c ON d.contact_id = c.id
            ORDER BY d.created_at DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def commission_earned(deal):
    return deal["loan_amount"] * deal["commission_rate"]


def get_weekly_deals(weeks_back=0):
    """Returns deals closed_won in a given week (0=this week, 1=last week, etc.)"""
    conn = get_conn()
    start = datetime.now() - timedelta(weeks=weeks_back) - timedelta(days=datetime.now().weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    rows = conn.execute("""
        SELECT d.*, c.name as contact_name, c.company
        FROM deals d JOIN contacts c ON d.contact_id = c.id
        WHERE d.status='closed_won'
          AND d.closed_at >= ? AND d.closed_at < ?
    """, (start.isoformat(), end.isoformat())).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pipeline_summary():
    conn = get_conn()
    rows = conn.execute("""
        SELECT status, COUNT(*) as count, SUM(loan_amount) as total_value
        FROM deals GROUP BY status
    """).fetchall()
    conn.close()
    return {r["status"]: {"count": r["count"], "total_value": r["total_value"] or 0} for r in rows}


def update_deal_status(deal_id, status):
    conn = get_conn()
    conn.execute("UPDATE deals SET status=? WHERE id=?", (status, deal_id))
    conn.commit()
    conn.close()
