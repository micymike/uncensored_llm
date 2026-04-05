// Mimo Advanced Chat Application JavaScript
// Features: Real-time chat, advanced animations, typing indicators, message history, and more

class MimoAdvancedChat {
    constructor() {
        this.messages = [];
        this.isTyping = false;
        this.apiBase = '/api/v1';
        this.messageHistory = [];
        this.userPreferences = {
            theme: 'dark',
            soundEnabled: true,
            autoSave: true
        };
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeParticles();
        this.checkModelStatus();
        this.loadChatHistory();
        this.initializeKeyboardShortcuts();
        this.startStatusAnimation();
    }

    initializeElements() {
        // Input elements
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        
        // Chat display
        this.chatMessages = document.getElementById('chatMessages');
        
        // Controls
        this.temperatureSlider = document.getElementById('temperature');
        this.maxTokensSlider = document.getElementById('maxTokens');
        this.ragKSlider = document.getElementById('ragK');
        this.agenticMode = document.getElementById('agenticMode');
        this.codeExec = document.getElementById('codeExec');
        
        // Display elements
        this.tempValue = document.getElementById('tempValue');
        this.tokensValue = document.getElementById('tokensValue');
        this.ragValue = document.getElementById('ragValue');
        this.maxTokensDisplay = document.getElementById('maxTokensDisplay');
        this.statsDisplay = document.getElementById('statsDisplay');
        this.modelStatus = document.getElementById('modelStatus');
        
        // Action buttons
        this.clearChatBtn = document.getElementById('clearChat');
        this.exportChatBtn = document.getElementById('exportChat');
        
        // Particles container
        this.particlesContainer = document.getElementById('particles');
    }

    attachEventListeners() {
        // Message input with advanced features
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize input field
        this.messageInput.addEventListener('input', () => {
            this.autoResizeInput();
            this.showTypingIndicator();
        });

        // Control sliders with real-time updates
        this.temperatureSlider.addEventListener('input', (e) => {
            this.tempValue.textContent = e.target.value;
            this.updateUserPreference('temperature', e.target.value);
        });

        this.maxTokensSlider.addEventListener('input', (e) => {
            this.tokensValue.textContent = e.target.value;
            this.maxTokensDisplay.textContent = e.target.value;
            this.updateUserPreference('maxTokens', e.target.value);
        });

        this.ragKSlider.addEventListener('input', (e) => {
            this.ragValue.textContent = e.target.value;
            this.updateUserPreference('ragK', e.target.value);
        });

        // Mode toggles with animations
        this.agenticMode.addEventListener('change', (e) => {
            this.updateUserPreference('agenticMode', e.target.checked);
            this.showNotification('Agentic Mode ' + (e.target.checked ? 'enabled' : 'disabled'));
        });

        this.codeExec.addEventListener('change', (e) => {
            this.updateUserPreference('codeExec', e.target.checked);
            this.showNotification('Code Execution ' + (e.target.checked ? 'enabled' : 'disabled'));
        });

        // Action buttons with enhanced feedback
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.exportChatBtn.addEventListener('click', () => this.exportChat());

        // Enable input when model is ready
        setTimeout(() => {
            this.enableInput();
        }, 1000);

        // Window focus/blur events for status updates
        window.addEventListener('focus', () => this.onWindowFocus());
        window.addEventListener('blur', () => this.onWindowBlur());

        // Online/offline detection
        window.addEventListener('online', () => this.onOnline());
        window.addEventListener('offline', () => this.onOffline());
    }

    initializeParticles() {
        // Create floating particles for visual effect
        for (let i = 0; i < 15; i++) {
            this.createParticle();
        }
    }

    createParticle() {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 20 + 's';
        particle.style.animationDuration = (15 + Math.random() * 10) + 's';
        
        // Create particle content (emerald green dots)
        const dot = document.createElement('div');
        dot.style.width = Math.random() * 4 + 2 + 'px';
        dot.style.height = dot.style.width;
        dot.style.background = '#10b981';
        dot.style.borderRadius = '50%';
        dot.style.boxShadow = '0 0 6px rgba(16, 185, 129, 0.8)';
        
        particle.appendChild(dot);
        this.particlesContainer.appendChild(particle);
        
        // Remove particle after animation
        setTimeout(() => {
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
            // Create new particle to maintain count
            this.createParticle();
        }, 25000);
    }

    initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for clear chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.clearChat();
            }
            
            // Ctrl/Cmd + E for export
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                this.exportChat();
            }
            
            // Ctrl/Cmd + / for help
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.showHelp();
            }
            
            // Escape to focus input
            if (e.key === 'Escape') {
                this.messageInput.focus();
            }
        });
    }

    startStatusAnimation() {
        // Animate status indicator
        setInterval(() => {
            if (this.modelStatus.textContent === 'Online') {
                this.modelStatus.style.opacity = '0.5';
                setTimeout(() => {
                    this.modelStatus.style.opacity = '1';
                }, 500);
            }
        }, 3000);
    }

    async checkModelStatus() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.updateModelStatus('Online', 'text-emerald-400');
                this.showNotification('Mimo AI is ready', 'success');
            } else {
                this.updateModelStatus('Offline', 'text-red-400');
                this.showNotification('Mimo AI is offline', 'error');
            }
        } catch (error) {
            this.updateModelStatus('Error', 'text-red-400');
            this.showNotification('Failed to connect to Mimo AI', 'error');
            console.error('Health check failed:', error);
        }
    }

    updateModelStatus(status, className) {
        this.modelStatus.textContent = status;
        this.modelStatus.className = `ml-1 ${className}`;
    }

    enableInput() {
        this.messageInput.disabled = false;
        this.sendButton.disabled = false;
        this.messageInput.focus();
        this.showNotification('Mimo AI is ready to chat!', 'success');
    }

    autoResizeInput() {
        // Auto-resize input field based on content
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    showTypingIndicator() {
        if (this.messageInput.value.trim() && !this.isTyping) {
            // Show user is typing indicator (optional feature)
            this.sendButton.style.background = 'linear-gradient(135deg, #34d399 0%, #10b981 100%)';
        } else {
            this.sendButton.style.background = '';
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        // Add user message with animation
        this.addMessage('user', message);
        this.messageInput.value = '';
        this.autoResizeInput();
        
        // Show advanced typing indicator
        this.showAdvancedTypingIndicator();
        this.isTyping = true;
        this.sendButton.disabled = true;

        try {
            const startTime = Date.now();
            
            // Prepare request with user preferences
            const requestData = {
                model: 'mimo',
                messages: [...this.messages, { role: 'user', content: message }],
                temperature: parseFloat(this.temperatureSlider.value),
                max_tokens: parseInt(this.maxTokensSlider.value),
                stream: false,
                user_preferences: this.userPreferences
            };

            // Make API request with retry logic
            const response = await this.makeAPIRequest(`${this.apiBase}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer any-key',
                    'X-Client-Version': '1.0.0'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const assistantMessage = data.choices[0].message.content;
            
            // Remove typing indicator with animation
            this.hideAdvancedTypingIndicator();
            
            // Add assistant message with typing effect
            await this.addMessageWithTyping('assistant', assistantMessage);
            
            // Update messages array
            this.messages.push({ role: 'user', content: message });
            this.messages.push({ role: 'assistant', content: assistantMessage });
            
            // Save chat history
            this.saveChatHistory();
            
            // Update stats with animation
            const elapsed = (Date.now() - startTime) / 1000;
            const tokens = data.usage.total_tokens;
            const tps = tokens / elapsed;
            this.updateStats(tokens, elapsed, tps);

            // Show completion notification
            this.showNotification('Response generated successfully', 'success');

        } catch (error) {
            this.hideAdvancedTypingIndicator();
            this.addMessage('system', `⚠️ Error: ${error.message}`);
            this.showNotification('Failed to get response: ' + error.message, 'error');
            console.error('Message sending failed:', error);
        } finally {
            this.isTyping = false;
            this.sendButton.disabled = false;
            this.messageInput.focus();
        }
    }

    async makeAPIRequest(url, options, retries = 3) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(url, options);
                if (response.ok) return response;
                
                if (i === retries - 1) throw new Error(`Request failed after ${retries} retries`);
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
            } catch (error) {
                if (i === retries - 1) throw error;
                await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
            }
        }
    }

    showAdvancedTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'flex justify-start mb-4';
        indicator.id = 'advancedTypingIndicator';
        
        indicator.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <span class="ml-3 text-sm text-gray-400">Mimo is thinking...</span>
            </div>
        `;
        
        this.chatMessages.appendChild(indicator);
        this.scrollToBottom();
    }

    hideAdvancedTypingIndicator() {
        const indicator = document.getElementById('advancedTypingIndicator');
        if (indicator) {
            indicator.style.opacity = '0';
            indicator.style.transform = 'translateY(-10px)';
            setTimeout(() => indicator.remove(), 300);
        }
    }

    async addMessageWithTyping(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-4`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${role}-message p-4`;
        
        // Add content with typing animation
        const processedContent = this.processContent(content);
        bubbleDiv.innerHTML = processedContent;

        messageDiv.appendChild(bubbleDiv);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Typing animation for assistant messages
        if (role === 'assistant') {
            await this.typingAnimation(bubbleDiv);
        }
    }

    async typingAnimation(element) {
        const originalContent = element.innerHTML;
        element.innerHTML = '';
        element.style.opacity = '0';
        
        await new Promise(resolve => setTimeout(resolve, 100));
        element.style.opacity = '1';
        element.innerHTML = originalContent;
        
        // Add subtle glow effect
        element.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.3)';
        setTimeout(() => {
            element.style.boxShadow = '';
        }, 1000);
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-4`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${role}-message p-4`;
        
        // Process content for code blocks and formatting
        const processedContent = this.processContent(content);
        bubbleDiv.innerHTML = processedContent;

        messageDiv.appendChild(bubbleDiv);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    processContent(content) {
        // Enhanced content processing with runnable code blocks
        let processed = content
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Enhanced code block processing with runnable functionality
            .replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
                const language = lang || 'text';
                const codeId = 'code-' + Math.random().toString(36).substr(2, 9);
                
                return `<div class="code-block">
                    <div class="flex justify-between items-center mb-3">
                        <div class="flex items-center gap-2">
                            <span class="text-xs text-emerald-400 font-semibold">${language.toUpperCase()}</span>
                            <span class="text-xs text-gray-500">•</span>
                            <span class="text-xs text-gray-400">${code.trim().split('\n').length} lines</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button onclick="window.mimoChat.copyCode('${codeId}')" class="text-xs text-gray-400 hover:text-emerald-400 transition-colors flex items-center gap-1">
                                <i class="fas fa-copy"></i> 
                                <span>Copy</span>
                            </button>
                            ${this.isRunnableLanguage(language) ? `
                                <button onclick="window.mimoChat.runCode('${codeId}')" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-2 py-1 rounded transition-colors flex items-center gap-1">
                                    <i class="fas fa-play"></i> 
                                    <span>Run</span>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="relative">
                        <pre id="${codeId}" class="bg-gray-900 rounded-lg p-4 overflow-x-auto"><code class="language-${language}">${this.escapeHtml(code.trim())}</code></pre>
                        ${this.isRunnableLanguage(language) ? `
                            <div id="output-${codeId}" class="hidden mt-3 p-3 bg-gray-800 border border-emerald-600 rounded-lg">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs text-emerald-400 font-semibold">Output</span>
                                    <button onclick="window.mimoChat.clearOutput('${codeId}')" class="text-xs text-gray-400 hover:text-red-400">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <div class="output-content text-sm text-gray-300 font-mono"></div>
                            </div>
                        ` : ''}
                    </div>
                </div>`;
            })
            // Enhanced inline code with syntax highlighting
            .replace(/`([^`]+)`/g, '<code class="bg-gray-800 text-emerald-400 px-2 py-1 rounded font-mono text-sm">$1</code>')
            // Enhanced markdown with emerald colors
            .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-emerald-400 font-semibold">$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em class="text-emerald-300">$1</em>')
            // Process links with emerald styling
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-emerald-400 hover:text-emerald-300 underline transition-colors">$1</a>')
            // Process line breaks
            .replace(/\n/g, '<br>');

        return processed;
    }

    isRunnableLanguage(language) {
        const runnableLanguages = ['python', 'javascript', 'js', 'html', 'css', 'sql', 'bash', 'shell', 'sh'];
        return runnableLanguages.includes(language.toLowerCase());
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Add methods to handle code execution
    copyCode(codeId) {
        const codeElement = document.getElementById(codeId);
        if (codeElement) {
            const codeText = codeElement.textContent;
            navigator.clipboard.writeText(codeText).then(() => {
                this.showNotification('Code copied to clipboard!', 'success');
            }).catch(err => {
                console.error('Failed to copy code:', err);
                this.showNotification('Failed to copy code', 'error');
            });
        }
    }

    async runCode(codeId) {
        const codeElement = document.getElementById(codeId);
        const outputElement = document.getElementById(`output-${codeId}`);
        
        if (!codeElement || !outputElement) return;

        const code = codeElement.textContent;
        const outputContent = outputElement.querySelector('.output-content');
        
        // Show output container
        outputElement.classList.remove('hidden');
        outputContent.innerHTML = '<div class="text-emerald-400">🔄 Running code...</div>';

        try {
            // Make API call to execute code
            const response = await fetch('/api/v1/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: code,
                    language: this.detectLanguage(code)
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                outputContent.innerHTML = `
                    <div class="text-emerald-400">✅ Execution successful</div>
                    <pre class="mt-2 text-sm">${this.escapeHtml(result.output || result.result)}</pre>
                `;
                this.showNotification('Code executed successfully!', 'success');
            } else {
                throw new Error(result.error || 'Execution failed');
            }
        } catch (error) {
            outputContent.innerHTML = `
                <div class="text-red-400">❌ Execution failed</div>
                <pre class="mt-2 text-sm text-red-300">${this.escapeHtml(error.message)}</pre>
            `;
            this.showNotification('Code execution failed: ' + error.message, 'error');
        }
    }

    clearOutput(codeId) {
        const outputElement = document.getElementById(`output-${codeId}`);
        if (outputElement) {
            outputElement.classList.add('hidden');
        }
    }

    detectLanguage(code) {
        // Simple language detection based on code content
        if (code.includes('def ') || code.includes('import ') || code.includes('print(')) {
            return 'python';
        } else if (code.includes('console.log') || code.includes('function ') || code.includes('const ')) {
            return 'javascript';
        } else if (code.includes('SELECT ') || code.includes('INSERT ') || code.includes('FROM ')) {
            return 'sql';
        } else if (code.includes('#!/bin/bash') || code.includes('echo ') || code.includes('ls ')) {
            return 'bash';
        }
        return 'text';
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    updateStats(tokens, elapsed, tps) {
        const statsText = `${tokens} tokens • ${elapsed.toFixed(1)}s • ${tps.toFixed(1)} tok/s`;
        
        // Animate stats update
        this.statsDisplay.style.opacity = '0';
        setTimeout(() => {
            this.statsDisplay.textContent = statsText;
            this.statsDisplay.style.opacity = '1';
        }, 200);
    }

    clearChat() {
        if (confirm('Are you sure you want to clear the chat history? This cannot be undone.')) {
            // Animate clear
            this.chatMessages.style.opacity = '0';
            
            setTimeout(() => {
                this.messages = [];
                this.messageHistory = [];
                this.chatMessages.innerHTML = `
                    <div class="text-center text-gray-500 py-12">
                        <div class="thinking-animation mb-4">
                            <div class="thinking-bar"></div>
                            <div class="thinking-bar"></div>
                            <div class="thinking-bar"></div>
                            <div class="thinking-bar"></div>
                        </div>
                        <p class="text-lg">Chat cleared</p>
                        <p class="text-sm text-gray-600 mt-2">Start a new conversation with Mimo AI</p>
                    </div>
                `;
                this.chatMessages.style.opacity = '1';
                this.statsDisplay.textContent = 'Ready';
                this.showNotification('Chat history cleared', 'info');
                this.saveChatHistory();
            }, 300);
        }
    }

    exportChat() {
        const chatData = {
            timestamp: new Date().toISOString(),
            messages: this.messages,
            settings: {
                temperature: this.temperatureSlider.value,
                max_tokens: this.maxTokensSlider.value,
                rag_k: this.ragKSlider.value,
                agentic_mode: this.agenticMode.checked,
                code_execution: this.codeExec.checked
            },
            user_preferences: this.userPreferences,
            stats: {
                total_messages: this.messages.length,
                session_duration: Date.now() - (this.sessionStart || Date.now())
            }
        };

        // Create enhanced export with multiple formats
        this.exportToFile(chatData, 'mimo-chat-export.json', 'application/json');
        this.showNotification('Chat exported successfully', 'success');
    }

    exportToFile(data, filename, mimeType) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    saveChatHistory() {
        if (this.userPreferences.autoSave) {
            localStorage.setItem('mimo_chat_history', JSON.stringify({
                messages: this.messages,
                timestamp: Date.now()
            }));
        }
    }

    loadChatHistory() {
        try {
            const saved = localStorage.getItem('mimo_chat_history');
            if (saved) {
                const data = JSON.parse(saved);
                // Only load if recent (within 24 hours)
                if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
                    this.messages = data.messages || [];
                    this.messageHistory = [...this.messages];
                    this.sessionStart = data.timestamp;
                    
                    // Restore messages to UI
                    if (this.messages.length > 0) {
                        this.chatMessages.innerHTML = '';
                        this.messages.forEach(msg => {
                            this.addMessage(msg.role, msg.content);
                        });
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }

    updateUserPreference(key, value) {
        this.userPreferences[key] = value;
        localStorage.setItem('mimo_user_preferences', JSON.stringify(this.userPreferences));
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 transform translate-x-full transition-transform duration-300`;
        
        // Set color based on type
        const colors = {
            success: 'bg-emerald-600',
            error: 'bg-red-600',
            info: 'bg-blue-600',
            warning: 'bg-yellow-600'
        };
        
        notification.classList.add(colors[type] || colors.info);
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    showHelp() {
        const helpText = `
🧠 Mimo AI Keyboard Shortcuts:

• Ctrl/Cmd + K - Clear chat
• Ctrl/Cmd + E - Export chat  
• Ctrl/Cmd + / - Show this help
• Escape - Focus input field
• Enter - Send message
• Shift + Enter - New line

📊 Features:
• Real-time chat with typing indicators
• Message history & auto-save
• Advanced code highlighting
• Export conversations
• Customizable settings
        `;
        
        this.addMessage('system', helpText);
        this.showNotification('Help displayed', 'info');
    }

    // Window event handlers
    onWindowFocus() {
        this.checkModelStatus();
        this.showNotification('Welcome back!', 'info');
    }

    onWindowBlur() {
        this.saveChatHistory();
    }

    onOnline() {
        this.showNotification('Connection restored', 'success');
        this.checkModelStatus();
    }

    onOffline() {
        this.showNotification('Connection lost', 'error');
        this.updateModelStatus('Offline', 'text-red-400');
    }
}

// Initialize the advanced application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Create session start timestamp
    window.mimoSessionStart = Date.now();
    
    // Initialize the advanced chat application
    window.mimoChat = new MimoAdvancedChat();
    
    // Show welcome message
    setTimeout(() => {
        window.mimoChat.showNotification('Welcome to Mimo Advanced AI! 🧠', 'success');
    }, 1500);
    
    // Periodic status check
    setInterval(() => {
        window.mimoChat.checkModelStatus();
    }, 30000); // Check every 30 seconds
});

// Performance monitoring
if (window.performance && window.performance.memory) {
    setInterval(() => {
        const memoryUsage = window.performance.memory.usedJSHeapSize / 1048576; // MB
        if (memoryUsage > 100) {
            console.warn(`High memory usage: ${memoryUsage.toFixed(2)} MB`);
        }
    }, 10000);
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('Application error:', e.error);
    if (window.mimoChat) {
        window.mimoChat.showNotification('An error occurred', 'error');
    }
});

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/sw.js').catch(() => {
        // Service worker not available, continue without it
    });
}
