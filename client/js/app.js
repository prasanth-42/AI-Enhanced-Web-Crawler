document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const urlInput = document.getElementById('url-input');
    const scrapeBtn = document.getElementById('scrape-btn');
    const chatContainer = document.getElementById('chat-container');
    const loadingContainer = document.getElementById('loading-container');
    const loadingText = document.getElementById('loading-text');
    const apiConnectionInfo = document.getElementById('api-connection-info');
    
    // Application state
    let sessionId = null;
    
    // Check if API key is set
    checkApiKey();
    
    // Clear all server sessions on page load
    fetch('/api/clear_sessions', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        console.log("On page load - Server sessions cleared:", data.message);
    })
    .catch(error => {
        console.error("Failed to clear sessions on load:", error);
    });
    
    // Initialize event listeners
    initEventListeners();
    
    /**
     * Initialize all event listeners
     */
    function initEventListeners() {
        // Scrape button click event
        scrapeBtn.addEventListener('click', () => {
            const url = urlInput.value.trim();
            if (url) {
                scrapeWebsite(url);
            } else {
                showNotification('Please enter a valid URL', 'error');
            }
        });
        
        // URL input enter key press
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const url = urlInput.value.trim();
                if (url) {
                    scrapeWebsite(url);
                } else {
                    showNotification('Please enter a valid URL', 'error');
                }
            }
        });
        
        // API key is now managed on the server side via .env file
        // No longer need the client-side API key input
    }
    
    /**
     * Check if API key is set
     */
    function checkApiKey() {
        fetch('/api/check_api_key')
            .then(response => response.json())
            .then(data => {
                // We now always use the API key from the .env file
                // No need to show the alert anymore
                console.log("API key status:", data.has_api_key ? "Available" : "Not available");
                
                // In a real app, we might want to disable functionality if no API key
                if (!data.has_api_key) {
                    console.warn("No API key found in environment, but continuing anyway");
                }
            })
            .catch(error => {
                console.error('Error checking API key:', error);
            });
    }
    
    /**
     * Clear previous session (not used anymore, API key is on server)
     */
    function clearPreviousSession() {
        sessionId = null;
        localStorage.removeItem('current_session_id');
        localStorage.removeItem('current_url');
    }
    
    /**
     * Scrape a website
     */
    function scrapeWebsite(url) {
        // Clear any previous session data
        clearPreviousSession();
        
        // Show loading state
        chatContainer.classList.add('d-none');
        loadingContainer.classList.remove('d-none');
        loadingText.textContent = 'Processing website...';
        
        // Store current URL
        localStorage.setItem('current_url', url);
        console.log("Starting to scrape new URL:", url);
        
        // First, explicitly clear all sessions on the server
        // This ensures a completely fresh start with every new URL
        fetch('/api/clear_sessions', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            console.log("Server sessions cleared:", data.message);
            
            // Now make API request to scrape website
            return fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url })
            });
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to scrape website');
            }
            return response.json();
        })
        .then(data => {
            sessionId = data.session_id;
            
            // Store session ID
            localStorage.setItem('current_session_id', sessionId);
            
            // Hide loading state and show chat container
            loadingContainer.classList.add('d-none');
            chatContainer.classList.remove('d-none');
            
            // Initialize chat system
            initChat(sessionId);
            
            showNotification(`Website ${url} scraped successfully!`, 'success');
        })
        .catch(error => {
            console.error('Error scraping website:', error);
            loadingContainer.classList.add('d-none');
            showNotification('Failed to scrape website. Please try again.', 'error');
        });
    }
    
    /**
     * Initialize chat system
     */
    function initChat(sessionId) {
        // Clear previous chat messages except the first welcome message
        const chatMessages = document.getElementById('chat-messages');
        const welcomeMessage = chatMessages.querySelector('.bot-message');
        chatMessages.innerHTML = '';
        chatMessages.appendChild(welcomeMessage);
        
        // Enable chat functionality
        enableChat(sessionId);
    }
    
    /**
     * Show notification
     */
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `cyberpunk-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${getIconForType(type)} me-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add to body
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Hide and remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    /**
     * Get icon class for notification type
     */
    function getIconForType(type) {
        switch (type) {
            case 'success':
                return 'fa-check-circle';
            case 'error':
                return 'fa-times-circle';
            case 'warning':
                return 'fa-exclamation-triangle';
            default:
                return 'fa-info-circle';
        }
    }
    
    // Add CSS for notifications
    const notificationStyles = `
        .cyberpunk-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            background: rgba(20, 25, 45, 0.9);
            color: #e0e0ff;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            transform: translateX(120%);
            transition: transform 0.3s ease;
            z-index: 1000;
            max-width: 350px;
            backdrop-filter: blur(5px);
        }
        
        .cyberpunk-notification.show {
            transform: translateX(0);
        }
        
        .cyberpunk-notification.success {
            border-left: 4px solid #00ffaa;
        }
        
        .cyberpunk-notification.error {
            border-left: 4px solid #ff3366;
        }
        
        .cyberpunk-notification.warning {
            border-left: 4px solid #ffaa00;
        }
        
        .cyberpunk-notification.info {
            border-left: 4px solid #0080ff;
        }
        
        .notification-content {
            display: flex;
            align-items: center;
        }
    `;
    
    // Add styles to head
    const styleElement = document.createElement('style');
    styleElement.textContent = notificationStyles;
    document.head.appendChild(styleElement);
});
