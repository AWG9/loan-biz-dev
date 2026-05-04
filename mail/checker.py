"""
IMAP reply checker — scans inbox for replies to sent emails
and updates the email_logs table with replied=1 + reply body.
"""
import imaplib
import email as email_lib
from email.header import decode_header
import os
from database.models import get_conn
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_HOST


def _imap_host():
    smtp = SMTP_HOST
    if "gmail" in smtp:
        return "imap.gmail.com"
    if "outlook" in smtp or "office365" in smtp:
        return "outlook.office365.com"
    if "yahoo" in smtp:
        return "imap.mail.yahoo.com"
    return smtp.replace("smtp.", "imap.")


def _decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []
    for b, enc in parts:
        if isinstance(b, bytes):
            decoded.append(b.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(b)
    return " ".join(decoded)


def _get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            pass
    return body.strip()


def check_replies():
    """
    Connect to IMAP, find replies to sent emails, update DB.
    Returns list of (email_log_id, contact_name, reply_snippet).
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return [], "Email credentials not configured."

    conn = get_conn()
    # Get all sent emails that haven't been replied to
    sent = conn.execute("""
        SELECT el.id, el.subject, el.contact_id, c.email as contact_email, c.name as contact_name
        FROM email_logs el
        JOIN contacts c ON el.contact_id = c.id
        WHERE el.status = 'sent' AND el.replied = 0 AND c.email IS NOT NULL
    """).fetchall()
    conn.close()

    if not sent:
        return [], "No pending sent emails to check."

    results = []
    try:
        imap = imaplib.IMAP4_SSL(_imap_host())
        imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        imap.select("INBOX")

        for row in sent:
            original_subject = row["subject"] or ""
            contact_email = row["contact_email"] or ""
            if not contact_email:
                continue

            # Search for replies: from contact + "Re:" subject pattern
            search_criteria = f'(FROM "{contact_email}")'
            _, msg_ids = imap.search(None, search_criteria)
            if not msg_ids or not msg_ids[0]:
                continue

            for mid in msg_ids[0].split():
                _, data = imap.fetch(mid, "(RFC822)")
                raw = data[0][1]
                msg = email_lib.message_from_bytes(raw)
                subj = _decode_str(msg.get("Subject", ""))
                clean_subj = subj.lower().replace("re:", "").replace("fwd:", "").strip()
                original_clean = original_subject.lower().replace("re:", "").strip()

                if clean_subj in original_clean or original_clean in clean_subj:
                    body = _get_body(msg)
                    db = get_conn()
                    db.execute("""
                        UPDATE email_logs
                        SET replied=1, reply_body=?, reply_received_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (body[:2000], row["id"]))
                    db.commit()
                    db.close()
                    results.append({
                        "log_id": row["id"],
                        "contact_name": row["contact_name"],
                        "snippet": body[:120],
                    })
                    break

        imap.logout()
    except Exception as e:
        return results, str(e)

    return results, None
