let currentTopic = null;

// Function to load available topics when the page loads
function loadTopics() {
    fetch('/get-topics')
        .then(response => response.json())
        .then(data => {
            const topicButtons = document.querySelector('.topic-buttons');
            data.topics.forEach(topic => {
                const button = document.createElement('button');
                button.className = 'topic-button';
                button.onclick = () => selectTopic(topic);
                button.textContent = topic;
                topicButtons.appendChild(button);
            });
        })
        .catch(error => console.error('Error loading topics:', error));
}

// Load topics when the page loads
document.addEventListener('DOMContentLoaded', loadTopics);

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
    
    if (!currentTopic) {
        addMessage('Please select a topic first!', false);
        return;
    }
    
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
            body: JSON.stringify({ 
                question: question,
                topic: currentTopic  // Include the selected topic
            })
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

function selectTopic(topic) {
    currentTopic = topic;
    
    // Add loading indicator
    const messagesDiv = document.getElementById('chat-messages');
    const loadingIndicator = createLoadingIndicator();
    messagesDiv.appendChild(loadingIndicator);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // First, initialize the topic
    fetch('/initialize-topic', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic: topic })
    })
    .then(response => response.json())
    .then(data => {
        // Remove loading indicator
        loadingIndicator.remove();
        
        if (data.success) {
            addMessage(`Selected topic: ${topic}`, true);
            addMessage(`Topic initialized. You can now ask questions about ${topic}.`);
        } else {
            addMessage(`Error initializing topic: ${data.error}`, false);
        }
    })
    .catch(error => {
        // Remove loading indicator
        loadingIndicator.remove();
        
        console.error('Error:', error);
        addMessage('Sorry, there was an error initializing the topic.');
    });
}