from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.username}! You are logged in as {Config.PERSONAS.get(user.persona, {}).get('label', user.persona)}.", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        persona = request.form.get('persona', 'salaried')
        monthly_income = float(request.form.get('monthly_income', 0.0) or 0.0)
        currency = request.form.get('currency', '$').strip()

        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please pick another.", "danger")
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "danger")
            return render_template('auth/register.html')

        new_user = User(
            username=username,
            email=email,
            persona=persona,
            monthly_income=monthly_income,
            currency=currency
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash("Registration successful! Welcome to Personal Finance Advisor Bot.", "success")
        return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been safely logged out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/demo-login/<persona_key>')
def demo_login(persona_key):
    """
    Instantly logs into any of the 4 scenario demo accounts:
    - alex_salaried (Scenario 1)
    - sam_student (Scenario 2)
    - jordan_freelancer (Scenario 3)
    - morgan_family (Scenario 4)
    """
    persona_map = {
        'salaried': 'alex_salaried',
        'student': 'sam_student',
        'freelancer': 'jordan_freelancer',
        'household': 'morgan_family'
    }
    username = persona_map.get(persona_key)
    if not username:
        flash("Unknown demo scenario.", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=username).first()
    if not user:
        # Re-seed if missing
        from app.seed_data import seed_all_scenarios
        seed_all_scenarios()
        user = User.query.filter_by(username=username).first()

    if user:
        login_user(user)
        label = Config.PERSONAS.get(user.persona, {}).get('label', user.persona)
        flash(f"Switched to Scenario Demo: {label} ({user.username})", "success")
        return redirect(url_for('dashboard.index'))
    else:
        flash("Demo account could not be loaded.", "danger")
        return redirect(url_for('auth.login'))
