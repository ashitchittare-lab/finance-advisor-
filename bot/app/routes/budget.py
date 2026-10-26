from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Budget, Expense
from app.ai_advisor import generate_ai_budget_plan

budget_bp = Blueprint('budget', __name__)

@budget_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)

    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        allocated_amount = float(request.form.get('allocated_amount', 0.0) or 0.0)
        notes = request.form.get('notes', '').strip()

        if allocated_amount <= 0:
            flash("Budget limit must be greater than 0.", "danger")
        elif not category:
            flash("Category is required.", "danger")
        else:
            budget_item = Budget.query.filter_by(
                user_id=current_user.id, category=category, month=month, year=year
            ).first()

            if budget_item:
                budget_item.allocated_amount = allocated_amount
                budget_item.notes = notes
                flash(f"Updated budget limit for {category} to {current_user.currency}{allocated_amount:,.2f}.", "success")
            else:
                budget_item = Budget(
                    user_id=current_user.id,
                    category=category,
                    allocated_amount=allocated_amount,
                    month=month,
                    year=year,
                    notes=notes
                )
                db.session.add(budget_item)
                flash(f"Set new budget limit for {category} at {current_user.currency}{allocated_amount:,.2f}.", "success")

            db.session.commit()
            return redirect(url_for('budget.index', month=month, year=year))

    # Calculate actual spending against budget items
    budgets = Budget.query.filter_by(user_id=current_user.id, month=month, year=year).all()
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        db.extract('month', Expense.date) == month,
        db.extract('year', Expense.date) == year
    ).all()

    spending_map = {}
    for exp in expenses:
        spending_map[exp.category] = spending_map.get(exp.category, 0.0) + exp.amount

    budget_cards = []
    total_budgeted = 0.0
    total_spent_budgeted = 0.0
    overspent_count = 0

    for b in budgets:
        spent = spending_map.get(b.category, 0.0)
        remaining = b.allocated_amount - spent
        pct = round((spent / b.allocated_amount) * 100, 1) if b.allocated_amount > 0 else 0.0
        
        status = 'success'
        if pct > 100:
            status = 'danger'
            overspent_count += 1
        elif pct >= 80:
            status = 'warning'

        total_budgeted += b.allocated_amount
        total_spent_budgeted += spent

        budget_cards.append({
            'id': b.id,
            'category': b.category,
            'allocated': b.allocated_amount,
            'spent': spent,
            'remaining': remaining,
            'percentage': pct,
            'status': status,
            'notes': b.notes
        })

    # AI Plan Preview
    ai_plan = generate_ai_budget_plan(current_user, month=month, year=year)

    return render_template(
        'budget/index.html',
        budget_cards=budget_cards,
        total_budgeted=total_budgeted,
        total_spent_budgeted=total_spent_budgeted,
        overspent_count=overspent_count,
        ai_plan=ai_plan,
        month=month,
        year=year
    )


@budget_bp.route('/apply-ai-plan', methods=['POST'])
@login_required
def apply_ai_plan():
    today = date.today()
    month = request.form.get('month', today.month, type=int)
    year = request.form.get('year', today.year, type=int)

    ai_plan = generate_ai_budget_plan(current_user, month=month, year=year)
    applied_count = 0

    for item in ai_plan['plan']:
        cat = item['category']
        amt = item['allocated_amount']
        
        b = Budget.query.filter_by(
            user_id=current_user.id, category=cat, month=month, year=year
        ).first()

        if b:
            b.allocated_amount = amt
        else:
            b = Budget(
                user_id=current_user.id,
                category=cat,
                allocated_amount=amt,
                month=month,
                year=year,
                notes=f"AI Generated Plan ({current_user.persona.title()} model)"
            )
            db.session.add(b)
        applied_count += 1

    db.session.commit()
    flash(f"Successfully generated and applied AI budget plan for {applied_count} categories!", "success")
    return redirect(url_for('budget.index', month=month, year=year))


@budget_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    b = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    month, year = b.month, b.year
    db.session.delete(b)
    db.session.commit()
    flash("Budget item deleted.", "info")
    return redirect(url_for('budget.index', month=month, year=year))
