from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from datetime import datetime

from crm.contacts import get_all_contacts, get_contacts_due_followup
from crm.deals import get_pipeline_summary, get_weekly_deals, get_all_deals
from outreach.call_tracker import get_call_stats
from outreach.email_sender import get_email_stats
from commission.tracker import get_weekly_commission, get_commission_summary
from config import DEALS_PER_WEEK, YOUR_NAME

console = Console()


def show_dashboard():
    now = datetime.now()
    console.print(Panel.fit(
        f"[bold cyan]BizDev Command Center[/bold cyan]  —  {YOUR_NAME}  —  {now.strftime('%A, %B %d %Y')}",
        border_style="cyan"
    ))

    _show_weekly_goal()
    _show_pipeline()
    _show_recent_activity()
    _show_followups()
    _show_commission_snapshot()


def _show_weekly_goal():
    weekly = get_weekly_deals(weeks_back=0)
    count = len(weekly)
    goal = DEALS_PER_WEEK
    pct = min(count / goal * 100, 100) if goal > 0 else 0

    bar_len = 20
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    color = "green" if count >= goal else "yellow" if count >= goal * 0.5 else "red"

    volume = sum(d["loan_amount"] for d in weekly)
    commission = sum(d["loan_amount"] * d["commission_rate"] for d in weekly)

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Weekly Goal", f"[{color}]{bar}[/{color}]  {count}/{goal} deals")
    table.add_row("Loan Volume", f"${volume:,.0f}")
    table.add_row("Est. Commission", f"[green]${commission:,.2f}[/green]")

    console.print(Panel(table, title="[bold]This Week[/bold]", border_style=color))


def _show_pipeline():
    summary = get_pipeline_summary()
    stages = ["prospect", "contacted", "interested", "proposal_sent", "negotiating", "closed_won", "closed_lost"]
    colors = {
        "prospect": "white", "contacted": "blue", "interested": "cyan",
        "proposal_sent": "yellow", "negotiating": "magenta",
        "closed_won": "green", "closed_lost": "red"
    }

    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("Stage", style="bold")
    table.add_column("Deals", justify="center")
    table.add_column("Total Value", justify="right")

    for stage in stages:
        data = summary.get(stage, {"count": 0, "total_value": 0})
        color = colors.get(stage, "white")
        table.add_row(
            f"[{color}]{stage.replace('_', ' ').title()}[/{color}]",
            str(data["count"]),
            f"${data['total_value']:,.0f}",
        )

    console.print(Panel(table, title="[bold]Deal Pipeline[/bold]", border_style="blue"))


def _show_recent_activity():
    calls = get_call_stats(days=7)
    emails = get_email_stats()

    call_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    call_table.add_column("Outcome")
    call_table.add_column("Count", justify="center")
    for row in calls["by_outcome"][:6]:
        call_table.add_row(row["outcome"].replace("_", " ").title(), str(row["count"]))
    if not calls["by_outcome"]:
        call_table.add_row("[dim]No calls logged[/dim]", "")

    email_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    email_table.add_column("Template")
    email_table.add_column("Sent", justify="center")
    for row in emails[:5]:
        email_table.add_row(row["template_name"].replace("_", " ").title(), str(row["sent"]))
    if not emails:
        email_table.add_row("[dim]No emails logged[/dim]", "")

    console.print(Columns([
        Panel(call_table, title="[bold]Calls (7d)[/bold]", border_style="yellow"),
        Panel(email_table, title="[bold]Emails Sent[/bold]", border_style="magenta"),
    ]))


def _show_followups():
    due = get_contacts_due_followup()
    if not due:
        console.print(Panel("[green]No follow-ups due today![/green]",
                            title="[bold]Follow-ups Due[/bold]", border_style="green"))
        return

    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("Name")
    table.add_column("Company")
    table.add_column("Type")
    table.add_column("Due")

    for f in due[:10]:
        table.add_row(
            f["name"], f.get("company", "—"),
            f.get("follow_up_type", "—"),
            f.get("scheduled_date", "—"),
        )

    console.print(Panel(table, title=f"[bold]Follow-ups Due ({len(due)})[/bold]",
                        border_style="red"))


def _show_commission_snapshot():
    now = datetime.now()
    month = get_commission_summary(year=now.year, month=now.month)
    ytd = get_commission_summary(year=now.year)

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Period", style="bold")
    table.add_column("Deals", justify="center")
    table.add_column("Volume", justify="right")
    table.add_column("Commission", justify="right", style="green")

    table.add_row(
        now.strftime("%B"),
        str(month["deal_count"]),
        f"${month['total_loan_volume']:,.0f}",
        f"${month['total_commission']:,.2f}",
    )
    table.add_row(
        f"YTD {now.year}",
        str(ytd["deal_count"]),
        f"${ytd['total_loan_volume']:,.0f}",
        f"${ytd['total_commission']:,.2f}",
    )

    console.print(Panel(table, title="[bold]Commission Tracker[/bold]", border_style="green"))


def show_contacts_table(contacts):
    if not contacts:
        console.print("[yellow]No contacts found.[/yellow]")
        return
    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("ID", justify="center", style="dim")
    table.add_column("Name")
    table.add_column("Company")
    table.add_column("Phone")
    table.add_column("Email")
    table.add_column("Status")
    table.add_column("Industry")

    status_colors = {
        "prospect": "white", "contacted": "blue", "interested": "cyan",
        "closed_won": "green", "closed_lost": "red",
    }
    for c in contacts:
        color = status_colors.get(c.get("status", ""), "white")
        table.add_row(
            str(c["id"]), c.get("name", ""), c.get("company", ""),
            c.get("phone", ""), c.get("email", ""),
            f"[{color}]{c.get('status', '')}[/{color}]",
            c.get("industry", ""),
        )
    console.print(table)


def show_deals_table(deals):
    if not deals:
        console.print("[yellow]No deals found.[/yellow]")
        return
    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("ID", justify="center", style="dim")
    table.add_column("Contact")
    table.add_column("Company")
    table.add_column("Loan Amount", justify="right")
    table.add_column("Rate", justify="center")
    table.add_column("Status")
    table.add_column("Commission", justify="right", style="green")

    for d in deals:
        commission = d["loan_amount"] * d["commission_rate"]
        status_color = "green" if d["status"] == "closed_won" else "red" if d["status"] == "closed_lost" else "yellow"
        table.add_row(
            str(d["id"]), d.get("contact_name", ""), d.get("company", ""),
            f"${d['loan_amount']:,.0f}",
            f"{d['interest_rate']*100:.1f}%",
            f"[{status_color}]{d['status']}[/{status_color}]",
            f"${commission:,.2f}",
        )
    console.print(table)
