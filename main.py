#!/usr/bin/env python3
"""
Loan BizDev Automation — CLI
Usage: python main.py [COMMAND]
"""
import sys
import os
import click
from rich.console import Console
from rich.prompt import Prompt, Confirm

sys.path.insert(0, os.path.dirname(__file__))
from database.models import init_db

console = Console()


@click.group()
def cli():
    """Loan BizDev Automation — manage contacts, outreach, deals, and commissions."""
    init_db()


# ──────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────

@cli.command()
def dashboard():
    """Show the main performance dashboard."""
    from analytics.dashboard import show_dashboard
    show_dashboard()


# ──────────────────────────────────────────
# CONTACTS
# ──────────────────────────────────────────

@cli.group()
def contacts():
    """Manage contacts (prospects / previous clients)."""


@contacts.command("list")
@click.option("--status", default=None, help="Filter by status")
def contacts_list(status):
    """List all contacts."""
    from crm.contacts import get_all_contacts
    from analytics.dashboard import show_contacts_table
    items = get_all_contacts(status=status)
    console.print(f"\n[bold]{len(items)} contact(s)[/bold]")
    show_contacts_table(items)


@contacts.command("add")
def contacts_add():
    """Add a new contact interactively."""
    from crm.contacts import add_contact
    console.print("[bold cyan]Add New Contact[/bold cyan]")
    name = Prompt.ask("Full name")
    company = Prompt.ask("Company", default="")
    phone = Prompt.ask("Phone", default="")
    email = Prompt.ask("Email", default="")
    industry = Prompt.ask("Industry", default="")
    prev_loan = Prompt.ask("Previous loan amount ($)", default="0")
    notes = Prompt.ask("Notes", default="")
    cid = add_contact(name, company, phone, email, industry, float(prev_loan or 0), notes)
    if cid:
        console.print(f"[green]Contact added (ID: {cid})[/green]")
    else:
        console.print("[red]Failed to add contact (email may already exist).[/red]")


@contacts.command("import")
@click.argument("filepath")
def contacts_import(filepath):
    """Import contacts from a CSV file."""
    from crm.contacts import import_from_csv
    imported, skipped, errors = import_from_csv(filepath)
    console.print(f"[green]Imported: {imported}[/green]  Skipped (duplicate): {skipped}")
    for e in errors[:5]:
        console.print(f"[red]Error: {e}[/red]")


@contacts.command("search")
@click.argument("query")
def contacts_search(query):
    """Search contacts by name, company, email, or industry."""
    from crm.contacts import search_contacts
    from analytics.dashboard import show_contacts_table
    results = search_contacts(query)
    console.print(f"[bold]{len(results)} result(s) for '{query}'[/bold]")
    show_contacts_table(results)


@contacts.command("view")
@click.argument("contact_id", type=int)
def contacts_view(contact_id):
    """View full details and history for a contact."""
    from crm.contacts import get_contact
    from outreach.call_tracker import get_call_history
    c = get_contact(contact_id)
    if not c:
        console.print(f"[red]Contact {contact_id} not found.[/red]")
        return
    console.print(f"\n[bold cyan]{c['name']}[/bold cyan]  ({c.get('company', 'N/A')})")
    console.print(f"Phone: {c.get('phone', '—')}   Email: {c.get('email', '—')}")
    console.print(f"Industry: {c.get('industry', '—')}   Status: [bold]{c['status']}[/bold]")
    console.print(f"Previous loan: ${c.get('prev_loan_amount', 0):,.0f}")
    console.print(f"Notes: {c.get('notes', '—')}")
    calls = get_call_history(contact_id)
    if calls:
        console.print(f"\n[bold]Call History ({len(calls)} calls)[/bold]")
        for call in calls[:5]:
            console.print(f"  {call['called_at'][:10]}  {call['outcome']}  — {call.get('notes', '')[:60]}")


# ──────────────────────────────────────────
# OUTREACH
# ──────────────────────────────────────────

@cli.group()
def outreach():
    """Email and call outreach tools."""


@outreach.command("email")
@click.option("--template", default="initial_outreach",
              help="Template: initial_outreach, follow_up_1, follow_up_2, proposal")
@click.option("--status", default="prospect", help="Send to contacts with this status")
@click.option("--contact-id", type=int, default=None, help="Send to a single contact by ID")
@click.option("--dry-run", is_flag=True, help="Preview emails without sending")
def outreach_email(template, status, contact_id, dry_run):
    """Send a templated email campaign."""
    from crm.contacts import get_all_contacts, get_contact
    from outreach.email_sender import send_campaign
    from outreach.templates import list_templates

    if template not in list_templates():
        console.print(f"[red]Unknown template. Available: {', '.join(list_templates())}[/red]")
        return

    if contact_id:
        contacts = [get_contact(contact_id)]
        contacts = [c for c in contacts if c]
    else:
        contacts = get_all_contacts(status=status)

    if not contacts:
        console.print("[yellow]No contacts found for that filter.[/yellow]")
        return

    console.print(f"[bold]Sending '{template}' to {len(contacts)} contact(s)...[/bold]")
    if not dry_run and not Confirm.ask("Confirm send?"):
        return

    results = send_campaign(contacts, template, dry_run=dry_run)
    ok = sum(1 for _, s, _ in results if s)
    fail = len(results) - ok
    console.print(f"\n[green]Sent: {ok}[/green]  [red]Failed: {fail}[/red]")
    for contact, success, msg in results:
        if not success:
            console.print(f"  [red]✗ {contact['name']} — {msg}[/red]")
        elif dry_run:
            console.print(f"  [cyan]✓ {contact['name']} ({contact.get('email', 'no email')}) — preview shown[/cyan]")


@outreach.command("call")
@click.argument("contact_id", type=int)
def outreach_call(contact_id):
    """Log a call with a contact."""
    from crm.contacts import get_contact
    from outreach.call_tracker import log_call, OUTCOMES

    c = get_contact(contact_id)
    if not c:
        console.print(f"[red]Contact {contact_id} not found.[/red]")
        return

    console.print(f"\n[bold cyan]Logging call with: {c['name']} ({c.get('company', '')})[/bold cyan]")
    console.print(f"Phone: {c.get('phone', 'N/A')}")
    console.print()

    for i, o in enumerate(OUTCOMES, 1):
        console.print(f"  {i}. {o.replace('_', ' ').title()}")
    idx = Prompt.ask("Outcome", choices=[str(i) for i in range(1, len(OUTCOMES)+1)])
    outcome = OUTCOMES[int(idx) - 1]

    duration = Prompt.ask("Duration (minutes)", default="0")
    notes = Prompt.ask("Notes", default="")
    follow_up = None
    if outcome in ["left_voicemail", "callback_scheduled", "interested"]:
        follow_up = Prompt.ask("Follow-up in how many days?", default="3")

    log_call(contact_id, outcome, int(duration or 0), notes,
             follow_up_days=int(follow_up) if follow_up else None)
    console.print(f"[green]Call logged: {outcome}[/green]")
    if follow_up:
        console.print(f"[cyan]Follow-up scheduled in {follow_up} days.[/cyan]")


@outreach.command("followups")
def outreach_followups():
    """List all contacts with follow-ups due today or overdue."""
    from crm.contacts import get_contacts_due_followup
    due = get_contacts_due_followup()
    if not due:
        console.print("[green]No follow-ups due.[/green]")
        return
    console.print(f"[bold red]{len(due)} follow-up(s) due:[/bold red]\n")
    for f in due:
        console.print(
            f"  [{f['followup_id']}] {f['name']} ({f.get('company','')}) — "
            f"{f.get('follow_up_type','').upper()} due {f.get('scheduled_date','')} "
            f"| Status: {f['status']}"
        )
    console.print("\nMark done: [bold]python main.py outreach done <followup_id>[/bold]")


@outreach.command("done")
@click.argument("followup_id", type=int)
def outreach_done(followup_id):
    """Mark a follow-up as completed."""
    from outreach.call_tracker import mark_follow_up_done
    mark_follow_up_done(followup_id)
    console.print(f"[green]Follow-up {followup_id} marked complete.[/green]")


# ──────────────────────────────────────────
# DEALS
# ──────────────────────────────────────────

@cli.group()
def deals():
    """Deal pipeline management."""


@deals.command("list")
@click.option("--status", default=None)
def deals_list(status):
    """List all deals."""
    from crm.deals import get_all_deals
    from analytics.dashboard import show_deals_table
    items = get_all_deals(status=status)
    console.print(f"\n[bold]{len(items)} deal(s)[/bold]")
    show_deals_table(items)


@deals.command("add")
@click.argument("contact_id", type=int)
def deals_add(contact_id):
    """Create a new deal for a contact."""
    from crm.contacts import get_contact
    from crm.deals import add_deal
    from commission.tracker import estimate_commission

    c = get_contact(contact_id)
    if not c:
        console.print(f"[red]Contact {contact_id} not found.[/red]")
        return

    console.print(f"\n[bold cyan]New deal for: {c['name']} ({c.get('company', '')})[/bold cyan]")
    loan_amount = float(Prompt.ask("Loan amount ($)"))
    interest_rate = float(Prompt.ask("Interest rate (%)", default="8")) / 100
    term_months = int(Prompt.ask("Term (months)", default="12"))
    from config import DEFAULT_COMMISSION_RATE
    commission_rate = float(Prompt.ask(
        f"Commission rate (%)", default=str(DEFAULT_COMMISSION_RATE * 100)
    )) / 100
    notes = Prompt.ask("Notes", default="")

    est = estimate_commission(loan_amount, commission_rate)
    console.print(f"\n[bold]Estimated commission: [green]${est:,.2f}[/green][/bold]")

    if Confirm.ask("Add this deal?"):
        did = add_deal(contact_id, loan_amount, interest_rate, term_months, commission_rate, notes)
        console.print(f"[green]Deal added (ID: {did})[/green]")


@deals.command("close")
@click.argument("deal_id", type=int)
@click.option("--won/--lost", default=True, help="Won or lost")
def deals_close(deal_id, won):
    """Mark a deal as closed (won or lost)."""
    from crm.deals import close_deal
    close_deal(deal_id, won=won)
    status = "closed_won" if won else "closed_lost"
    color = "green" if won else "red"
    console.print(f"[{color}]Deal {deal_id} marked as {status}.[/{color}]")


@deals.command("update")
@click.argument("deal_id", type=int)
@click.argument("status")
def deals_update(deal_id, status):
    """Update deal status (e.g. proposal_sent, negotiating)."""
    from crm.deals import update_deal_status, PIPELINE_STAGES
    if status not in PIPELINE_STAGES:
        console.print(f"[red]Valid statuses: {', '.join(PIPELINE_STAGES)}[/red]")
        return
    update_deal_status(deal_id, status)
    console.print(f"[green]Deal {deal_id} updated to '{status}'.[/green]")


# ──────────────────────────────────────────
# COMMISSION
# ──────────────────────────────────────────

@cli.command()
@click.option("--month", type=int, default=None, help="Month number (1-12)")
@click.option("--year", type=int, default=None)
def commission(month, year):
    """Show commission earnings summary."""
    from commission.tracker import get_commission_summary, monthly_breakdown
    from datetime import datetime

    y = year or datetime.now().year
    summary = get_commission_summary(year=y, month=month)

    title = f"Commission — {datetime.now().strftime('%B') if not month else ''} {y}"
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"  Deals closed:   {summary['deal_count']}")
    console.print(f"  Loan volume:    ${summary['total_loan_volume']:,.0f}")
    console.print(f"  Commission:     [bold green]${summary['total_commission']:,.2f}[/bold green]")

    if summary["deals"]:
        console.print("\n[bold]Deals:[/bold]")
        for d in summary["deals"]:
            console.print(
                f"  ${d['loan_amount']:>10,.0f}  →  [green]${d['commission']:,.2f}[/green]"
                f"  ({d.get('contact_name','')} / {d.get('company','')})"
            )

    if not month:
        breakdown = monthly_breakdown(year=y)
        if breakdown:
            console.print("\n[bold]Monthly Breakdown:[/bold]")
            months = ["Jan","Feb","Mar","Apr","May","Jun",
                      "Jul","Aug","Sep","Oct","Nov","Dec"]
            for row in breakdown:
                m_name = months[int(row["month"]) - 1]
                console.print(
                    f"  {m_name}  {row['deals']} deal(s)  "
                    f"${row['volume']:,.0f}  →  [green]${row['commission']:,.2f}[/green]"
                )


# ──────────────────────────────────────────
# QUICK ACTIONS
# ──────────────────────────────────────────

@cli.command()
def quickstart():
    """Setup guide for first-time use."""
    console.print("""
[bold cyan]Loan BizDev Automation — Quick Start[/bold cyan]

[bold]1. Set up credentials[/bold]
   cp .env.example .env
   # Edit .env with your email, name, and company

[bold]2. Import your contacts[/bold]
   python main.py contacts import data/sample_contacts.csv

[bold]3. Send your first email blast[/bold]
   python main.py outreach email --dry-run          # Preview first
   python main.py outreach email                    # Send initial_outreach to all prospects

[bold]4. Log calls as you make them[/bold]
   python main.py outreach call <contact_id>

[bold]5. Check follow-ups each morning[/bold]
   python main.py outreach followups

[bold]6. Add a deal when someone says yes[/bold]
   python main.py deals add <contact_id>

[bold]7. Track your dashboard and commissions[/bold]
   python main.py dashboard
   python main.py commission

[dim]Tips:
  • Use --dry-run on email commands to preview before sending
  • Log every call — even no-answers — so the dashboard stays accurate
  • Set follow-up dates aggressively: 2–3 days for warm leads[/dim]
""")


if __name__ == "__main__":
    cli()
