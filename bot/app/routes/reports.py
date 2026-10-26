from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, FinancialReport
from app.ai_advisor import generate_monthly_report_data

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)

    # Check if a saved report exists, or generate on the fly
    saved_report = FinancialReport.query.filter_by(
        user_id=current_user.id, month=month, year=year
    ).first()

    report_data = generate_monthly_report_data(current_user, month=month, year=year)

    # Past reports list for dropdown/history
    past_reports = FinancialReport.query.filter_by(
        user_id=current_user.id
    ).order_by(FinancialReport.year.desc(), FinancialReport.month.desc()).all()

    return render_template(
        'reports/monthly.html',
        report=report_data,
        saved_report=saved_report,
        past_reports=past_reports,
        month=month,
        year=year
    )


@reports_bp.route('/save', methods=['POST'])
@login_required
def save_report():
    today = date.today()
    month = request.form.get('month', today.month, type=int)
    year = request.form.get('year', today.year, type=int)

    data = generate_monthly_report_data(current_user, month=month, year=year)

    report = FinancialReport.query.filter_by(
        user_id=current_user.id, month=month, year=year
    ).first()

    if not report:
        report = FinancialReport(
            user_id=current_user.id,
            month=month,
            year=year,
            total_income=data['total_income'],
            total_expense=data['total_expense'],
            net_savings=data['net_savings'],
            savings_rate=data['savings_rate'],
            top_spending_category=data['top_spending_category'],
            ai_summary=data['ai_summary'],
            ai_recommendations=data['ai_recommendations'],
            financial_health_score=data['financial_health_score']
        )
        db.session.add(report)
    else:
        report.total_income = data['total_income']
        report.total_expense = data['total_expense']
        report.net_savings = data['net_savings']
        report.savings_rate = data['savings_rate']
        report.top_spending_category = data['top_spending_category']
        report.ai_summary = data['ai_summary']
        report.ai_recommendations = data['ai_recommendations']
        report.financial_health_score = data['financial_health_score']

    db.session.commit()
    flash(f"Monthly financial report for {month}/{year} saved successfully!", "success")
    return redirect(url_for('reports.index', month=month, year=year))
