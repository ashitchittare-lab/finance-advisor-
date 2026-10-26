from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access your financial dashboard.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.transactions import transactions_bp
    from app.routes.budget import budget_bp
    from app.routes.goals import goals_bp
    from app.routes.advisor import advisor_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    app.register_blueprint(budget_bp, url_prefix='/budget')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(advisor_bp, url_prefix='/advisor')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Global template context helpers
    @app.context_processor
    def inject_global_vars():
        from datetime import date
        today = date.today()
        return {
            'personas_config': app.config.get('PERSONAS', {}),
            'expense_categories': app.config.get('EXPENSE_CATEGORIES', []),
            'income_categories': app.config.get('INCOME_CATEGORIES', []),
            'current_year': today.year,
            'current_month': today.month,
            'mentor_name': 'Sai prathyusha Nagilla',
            'mentor_email': 'prathyusha+mentor@thesmartbridge.com'
        }

    # Create tables and auto-seed demo scenarios if database is newly initialized
    with app.app_context():
        db.create_all()
        try:
            from app.seed_data import seed_all_scenarios
            seed_all_scenarios()
        except Exception as e:
            app.logger.warning(f"Could not auto-seed database: {e}")

    return app
