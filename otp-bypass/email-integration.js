// Advanced Email Integration for OTP Bypass
// Real email capture methods

// Method 1: Gmail API Integration
class GmailAPIIntegration {
  constructor() {
    this.clientId = 'YOUR_GMAIL_CLIENT_ID';
    this.clientSecret = 'YOUR_GMAIL_CLIENT_SECRET';
    this.redirectUri = 'http://localhost:3000/auth/gmail/callback';
  }

  async authenticate() {
    // OAuth2 flow for Gmail
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${this.clientId}&` +
      `redirect_uri=${encodeURIComponent(this.redirectUri)}&` +
      `response_type=code&` +
      `scope=https://www.googleapis.com/auth/gmail.readonly%20https://www.googleapis.com/auth/gmail.modify`;
    
    return authUrl;
  }

  async captureOTPEmails() {
    // Monitor Gmail for OTP emails
    const response = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages', {
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'q': 'subject:(OTP OR verification OR code) newer_than:1h'
      }
    });
    
    const data = await response.json();
    return this.extractOTPCodes(data.messages);
  }

  extractOTPCodes(messages) {
    const otpCodes = [];
    
    for (const message of messages) {
      const fullMessage = await this.getMessage(message.id);
      const otpMatch = fullMessage.body.match(/\b\d{4,8}\b/g);
      
      if (otpMatch) {
        otpCodes.push({
          email: this.extractEmail(fullMessage),
          code: otpMatch[0],
          timestamp: message.internalDate,
          subject: fullMessage.subject
        });
      }
    }
    
    return otpCodes;
  }
}

// Method 2: IMAP Email Monitoring
class IMAPMonitor {
  constructor(email, password) {
    this.email = email;
    this.password = password;
    this.imapConfig = {
      user: email,
      password: password,
      host: 'imap.gmail.com',
      port: 993,
      tls: true
    };
  }

  async startMonitoring() {
    const Imap = require('node-imap');
    const simpleParser = require('mailparser').simpleParser;
    
    const connection = await Imap.connect(this.imapConfig);
    
    connection.openBox('INBOX', (err, box) => {
      if (err) throw err;
      
      // Watch for new messages
      connection.on('mail', (numNewMsgs) => {
        console.log(`${numNewMsgs} new messages received`);
        this.processNewMessages(connection, simpleParser);
      });
      
      // Search for existing OTP emails
      this.searchOTPEmails(connection, simpleParser);
    });
  }

  async searchOTPEmails(connection, parser) {
    const searchCriteria = [
      ['UNSEEN'],
      ['SUBJECT', 'OTP'],
      ['SINCE', new Date(Date.now() - 24 * 60 * 60 * 1000)]
    ];
    
    connection.search(searchCriteria, (err, results) => {
      if (err) throw err;
      
      const fetch = connection.fetch(results, { bodies: 'TEXT' });
      
      fetch.on('message', (msg) => {
        parser.write(msg);
      });
      
      parser.on('data', (data) => {
        const otpCode = this.extractOTPCode(data);
        if (otpCode) {
          this.sendToExtension({
            type: 'OTP_CAPTURED',
            email: data.from.value[0].address,
            code: otpCode,
            subject: data.subject,
            timestamp: new Date()
          });
        }
      });
    });
  }

  extractOTPCode(emailData) {
    const patterns = [
      /\b(\d{4,8})\b/g,
      /code[:\s]+(\d{4,8})/gi,
      /verification[:\s]+(\d{4,8})/gi,
      /pin[:\s]+(\d{4,8})/gi
    ];
    
    for (const pattern of patterns) {
      const match = emailData.text.match(pattern);
      if (match) return match[1];
    }
    
    return null;
  }
}

// Method 3: Browser Extension Email Interception
class EmailInterceptor {
  constructor() {
    this.capturedEmails = new Map();
    this.otpCodes = new Map();
  }

  initialize() {
    // Intercept webmail clients
    this.interceptGmail();
    this.interceptOutlook();
    this.interceptYahoo();
    this.interceptProtonMail();
  }

  interceptGmail() {
    // Gmail specific interception
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check for Gmail email content
            const emailContent = node.querySelector('.a3s, .ii, .gmail_quote');
            if (emailContent) {
              const otpCode = this.extractOTPFromText(emailContent.textContent);
              if (otpCode) {
                this.handleOTPCapture(otpCode, 'gmail');
              }
            }
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  interceptOutlook() {
    // Outlook specific interception
    setInterval(() => {
      const emails = document.querySelectorAll('[role="option"]');
      emails.forEach(email => {
        const text = email.textContent;
        const otpCode = this.extractOTPFromText(text);
        if (otpCode && !this.otpCodes.has(otpCode)) {
          this.handleOTPCapture(otpCode, 'outlook');
        }
      });
    }, 2000);
  }

  extractOTPFromText(text) {
    const patterns = [
      /(?:code|verification|pin|otp)[:\s]*(\d{4,8})/gi,
      /\b(\d{4,8})\b/g,
      /enter[:\s]*(\d{4,8})/gi
    ];

    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }

    return null;
  }

  handleOTPCapture(code, source) {
    this.otpCodes.set(code, {
      code: code,
      source: source,
      timestamp: Date.now()
    });

    // Send to background script
    chrome.runtime.sendMessage({
      type: 'OTP_CAPTURED',
      code: code,
      source: source,
      timestamp: Date.now()
    });

    // Auto-fill OTP if input field exists
    this.autoFillOTP(code);
  }

  autoFillOTP(code) {
    const otpInputs = document.querySelectorAll('input[type="text"], input[type="number"]');
    otpInputs.forEach(input => {
      if (input.placeholder?.toLowerCase().includes('code') ||
          input.name?.toLowerCase().includes('otp') ||
          input.id?.toLowerCase().includes('verification')) {
        input.value = code;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
  }
}

// Method 4: SMS Gateway Integration
class SMSGateway {
  constructor() {
    this.apiKey = 'YOUR_SMS_API_KEY';
    this.webhookUrl = 'http://localhost:3000/sms-webhook';
  }

  async setupSMSForwarding() {
    // Setup SMS forwarding to capture OTP codes
    const forwardConfig = {
      phoneNumber: '+1234567890', // Your virtual number
      webhook: this.webhookUrl,
      keywords: ['verify', 'code', 'otp', 'login']
    };

    // Register with SMS gateway service
    const response = await fetch('https://api.sms-gateway.com/forwarding', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(forwardConfig)
    });

    return response.json();
  }

  handleSMSWebhook(smsData) {
    const otpCode = this.extractOTPFromSMS(smsData.message);
    if (otpCode) {
      chrome.runtime.sendMessage({
        type: 'SMS_OTP_CAPTURED',
        code: otpCode,
        from: smsData.from,
        timestamp: Date.now()
      });
    }
  }

  extractOTPFromSMS(message) {
    const patterns = [
      /(?:code|verification|pin|otp)[:\s]*(\d{4,8})/gi,
      /\b(\d{4,8})\b/g
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }

    return null;
  }
}

// Export all methods
module.exports = {
  GmailAPIIntegration,
  IMAPMonitor,
  EmailInterceptor,
  SMSGateway
};
