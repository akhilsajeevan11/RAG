let currentTopic = null;

// Function to load available topics when the page loads
function loadTopics() {
    fetch('/get-topics')
        .then(response => response.json())
        .then(data => {
            const topicButtons = document.querySelector('.topic-buttons');
            topicButtons.innerHTML = ''; // Clear existing buttons
            
            data.topics.forEach(topic => {
                const button = document.createElement('button');
                button.className = 'topic-button';
                button.onclick = () => selectTopic(topic);
                // Format the display text (replace underscores with spaces)
                button.textContent = topic.replace(/_/g, ' ');
                topicButtons.appendChild(button);
            });
        })
        .catch(error => console.error('Error loading topics:', error));
}

// Load topics when the page loads
document.addEventListener('DOMContentLoaded', () => {
    loadTopics();
    initializeUI();
});

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
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    if (typeof message === 'object') {
        let messageContent = message.answer;
        
        // Only add sources section if sources exist and are not empty
        if (message.sources && message.sources.length > 0) {
            messageContent += `
                <div class="sources">
                    <i class="fas fa-book"></i> Sources: ${message.sources.map(source => 
                        `Page ${source.page} from ${source.source.split('/').pop()}`
                    ).join(', ')}
                </div>`;
        }
        
        messageDiv.innerHTML = messageContent;
    } else {
        messageDiv.textContent = message;
    }
    
    document.getElementById('chat-messages').appendChild(messageDiv);
    messageDiv.scrollIntoView({ behavior: 'smooth' });
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
    // Remove active class from all buttons
    document.querySelectorAll('.topic-button').forEach(button => {
        button.classList.remove('active');
    });

    // Add active class to selected button
    const selectedButton = Array.from(document.querySelectorAll('.topic-button'))
        .find(button => button.textContent === topic);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }

    currentTopic = topic;
    
    // Clear previous chat messages
    const messagesDiv = document.getElementById('chat-messages');
    const welcomeMessage = document.querySelector('.welcome-message');
    // Keep the welcome message but clear the rest
    Array.from(messagesDiv.children)
        .filter(child => child !== welcomeMessage)
        .forEach(child => child.remove());
    
    // Add loading indicator
    const loadingIndicator = createLoadingIndicator();
    messagesDiv.appendChild(loadingIndicator);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Initialize the topic
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
            // Simple welcome message with topic name
            const welcomeText = `Topic initialized. You can now ask questions about ${topic}.`;
            
            addMessage(welcomeText, false);

            // Enable input field
            document.getElementById('user-input').disabled = false;
            document.getElementById('user-input').placeholder = `Ask a question about ${topic}...`;
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

// Add this function to handle initial UI state
function initializeUI() {
    // Disable input field until topic is selected
    const inputField = document.getElementById('user-input');
    inputField.disabled = true;
    inputField.placeholder = 'Please select a topic first...';
}