document.addEventListener('DOMContentLoaded', () => {
    const chatApp = new ChatApplication();
    chatApp.initialize();
});

class ChatApplication {
    constructor() {
        this.currentTopic = null;
        this.abortController = null;
        this.isTopicLoading = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        // DOM Elements
        this.dom = {
            userInput: document.getElementById('user-input'),
            sendButton: document.getElementById('send-button'),
            chatMessages: document.getElementById('chat-messages'),
            typingIndicator: document.getElementById('typing-indicator'),
            topicGrid: document.querySelector('.topic-grid')
        };
    }

    initialize() {
        this.initializeUI();
        this.setupEventListeners();
        this.loadTopics();
    }

    initializeUI() {
        this.dom.userInput.disabled = true;
        this.dom.userInput.placeholder = 'Select a topic to begin...';
        this.dom.typingIndicator.style.display = 'none';
    }

    setupEventListeners() {
        this.dom.sendButton.addEventListener('click', () => this.sendMessage());
        
        this.dom.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.dom.topicGrid.addEventListener('click', (e) => {
            const topicCard = e.target.closest('.topic-card');
            if (topicCard) {
                this.selectTopic(topicCard.dataset.topic);
            }
        });
    }

    async loadTopics() {
        try {
            this.showTypingIndicator();
            const response = await fetch('/get-topics');
            
            // Check for HTTP errors first
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Handle explicit server errors
            if (data.error) {
                throw new Error(data.error);
            }
    
            // Handle empty topics case
            if (!data.topics || data.topics.length === 0) {
                this.addSystemMessage('No topics available. Contact administrator.');
                return;
            }
    
            // Clear and rebuild topics
            this.dom.topicGrid.innerHTML = '';
            data.topics.forEach(topic => this.createTopicCard(topic));
            
        } catch (error) {
            console.error('Topic load error:', error);
            this.addSystemMessage(error.message || 'Failed to load topics');
        } finally {
            this.hideTypingIndicator();
        }
    }

    createTopicCard(topic) {
        const topicCard = document.createElement('button');
        topicCard.className = 'topic-card';
        topicCard.dataset.topic = topic;
        topicCard.innerHTML = `
            <i class="${this.getTopicIcon(topic)}"></i>
            <span>${this.formatTopicName(topic)}</span>
        `;
        topicCard.addEventListener('click', () => this.handleTopicSelection(topicCard));
        this.dom.topicGrid.appendChild(topicCard);
    }

    async selectTopic(topic) {
        if (this.isTopicLoading || this.currentTopic === topic) return;
        
        try {
            this.isTopicLoading = true;
            this.showTypingIndicator();
            this.clearPreviousTopicState();
            
            if (this.abortController) {
                this.abortController.abort();
            }
            
            this.abortController = new AbortController();
            
            const response = await fetch('/initialize-topic', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic }),
                signal: this.abortController.signal
            });
            
            const data = await this.validateResponse(response);
            
            if (data.success) {
                this.currentTopic = topic;
                this.updateUIForSelectedTopic(topic);
                this.addSystemMessage(`Now ready to answer questions about ${this.formatTopicName(topic)}`);
            }
        } catch (error) {
            this.handleError('Topic initialization error:', error);
            this.currentTopic = null;
            this.addSystemMessage(error.message || 'Failed to initialize topic');
        } finally {
            this.isTopicLoading = false;
            this.hideTypingIndicator();
        }
    }

    async sendMessage() {
        const question = this.dom.userInput.value.trim();
        if (!question || !this.currentTopic) return;

        try {
            this.addMessage(question, true);
            this.dom.userInput.value = '';
            this.showTypingIndicator();
            
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    question: this.sanitizeInput(question), 
                    topic: this.currentTopic 
                })
            });
            
            const data = await this.validateResponse(response);
            this.handleBotResponse(data);
        } catch (error) {
            this.handleError('Message sending error:', error);
            this.addMessage('Sorry, there was an error processing your request.');
        } finally {
            this.hideTypingIndicator();
        }
    }

    // Helper methods
    sanitizeInput(input) {
        // Basic sanitization - implement proper sanitization based on your needs
        return input.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    async fetchWithRetry(url, options = {}, retries = this.maxRetries) {
        try {
            const response = await fetch(url, options);
            return await this.validateResponse(response);
        } catch (error) {
            if (retries > 0) {
                this.retryCount++;
                await new Promise(resolve => setTimeout(resolve, 1000 * this.retryCount));
                return this.fetchWithRetry(url, options, retries - 1);
            }
            throw error;
        }
    }

    async validateResponse(response) {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Response data:', data);
        if (data.error) throw new Error(data.error);
        return data;
    }

    handleBotResponse(data) {
        let responseContent = this.sanitizeInput(data.answer);
        if (data.sources?.length > 0) {
            responseContent += this.formatSources(data.sources);
        }
        this.addMessage(responseContent);
    }

    formatSources(sources) {
        return `
            <div class="sources" role="complementary" aria-label="Document sources">
                <i class="fas fa-file-pdf"></i>
                ${sources.map(src => `
                    <div class="source-item" role="listitem">
                        Page ${src.page} in ${src.source.split('/').pop()}
                    </div>
                `).join('')}
            </div>
        `;
    }

    addMessage(content, isUser = false) {
        const messageElement = this.createMessageElement(content, isUser);
        this.dom.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    createMessageElement(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.setAttribute('role', 'article');
        messageDiv.setAttribute('aria-live', 'assertive');

        const timestamp = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        messageDiv.innerHTML = `
            <div class="message-info" role="heading" aria-level="2">
                <i class="${isUser ? 'fas fa-user' : 'fas fa-robot'}" aria-hidden="true"></i>
                <span>${isUser ? 'You' : 'Assistant'}</span>
                <span>${timestamp}</span>
            </div>
            <div class="message-content" role="region">${content}</div>
        `;

        return messageDiv;
    }

    addSystemMessage(content) {
        const systemMessage = document.createElement('div');
        systemMessage.className = 'system-message';
        systemMessage.setAttribute('role', 'alert');
        systemMessage.innerHTML = `
            <i class="fas fa-info-circle" aria-hidden="true"></i>
            ${this.sanitizeInput(content)}
        `;
        this.dom.chatMessages.appendChild(systemMessage);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.dom.chatMessages.scrollTop = this.dom.chatMessages.scrollHeight;
    }

    updateUIForSelectedTopic(topic) {
        document.querySelectorAll('.topic-card').forEach(card => {
            card.classList.toggle('active', card.dataset.topic === topic);
        });
        this.dom.userInput.disabled = false;
        this.dom.userInput.placeholder = `Ask about ${this.formatTopicName(topic)}...`;
        this.dom.userInput.focus();
    }

    clearPreviousTopicState() {
        this.dom.chatMessages.querySelectorAll('.message-bubble').forEach(msg => msg.remove());
    }

    handleError(context, error) {
        console.error(context, error);
        if (error.name !== 'AbortError') {
            this.addSystemMessage(error.message || 'An unexpected error occurred');
        }
    }

    showTypingIndicator() {
        this.dom.typingIndicator.style.display = 'flex';
    }

    hideTypingIndicator() {
        this.dom.typingIndicator.style.display = 'none';
    }

    formatTopicName(topic) {
        return topic.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    getTopicIcon(topic) {
        const icons = {
            "RDBMS": 'fas fa-database',
            "Python Programming": 'fab fa-python',
            "Data Visualization": 'fas fa-chart-line',
            "Problem Solving C": 'fas fa-copyright',
            "Discrete Mathematics": 'fas fa-calculator'
        };
        return icons[topic] || 'fas fa-file-alt';
    }
}