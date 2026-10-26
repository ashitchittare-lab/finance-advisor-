// AI Advisor Chat Interface Script

document.addEventListener('DOMContentLoaded', function () {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const messagesContainer = document.getElementById('chatMessages');
    const sendButton = document.getElementById('sendButton');
    const promptPills = document.querySelectorAll('.prompt-pill');

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    scrollToBottom();

    // Suggested prompt click handler
    promptPills.forEach(pill => {
        pill.addEventListener('click', function () {
            const promptText = this.getAttribute('data-prompt') || this.innerText.trim();
            messageInput.value = promptText;
            chatForm.dispatchEvent(new Event('submit'));
        });
    });

    if (chatForm) {
        chatForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (!message) return;

            // Append user bubble
            appendMessage('user', message, 'Just now');
            messageInput.value = '';
            scrollToBottom();

            // Append thinking placeholder
            const thinkingId = 'thinking-' + Date.now();
            appendThinkingPlaceholder(thinkingId);
            scrollToBottom();

            // Disable input while generating
            messageInput.disabled = true;
            sendButton.disabled = true;

            try {
                const response = await fetch('/advisor/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                removeElement(thinkingId);

                if (response.ok && data.reply) {
                    appendMessage('assistant', data.reply, data.timestamp || 'Just now', data.engine);
                } else {
                    appendMessage('assistant', data.error || 'Sorry, I encountered an issue processing your request.', 'Now', 'System Alert');
                }
            } catch (err) {
                removeElement(thinkingId);
                appendMessage('assistant', 'Network communication error. Please try again.', 'Now', 'Error');
            } finally {
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
                scrollToBottom();
            }
        });
    }

    function appendMessage(sender, text, timestamp, engine = null) {
        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${sender}`;

        let engineBadge = '';
        if (sender === 'assistant' && engine) {
            engineBadge = `<div class="small text-muted mb-1 d-flex align-items-center gap-1">
                <i class="bi bi-robot text-primary"></i>
                <span class="badge bg-white text-secondary border fs-8">${escapeHtml(engine)}</span>
            </div>`;
        }

        const formattedHtml = formatMarkdown(text);
        bubble.innerHTML = `${engineBadge}<div class="message-content">${formattedHtml}</div><div class="small text-end mt-1 opacity-75 fs-8">${timestamp}</div>`;
        messagesContainer.appendChild(bubble);
    }

    function appendThinkingPlaceholder(id) {
        const placeholder = document.createElement('div');
        placeholder.id = id;
        placeholder.className = 'message-bubble assistant thinking-bubble';
        placeholder.innerHTML = `
            <div class="d-flex align-items-center gap-2 text-muted">
                <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                <span class="small fst-italic">AI Advisor is analyzing your financial data...</span>
            </div>
        `;
        messagesContainer.appendChild(placeholder);
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.innerText = text;
        return div.innerHTML;
    }

    function formatMarkdown(text) {
        let raw = escapeHtml(text);
        
        // Headers
        raw = raw.replace(/^### (.*$)/gim, '<h6 class="fw-bold mt-2 mb-1 text-primary">$1</h6>');
        raw = raw.replace(/^## (.*$)/gim, '<h5 class="fw-bold mt-2 mb-1 text-primary">$1</h5>');
        
        // Bold
        raw = raw.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Italic
        raw = raw.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Bullet points
        raw = raw.replace(/^\s*[-•]\s+(.*$)/gim, '<li class="ms-2">$1</li>');
        
        // Numbers
        raw = raw.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="ms-2">$2</li>');
        
        // Line breaks
        raw = raw.replace(/\n\n/g, '<br><br>');
        raw = raw.replace(/\n/g, '<br>');

        return raw;
    }
});
