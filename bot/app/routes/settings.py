import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        monthly_income = float(request.form.get('monthly_income', 0.0) or 0.0)
        persona = request.form.get('persona', current_user.persona)
        currency = request.form.get('currency', current_user.currency).strip()
        gemini_api_key = request.form.get('gemini_api_key', '').strip()

        current_user.monthly_income = monthly_income
        current_user.persona = persona
        current_user.currency = currency
        
        if gemini_api_key:
            current_user.gemini_api_key = gemini_api_key
            flash("Gemini API Key saved! Live AI analysis is now active.", "success")
        elif request.form.get('clear_api_key'):
            current_user.gemini_api_key = None
            flash("Gemini API Key removed. System will use intelligent heuristic advisor.", "info")

        db.session.commit()
        flash("Profile and financial settings updated successfully.", "success")
        return redirect(url_for('settings.index'))

    # Determine status of Gemini API
    active_key = current_user.gemini_api_key or current_app.config.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    ai_status = {
        'connected': bool(active_key and active_key.strip()),
        'model': current_app.config.get('GEMINI_MODEL', 'gemini-3.8-flash'),
        'has_user_key': bool(current_user.gemini_api_key)
    }

    return render_template('settings/index.html', ai_status=ai_status)
