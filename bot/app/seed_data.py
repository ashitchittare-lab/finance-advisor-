from datetime import date, timedelta
from app.models import db, User, Income, Expense, Budget, SavingsGoal, ChatMessage, FinancialReport

def seed_all_scenarios():
    """
    Populates the database with realistic demo accounts for all 4 scenarios described
    in the project requirements.
    """
    today = date.today()
    curr_month = today.month
    curr_year = today.year

    # -------------------------------------------------------------
    # Scenario 1: Salaried Professional (Alex Vance)
    # Income: $5,500/month
    # Categories: Rent ($1,800), Food ($650), Transport ($300), Entertainment ($450)
    # Overspending in Entertainment
    # -------------------------------------------------------------
    alex = User.query.filter_by(username='alex_salaried').first()
    if not alex:
        alex = User(
            username='alex_salaried',
            email='alex.salaried@example.com',
            persona='salaried',
            monthly_income=5500.0,
            currency='$'
        )
        alex.set_password('alex123')
        db.session.add(alex)
        db.session.flush()

        # Incomes
        db.session.add(Income(
            user_id=alex.id,
            source='Tech Corp - Monthly Salary',
            amount=5500.0,
            category='Monthly Salary',
            date=today.replace(day=1),
            notes='Direct deposit after taxes'
        ))

        # Budgets
        alex_budgets = [
            ('Housing & Rent', 1800.0),
            ('Food & Groceries', 650.0),
            ('Transportation', 350.0),
            ('Utilities & Bills', 300.0),
            ('Entertainment & Dining', 350.0),  # Limit is 350
            ('Investments & Savings', 1200.0),
            ('Healthcare & Medical', 150.0)
        ]
        for cat, limit in alex_budgets:
            db.session.add(Budget(
                user_id=alex.id, category=cat, allocated_amount=limit, month=curr_month, year=curr_year
            ))

        # Expenses (Intentionally showing overspending in Entertainment $480 > $350)
        alex_expenses = [
            ('Apartment Rent', 1800.0, 'Housing & Rent', 1, True),
            ('Electricity & Internet', 220.0, 'Utilities & Bills', 5, True),
            ('Grocery Haul at Whole Foods', 240.0, 'Food & Groceries', 7, True),
            ('Subway Monthly Pass', 130.0, 'Transportation', 8, True),
            ('Gasoline & Tolls', 120.0, 'Transportation', 12, True),
            ('Fine Dining & Weekend Lounge', 260.0, 'Entertainment & Dining', 14, False),
            ('Weekly Groceries', 190.0, 'Food & Groceries', 18, True),
            ('Concert Tickets & Movies', 220.0, 'Entertainment & Dining', 20, False),  # Pushes entertainment to $480!
            ('Health Insurance Co-pay', 45.0, 'Healthcare & Medical', 22, True),
        ]
        for title, amt, cat, day, is_ess in alex_expenses:
            day_clamped = min(day, 28)
            db.session.add(Expense(
                user_id=alex.id, title=title, amount=amt, category=cat,
                date=today.replace(day=day_clamped), is_essential=is_ess
            ))

        # Savings Goals
        db.session.add(SavingsGoal(
            user_id=alex.id, title='Index Fund & Roth IRA', target_amount=10000.0,
            current_amount=4500.0, target_date=today + timedelta(days=180),
            category='Investment'
        ))
        db.session.add(SavingsGoal(
            user_id=alex.id, title='Emergency Safety Buffer (3 Months)', target_amount=8000.0,
            current_amount=6200.0, target_date=today + timedelta(days=90),
            is_emergency_fund=True
        ))

        # Sample Chat Message
        db.session.add(ChatMessage(
            user_id=alex.id, sender='user',
            message='I noticed my entertainment spending is high. Can you check my budget?'
        ))
        db.session.add(ChatMessage(
            user_id=alex.id, sender='assistant',
            message='Hi Alex! You have spent $480 in Entertainment & Dining against your $350 limit ($130 over budget). Consider capping weekend dining for the remainder of this month to protect your Roth IRA contribution goal.'
        ))

    # -------------------------------------------------------------
    # Scenario 2: College Student (Sam Rivera)
    # Income: $850/month (Allowance + Campus Job)
    # Focus: Essential vs Discretionary, tight limits, cutting waste
    # -------------------------------------------------------------
    sam = User.query.filter_by(username='sam_student').first()
    if not sam:
        sam = User(
            username='sam_student',
            email='sam.student@example.com',
            persona='student',
            monthly_income=850.0,
            currency='$'
        )
        sam.set_password('sam123')
        db.session.add(sam)
        db.session.flush()

        db.session.add(Income(
            user_id=sam.id, source='Monthly Parental Allowance', amount=500.0,
            category='Allowance / Stipend', date=today.replace(day=1)
        ))
        db.session.add(Income(
            user_id=sam.id, source='Campus Library Work-Study', amount=350.0,
            category='Side Hustle / Business', date=today.replace(day=15)
        ))

        sam_budgets = [
            ('Housing & Rent', 300.0),
            ('Food & Groceries', 200.0),
            ('Education & Books', 100.0),
            ('Transportation', 50.0),
            ('Entertainment & Dining', 80.0),
            ('Investments & Savings', 120.0),
        ]
        for cat, limit in sam_budgets:
            db.session.add(Budget(
                user_id=sam.id, category=cat, allocated_amount=limit, month=curr_month, year=curr_year
            ))

        sam_expenses = [
            ('Campus Dorm Contribution', 300.0, 'Housing & Rent', 1, True),
            ('CS Textbook & Lab Manual', 75.0, 'Education & Books', 3, True),
            ('Campus Dining Card Top-up', 110.0, 'Food & Groceries', 6, True),
            ('Bus Pass', 35.0, 'Transportation', 8, True),
            ('Coffee & Energy Drinks', 42.0, 'Food & Groceries', 12, False),
            ('Streaming Subscriptions', 28.0, 'Entertainment & Dining', 14, False),
            ('Late Night Pizza with Friends', 45.0, 'Entertainment & Dining', 19, False),
        ]
        for title, amt, cat, day, is_ess in sam_expenses:
            day_clamped = min(day, 28)
            db.session.add(Expense(
                user_id=sam.id, title=title, amount=amt, category=cat,
                date=today.replace(day=day_clamped), is_essential=is_ess
            ))

        db.session.add(SavingsGoal(
            user_id=sam.id, title='New Coding Laptop Fund', target_amount=900.0,
            current_amount=320.0, target_date=today + timedelta(days=120)
        ))

    # -------------------------------------------------------------
    # Scenario 3: Freelancer (Jordan Reed)
    # Variable income from multiple clients ($4,800 this month, $2,900 previous)
    # Focus: Fluctuating income, project expenses, 6-month emergency buffer
    # -------------------------------------------------------------
    jordan = User.query.filter_by(username='jordan_freelancer').first()
    if not jordan:
        jordan = User(
            username='jordan_freelancer',
            email='jordan.freelancer@example.com',
            persona='freelancer',
            monthly_income=4600.0,
            currency='$'
        )
        jordan.set_password('jordan123')
        db.session.add(jordan)
        db.session.flush()

        # Variable income from 3 distinct clients
        db.session.add(Income(
            user_id=jordan.id, source='Client Apex - UI/UX Design Contract', amount=2400.0,
            category='Freelance / Client Payment', date=today.replace(day=3)
        ))
        db.session.add(Income(
            user_id=jordan.id, source='Client Bloom - Logo & Branding Assets', amount=1200.0,
            category='Freelance / Client Payment', date=today.replace(day=12)
        ))
        db.session.add(Income(
            user_id=jordan.id, source='Client Cypher - Mobile App Consulting', amount=1000.0,
            category='Freelance / Client Payment', date=today.replace(day=20)
        ))

        jordan_budgets = [
            ('Housing & Rent', 1400.0),
            ('Food & Groceries', 600.0),
            ('Business / Project Expenses', 450.0),
            ('Utilities & Bills', 250.0),
            ('Transportation', 200.0),
            ('Entertainment & Dining', 300.0),
            ('Investments & Savings', 1400.0),
        ]
        for cat, limit in jordan_budgets:
            db.session.add(Budget(
                user_id=jordan.id, category=cat, allocated_amount=limit, month=curr_month, year=curr_year
            ))

        jordan_expenses = [
            ('Studio Apartment Rent', 1400.0, 'Housing & Rent', 1, True),
            ('Figma & Adobe CC Subscription', 85.0, 'Business / Project Expenses', 4, True),
            ('Cloud Server & Hosting', 45.0, 'Business / Project Expenses', 5, True),
            ('Groceries & Home Supplies', 320.0, 'Food & Groceries', 9, True),
            ('Co-working Day Pass', 60.0, 'Business / Project Expenses', 15, True),
            ('Dining Out with Clients', 180.0, 'Entertainment & Dining', 17, False),
            ('High Speed Fiber Internet', 90.0, 'Utilities & Bills', 18, True),
        ]
        for title, amt, cat, day, is_ess in jordan_expenses:
            day_clamped = min(day, 28)
            db.session.add(Expense(
                user_id=jordan.id, title=title, amount=amt, category=cat,
                date=today.replace(day=day_clamped), is_essential=is_ess
            ))

        db.session.add(SavingsGoal(
            user_id=jordan.id, title='6-Month Freelance Runway Fund', target_amount=15000.0,
            current_amount=9400.0, target_date=today + timedelta(days=240),
            is_emergency_fund=True
        ))
        db.session.add(SavingsGoal(
            user_id=jordan.id, title='Q4 Estimated Quarterly Tax Reserve', target_amount=3500.0,
            current_amount=2800.0, target_date=today + timedelta(days=45)
        ))

    # -------------------------------------------------------------
    # Scenario 4: Household Manager (Morgan Family)
    # Shared family income: $7,200 ($4,200 Primary + $3,000 Partner)
    # Categories: Groceries ($1,200), Utilities ($450), Education ($600), Healthcare ($350)
    # Overspending in Groceries & Utilities
    # -------------------------------------------------------------
    morgan = User.query.filter_by(username='morgan_family').first()
    if not morgan:
        morgan = User(
            username='morgan_family',
            email='morgan.family@example.com',
            persona='household',
            monthly_income=7200.0,
            currency='$'
        )
        morgan.set_password('morgan123')
        db.session.add(morgan)
        db.session.flush()

        db.session.add(Income(
            user_id=morgan.id, source='Primary Earner - Tech Lead Salary', amount=4200.0,
            category='Monthly Salary', date=today.replace(day=1)
        ))
        db.session.add(Income(
            user_id=morgan.id, source='Partner - Healthcare Administrator Salary', amount=3000.0,
            category='Monthly Salary', date=today.replace(day=1)
        ))

        morgan_budgets = [
            ('Housing & Rent', 2200.0),
            ('Food & Groceries', 1100.0),  # Limit is 1100
            ('Utilities & Bills', 400.0),   # Limit is 400
            ('Education & Books', 600.0),
            ('Healthcare & Medical', 350.0),
            ('Transportation', 500.0),
            ('Investments & Savings', 1500.0),
            ('Entertainment & Dining', 400.0),
        ]
        for cat, limit in morgan_budgets:
            db.session.add(Budget(
                user_id=morgan.id, category=cat, allocated_amount=limit, month=curr_month, year=curr_year
            ))

        morgan_expenses = [
            ('Family Home Mortgage', 2200.0, 'Housing & Rent', 1, True),
            ('Electricity, Gas & Water', 440.0, 'Utilities & Bills', 5, True),  # Over budget ($440 > $400)
            ('Costco Wholesale Bulk Grocery Haul', 680.0, 'Food & Groceries', 7, True),
            ('Children After-School Coding Class', 350.0, 'Education & Books', 9, True),
            ('School Uniforms & Activity Supplies', 180.0, 'Education & Books', 11, True),
            ('Supermarket Restock & Produce', 540.0, 'Food & Groceries', 16, True), # Over budget ($1220 > $1100)
            ('Pediatrician Checkup & Prescriptions', 160.0, 'Healthcare & Medical', 19, True),
            ('Family Weekend Dinner & Movies', 280.0, 'Entertainment & Dining', 21, False),
            ('Vehicle Fuel & Maintenance', 310.0, 'Transportation', 23, True),
        ]
        for title, amt, cat, day, is_ess in morgan_expenses:
            day_clamped = min(day, 28)
            db.session.add(Expense(
                user_id=morgan.id, title=title, amount=amt, category=cat,
                date=today.replace(day=day_clamped), is_essential=is_ess
            ))

        db.session.add(SavingsGoal(
            user_id=morgan.id, title='College Tuition Trust', target_amount=25000.0,
            current_amount=14200.0, target_date=today + timedelta(days=720)
        ))
        db.session.add(SavingsGoal(
            user_id=morgan.id, title='Family Emergency Fund (6 Months)', target_amount=20000.0,
            current_amount=15800.0, target_date=today + timedelta(days=365),
            is_emergency_fund=True
        ))

    db.session.commit()
