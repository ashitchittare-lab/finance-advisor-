import os
import json
import logging
from datetime import date
from flask import current_app
from app.models import Income, Expense, Budget, SavingsGoal

logger = logging.getLogger(__name__)

def get_gemini_client(api_key=None):
    """
    Initializes and returns a Google GenAI client if an API key is available.
    """
    key = api_key or current_app.config.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    if not key or key.strip() == '':
        return None, None
    try:
        from google import genai
        client = genai.Client(api_key=key.strip())
        model_name = current_app.config.get('GEMINI_MODEL', 'gemini-3.8-flash')
        return client, model_name
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini Client: {e}")
        return None, None


def assemble_financial_context(user, year=None, month=None):
    """
    Gathers comprehensive, real-time financial telemetry for the user
    to ground Gemini AI prompts in concrete numbers.
    """
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month

    incomes = [i for i in user.incomes if i.date.year == year and i.date.month == month]
    expenses = [e for e in user.expenses if e.date.year == year and e.date.month == month]
    budgets = [b for b in user.budgets if b.year == year and b.month == month]
    goals = list(user.goals)

    total_income = sum(i.amount for i in incomes) or user.monthly_income or 0.0
    total_expense = sum(e.amount for e in expenses)
    net_savings = total_income - total_expense
    savings_rate = round((net_savings / total_income * 100), 1) if total_income > 0 else 0.0

    # Categorize spending
    category_spending = {}
    essential_spending = 0.0
    discretionary_spending = 0.0
    for e in expenses:
        category_spending[e.category] = category_spending.get(e.category, 0.0) + e.amount
        if e.is_essential:
            essential_spending += e.amount
        else:
            discretionary_spending += e.amount

    # Compare with budgets
    budget_status = []
    overspent_categories = []
    for b in budgets:
        spent = category_spending.get(b.category, 0.0)
        variance = b.allocated_amount - spent
        pct_used = round((spent / b.allocated_amount * 100), 1) if b.allocated_amount > 0 else 0.0
        status_info = {
            'category': b.category,
            'allocated': b.allocated_amount,
            'spent': spent,
            'variance': variance,
            'pct_used': pct_used
        }
        budget_status.append(status_info)
        if spent > b.allocated_amount:
            overspent_categories.append(f"{b.category} (exceeded by {user.currency}{round(spent - b.allocated_amount, 2)})")

    # Goals summary
    goals_summary = []
    for g in goals:
        goals_summary.append({
            'title': g.title,
            'target': g.target_amount,
            'current': g.current_amount,
            'progress_pct': g.progress_percentage,
            'is_emergency': g.is_emergency_fund
        })

    return {
        'user_name': user.username,
        'persona': user.persona,
        'currency': user.currency,
        'month': month,
        'year': year,
        'total_income': round(total_income, 2),
        'total_expense': round(total_expense, 2),
        'net_savings': round(net_savings, 2),
        'savings_rate': savings_rate,
        'essential_spending': round(essential_spending, 2),
        'discretionary_spending': round(discretionary_spending, 2),
        'category_spending': {k: round(v, 2) for k, v in category_spending.items()},
        'budget_status': budget_status,
        'overspent_categories': overspent_categories,
        'goals_summary': goals_summary
    }


def generate_chat_response(user, user_message, chat_history=None):
    """
    Generates an intelligent financial advice response.
    Uses Gemini API if key is available; otherwise uses rule-based financial advisor fallback.
    """
    context = assemble_financial_context(user)
    api_key = user.gemini_api_key or current_app.config.get('GEMINI_API_KEY')
    client, model_name = get_gemini_client(api_key)

    if client:
        try:
            # Build persona-focused prompt
            system_instruction = f"""
You are the "Personal Finance Advisor Bot", a friendly, highly skilled, and practical AI financial planning assistant.
The current user profile is:
- Persona: {context['persona'].upper()} (e.g. Salaried Professional, College Student, Freelancer, Household Manager)
- User Name: {context['user_name']}
- Monthly Income: {context['currency']}{context['total_income']}
- Monthly Expenses: {context['currency']}{context['total_expense']}
- Net Savings: {context['currency']}{context['net_savings']} (Savings Rate: {context['savings_rate']}%)
- Essential Expenses: {context['currency']}{context['essential_spending']}
- Discretionary Expenses: {context['currency']}{context['discretionary_spending']}
- Overspent Categories: {', '.join(context['overspent_categories']) if context['overspent_categories'] else 'None (Well within budget!)'}
- Category Spending: {json.dumps(context['category_spending'])}
- Active Goals: {json.dumps(context['goals_summary'])}

Guidelines for your response:
1. Base your recommendations on the user's real numbers above and their persona:
   - If Salaried: Focus on 50/30/20 rule, automated savings, index investing, and tax efficiency.
   - If College Student: Focus on frugal habits, meal prep, student discounts, textbook alternatives, and zero-debt living.
   - If Freelancer: Focus on income volatility, building a 3-6 month emergency fund, setting aside 25-30% for tax/buffer, and uneven cashflow management.
   - If Household Manager: Focus on bulk groceries, utility efficiency, kids education funds, shared healthcare buffers, and long-term family security.
2. Be encouraging, actionable, and structured with bullet points.
3. If they ask about overspending, pinpoint the exact categories from their data.
4. Keep the tone empathetic and conversational.
"""

            # Prepare messages/prompt with history
            conversation_text = ""
            if chat_history:
                recent_history = chat_history[-6:]
                for msg in recent_history:
                    role = "User" if msg.sender == 'user' else "Advisor"
                    conversation_text += f"{role}: {msg.message}\n"
            conversation_text += f"User: {user_message}\nAdvisor:"

            full_prompt = f"{system_instruction}\n\nRecent Conversation History:\n{conversation_text}"
            
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt
            )
            if response and response.text:
                return response.text.strip(), f"Gemini AI ({model_name})"
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}. Falling back to heuristic advisor.")

    # Heuristic Rule-Based Fallback Engine
    return heuristic_advisor_response(user, user_message, context), "Heuristic Financial Engine"


def heuristic_advisor_response(user, user_message, context):
    """
    Intelligent heuristic fallback when Gemini API key is not present or offline.
    Provides data-grounded, persona-specific financial guidance.
    """
    msg = user_message.lower()
    currency = context['currency']
    income = context['total_income']
    expense = context['total_expense']
    savings = context['net_savings']
    savings_rate = context['savings_rate']
    persona = context['persona']
    overspent = context['overspent_categories']
    
    # 1. Overspending or Budget Query
    if any(k in msg for k in ['overspend', 'budget', 'limit', 'exceed', 'spending too much']):
        if overspent:
            lines = [
                f"### ⚠️ Budget Alert Analysis for {context['user_name']}:",
                f"You have overspent in the following categories this month:",
                "".join([f"\n- **{cat}**" for cat in overspent]),
                f"\n**Total Spent**: {currency}{expense} / **Income**: {currency}{income} (Remaining: {currency}{savings}).",
                f"\n💡 **Action Plan:**",
                f"1. Freeze non-essential purchases in {overspent[0].split('(')[0].strip()} for the rest of the cycle.",
                f"2. Reallocate unspent funds from other categories to balance the deficit.",
                f"3. Review discretionary subscriptions and dining to protect your savings goal."
            ]
            return "\n".join(lines)
        else:
            return (
                f"### ✅ Excellent Budget Control!\n\n"
                f"You are currently **within budget across all allocated categories** for this period!\n"
                f"- **Monthly Income**: {currency}{income}\n"
                f"- **Total Spent**: {currency}{expense}\n"
                f"- **Projected Net Savings**: {currency}{savings} ({savings_rate}% savings rate)\n\n"
                f"Keep up this financial discipline. You are well positioned to channel this surplus into your savings goals."
            )

    # 2. Emergency Fund or Savings Query
    if any(k in msg for k in ['emergency', 'emergency fund', 'rainy day', 'safety net']):
        monthly_essential = context['essential_spending'] or (expense * 0.7)
        target_3mo = round(monthly_essential * 3, 2)
        target_6mo = round(monthly_essential * 6, 2)
        if persona == 'freelancer':
            target_recommended = target_6mo
            advice = "As a freelancer with variable monthly income, financial planners strongly recommend a **6-month cushion** to withstand quiet client cycles."
        else:
            target_recommended = target_3mo
            advice = "For stable earners and households, a **3-to-6 month essential expense buffer** protects against unexpected health or repair expenses."

        return (
            f"### 🛡️ Emergency Fund Assessment\n\n"
            f"- **Your Monthly Essential Expenses**: {currency}{round(monthly_essential, 2)}\n"
            f"- **3-Month Target**: {currency}{target_3mo}\n"
            f"- **6-Month Target**: {currency}{target_6mo}\n\n"
            f"{advice}\n\n"
            f"**Recommended Action**: Set aside {currency}{round(max(50.0, savings * 0.4), 2)} every month automatically into a high-yield liquid account until you reach {currency}{target_recommended}."
        )

    # 3. How to save more / cut expenses
    if any(k in msg for k in ['save', 'cut', 'reduce', 'tip', 'advice', 'invest', 'plan']):
        top_cats = sorted(context['category_spending'].items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = "\n".join([f"- **{cat}**: {currency}{amt}" for cat, amt in top_cats]) if top_cats else "- No logged expenses yet."

        persona_specific = {
            'salaried': (
                "1. **Adopt the 50/30/20 Rule**: 50% Needs, 30% Wants, 20% Savings & Debt elimination.\n"
                "2. **Automate Payday Transfers**: Transfer at least 20% to savings on the day your salary hits your account.\n"
                "3. **Audit Recurring Subscriptions**: Cancel gym/streaming services unused for over 30 days."
            ),
            'student': (
                "1. **Apply the 24-Hour Rule**: Wait 24 hours before buying anything non-essential over $25.\n"
                "2. **Optimize Textbooks & Food**: Utilize library reserves, digital rentals, and campus meal deals.\n"
                "3. **Track Every Small Coffee/Snack**: Micro-transactions often add up to over 30% of a student budget."
            ),
            'freelancer': (
                "1. **Base Living Expenses on Your Lowest Month**: Never increase lifestyle spending during peak invoice months.\n"
                "2. **Separate Tax & Profit Accounts**: Deduct 25% for taxes immediately upon receiving any client invoice payment.\n"
                "3. **Track Deductible Project Expenses**: Ensure software, gear, and workspace deductions are recorded."
            ),
            'household': (
                "1. **Meal Planning & Batch Groceries**: Plan weekly meals to cut grocery waste by up to 25%.\n"
                "2. **Utility Conservation**: Audit electricity and heating during off-peak hours.\n"
                "3. **Annual Family Goal Reviews**: Involve the household in setting milestone targets for vacations and education."
            )
        }

        return (
            f"### 💡 Personalized Financial Recommendations ({persona.title()})\n\n"
            f"Here is your real-time financial health snapshot:\n"
            f"- **Current Savings Rate**: {savings_rate}%\n"
            f"- **Top Spending Areas**:\n{top_str}\n\n"
            f"**Tailored Action Steps:**\n"
            f"{persona_specific.get(persona, persona_specific['salaried'])}\n\n"
            f"Would you like me to generate a complete monthly budget breakdown or simulate a specific savings goal?"
        )

    # Default general greeting & helper
    return (
        f"Hello {context['user_name']}! 👋 I am your **Personal Finance Advisor Bot**.\n\n"
        f"Here is where you stand today:\n"
        f"- 💵 **Monthly Income**: {currency}{income}\n"
        f"- 💳 **Total Expenses**: {currency}{expense}\n"
        f"- 📈 **Net Savings**: {currency}{savings} ({savings_rate}%)\n\n"
        f"You can ask me questions like:\n"
        f"1. *'How can I optimize my monthly budget?'*\n"
        f"2. *'Where am I spending the most money?'*\n"
        f"3. *'How large should my emergency fund be?'*\n"
        f"4. *'Give me advice tailored for my {persona} persona.'*\n\n"
        f"How can I assist your financial journey today?"
    )


def generate_ai_budget_plan(user, month=None, year=None):
    """
    Generates recommended category budget allocations based on user persona,
    income, and the classic 50/30/20 framework (adapted per scenario).
    """
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month

    incomes = [i for i in user.incomes if i.date.year == year and i.date.month == month]
    income = sum(i.amount for i in incomes) or user.monthly_income or 3000.0
    persona = user.persona

    # Persona tailored budget weights
    if persona == 'student':
        # 65% Needs, 20% Wants, 15% Savings
        weights = {
            'Housing & Rent': 0.35,
            'Food & Groceries': 0.22,
            'Education & Books': 0.08,
            'Transportation': 0.08,
            'Entertainment & Dining': 0.08,
            'Personal Care & Shopping': 0.04,
            'Investments & Savings': 0.15
        }
        philosophy = "Student Allowance Budget: Emphasizes tuition/books and essentials while keeping discretionary items strictly capped."
    elif persona == 'freelancer':
        # 45% Needs, 25% Wants, 30% Buffer / Emergency & Tax
        weights = {
            'Housing & Rent': 0.25,
            'Food & Groceries': 0.15,
            'Transportation': 0.05,
            'Utilities & Bills': 0.08,
            'Business / Project Expenses': 0.12,
            'Entertainment & Dining': 0.07,
            'Investments & Savings': 0.28
        }
        philosophy = "Freelance Cashflow Buffer: Maximizes savings allocation to 28% for tax reserves and dry-season cushion."
    elif persona == 'household':
        # 60% Needs, 20% Wants, 20% Family Savings
        weights = {
            'Housing & Rent': 0.28,
            'Food & Groceries': 0.20,
            'Utilities & Bills': 0.08,
            'Healthcare & Medical': 0.07,
            'Education & Books': 0.07,
            'Transportation': 0.08,
            'Entertainment & Dining': 0.05,
            'Investments & Savings': 0.17
        }
        philosophy = "Household Manager Plan: Allocates higher proportions to family groceries, utilities, healthcare, and education."
    else:  # salaried
        # Standard 50/30/20
        weights = {
            'Housing & Rent': 0.28,
            'Food & Groceries': 0.14,
            'Utilities & Bills': 0.06,
            'Transportation': 0.08,
            'Healthcare & Medical': 0.04,
            'Entertainment & Dining': 0.10,
            'Personal Care & Shopping': 0.06,
            'Investments & Savings': 0.20,
            'Miscellaneous': 0.04
        }
        philosophy = "Classic 50/30/20 Allocation: 50% Essential Needs, 30% Flexible Wants, 20% Dedicated Savings & Wealth Building."

    plan = []
    total_allocated = 0.0
    for cat, ratio in weights.items():
        amount = round(income * ratio, 2)
        total_allocated += amount
        plan.append({
            'category': cat,
            'allocated_amount': amount,
            'percentage': round(ratio * 100, 1)
        })

    return {
        'income': income,
        'persona': persona,
        'philosophy': philosophy,
        'plan': plan,
        'total_allocated': round(total_allocated, 2)
    }


def generate_monthly_report_data(user, month=None, year=None):
    """
    Computes a comprehensive monthly financial health review and AI summary.
    """
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month

    incomes = [i for i in user.incomes if i.date.year == year and i.date.month == month]
    expenses = [e for e in user.expenses if e.date.year == year and e.date.month == month]
    budgets = [b for b in user.budgets if b.year == year and b.month == month]

    total_income = sum(i.amount for i in incomes) or user.monthly_income or 0.0
    total_expense = sum(e.amount for e in expenses)
    net_savings = total_income - total_expense
    savings_rate = round((net_savings / total_income * 100), 1) if total_income > 0 else 0.0

    # Categorize
    cat_map = {}
    for e in expenses:
        cat_map[e.category] = cat_map.get(e.category, 0.0) + e.amount
    
    top_cat = max(cat_map.items(), key=lambda x: x[1])[0] if cat_map else "None"

    # Compute Financial Health Score (0 - 100)
    score = 50
    # Savings rate impact (+-25)
    if savings_rate >= 25:
        score += 25
    elif savings_rate >= 15:
        score += 15
    elif savings_rate >= 5:
        score += 5
    elif savings_rate < 0:
        score -= 20

    # Budget discipline (+-25)
    over_budget_count = 0
    for b in budgets:
        spent = cat_map.get(b.category, 0.0)
        if spent > b.allocated_amount:
            over_budget_count += 1

    if budgets:
        if over_budget_count == 0:
            score += 25
        elif over_budget_count == 1:
            score += 10
        else:
            score -= (over_budget_count * 8)

    health_score = max(10, min(100, int(score)))

    # Try Gemini AI for custom narrative report
    api_key = user.gemini_api_key or current_app.config.get('GEMINI_API_KEY')
    client, model_name = get_gemini_client(api_key)
    ai_summary = ""
    ai_recommendations = ""

    if client:
        try:
            prompt = f"""
Write an executive monthly financial summary report for a user with the persona '{user.persona}'.
Numbers for Month {month}/{year}:
- Total Income: {user.currency}{total_income}
- Total Expenses: {user.currency}{total_expense}
- Net Savings: {user.currency}{net_savings}
- Savings Rate: {savings_rate}%
- Top Expense Category: {top_cat} ({user.currency}{cat_map.get(top_cat, 0)})
- Calculated Financial Health Score: {health_score}/100

Format the output as two sections:
1. Executive Summary: (2-3 concise paragraphs evaluating performance)
2. Strategic Recommendations for Next Month: (3-4 bullet points)
"""
            res = client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                parts = res.text.split("Strategic Recommendations")
                if len(parts) == 2:
                    ai_summary = parts[0].replace("Executive Summary:", "").strip()
                    ai_recommendations = "Strategic Recommendations" + parts[1]
                else:
                    ai_summary = res.text.strip()
                    ai_recommendations = "• Maintain consistent tracking.\n• Keep essential costs prioritized.\n• Increase emergency fund contribution."
        except Exception as e:
            logger.warning(f"Gemini API report generation failed: {e}")

    if not ai_summary:
        ai_summary = (
            f"During {month}/{year}, your total recorded earnings reached {user.currency}{total_income:,.2f} "
            f"against total living expenditures of {user.currency}{total_expense:,.2f}. "
            f"This resulted in a net capital surplus of {user.currency}{net_savings:,.2f}, representing a {savings_rate}% savings rate. "
            f"Your largest area of expenditure was '{top_cat}', accounting for {user.currency}{cat_map.get(top_cat, 0):,.2f}."
        )
        ai_recommendations = (
            f"• **Target Top Expense**: Review '{top_cat}' to discover opportunities to negotiate recurring fees or trim discretionary purchases.\n"
            f"• **Savings Allocation**: Automatically transfer at least {user.currency}{max(50.0, net_savings * 0.5):,.2f} into dedicated savings goals on your next pay cycle.\n"
            f"• **Budget Guardrails**: Adjust category limits for the upcoming month to avoid unexpected overruns."
        )

    return {
        'month': month,
        'year': year,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': net_savings,
        'savings_rate': savings_rate,
        'top_spending_category': top_cat,
        'financial_health_score': health_score,
        'ai_summary': ai_summary,
        'ai_recommendations': ai_recommendations,
        'category_breakdown': cat_map
    }
