from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Income, Expense
from app.config import Config

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/income', methods=['GET', 'POST'])
@login_required
def income():
    if request.method == 'POST':
        source = request.form.get('source', '').strip()
        amount = float(request.form.get('amount', 0.0) or 0.0)
        category = request.form.get('category', 'Monthly Salary')
        date_str = request.form.get('date', '')
        notes = request.form.get('notes', '').strip()
        is_recurring = bool(request.form.get('is_recurring'))

        if amount <= 0:
            flash("Income amount must be greater than 0.", "danger")
        elif not source:
            flash("Source or client name is required.", "danger")
        else:
            try:
                txn_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
            except ValueError:
                txn_date = date.today()

            new_inc = Income(
                user_id=current_user.id,
                source=source,
                amount=amount,
                category=category,
                date=txn_date,
                is_recurring=is_recurring,
                notes=notes
            )
            db.session.add(new_inc)
            db.session.commit()
            flash(f"Logged income of {current_user.currency}{amount:,.2f} from {source}.", "success")
            return redirect(url_for('transactions.income'))

    # Filtering
    selected_month = request.args.get('month', type=int)
    selected_year = request.args.get('year', type=int)
    
    query = Income.query.filter_by(user_id=current_user.id)
    if selected_year:
        query = query.filter(db.extract('year', Income.date) == selected_year)
    if selected_month:
        query = query.filter(db.extract('month', Income.date) == selected_month)

    incomes_list = query.order_by(Income.date.desc()).all()
    total_income = sum(i.amount for i in incomes_list)

    return render_template(
        'transactions/income.html',
        incomes=incomes_list,
        total_income=total_income,
        selected_month=selected_month,
        selected_year=selected_year
    )


@transactions_bp.route('/income/delete/<int:id>', methods=['POST'])
@login_required
def delete_income(id):
    inc = Income.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(inc)
    db.session.commit()
    flash("Income record removed.", "info")
    return redirect(url_for('transactions.income'))


@transactions_bp.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        amount = float(request.form.get('amount', 0.0) or 0.0)
        category = request.form.get('category', 'Miscellaneous')
        date_str = request.form.get('date', '')
        is_essential = request.form.get('is_essential') == 'true'
        payment_method = request.form.get('payment_method', 'Card')
        notes = request.form.get('notes', '').strip()

        if amount <= 0:
            flash("Expense amount must be greater than 0.", "danger")
        elif not title:
            flash("Title or description is required.", "danger")
        else:
            try:
                txn_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
            except ValueError:
                txn_date = date.today()

            new_exp = Expense(
                user_id=current_user.id,
                title=title,
                amount=amount,
                category=category,
                date=txn_date,
                is_essential=is_essential,
                payment_method=payment_method,
                notes=notes
            )
            db.session.add(new_exp)
            db.session.commit()
            flash(f"Logged expense of {current_user.currency}{amount:,.2f} for {title}.", "success")
            return redirect(url_for('transactions.expenses'))

    # Filtering
    selected_month = request.args.get('month', type=int)
    selected_year = request.args.get('year', type=int)
    selected_category = request.args.get('category', '').strip()

    query = Expense.query.filter_by(user_id=current_user.id)
    if selected_year:
        query = query.filter(db.extract('year', Expense.date) == selected_year)
    if selected_month:
        query = query.filter(db.extract('month', Expense.date) == selected_month)
    if selected_category:
        query = query.filter_by(category=selected_category)

    expenses_list = query.order_by(Expense.date.desc()).all()
    total_expenses = sum(e.amount for e in expenses_list)
    essential_sum = sum(e.amount for e in expenses_list if e.is_essential)
    discretionary_sum = total_expenses - essential_sum

    return render_template(
        'transactions/expenses.html',
        expenses=expenses_list,
        total_expenses=total_expenses,
        essential_sum=essential_sum,
        discretionary_sum=discretionary_sum,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_category=selected_category
    )


@transactions_bp.route('/expenses/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    exp = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(exp)
    db.session.commit()
    flash("Expense entry removed.", "info")
    return redirect(url_for('transactions.expenses'))
