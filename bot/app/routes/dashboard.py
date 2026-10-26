from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Income, Expense, Budget, SavingsGoal
from app.ai_advisor import assemble_financial_context

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    month = today.month
    year = today.year

    context = assemble_financial_context(current_user, year=year, month=month)

    # Recent transactions
    recent_incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).limit(5).all()
    recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(7).all()
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).all()

    # Pre-calculated monthly trends for the last 4 months
    monthly_trend = []
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for offset in range(3, -1, -1):
        target_m = month - offset
        target_y = year
        if target_m <= 0:
            target_m += 12
            target_y -= 1
        
        inc_sum = sum(i.amount for i in current_user.incomes if i.date.year == target_y and i.date.month == target_m)
        exp_sum = sum(e.amount for e in current_user.expenses if e.date.year == target_y and e.date.month == target_m)
        if inc_sum == 0 and offset == 0:
            inc_sum = current_user.monthly_income or 0.0
            
        monthly_trend.append({
            'label': f"{month_names[target_m - 1]} {target_y}",
            'income': round(inc_sum, 2),
            'expense': round(exp_sum, 2)
        })

    return render_template(
        'dashboard/index.html',
        context=context,
        recent_incomes=recent_incomes,
        recent_expenses=recent_expenses,
        goals=goals,
        monthly_trend=monthly_trend
    )
