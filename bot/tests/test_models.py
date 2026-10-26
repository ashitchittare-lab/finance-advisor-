from datetime import date
import pytest
from app import create_app
from app.config import Config
from app.models import db, User, Income, Expense, Budget, SavingsGoal

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

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_password_hashing(app):
    user = User(username='testuser', email='test@example.com', persona='salaried')
    user.set_password('securepassword')
    assert user.password_hash != 'securepassword'
    assert user.check_password('securepassword') is True
    assert user.check_password('wrongpassword') is False

def test_financial_calculations(app):
    user = User(username='calc_user', email='calc@example.com', persona='salaried', monthly_income=5000.0)
    user.set_password('pass123')
    db.session.add(user)
    db.session.commit()

    today = date.today()
    # Add income
    inc = Income(user_id=user.id, source='Salary', amount=6000.0, category='Monthly Salary', date=today)
    db.session.add(inc)

    # Add expenses
    exp1 = Expense(user_id=user.id, title='Rent', amount=2000.0, category='Housing & Rent', date=today, is_essential=True)
    exp2 = Expense(user_id=user.id, title='Groceries', amount=500.0, category='Food & Groceries', date=today, is_essential=True)
    exp3 = Expense(user_id=user.id, title='Concert', amount=500.0, category='Entertainment & Dining', date=today, is_essential=False)
    db.session.add_all([exp1, exp2, exp3])
    db.session.commit()

    assert user.get_monthly_income_total(today.year, today.month) == 6000.0
    assert user.get_monthly_expense_total(today.year, today.month) == 3000.0
    assert user.get_monthly_savings(today.year, today.month) == 3000.0
    assert user.get_savings_rate(today.year, today.month) == 50.0

def test_savings_goal_progress(app):
    user = User(username='goal_user', email='goal@example.com', persona='student')
    user.set_password('pass123')
    db.session.add(user)
    db.session.commit()

    goal = SavingsGoal(user_id=user.id, title='Laptop', target_amount=1000.0, current_amount=400.0)
    db.session.add(goal)
    db.session.commit()

    assert goal.progress_percentage == 40.0
    assert goal.remaining_amount == 600.0
