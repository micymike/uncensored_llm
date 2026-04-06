// Advanced OTP Capture Script
// Real-time OTP detection and auto-fill

class OTPCaptureSystem {
  constructor() {
    this.capturedCodes = new Map();
    this.isMonitoring = false;
    this.otpPatterns = [
      /(?:code|verification|pin|otp|authenticate|confirm)[:\s]*(\d{4,8})/gi,
      /\b(\d{4,8})\b/g,
      /enter[:\s]*(\d{4,8})/gi,
      /your[:\s]*(\d{4,8})/gi,
      /security[:\s]*(\d{4,8})/gi
    ];
  }

  start() {
    console.log('🔍 Starting OTP Capture System...');
    this.isMonitoring = true;
    
    // Monitor for new emails
    this.monitorEmailClients();
    
    // Monitor for SMS messages (if available)
    this.monitorSMSMessages();
    
    // Auto-fill detected OTPs
    this.setupAutoFill();
    
    // Keyboard shortcuts for manual capture
    this.setupKeyboardShortcuts();
  }

  moniMitorEmailClients() {
    // Gmail monitoring
    if (window.location.hostname.includes('gmail.com')) {
      this.monitorGmail();
    }
    
    // Outlook monitoring
    else if (window.location.hostname.includes('outlook.com')) {
      this.monitorOutlook();
    }
    
    // Yahoo monitoring
    else if (window.location.hostname.includes('yahoo.com')) {
      this.monitorYahoo();
    }
    
    // Generic email monitoring
    else {
      this.monitorGenericEmail();
    }
  }

  monitorGmail() {
    console.log('📧 Setting up Gmail monitoring...');
    
    // Monitor for new email opens
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check email content
            const emailContent = node.querySelector('.a3s, .ii, .gmail_quote, [role="article"]');
            if (emailContent) {
              this.extractOTPFromContent(emailContent.textContent, 'gmail');
            }
            
            // Check for OTP in subject lines
            const subjectLine = node.querySelector('.hN, .bog');
            if (subjectLine) {
              this.extractOTPFromContent(subjectLine.textContent, 'gmail-subject');
            }
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: false
    });

    // Also check existing emails
    setTimeout(() => {
      const existingEmails = document.querySelectorAll('[role="article"], .a3s, .ii');
      existingEmails.forEach(email => {
        this.extractOTPFromContent(email.textContent, 'gmail-existing');
      });
    }, 2000);
  }

  monitorOutlook() {
    console.log('📧 Setting up Outlook monitoring...');
    
    setInterval(() => {
      const emails = document.querySelectorAll('[role="option"], .ms-MessageCard');
      emails.forEach(email => {
        const text = email.textContent;
        this.extractOTPFromContent(text, 'outlook');
      });
    }, 3000);
  }

  monitorYahoo() {
    console.log('📧 Setting up Yahoo monitoring...');
    
    setInterval(() => {
      const emails = document.querySelectorAll('.message-content, .data-inbox-message');
      emails.forEach(email => {
        const text = email.textContent;
        this.extractOTPFromContent(text, 'yahoo');
      });
    }, 3000);
  }

  monitorGenericEmail() {
    console.log('📧 Setting up generic email monitoring...');
    
    setInterval(() => {
      // Look for common email content patterns
      const emailContainers = document.querySelectorAll('.email-body, .message-content, .content-body');
      emailContainers.forEach(container => {
        this.extractOTPFromContent(container.textContent, 'generic');
      });
    }, 4000);
  }

  monitorSMSMessages() {
    // Monitor for SMS messages (web-based SMS clients)
    if (window.location.hostname.includes('sms') || 
        window.location.hostname.includes('text') ||
        window.location.hostname.includes('message')) {
      
      console.log('📱 Setting up SMS monitoring...');
      
      setInterval(() => {
        const messages = document.querySelectorAll('.message, .sms, .text-message');
        messages.forEach(message => {
          this.extractOTPFromContent(message.textContent, 'sms');
        });
      }, 2000);
    }
  }

  extractOTPFromContent(text, source) {
    for (const pattern of this.otpPatterns) {
      const matches = text.match(pattern);
      if (matches && matches[1]) {
        const code = matches[1];
        
        // Only process if we haven't seen this code recently
        const existing = this.capturedCodes.get(code);
        if (!existing || (Date.now() - existing.timestamp > 30000)) { // 30 second cooldown
          
          this.capturedCodes.set(code, {
            code: code,
            source: source,
            timestamp: Date.now(),
            context: text.substring(0, 100) + '...'
          });
          
          console.log(`✅ OTP Captured: ${code} from ${source}`);
          
          // Send to background script
          chrome.runtime.sendMessage({
            type: 'OTP_CAPTURED',
            code: code,
            source: source,
            timestamp: Date.now(),
            context: text.substring(0, 100)
          });
          
          // Auto-fill
          this.autoFillOTP(code);
          
          // Show notification
          this.showNotification(code, source);
        }
      }
    }
  }

  setupAutoFill() {
    // Auto-fill OTP codes into input fields
    setInterval(() => {
      const otpInputs = document.querySelectorAll('input[type="text"], input[type="number"]');
      
      otpInputs.forEach(input => {
        const isOTPField = this.isOTPInput(input);
        if (isOTPField && this.capturedCodes.size > 0) {
          const latestCode = Array.from(this.capturedCodes.keys()).pop();
          if (latestCode && input.value !== latestCode) {
            input.value = latestCode;
            input.style.backgroundColor = '#e8f5e8';
            input.style.border = '2px solid #28a745';
            
            // Trigger events
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            
            console.log(`🔓 Auto-filled OTP: ${latestCode}`);
          }
        }
      });
    }, 1000);
  }

  isOTPInput(input) {
    const placeholders = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm'];
    const names = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm'];
    const ids = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm'];
    
    const placeholder = input.placeholder?.toLowerCase() || '';
    const name = input.name?.toLowerCase() || '';
    const id = input.id?.toLowerCase() || '';
    
    return placeholders.some(p => placeholder.includes(p)) ||
           names.some(n => name.includes(n)) ||
           ids.some(i => id.includes(i));
  }

  showNotification(code, source) {
    // Create visual notification
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #28a745, #20c997);
      color: white;
      padding: 15px 20px;
      border-radius: 10px;
      font-weight: bold;
      z-index: 10000;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      animation: slideIn 0.3s ease-out;
      font-family: Arial, sans-serif;
      max-width: 300px;
    `;
    
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 20px;">🔓</span>
        <div>
          <div style="font-size: 14px; margin-bottom: 5px;">OTP Captured!</div>
          <div style="font-size: 18px; font-weight: bold;">${code}</div>
          <div style="font-size: 12px; opacity: 0.9;">Source: ${source}</div>
        </div>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 10000);
    
    // Click to dismiss
    notification.addEventListener('click', () => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    });
  }

  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+Shift+C to capture latest OTP
      if (e.ctrlKey && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        const latestCode = Array.from(this.capturedCodes.keys()).pop();
        if (latestCode) {
          navigator.clipboard.writeText(latestCode);
          console.log(`📋 Copied OTP to clipboard: ${latestCode}`);
        }
      }
      
      // Ctrl+Shift+V to view captured codes
      if (e.ctrlKey && e.shiftKey && e.key === 'V') {
        e.preventDefault();
        this.showCapturedCodes();
      }
    });
  }

  showCapturedCodes() {
    const codes = Array.from(this.capturedCodes.entries());
    if (codes.length === 0) {
      alert('No OTP codes captured yet.');
      return;
    }
    
    let message = 'Captured OTP Codes:\n\n';
    codes.forEach(([code, data]) => {
      const time = new Date(data.timestamp).toLocaleTimeString();
      message += `${code} (${data.source}) - ${time}\n`;
    });
    
    alert(message);
  }
}

// Initialize the OTP capture system
const otpSystem = new OTPCaptureSystem();

// Start monitoring when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    otpSystem.start();
  });
} else {
  otpSystem.start();
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_CAPTURED_CODES') {
    const codes = Array.from(otpSystem.capturedCodes.entries());
    sendResponse({ codes: codes });
  } else if (request.type === 'COPY_LATEST_CODE') {
    const latestCode = Array.from(otpSystem.capturedCodes.keys()).pop();
    if (latestCode) {
      navigator.clipboard.writeText(latestCode);
      sendResponse({ success: true, code: latestCode });
    } else {
      sendResponse({ success: false, error: 'No codes captured' });
    }
  }
});

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;
document.head.appendChild(style);
