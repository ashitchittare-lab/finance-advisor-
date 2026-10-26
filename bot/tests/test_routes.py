import json
from datetime import date
import pytest
from app import create_app
from app.config import Config
from app.models import db, User, Income, Expense, Budget

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Seed scenarios
        from app.seed_data import seed_all_scenarios
        seed_all_scenarios()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_demo_login_scenarios(client):
    for persona in ['salaried', 'student', 'freelancer', 'household']:
        res = client.get(f'/demo-login/{persona}', follow_redirects=True)
        assert res.status_code == 200
        assert b"Scenario Demo:" in res.data or b"Personal Finance" in res.data

def test_dashboard_requires_auth(client):
    client.get('/logout', follow_redirects=True)
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location

def test_income_routes(client):
    client.get('/demo-login/salaried', follow_redirects=True)
    # View incomes
    res = client.get('/transactions/income')
    assert res.status_code == 200
    assert b"Income Records" in res.data

    # Add income
    res = client.post('/transactions/income', data={
        'source': 'Bonus Payment',
        'amount': '1200.00',
        'category': 'Other Income',
        'date': str(date.today()),
        'notes': 'Quarterly KPI bonus',
        'is_recurring': ''
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Bonus Payment" in res.data

def test_expense_routes(client):
    client.get('/demo-login/student', follow_redirects=True)
    # View expenses
    res = client.get('/transactions/expenses')
    assert res.status_code == 200
    assert b"Daily &amp; Weekly Expenses" in res.data or b"Daily & Weekly Expenses" in res.data

    # Add expense
    res = client.post('/transactions/expenses', data={
        'title': 'Course Notebooks',
        'amount': '18.50',
        'category': 'Education & Books',
        'is_essential': 'true',
        'date': str(date.today()),
        'payment_method': 'Cash',
        'notes': 'Stationery'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Course Notebooks" in res.data

def test_budget_routes_and_ai_plan(client):
    client.get('/demo-login/freelancer', follow_redirects=True)
    res = client.get('/budget/')
    assert res.status_code == 200
    assert b"Budget Planning &amp; Limits" in res.data or b"Budget Planning & Limits" in res.data

    # Apply AI plan
    res = client.post('/budget/apply-ai-plan', data={
        'month': str(date.today().month),
        'year': str(date.today().year)
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Successfully generated and applied AI budget plan" in res.data

def test_goals_routes(client):
    client.get('/demo-login/household', follow_redirects=True)
    res = client.get('/goals/')
    assert res.status_code == 200
    assert b"Savings Goals &amp; Emergency Fund" in res.data or b"Savings Goals & Emergency Fund" in res.data

    # Create goal
    res = client.post('/goals/', data={
        'title': 'Kitchen Remodel',
        'target_amount': '3000.00',
        'current_amount': '500.00',
        'category': 'Major Purchase',
        'target_date': '',
        'notes': ''
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Kitchen Remodel" in res.data

def test_advisor_chat_api(client):
    client.get('/demo-login/salaried', follow_redirects=True)
    res = client.post('/advisor/chat', 
        data=json.dumps({'message': 'How can I save more money on groceries?'}),
        content_type='application/json'
    )
    assert res.status_code == 200
    data = json.loads(res.data)
    assert 'reply' in data
    assert 'engine' in data
    assert len(data['reply']) > 10

def test_reports_route(client):
    client.get('/demo-login/salaried', follow_redirects=True)
    res = client.get('/reports/')
    assert res.status_code == 200
    assert b"Monthly Financial Performance Report" in res.data
    assert b"Executive Synthesis" in res.data
