// Popup script for OTP Bypass Extension
console.log("OTP Bypass Popup Loaded");

// DOM elements
const statusDiv = document.getElementById('status');
const emailInput = document.getElementById('email-input');
const sendLinkBtn = document.getElementById('send-link-btn');
const magicLink = document.getElementById('magic-link');
const linkText = document.getElementById('link-text');
const resetBtn = document.getElementById('reset-btn');
const emailList = document.getElementById('email-list');

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
  loadStoredEmails();
  setupEventListeners();
  updateStatus('Ready for email extraction...');
});

// Setup event listeners
function setupEventListeners() {
  sendLinkBtn.addEventListener('click', handleGenerateMagicLink);
  resetBtn.addEventListener('click', handleReset);
  emailInput.addEventListener('input', handleEmailInput);
  magicLink.addEventListener('click', handleMagicLinkClick);
  
  // Listen for messages from background
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "EMAIL_CAPTURED") {
      handleNewEmailCapture(message.data);
    }
  });
}

// Load stored emails from background
function loadStoredEmails() {
  chrome.runtime.sendMessage({ type: "GET_CAPTURED_EMAILS" }, (response) => {
    if (response && response.emails) {
      updateEmailList(response.emails);
    }
  });
}

// Handle email input
function handleEmailInput() {
  const email = emailInput.value.trim();
  const isValid = validateEmail(email);
  
  sendLinkBtn.disabled = !isValid;
  sendLinkBtn.style.opacity = isValid ? '1' : '0.6';
  
  if (isValid) {
    updateStatus('Valid email detected');
  } else if (email) {
    updateStatus('Invalid email format', 'error');
  } else {
    updateStatus('Enter email address');
  }
}

// Handle generate magic link
function handleGenerateMagicLink() {
  const email = emailInput.value.trim();
  
  if (!validateEmail(email)) {
    updateStatus('Please enter a valid email', 'error');
    return;
  }
  
  updateStatus('Generating magic link...');
  sendLinkBtn.disabled = true;
  sendLinkBtn.textContent = 'Generating...';
  
  chrome.runtime.sendMessage({ 
    type: "GENERATE_MAGIC_LINK", 
    email: email 
  }, (response) => {
    if (response && response.magicLink) {
      displayMagicLink(response.magicLink, email);
      updateStatus('Magic link generated successfully!', 'success');
    } else {
      updateStatus('Failed to generate magic link', 'error');
    }
    
    sendLinkBtn.disabled = false;
    sendLinkBtn.textContent = 'Generate Magic Link';
  });
}

// Display magic link
function displayMagicLink(link, email) {
  magicLink.href = link;
  linkText.textContent = `Verify ${email}`;
  magicLink.style.display = 'block';
  
  // Add animation
  magicLink.style.animation = 'slideIn 0.3s ease-out';
}

// Handle magic link click
function handleMagicLinkClick(e) {
  e.preventDefault();
  const link = magicLink.href;
  
  // Copy to clipboard
  navigator.clipboard.writeText(link).then(() => {
    updateStatus('Magic link copied to clipboard!', 'success');
    
    // Open in new tab after a short delay
    setTimeout(() => {
      chrome.tabs.create({ url: link });
    }, 500);
  }).catch(() => {
    // Fallback: open directly
    chrome.tabs.create({ url: link });
  });
}

// Handle reset
function handleReset() {
  emailInput.value = '';
  magicLink.style.display = 'none';
  sendLinkBtn.disabled = true;
  sendLinkBtn.textContent = 'Generate Magic Link';
  
  // Clear storage
  chrome.runtime.sendMessage({ type: "RESET_STORAGE" }, () => {
    updateStatus('Storage reset', 'success');
    loadStoredEmails();
  });
}

// Handle new email capture from background
function handleNewEmailCapture(emailData) {
  updateStatus(`New email captured: ${emailData.email}`, 'success');
  loadStoredEmails();
  
  // Auto-fill if input is empty
  if (!emailInput.value.trim()) {
    emailInput.value = emailData.email;
    handleEmailInput();
  }
}

// Update email list display
function updateEmailList(emails) {
  const topEmails = emails.slice(0, 3);
  
  topEmails.forEach((emailData, index) => {
    const span = document.getElementById(`email-${index + 1}`);
    if (span && emailData) {
      span.textContent = `${emailData.email} (${emailData.source || 'unknown'})`;
      span.style.cursor = 'pointer';
      span.onclick = () => {
        emailInput.value = emailData.email;
        handleEmailInput();
      };
    }
  });
  
  // Clear remaining slots
  for (let i = topEmails.length + 1; i <= 3; i++) {
    const span = document.getElementById(`email-${i}`);
    if (span) {
      span.textContent = '-';
      span.onclick = null;
      span.style.cursor = 'default';
    }
  }
}

// Update status message
function updateStatus(message, type = 'info') {
  statusDiv.textContent = message;
  statusDiv.className = 'status';
  
  if (type === 'error') {
    statusDiv.style.color = '#dc3545';
  } else if (type === 'success') {
    statusDiv.style.color = '#28a745';
  } else {
    statusDiv.style.color = '#007bff';
  }
  
  // Add animation
  statusDiv.style.animation = 'pulse 0.5s ease-out';
  setTimeout(() => {
    statusDiv.style.animation = '';
  }, 500);
}

// Validate email format
function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// Auto-capture from current tab
function autoCaptureFromCurrentTab() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: extractEmailsFromPage
      }, (results) => {
        if (results && results[0] && results[0].result) {
          const emails = results[0].result;
          if (emails.length > 0) {
            updateStatus(`Found ${emails.length} email(s) on page`, 'success');
            emails.forEach(email => {
              chrome.runtime.sendMessage({
                type: "CAPTURE_EMAIL",
                email: email,
                source: "auto_capture"
              });
            });
          }
        }
      });
    }
  });
}

// Function to inject for email extraction
function extractEmailsFromPage() {
  const emailRegex = /[\w\.-]+@[\w\.-]+\.\w+/g;
  const text = document.body.innerText;
  const matches = text.match(emailRegex);
  return matches ? [...new Set(matches)] : []; // Remove duplicates
}

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey) {
    switch(e.key) {
      case 'Enter':
        e.preventDefault();
        if (!sendLinkBtn.disabled) {
          handleGenerateMagicLink();
        }
        break;
      case 'r':
        e.preventDefault();
        handleReset();
        break;
      case 'a':
        e.preventDefault();
        autoCaptureFromCurrentTab();
        break;
    }
  }
});

// Add drag and drop for email
emailInput.addEventListener('dragover', (e) => {
  e.preventDefault();
  emailInput.style.backgroundColor = '#e3f2fd';
});

emailInput.addEventListener('dragleave', () => {
  emailInput.style.backgroundColor = '';
});

emailInput.addEventListener('drop', (e) => {
  e.preventDefault();
  emailInput.style.backgroundColor = '';
  
  const text = e.dataTransfer.getData('text');
  const emailMatch = text.match(/[\w\.-]+@[\w\.-]+\.\w+/);
  
  if (emailMatch) {
    emailInput.value = emailMatch[0];
    handleEmailInput();
  }
});

// Periodic status update
setInterval(() => {
  if (statusDiv.textContent.includes('Waiting') || statusDiv.textContent.includes('Ready')) {
    const time = new Date().toLocaleTimeString();
    updateStatus(`Ready - ${time}`);
  }
}, 30000);
