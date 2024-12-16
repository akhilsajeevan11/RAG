document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function createLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-message loading';
    loadingDiv.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;
    return loadingDiv;
}

function addMessage(message, isUser = false) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    if (typeof message === 'object') {
        // Bot message with sources
        messageDiv.innerHTML = `
            ${message.answer}
            <div class="sources">
                <i class="fas fa-book"></i> Sources: ${message.sources.map(source => 
                    `Page ${source.page} from ${source.source.split('/').pop()}`
                ).join(', ')}
            </div>
        `;
    } else {
        // User message
        messageDiv.textContent = message;
    }
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('user-input');
    const question = input.value.trim();
    
    if (question) {
        // Add user message to chat
        addMessage(question, true);
        
        // Clear input
        input.value = '';
        
        // Add loading indicator
        const messagesDiv = document.getElementById('chat-messages');
        const loadingIndicator = createLoadingIndicator();
        messagesDiv.appendChild(loadingIndicator);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Send request to backend
        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: question })
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            loadingIndicator.remove();
            // Add bot response to chat
            addMessage(data);
        })
        .catch(error => {
            // Remove loading indicator
            loadingIndicator.remove();
            console.error('Error:', error);
            addMessage('Sorry, there was an error processing your request.');
        });
    }
}