from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    persona = db.Column(db.String(32), default='salaried', nullable=False)  # salaried, student, freelancer, household
    monthly_income = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(8), default='$')
    gemini_api_key = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # Relationships
    incomes = db.relationship('Income', backref='user', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='user', lazy=True, cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy=True, cascade='all, delete-orphan')
    goals = db.relationship('SavingsGoal', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True, cascade='all, delete-orphan')
    reports = db.relationship('FinancialReport', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_monthly_income_total(self, year=None, month=None):
        if not year or not month:
            today = date.today()
            year, month = today.year, today.month
        return sum(
            inc.amount for inc in self.incomes 
            if inc.date.year == year and inc.date.month == month
        ) or self.monthly_income or 0.0

    def get_monthly_expense_total(self, year=None, month=None):
        if not year or not month:
            today = date.today()
            year, month = today.year, today.month
        return sum(
            exp.amount for exp in self.expenses 
            if exp.date.year == year and exp.date.month == month
        )

    def get_monthly_savings(self, year=None, month=None):
        return self.get_monthly_income_total(year, month) - self.get_monthly_expense_total(year, month)
        
    def get_savings_rate(self, year=None, month=None):
        income = self.get_monthly_income_total(year, month)
        if income <= 0:
            return 0.0
        savings = self.get_monthly_savings(year, month)
        return round(max(0.0, (savings / income) * 100), 1)

    def __repr__(self):
        return f'<User {self.username} [{self.persona}]>'


class Income(db.Model):
    __tablename__ = 'incomes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    source = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(64), default='Monthly Salary')
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    is_recurring = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<Income {self.source}: {self.amount}>'


class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    is_essential = db.Column(db.Boolean, default=True)
    payment_method = db.Column(db.String(32), default='Card')
    notes = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<Expense {self.title}: {self.amount}>'


class Budget(db.Model):
    __tablename__ = 'budgets'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category', 'month', 'year', name='uq_user_cat_month_year'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category = db.Column(db.String(64), nullable=False)
    allocated_amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<Budget {self.category} ({self.month}/{self.year}): {self.allocated_amount}>'


class SavingsGoal(db.Model):
    __tablename__ = 'savings_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(64), default='Emergency Fund')
    is_emergency_fund = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    @property
    def progress_percentage(self):
        if self.target_amount <= 0:
            return 100.0
        pct = (self.current_amount / self.target_amount) * 100
        return min(round(pct, 1), 100.0)

    @property
    def remaining_amount(self):
        return max(0.0, self.target_amount - self.current_amount)

    def __repr__(self):
        return f'<SavingsGoal {self.title}: {self.current_amount}/{self.target_amount}>'


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    sender = db.Column(db.String(16), nullable=False)  # 'user' or 'assistant'
    message = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(64), default='gemini-3.8-flash')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<ChatMessage {self.sender} at {self.created_at}>'


class FinancialReport(db.Model):
    __tablename__ = 'financial_reports'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'month', 'year', name='uq_report_user_month_year'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_income = db.Column(db.Float, nullable=False)
    total_expense = db.Column(db.Float, nullable=False)
    net_savings = db.Column(db.Float, nullable=False)
    savings_rate = db.Column(db.Float, nullable=False)
    top_spending_category = db.Column(db.String(64), nullable=True)
    ai_summary = db.Column(db.Text, nullable=True)
    ai_recommendations = db.Column(db.Text, nullable=True)
    financial_health_score = db.Column(db.Integer, default=75)  # 0 to 100
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<FinancialReport {self.month}/{self.year} score={self.financial_health_score}>'
