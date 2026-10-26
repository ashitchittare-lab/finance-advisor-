from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, SavingsGoal, Expense

goals_bp = Blueprint('goals', __name__)

@goals_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        target_amount = float(request.form.get('target_amount', 0.0) or 0.0)
        current_amount = float(request.form.get('current_amount', 0.0) or 0.0)
        category = request.form.get('category', 'General Savings')
        target_date_str = request.form.get('target_date', '')
        is_emergency = bool(request.form.get('is_emergency_fund'))
        notes = request.form.get('notes', '').strip()

        if target_amount <= 0:
            flash("Target amount must be greater than 0.", "danger")
        elif not title:
            flash("Goal title is required.", "danger")
        else:
            t_date = None
            if target_date_str:
                try:
                    t_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
                except ValueError:
                    t_date = None

            new_goal = SavingsGoal(
                user_id=current_user.id,
                title=title,
                target_amount=target_amount,
                current_amount=current_amount,
                target_date=t_date,
                category=category,
                is_emergency_fund=is_emergency,
                notes=notes
            )
            db.session.add(new_goal)
            db.session.commit()
            flash(f"Savings goal '{title}' created successfully!", "success")
            return redirect(url_for('goals.index'))

    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.created_at.desc()).all()
    
    total_target = sum(g.target_amount for g in goals)
    total_saved = sum(g.current_amount for g in goals)
    overall_progress = round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0

    # Calculate real monthly essential expenses to recommend emergency fund
    today = date.today()
    essential_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.is_essential == True,
        db.extract('month', Expense.date) == today.month,
        db.extract('year', Expense.date) == today.year
    ).all()
    monthly_essential = sum(e.amount for e in essential_expenses)
    if monthly_essential == 0:
        monthly_essential = (current_user.monthly_income or 3000.0) * 0.5

    rec_3mo = round(monthly_essential * 3, 2)
    rec_6mo = round(monthly_essential * 6, 2)

    return render_template(
        'goals/index.html',
        goals=goals,
        total_target=total_target,
        total_saved=total_saved,
        overall_progress=overall_progress,
        monthly_essential=monthly_essential,
        rec_3mo=rec_3mo,
        rec_6mo=rec_6mo
    )


@goals_bp.route('/contribute/<int:id>', methods=['POST'])
@login_required
def contribute(id):
    goal = SavingsGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    amount = float(request.form.get('amount', 0.0) or 0.0)
    
    if amount <= 0:
        flash("Contribution amount must be greater than 0.", "danger")
    else:
        goal.current_amount = round(goal.current_amount + amount, 2)
        db.session.commit()
        flash(f"Added {current_user.currency}{amount:,.2f} to '{goal.title}'. New balance: {current_user.currency}{goal.current_amount:,.2f}!", "success")

    return redirect(url_for('goals.index'))


@goals_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    goal = SavingsGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash("Savings goal deleted.", "info")
    return redirect(url_for('goals.index'))
