from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, ChatMessage
from app.ai_advisor import generate_chat_response, assemble_financial_context

advisor_bp = Blueprint('advisor', __name__)

@advisor_bp.route('/')
@login_required
def index():
    history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()
    context = assemble_financial_context(current_user)

    # Contextual quick prompts per persona
    persona_prompts = {
        'salaried': [
            "How can I optimize my 50/30/20 budget this month?",
            "Where am I spending too much on entertainment and dining?",
            "What is the best way to invest my monthly surplus?",
            "How healthy is my current savings rate?"
        ],
        'student': [
            "How can I cut non-essential spending on a student budget?",
            "Give me actionable tips to save on campus dining and coffee.",
            "Can I afford to buy a new laptop with my current allowance?",
            "How do I set up a realistic zero-debt student budget?"
        ],
        'freelancer': [
            "My income fluctuates each month. How do I build a 6-month buffer?",
            "How much should I set aside for quarterly taxes from my invoices?",
            "Analyze my client project expenses vs personal living costs.",
            "What should my budget strategy be during slow client months?"
        ],
        'household': [
            "How can we reduce our grocery and utility bills for the family?",
            "Are we on track with our children's education and vacation goals?",
            "Analyze our family spending overruns and give recommendations.",
            "How do we balance mortgage payments with emergency savings?"
        ]
    }

    quick_prompts = persona_prompts.get(current_user.persona, persona_prompts['salaried'])

    return render_template(
        'advisor/chat.html',
        history=history,
        context=context,
        quick_prompts=quick_prompts
    )


@advisor_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message cannot be empty.'}), 400

    # Save User message
    user_msg_record = ChatMessage(
        user_id=current_user.id,
        sender='user',
        message=user_message
    )
    db.session.add(user_msg_record)
    db.session.commit()

    # Retrieve history
    history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()

    # Generate response
    ai_text, engine_info = generate_chat_response(current_user, user_message, chat_history=history)

    # Save Assistant message
    ai_msg_record = ChatMessage(
        user_id=current_user.id,
        sender='assistant',
        message=ai_text,
        model_used=engine_info
    )
    db.session.add(ai_msg_record)
    db.session.commit()

    return jsonify({
        'reply': ai_text,
        'engine': engine_info,
        'timestamp': datetime.now(timezone.utc).strftime('%I:%M %p')
    })


@advisor_bp.route('/clear', methods=['POST'])
@login_required
def clear_history():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Conversation history cleared.", "info")
    return redirect(url_for('advisor.index'))
