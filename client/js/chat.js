/**
 * Chat functionality for AI Web Crawler
 */

// Initialize variables
let activeSessionId = null;

/**
 * Enable chat functionality with the given session ID
 * @param {string} sessionId - The session ID for the current chat
 */
function enableChat(sessionId) {
    // Store the session ID
    activeSessionId = sessionId;
    
    // Get DOM elements
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    
    // Enable message input
    messageInput.disabled = false;
    messageInput.placeholder = 'Ask a question about the website...';
    messageInput.focus();
    
    // Setup event listeners
    setupChatEventListeners();
}

/**
 * Setup event listeners for chat functionality
 */
function setupChatEventListeners() {
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    
    // Clear previous event listeners (to avoid duplicates)
    const newMessageInput = messageInput.cloneNode(true);
    const newSendBtn = sendBtn.cloneNode(true);
    messageInput.parentNode.replaceChild(newMessageInput, messageInput);
    sendBtn.parentNode.replaceChild(newSendBtn, sendBtn);
    
    // Add event listeners
    newSendBtn.addEventListener('click', sendMessage);
    newMessageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

/**
 * Send a message to the API
 */
function sendMessage() {
    // Get message text
    const messageInput = document.getElementById('message-input');
    const messageText = messageInput.value.trim();
    
    // Don't send empty messages
    if (!messageText) return;
    
    // Clear input
    messageInput.value = '';
    
    // Add message to chat
    addMessageToChat(messageText, 'user');
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send message to API
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: activeSessionId,
            query: messageText
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        return response.json();
    })
    .then(data => {
        // Hide typing indicator
        hideTypingIndicator();
        
        // Check if the URL is included in the response and verify session
        const currentUrl = localStorage.getItem('current_url');
        const currentSessionId = localStorage.getItem('current_session_id');
        
        // Session validation
        if (data.session_id && data.session_id !== currentSessionId) {
            console.warn(`Session mismatch: Response from ${data.session_id} but current is ${currentSessionId}`);
            localStorage.setItem('current_session_id', data.session_id);
        }
        
        // URL validation
        if (data.url && data.url !== currentUrl) {
            console.warn(`URL mismatch: Response from URL ${data.url} but current URL is ${currentUrl}`);
            addMessageToChat(`Note: This response is based on content from: ${data.url}`, 'bot', true);
            // Update the stored URL to match what the server is using
            localStorage.setItem('current_url', data.url);
        }
        
        // Add bot response to chat
        addMessageToChat(data.response, 'bot');
    })
    .catch(error => {
        console.error('Error sending message:', error);
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Add error message
        addMessageToChat('Sorry, I encountered an error processing your request. Please try again.', 'bot', true);
    });
}

/**
 * Add a message to the chat
 * @param {string} text - The message text
 * @param {string} sender - 'user' or 'bot'
 * @param {boolean} isError - Whether this is an error message
 */
function addMessageToChat(text, sender, isError = false) {
    const chatMessages = document.getElementById('chat-messages');
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `cyberpunk-message ${sender}-message`;
    
    // HTML for the message
    messageDiv.innerHTML = `
        <div class="message-content ${isError ? 'error-message' : ''}">
            <div class="cyberpunk-message-text">${formatMessageText(text)}</div>
        </div>
    `;
    
    // Add to chat container
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Format message text with Markdown-like syntax
 * @param {string} text - The raw message text
 * @returns {string} - Formatted HTML
 */
function formatMessageText(text) {
    // Replace URLs with clickable links
    text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="cyberpunk-link">$1</a>');
    
    // Replace **bold** with <strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Replace *italic* with <em>
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Replace `code` with <code>
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Replace --- with <hr>
    text = text.replace(/\n---\n/g, '<hr class="cyberpunk-separator">');
    
    // Replace newlines with <br>
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

/**
 * Show typing indicator in chat
 */
function showTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    
    // Create typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'cyberpunk-message bot-message typing-indicator';
    typingDiv.id = 'typing-indicator';
    
    // HTML for the typing indicator
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    
    // Add to chat container
    chatMessages.appendChild(typingDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Add CSS for the typing indicator
document.addEventListener('DOMContentLoaded', () => {
    const typingStyles = `
        .typing-dots {
            display: flex;
            align-items: center;
            height: 20px;
        }
        
        .typing-dots span {
            height: 8px;
            width: 8px;
            margin-right: 4px;
            border-radius: 50%;
            background-color: #0080ff;
            display: inline-block;
            opacity: 0.4;
        }
        
        .typing-dots span:nth-child(1) {
            animation: typingDot 1.5s infinite 0s;
        }
        
        .typing-dots span:nth-child(2) {
            animation: typingDot 1.5s infinite 0.2s;
        }
        
        .typing-dots span:nth-child(3) {
            animation: typingDot 1.5s infinite 0.4s;
        }
        
        @keyframes typingDot {
            0% {
                opacity: 0.4;
                transform: scale(1);
            }
            50% {
                opacity: 1;
                transform: scale(1.2);
                background-color: #00ffaa;
            }
            100% {
                opacity: 0.4;
                transform: scale(1);
            }
        }
        
        .cyberpunk-link {
            color: #00aeff;
            text-decoration: none;
            border-bottom: 1px dashed #00aeff;
            transition: all 0.3s ease;
        }
        
        .cyberpunk-link:hover {
            color: #00ffaa;
            border-bottom-color: #00ffaa;
            text-shadow: 0 0 5px rgba(0, 255, 170, 0.5);
        }
        
        .error-message {
            background: linear-gradient(135deg, rgba(255, 50, 50, 0.2), rgba(255, 100, 100, 0.1)) !important;
            border-left: 3px solid #ff3366 !important;
        }
        
        code {
            background-color: rgba(0, 0, 0, 0.3);
            padding: 2px 5px;
            border-radius: 3px;
            font-family: monospace;
            border-left: 2px solid #00aeff;
        }
    `;
    
    // Add styles to head
    const styleElement = document.createElement('style');
    styleElement.textContent = typingStyles;
    document.head.appendChild(styleElement);
});
