from datetime import date
import pytest
from app import create_app
from app.config import Config
from app.models import db, User, Income, Expense, Budget
from app.ai_advisor import (
    assemble_financial_context,
    generate_ai_budget_plan,
    generate_chat_response,
    generate_monthly_report_data
)

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_ai_budget_plan_all_personas(app):
    for persona in ['salaried', 'student', 'freelancer', 'household']:
        user = User(username=f'user_{persona}', email=f'{persona}@example.com', persona=persona, monthly_income=4000.0)
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        plan = generate_ai_budget_plan(user)
        assert plan['persona'] == persona
        assert len(plan['plan']) > 0
        assert plan['total_allocated'] > 0
        # Check percentage sum is roughly 100%
        pct_sum = sum(item['percentage'] for item in plan['plan'])
        assert 95.0 <= pct_sum <= 105.0

def test_financial_context_assembly(app):
    today = date.today()
    user = User(username='telemetry_user', email='tel@example.com', persona='freelancer', monthly_income=5000.0)
    user.set_password('pass123')
    db.session.add(user)
    db.session.commit()

    db.session.add(Income(user_id=user.id, source='Client 1', amount=5000.0, date=today))
    db.session.add(Expense(user_id=user.id, title='Rent', amount=1500.0, category='Housing & Rent', date=today, is_essential=True))
    db.session.add(Expense(user_id=user.id, title='Software', amount=200.0, category='Business / Project Expenses', date=today, is_essential=True))
    db.session.add(Budget(user_id=user.id, category='Housing & Rent', allocated_amount=1400.0, month=today.month, year=today.year))
    db.session.commit()

    context = assemble_financial_context(user)
    assert context['total_income'] == 5000.0
    assert context['total_expense'] == 1700.0
    assert context['net_savings'] == 3300.0
    assert context['savings_rate'] == 66.0
    # Overspent category detected ($1500 spent > $1400 budgeted)
    assert len(context['overspent_categories']) == 1
    assert 'Housing & Rent' in context['overspent_categories'][0]

def test_heuristic_advisor_response(app):
    user = User(username='chat_user', email='chat@example.com', persona='student', monthly_income=1000.0)
    user.set_password('pass123')
    db.session.add(user)
    db.session.commit()

    # Query about overspending
    reply, engine = generate_chat_response(user, "Why is my budget overspent?")
    assert len(reply) > 20
    assert "budget" in reply.lower() or "overspent" in reply.lower() or "within budget" in reply.lower()

    # Query about emergency fund
    reply, engine = generate_chat_response(user, "How much emergency fund do I need?")
    assert "emergency fund" in reply.lower()

def test_monthly_report_generation(app):
    today = date.today()
    user = User(username='rep_user', email='rep@example.com', persona='household', monthly_income=7000.0)
    user.set_password('pass123')
    db.session.add(user)
    db.session.commit()

    db.session.add(Income(user_id=user.id, source='Salary', amount=7000.0, date=today))
    db.session.add(Expense(user_id=user.id, title='Mortgage', amount=2000.0, category='Housing & Rent', date=today, is_essential=True))
    db.session.commit()

    report = generate_monthly_report_data(user, month=today.month, year=today.year)
    assert report['total_income'] == 7000.0
    assert report['total_expense'] == 2000.0
    assert report['net_savings'] == 5000.0
    assert report['financial_health_score'] >= 50
    assert len(report['ai_summary']) > 0
    assert len(report['ai_recommendations']) > 0
