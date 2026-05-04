"""
Loan BizDev Web App
Run: python app.py
Open: http://localhost:5000
"""
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database.models import init_db, get_conn
from crm.contacts import (get_all_contacts, get_contact, add_contact,
                           import_from_csv, search_contacts, update_contact_status)
from crm.deals import (get_all_deals, add_deal, close_deal, update_deal_status,
                       get_pipeline_summary, get_weekly_deals, PIPELINE_STAGES)
from outreach.templates import render_template as render_email_template, list_templates, TEMPLATES
from outreach.email_sender import send_email
from outreach.call_tracker import log_call, get_call_history, schedule_follow_up, mark_follow_up_done, OUTCOMES
from commission.tracker import get_commission_summary, get_weekly_commission, monthly_breakdown
from config import DEALS_PER_WEEK, YOUR_NAME, COMPANY_NAME

app = Flask(__name__)
app.secret_key = os.urandom(24)


def init():
    init_db()


# ──────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────

def _email_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT el.*, c.name as contact_name, c.company, c.email as contact_email
        FROM email_logs el JOIN contacts c ON el.contact_id = c.id
        ORDER BY el.sent_at DESC, el.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _draft_queue():
    conn = get_conn()
    rows = conn.execute("""
        SELECT el.*, c.name as contact_name, c.company, c.email as contact_email, c.industry
        FROM email_logs el JOIN contacts c ON el.contact_id = c.id
        WHERE el.status = 'draft'
        ORDER BY el.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _followups_due():
    conn = get_conn()
    rows = conn.execute("""
        SELECT f.*, c.name as contact_name, c.company, c.phone
        FROM follow_ups f JOIN contacts c ON f.contact_id = c.id
        WHERE f.completed = 0 AND f.scheduled_date <= date('now')
        ORDER BY f.scheduled_date ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────

@app.route("/")
def dashboard():
    now = datetime.now()
    weekly = get_weekly_deals(weeks_back=0)
    week_commission = sum(d["loan_amount"] * d["commission_rate"] for d in weekly)
    pipeline = get_pipeline_summary()
    month_summary = get_commission_summary(year=now.year, month=now.month)
    ytd = get_commission_summary(year=now.year)
    followups = _followups_due()

    # Email stats
    conn = get_conn()
    total_sent = conn.execute("SELECT COUNT(*) FROM email_logs WHERE status='sent'").fetchone()[0]
    total_replied = conn.execute("SELECT COUNT(*) FROM email_logs WHERE replied=1").fetchone()[0]
    total_drafts = conn.execute("SELECT COUNT(*) FROM email_logs WHERE status='draft'").fetchone()[0]
    conn.close()

    reply_rate = round(total_replied / total_sent * 100, 1) if total_sent else 0

    return render_template("dashboard.html",
        page="dashboard",
        your_name=YOUR_NAME,
        now=now,
        weekly_deals=len(weekly),
        weekly_goal=DEALS_PER_WEEK,
        week_commission=week_commission,
        pipeline=pipeline,
        month_summary=month_summary,
        ytd=ytd,
        followups=followups,
        total_sent=total_sent,
        total_replied=total_replied,
        total_drafts=total_drafts,
        reply_rate=reply_rate,
    )


# ──────────────────────────────────────────
# CONTACTS
# ──────────────────────────────────────────

@app.route("/contacts")
def contacts():
    status_filter = request.args.get("status")
    query = request.args.get("q", "").strip()
    if query:
        items = search_contacts(query)
    else:
        items = get_all_contacts(status=status_filter)
    statuses = ["prospect", "contacted", "interested", "proposal_sent",
                "negotiating", "closed_won", "closed_lost"]
    return render_template("contacts.html", page="contacts",
                           contacts=items, statuses=statuses,
                           status_filter=status_filter, query=query)


@app.route("/contacts/add", methods=["GET", "POST"])
def contacts_add():
    if request.method == "POST":
        cid = add_contact(
            name=request.form["name"],
            company=request.form.get("company", ""),
            phone=request.form.get("phone", ""),
            email=request.form.get("email", ""),
            industry=request.form.get("industry", ""),
            prev_loan_amount=float(request.form.get("prev_loan_amount", 0) or 0),
            notes=request.form.get("notes", ""),
        )
        if cid:
            flash(f"Contact added (ID {cid})", "success")
            return redirect(url_for("contacts"))
        else:
            flash("Failed — email may already exist.", "danger")
    return render_template("contact_form.html", page="contacts", contact=None)


@app.route("/contacts/<int:cid>")
def contact_detail(cid):
    c = get_contact(cid)
    if not c:
        flash("Contact not found.", "danger")
        return redirect(url_for("contacts"))
    calls = get_call_history(cid)
    conn = get_conn()
    emails = conn.execute("""
        SELECT * FROM email_logs WHERE contact_id=? ORDER BY id DESC
    """, (cid,)).fetchall()
    deals = conn.execute("""
        SELECT * FROM deals WHERE contact_id=? ORDER BY created_at DESC
    """, (cid,)).fetchall()
    followups = conn.execute("""
        SELECT * FROM follow_ups WHERE contact_id=? ORDER BY scheduled_date ASC
    """, (cid,)).fetchall()
    conn.close()
    return render_template("contact_detail.html", page="contacts",
                           contact=c, calls=calls,
                           emails=[dict(e) for e in emails],
                           deals=[dict(d) for d in deals],
                           followups=[dict(f) for f in followups],
                           outcomes=OUTCOMES)


@app.route("/contacts/<int:cid>/status", methods=["POST"])
def contact_status(cid):
    update_contact_status(cid, request.form["status"])
    return redirect(url_for("contact_detail", cid=cid))


@app.route("/contacts/import", methods=["POST"])
def contacts_import():
    f = request.files.get("csv_file")
    if not f:
        flash("No file selected.", "danger")
        return redirect(url_for("contacts"))
    path = os.path.join("data", "import_upload.csv")
    f.save(path)
    imported, skipped, errors = import_from_csv(path)
    flash(f"Imported {imported}, skipped {skipped} duplicates. {len(errors)} error(s).", "success")
    return redirect(url_for("contacts"))


# ──────────────────────────────────────────
# EMAILS — DRAFT QUEUE + LOG
# ──────────────────────────────────────────

@app.route("/emails")
def emails():
    tab = request.args.get("tab", "log")
    log = _email_stats()
    drafts = _draft_queue()
    templates = list_templates()
    contacts_list = get_all_contacts()
    return render_template("emails.html", page="emails",
                           tab=tab, log=log, drafts=drafts,
                           templates=templates, contacts=contacts_list)


@app.route("/emails/draft", methods=["POST"])
def email_draft():
    """Stage an email as a draft for review before sending."""
    contact_id = int(request.form["contact_id"])
    template_name = request.form["template_name"]
    contact = get_contact(contact_id)
    if not contact:
        flash("Contact not found.", "danger")
        return redirect(url_for("emails"))

    subject = request.form.get("subject") or ""
    body = request.form.get("body") or ""

    # If no custom body, render from template
    if not subject or not body:
        s, b = render_email_template(template_name, contact)
        subject = subject or s
        body = body or b

    conn = get_conn()
    conn.execute("""
        INSERT INTO email_logs (contact_id, template_name, subject, body, status)
        VALUES (?, ?, ?, ?, 'draft')
    """, (contact_id, template_name, subject, body))
    conn.commit()
    conn.close()
    flash(f"Draft saved for {contact['name']}. Review it in the Draft Queue.", "success")
    return redirect(url_for("emails", tab="drafts"))


@app.route("/emails/compose")
def compose():
    """Compose page — loads contact info + template preview side by side."""
    contact_id = request.args.get("contact_id", type=int)
    template_name = request.args.get("template", "initial_outreach")
    contacts_list = get_all_contacts()
    contact = get_contact(contact_id) if contact_id else None

    subject, body = ("", "")
    if contact and template_name:
        subject, body = render_email_template(template_name, contact)

    return render_template("compose.html", page="emails",
                           contacts=contacts_list,
                           contact=contact,
                           template_name=template_name,
                           templates=list_templates(),
                           subject=subject,
                           body=body)


@app.route("/emails/draft/<int:log_id>/edit", methods=["GET", "POST"])
def draft_edit(log_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT el.*, c.name as contact_name, c.company, c.email as contact_email
        FROM email_logs el JOIN contacts c ON el.contact_id = c.id
        WHERE el.id=?
    """, (log_id,)).fetchone()
    conn.close()
    if not row:
        flash("Draft not found.", "danger")
        return redirect(url_for("emails", tab="drafts"))

    draft = dict(row)

    if request.method == "POST":
        conn = get_conn()
        conn.execute("""
            UPDATE email_logs SET subject=?, body=? WHERE id=?
        """, (request.form["subject"], request.form["body"], log_id))
        conn.commit()
        conn.close()
        flash("Draft updated.", "success")
        return redirect(url_for("emails", tab="drafts"))

    return render_template("draft_edit.html", page="emails", draft=draft)


@app.route("/emails/draft/<int:log_id>/send", methods=["POST"])
def draft_send(log_id):
    """Send a staged draft email."""
    conn = get_conn()
    row = conn.execute("""
        SELECT el.*, c.email as contact_email, c.name as contact_name
        FROM email_logs el JOIN contacts c ON el.contact_id = c.id
        WHERE el.id=?
    """, (log_id,)).fetchone()
    conn.close()

    if not row:
        flash("Draft not found.", "danger")
        return redirect(url_for("emails", tab="drafts"))

    draft = dict(row)
    ok, msg = send_email(
        to_address=draft["contact_email"],
        subject=draft["subject"],
        body=draft["body"],
        contact_id=draft["contact_id"],
        template_name=draft["template_name"],
    )

    if ok:
        conn = get_conn()
        conn.execute("""
            UPDATE email_logs SET status='sent', sent_at=CURRENT_TIMESTAMP WHERE id=?
        """, (log_id,))
        conn.commit()
        conn.close()
        flash(f"Email sent to {draft['contact_name']}!", "success")
    else:
        flash(f"Send failed: {msg}", "danger")

    return redirect(url_for("emails", tab="drafts"))


@app.route("/emails/draft/<int:log_id>/delete", methods=["POST"])
def draft_delete(log_id):
    conn = get_conn()
    conn.execute("DELETE FROM email_logs WHERE id=? AND status='draft'", (log_id,))
    conn.commit()
    conn.close()
    flash("Draft deleted.", "info")
    return redirect(url_for("emails", tab="drafts"))


@app.route("/emails/send-all-drafts", methods=["POST"])
def send_all_drafts():
    """Send all drafts at once."""
    drafts = _draft_queue()
    sent, failed = 0, 0
    for d in drafts:
        if not d.get("contact_email"):
            failed += 1
            continue
        ok, _ = send_email(d["contact_email"], d["subject"], d["body"],
                           contact_id=d["contact_id"], template_name=d["template_name"])
        if ok:
            conn = get_conn()
            conn.execute("UPDATE email_logs SET status='sent', sent_at=CURRENT_TIMESTAMP WHERE id=?",
                         (d["id"],))
            conn.commit()
            conn.close()
            sent += 1
        else:
            failed += 1
    flash(f"Sent {sent} email(s). {failed} failed.", "success" if not failed else "warning")
    return redirect(url_for("emails", tab="log"))


@app.route("/emails/check-replies", methods=["POST"])
def check_replies():
    from mail.checker import check_replies as _check
    results, error = _check()
    if error and not results:
        flash(f"Reply check error: {error}", "danger")
    elif results:
        names = ", ".join(r["contact_name"] for r in results)
        flash(f"Found {len(results)} new reply(s): {names}", "success")
    else:
        flash("No new replies found.", "info")
    return redirect(url_for("emails", tab="log"))


@app.route("/emails/<int:log_id>/reply")
def view_reply(log_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT el.*, c.name as contact_name, c.email as contact_email, c.company
        FROM email_logs el JOIN contacts c ON el.contact_id = c.id
        WHERE el.id=?
    """, (log_id,)).fetchone()
    conn.close()
    if not row:
        flash("Not found.", "danger")
        return redirect(url_for("emails"))
    return render_template("reply_view.html", page="emails", log=dict(row))


# ──────────────────────────────────────────
# API — template preview (AJAX)
# ──────────────────────────────────────────

@app.route("/api/preview-template")
def api_preview_template():
    contact_id = request.args.get("contact_id", type=int)
    template_name = request.args.get("template")
    contact = get_contact(contact_id) if contact_id else {}
    if contact and template_name:
        subject, body = render_email_template(template_name, contact or {})
    else:
        subject, body = "", ""
    return jsonify({"subject": subject, "body": body})


@app.route("/api/contact-info/<int:cid>")
def api_contact_info(cid):
    c = get_contact(cid)
    if not c:
        return jsonify({}), 404
    return jsonify(c)


# ──────────────────────────────────────────
# CALLS
# ──────────────────────────────────────────

@app.route("/contacts/<int:cid>/log-call", methods=["POST"])
def log_call_route(cid):
    outcome = request.form["outcome"]
    duration = int(request.form.get("duration", 0) or 0)
    notes = request.form.get("notes", "")
    follow_up_days = request.form.get("follow_up_days")
    log_call(cid, outcome, duration, notes,
             follow_up_days=int(follow_up_days) if follow_up_days else None)
    flash(f"Call logged: {outcome.replace('_',' ').title()}", "success")
    return redirect(url_for("contact_detail", cid=cid))


@app.route("/followups/<int:fid>/done", methods=["POST"])
def followup_done(fid):
    mark_follow_up_done(fid)
    flash("Follow-up marked complete.", "success")
    return redirect(request.referrer or url_for("dashboard"))


# ──────────────────────────────────────────
# DEALS
# ──────────────────────────────────────────

@app.route("/deals")
def deals():
    all_deals = get_all_deals()
    pipeline = get_pipeline_summary()
    stages = PIPELINE_STAGES
    return render_template("deals.html", page="deals",
                           deals=all_deals, pipeline=pipeline, stages=stages)


@app.route("/deals/add", methods=["POST"])
def deals_add():
    from config import DEFAULT_COMMISSION_RATE
    contact_id = int(request.form["contact_id"])
    loan_amount = float(request.form["loan_amount"])
    interest_rate = float(request.form.get("interest_rate", 8)) / 100
    term_months = int(request.form.get("term_months", 12))
    commission_rate = float(request.form.get("commission_rate", DEFAULT_COMMISSION_RATE * 100)) / 100
    notes = request.form.get("notes", "")
    did = add_deal(contact_id, loan_amount, interest_rate, term_months, commission_rate, notes)
    flash(f"Deal added (ID {did})", "success")
    return redirect(url_for("deals"))


@app.route("/deals/<int:did>/close", methods=["POST"])
def deals_close(did):
    won = request.form.get("won", "true") == "true"
    close_deal(did, won=won)
    flash("Deal " + ("won! 🎉" if won else "marked lost."), "success" if won else "warning")
    return redirect(url_for("deals"))


@app.route("/deals/<int:did>/status", methods=["POST"])
def deals_status(did):
    update_deal_status(did, request.form["status"])
    return redirect(url_for("deals"))


# ──────────────────────────────────────────
# COMMISSION
# ──────────────────────────────────────────

@app.route("/commission")
def commission():
    now = datetime.now()
    month = get_commission_summary(year=now.year, month=now.month)
    ytd = get_commission_summary(year=now.year)
    breakdown = monthly_breakdown(year=now.year)
    months_map = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
    for row in breakdown:
        row["month_name"] = months_map[int(row["month"]) - 1]
    return render_template("commission.html", page="commission",
                           now=now, month=month, ytd=ytd, breakdown=breakdown)


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

if __name__ == "__main__":
    init()
    print("\n  Loan BizDev App running → http://localhost:5000\n")
    app.run(debug=True, port=5000)
