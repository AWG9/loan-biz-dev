import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database.models import get_conn
from outreach.templates import render_template
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT


def _log_email(contact_id, template_name, subject, body):
    conn = get_conn()
    conn.execute("""
        INSERT INTO email_logs (contact_id, template_name, subject, body)
        VALUES (?, ?, ?, ?)
    """, (contact_id, template_name, subject, body))
    conn.commit()
    conn.close()


def send_email(to_address, subject, body, contact_id=None, template_name=None, dry_run=False):
    """
    Send a plain-text email. Set dry_run=True to preview without sending.
    Returns (success: bool, message: str)
    """
    if dry_run:
        print(f"\n[DRY RUN] To: {to_address}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        return True, "dry_run"

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return False, "Email credentials not set. Copy .env.example to .env and fill in credentials."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_address, msg.as_string())
        if contact_id:
            _log_email(contact_id, template_name or "", subject, body)
        return True, "sent"
    except Exception as e:
        return False, str(e)


def send_campaign(contacts, template_name, dry_run=False, extra=None):
    """
    Send a templated email to a list of contacts.
    contacts: list of dicts with at least {id, name, company, email}
    Returns list of (contact, success, message)
    """
    results = []
    for contact in contacts:
        if not contact.get("email"):
            results.append((contact, False, "no email address"))
            continue
        subject, body = render_template(template_name, contact, extra)
        ok, msg = send_email(
            contact["email"], subject, body,
            contact_id=contact["id"],
            template_name=template_name,
            dry_run=dry_run,
        )
        results.append((contact, ok, msg))
    return results


def get_email_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT template_name,
               COUNT(*) as sent,
               SUM(opened) as opened,
               SUM(replied) as replied
        FROM email_logs
        GROUP BY template_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
