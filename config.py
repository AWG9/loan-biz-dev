import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

DEFAULT_COMMISSION_RATE = float(os.getenv("DEFAULT_COMMISSION_RATE", 0.02))
DEALS_PER_WEEK = int(os.getenv("DEALS_PER_WEEK", 1))

COMPANY_NAME = os.getenv("COMPANY_NAME", "Capital Solutions Group")
YOUR_NAME = os.getenv("YOUR_NAME", "Anthony")
YOUR_PHONE = os.getenv("YOUR_PHONE", "")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bizdev.db")
