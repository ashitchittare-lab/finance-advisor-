import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key-pfab-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{BASE_DIR / 'finance.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')
    
    # Personas configuration
    PERSONAS = {
        'salaried': {
            'label': 'Salaried Professional',
            'icon': 'bi-briefcase',
            'description': 'Regular monthly income, focus on 50/30/20 budgeting, long-term savings & tax planning.',
            'default_income': 5000.0,
            'default_currency': '$',
        },
        'student': {
            'label': 'College Student',
            'icon': 'bi-mortarboard',
            'description': 'Limited allowance or part-time earnings, essential vs. discretionary spending, budget limits.',
            'default_income': 850.0,
            'default_currency': '$',
        },
        'freelancer': {
            'label': 'Freelancer / Contractor',
            'icon': 'bi-laptop',
            'description': 'Fluctuating income from multiple clients, business expenses, emergency fund prioritization.',
            'default_income': 4200.0,
            'default_currency': '$',
        },
        'household': {
            'label': 'Household Manager',
            'icon': 'bi-house-heart',
            'description': 'Shared family income, utilities, groceries, childcare, health, and collective financial goals.',
            'default_income': 6800.0,
            'default_currency': '$',
        }
    }
    
    EXPENSE_CATEGORIES = [
        'Housing & Rent',
        'Food & Groceries',
        'Transportation',
        'Utilities & Bills',
        'Healthcare & Medical',
        'Education & Books',
        'Entertainment & Dining',
        'Personal Care & Shopping',
        'Debt & Loans',
        'Investments & Savings',
        'Business / Project Expenses',
        'Miscellaneous'
    ]
    
    INCOME_CATEGORIES = [
        'Monthly Salary',
        'Freelance / Client Payment',
        'Allowance / Stipend',
        'Dividends & Investments',
        'Side Hustle / Business',
        'Gift / Reimbursement',
        'Other Income'
    ]
