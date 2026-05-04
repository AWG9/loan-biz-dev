from config import YOUR_NAME, COMPANY_NAME, YOUR_PHONE

TEMPLATES = {
    "initial_outreach": {
        "subject": "Quick question about funding for {company}",
        "body": """Hi {name},

I hope this finds you well. My name is {your_name} from {company_name} — we specialize in fast, flexible business loans for small business owners.

I noticed that {company} has previously worked with us, and I wanted to personally reach out. Many of our clients are using this time to secure additional capital for growth, inventory, or cash flow needs.

We currently offer:
• Loans from $10,000 – $500,000
• Approval in as little as 24–48 hours
• Flexible repayment terms (6–60 months)
• No collateral required for qualifying businesses

Would you have 10 minutes this week for a quick call to explore what options might be a fit for you?

Looking forward to reconnecting,

{your_name}
{company_name}
{your_phone}
""",
    },

    "follow_up_1": {
        "subject": "Re: Funding options for {company} — following up",
        "body": """Hi {name},

I wanted to follow up on my previous message about business funding options for {company}.

I understand you're busy running your business — that's exactly why I want to make this as simple as possible. Many owners I speak with are surprised at how quickly we can get capital into their hands (sometimes same-week).

If the timing isn't right, no worries at all. But if you'd like to see what you qualify for with zero obligation, I'd love to chat.

A quick 10-minute call could save you weeks of back-and-forth with a bank.

Would any time this week work for you?

Best,
{your_name}
{company_name}
{your_phone}
""",
    },

    "follow_up_2": {
        "subject": "Last reach-out — {company} funding options",
        "body": """Hi {name},

I don't want to keep filling your inbox, so this will be my last note for now.

If you ever find yourself in need of fast business capital — whether it's to cover a slow season, jump on a growth opportunity, or manage cash flow — please don't hesitate to reach out.

We've helped hundreds of small business owners just like you get the funding they need, fast.

You can reach me directly at {your_phone} or simply reply to this email.

Wishing you and {company} continued success,

{your_name}
{company_name}
""",
    },

    "proposal": {
        "subject": "Your personalized loan proposal — {company}",
        "body": """Hi {name},

Thank you for taking the time to speak with me! As discussed, here is a summary of the loan option I believe fits {company} best:

Loan Amount:    ${loan_amount:,.0f}
Interest Rate:  {interest_rate:.1f}% APR
Term:           {term_months} months
Est. Monthly:   ~${monthly_payment:,.0f}/month

Next steps to move forward:
1. Reply to this email or call me at {your_phone}
2. I'll send you a short application (takes ~5 minutes)
3. We review and get back to you within 24–48 hours

I'm confident we can get you funded quickly. Please don't hesitate to reach out with any questions.

Looking forward to getting this done for you,

{your_name}
{company_name}
{your_phone}
""",
    },
}


def render_template(template_name, contact, extra=None):
    t = TEMPLATES.get(template_name)
    if not t:
        return None, None
    ctx = {
        "name": contact.get("name", "there").split()[0],
        "company": contact.get("company", "your business"),
        "your_name": YOUR_NAME,
        "company_name": COMPANY_NAME,
        "your_phone": YOUR_PHONE,
        **(extra or {}),
    }
    subject = t["subject"].format(**ctx)
    body = t["body"].format(**ctx)
    return subject, body


def list_templates():
    return list(TEMPLATES.keys())
