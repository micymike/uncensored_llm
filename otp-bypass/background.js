// Background service worker for OTP Bypass Extension
console.log("OTP Bypass Background Service Worker Started");

// Storage for captured emails and magic links
let emailStorage = {
  capturedEmails: [],
  magicLinks: {},
  lastCapture: null
};

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Background received message:", request);
  
  if (request.type === "CAPTURE_EMAIL") {
    handleEmailCapture(request.email, request.source, request.otpCode);
    sendResponse({ success: true });
  } else if (request.type === "GET_CAPTURED_EMAILS") {
    sendResponse({ emails: emailStorage.capturedEmails });
  } else if (request.type === "GENERATE_MAGIC_LINK") {
    const magicLink = generateMagicLink(request.email);
    sendResponse({ magicLink: magicLink });
  } else if (request.type === "RESET_STORAGE") {
    resetStorage();
    sendResponse({ success: true });
  }
  
  return true; // Keep message channel open for async response
});

// Handle email capture
function handleEmailCapture(email, source, otpCode = null) {
  const timestamp = new Date().toISOString();
  const emailData = {
    email: email,
    source: source || "unknown",
    otpCode: otpCode,
    timestamp: timestamp,
    id: Date.now().toString()
  };
  
  // Add to captured emails (keep only last 20)
  emailStorage.capturedEmails.unshift(emailData);
  if (emailStorage.capturedEmails.length > 20) {
    emailStorage.capturedEmails = emailStorage.capturedEmails.slice(0, 20);
  }
  
  // Generate magic link
  const magicLink = generateMagicLink(email);
  emailStorage.magicLinks[email] = {
    link: magicLink,
    timestamp: timestamp,
    used: false
  };
  
  emailStorage.lastCapture = emailData;
  
  // Save to persistent storage
  chrome.storage.local.set({ 
    emailStorage: emailStorage,
    lastCapture: emailData 
  });
  
  console.log("Email captured:", emailData);
  
  // Notify popup if open
  chrome.runtime.sendMessage({
    type: "EMAIL_CAPTURED",
    data: emailData
  }).catch(() => {
    // Popup not open, ignore error
  });
}

// Generate magic link for bypass
function generateMagicLink(email) {
  // Create a deterministic but secure magic link
  const timestamp = Date.now();
  const hash = btoa(`${email}:${timestamp}`).replace(/[+/=]/g, '').substring(0, 12);
  return `https://auth.secure-verify.com/bypass/${hash}/${encodeURIComponent(email)}`;
}

// Reset storage
function resetStorage() {
  emailStorage = {
    capturedEmails: [],
    magicLinks: {},
    lastCapture: null
  };
  
  chrome.storage.local.set({ emailStorage: emailStorage });
  chrome.storage.local.remove(['lastCapture']);
  
  console.log("Storage reset");
}

// Initialize storage on startup
chrome.runtime.onStartup.addListener(() => {
  chrome.storage.local.get(['emailStorage'], (result) => {
    if (result.emailStorage) {
      emailStorage = result.emailStorage;
      console.log("Storage loaded from persistence");
    }
  });
});

// Handle installation
chrome.runtime.onInstalled.addListener((details) => {
  console.log("OTP Bypass Extension installed:", details);
  
  if (details.reason === "install") {
    // Initialize with welcome message
    chrome.storage.local.set({ 
      emailStorage: emailStorage,
      installed: true 
    });
  }
});

// Web request interceptor for email providers
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    // Check if this is an email provider URL that might contain OTP links
    const url = details.url.toLowerCase();
    
    if (url.includes('gmail.com') || url.includes('outlook.com') || 
        url.includes('yahoo.com') || url.includes('mail.') || 
        url.includes('verify') || url.includes('auth')) {
      
      // Look for email patterns in the URL
      const emailMatch = url.match(/[\w\.-]+@[\w\.-]+\.\w+/);
      if (emailMatch) {
        console.log("Potential email found in URL:", emailMatch[0]);
        handleEmailCapture(emailMatch[0], "url_intercept", null);
      }
    }
    
    return { cancel: false };
  },
  { urls: ["<all_urls>"] },
  ["requestBody"]
);

// Context menu for quick capture
chrome.contextMenus.create({
  id: "captureEmail",
  title: "Capture Email from Page",
  contexts: ["selection", "page"]
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "captureEmail") {
    // Extract email from selected text or page
    let email = info.selectionText || "";
    
    if (!email) {
      // Try to extract from page content
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractEmailFromPage
      }, (results) => {
        if (results && results[0] && results[0].result) {
          handleEmailCapture(results[0].result, "context_menu", null);
        }
      });
    } else {
      const emailMatch = email.match(/[\w\.-]+@[\w\.-]+\.\w+/);
      if (emailMatch) {
        handleEmailCapture(emailMatch[0], "context_menu", null);
      }
    }
  }
});

// Function to inject into page for email extraction
function extractEmailFromPage() {
  const emailRegex = /[\w\.-]+@[\w\.-]+\.\w+/g;
  const text = document.body.innerText;
  const matches = text.match(emailRegex);
  return matches ? matches[0] : null;
}
