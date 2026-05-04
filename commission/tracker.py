from database.models import get_conn
from datetime import datetime, timedelta


def get_commission_summary(year=None, month=None):
    conn = get_conn()
    year = year or datetime.now().year
    if month:
        rows = conn.execute("""
            SELECT d.*, c.name as contact_name, c.company,
                   (d.loan_amount * d.commission_rate) as commission
            FROM deals d JOIN contacts c ON d.contact_id = c.id
            WHERE d.status = 'closed_won'
              AND strftime('%Y', d.closed_at) = ?
              AND strftime('%m', d.closed_at) = ?
            ORDER BY d.closed_at DESC
        """, (str(year), f"{month:02d}")).fetchall()
    else:
        rows = conn.execute("""
            SELECT d.*, c.name as contact_name, c.company,
                   (d.loan_amount * d.commission_rate) as commission
            FROM deals d JOIN contacts c ON d.contact_id = c.id
            WHERE d.status = 'closed_won'
              AND strftime('%Y', d.closed_at) = ?
            ORDER BY d.closed_at DESC
        """, (str(year),)).fetchall()
    conn.close()
    deals = [dict(r) for r in rows]
    total_commission = sum(d["commission"] for d in deals)
    total_loan_volume = sum(d["loan_amount"] for d in deals)
    return {
        "deals": deals,
        "total_commission": total_commission,
        "total_loan_volume": total_loan_volume,
        "deal_count": len(deals),
    }


def get_weekly_commission(weeks_back=0):
    start = datetime.now() - timedelta(weeks=weeks_back) - timedelta(days=datetime.now().weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, (d.loan_amount * d.commission_rate) as commission
        FROM deals d
        WHERE d.status = 'closed_won'
          AND d.closed_at >= ? AND d.closed_at < ?
    """, (start.isoformat(), end.isoformat())).fetchall()
    conn.close()
    deals = [dict(r) for r in rows]
    return {
        "deals": deals,
        "total": sum(d["commission"] for d in deals),
        "count": len(deals),
        "week_start": start.strftime("%Y-%m-%d"),
    }


def estimate_commission(loan_amount, commission_rate=None):
    from config import DEFAULT_COMMISSION_RATE
    rate = commission_rate if commission_rate is not None else DEFAULT_COMMISSION_RATE
    return loan_amount * rate


def monthly_breakdown(year=None):
    conn = get_conn()
    year = year or datetime.now().year
    rows = conn.execute("""
        SELECT strftime('%m', closed_at) as month,
               COUNT(*) as deals,
               SUM(loan_amount) as volume,
               SUM(loan_amount * commission_rate) as commission
        FROM deals
        WHERE status = 'closed_won' AND strftime('%Y', closed_at) = ?
        GROUP BY month
        ORDER BY month
    """, (str(year),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
