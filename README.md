# Loan BizDev Automation

An automated business development system for loan company interns doing cold outreach to small business owners. Tracks contacts, calls, emails, deals, and commissions — all from the terminal.

## Features

- **Contact CRM** — Import previous clients from CSV, track status through the pipeline
- **Cold Email Campaigns** — Templated sequences (initial outreach → follow-ups → proposal)
- **Call Logger** — Log every call with outcome and auto-schedule follow-ups
- **Deal Pipeline** — Prospect → Contacted → Interested → Proposal → Closed
- **Commission Tracker** — Real-time earnings by deal, week, month, and YTD
- **Dashboard** — Weekly goal progress, pipeline summary, follow-ups due

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env — add your email, name, phone, company name

# 3. Run the quickstart guide
python main.py quickstart
```

## Daily Workflow

```bash
# Morning: Check what's due
python main.py dashboard
python main.py outreach followups

# Import contacts (first time or new batch)
python main.py contacts import data/sample_contacts.csv

# Send email blast (preview first)
python main.py outreach email --dry-run
python main.py outreach email

# After a call
python main.py outreach call 3

# When someone says yes
python main.py deals add 3

# Close a deal
python main.py deals close 1 --won

# Track earnings
python main.py commission
```

## Email Templates

| Template | When to Use |
|---|---|
| `initial_outreach` | First contact with a previous client |
| `follow_up_1` | No response after 3–4 days |
| `follow_up_2` | Final follow-up before moving on |
| `proposal` | After a verbal agreement — send loan details |

Send to a specific contact:
```bash
python main.py outreach email --template follow_up_1 --contact-id 5
```

## Deal Pipeline Stages

`prospect` → `contacted` → `interested` → `proposal_sent` → `negotiating` → `closed_won` / `closed_lost`

Update a deal's stage:
```bash
python main.py deals update 2 proposal_sent
```

## Contact CSV Format

```csv
name,company,phone,email,industry,prev_loan_amount,notes
John Smith,Smith Bakery,555-123-4567,john@smith.example,Food & Beverage,15000,Good payer
```

## Commission

Default commission rate is set in `.env` (`DEFAULT_COMMISSION_RATE=0.02` = 2%).
Override per deal when adding it.

```bash
python main.py commission              # This month + YTD
python main.py commission --month 3    # March only
```

## All Commands

```
python main.py dashboard
python main.py quickstart

python main.py contacts list [--status prospect]
python main.py contacts add
python main.py contacts import FILE
python main.py contacts search QUERY
python main.py contacts view ID

python main.py outreach email [--template X] [--status X] [--contact-id X] [--dry-run]
python main.py outreach call CONTACT_ID
python main.py outreach followups
python main.py outreach done FOLLOWUP_ID

python main.py deals list [--status X]
python main.py deals add CONTACT_ID
python main.py deals close DEAL_ID [--won | --lost]
python main.py deals update DEAL_ID STATUS

python main.py commission [--month M] [--year Y]
```
