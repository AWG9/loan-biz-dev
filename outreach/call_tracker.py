from database.models import get_conn
from datetime import datetime, timedelta


OUTCOMES = ["no_answer", "left_voicemail", "not_interested", "callback_scheduled",
            "interested", "meeting_set", "deal_closed"]


def log_call(contact_id, outcome, duration_minutes=0, notes="", follow_up_days=None):
    conn = get_conn()
    follow_up_date = None
    if follow_up_days:
        follow_up_date = (datetime.now() + timedelta(days=follow_up_days)).date().isoformat()

    conn.execute("""
        INSERT INTO call_logs (contact_id, outcome, duration_minutes, notes, follow_up_date)
        VALUES (?, ?, ?, ?, ?)
    """, (contact_id, outcome, duration_minutes, notes, follow_up_date))

    if follow_up_date:
        conn.execute("""
            INSERT INTO follow_ups (contact_id, follow_up_type, scheduled_date, notes)
            VALUES (?, 'call', ?, ?)
        """, (contact_id, follow_up_date, f"Follow-up from call: {notes[:80]}"))

    status_map = {
        "interested": "interested",
        "meeting_set": "interested",
        "deal_closed": "closed_won",
        "not_interested": "closed_lost",
    }
    if outcome in status_map:
        conn.execute(
            "UPDATE contacts SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status_map[outcome], contact_id)
        )

    conn.commit()
    conn.close()


def get_call_history(contact_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM call_logs WHERE contact_id=? ORDER BY called_at DESC
    """, (contact_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_call_stats(days=30):
    conn = get_conn()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT outcome, COUNT(*) as count
        FROM call_logs
        WHERE called_at >= ?
        GROUP BY outcome
        ORDER BY count DESC
    """, (since,)).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM call_logs WHERE called_at >= ?", (since,)
    ).fetchone()[0]
    conn.close()
    return {"total": total, "by_outcome": [dict(r) for r in rows]}


def schedule_follow_up(contact_id, follow_up_type, days_from_now, notes=""):
    date = (datetime.now() + timedelta(days=days_from_now)).date().isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT INTO follow_ups (contact_id, follow_up_type, scheduled_date, notes)
        VALUES (?, ?, ?, ?)
    """, (contact_id, follow_up_type, date, notes))
    conn.commit()
    conn.close()


def mark_follow_up_done(follow_up_id):
    conn = get_conn()
    conn.execute("UPDATE follow_ups SET completed=1 WHERE id=?", (follow_up_id,))
    conn.commit()
    conn.close()
