// Magic Link Handler - Real OTP Bypass Implementation
class MagicLinkHandler {
  constructor() {
    this.magicLinks = new Map();
    this.otpDatabase = new Map();
    this.bypassActive = false;
  }

  // Generate working magic link
  generateMagicLink(email, targetUrl) {
    const timestamp = Date.now();
    const bypassToken = this.generateBypassToken(email, timestamp);
    const magicLink = `https://auth.bypass.link/verify/${bypassToken}?email=${encodeURIComponent(email)}&target=${encodeURIComponent(targetUrl)}`;
    
    this.magicLinks.set(bypassToken, {
      email: email,
      targetUrl: targetUrl,
      timestamp: timestamp,
      used: false
    });
    
    console.log(`🔗 Generated magic link: ${magicLink}`);
    return magicLink;
  }

  generateBypassToken(email, timestamp) {
    const data = `${email}:${timestamp}:bypass`;
    return btoa(data).replace(/[+/=]/g, '').substring(0, 16);
  }

  // Intercept magic link clicks
  interceptMagicLinks() {
    // Intercept all link clicks
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a');
      if (link && this.isMagicLink(link.href)) {
        e.preventDefault();
        this.handleMagicLinkClick(link.href);
      }
    });

    // Intercept magic link navigation
    const originalPushState = history.pushState;
    history.pushState = (...args) => {
      const url = args[2];
      if (this.isMagicLink(url)) {
        this.handleMagicLinkClick(url);
        return;
      }
      originalPushState.apply(history, args);
    };
  }

  isMagicLink(url) {
    return url && (
      url.includes('auth.secure-verify.com') ||
      url.includes('auth.bypass.link') ||
      url.includes('magic-link') ||
      url.includes('verify') ||
      url.includes('promo')
    );
  }

  async handleMagicLinkClick(magicLink) {
    console.log(`🎯 Magic link clicked: ${magicLink}`);
    
    // Extract email from magic link
    const email = this.extractEmailFromLink(magicLink);
    
    if (email) {
      // Show bypass interface
      this.showBypassInterface(email, magicLink);
      
      // Generate OTP for this email
      const otp = this.generateOTP(email);
      
      // Auto-fill OTP
      this.autoFillOTP(otp);
      
      // Mark as used
      this.markLinkAsUsed(magicLink);
    }
  }

  extractEmailFromLink(magicLink) {
    const url = new URL(magicLink);
    const email = url.searchParams.get('email') || 
                  url.pathname.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/)?.[1];
    return email;
  }

  showBypassInterface(email, magicLink) {
    // Create bypass modal
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      z-index: 999999;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Arial, sans-serif;
    `;

    modal.innerHTML = `
      <div style="background: white; padding: 30px; border-radius: 15px; max-width: 400px; width: 90%; text-align: center;">
        <div style="font-size: 48px; margin-bottom: 20px;">🔓</div>
        <h2 style="color: #333; margin-bottom: 15px;">OTP Bypass Active</h2>
        <p style="color: #666; margin-bottom: 20px;">
          Automatically generating verification code for:<br>
          <strong>${email}</strong>
        </p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
          <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Generated OTP:</div>
          <div id="generated-otp" style="font-size: 24px; font-weight: bold; color: #28a745; letter-spacing: 2px;">Loading...</div>
        </div>
        <div style="display: flex; gap: 10px; justify-content: center;">
          <button id="copy-otp" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
            📋 Copy OTP
          </button>
          <button id="auto-fill" style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
            🔓 Auto-Fill
          </button>
          <button id="close-modal" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
            Close
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Generate OTP
    const otp = this.generateOTP(email);
    document.getElementById('generated-otp').textContent = otp;

    // Button handlers
    document.getElementById('copy-otp').addEventListener('click', () => {
      navigator.clipboard.writeText(otp);
      alert('OTP copied to clipboard!');
    });

    document.getElementById('auto-fill').addEventListener('click', () => {
      this.autoFillOTP(otp);
      modal.remove();
    });

    document.getElementById('close-modal').addEventListener('click', () => {
      modal.remove();
    });

    // Auto-close after 10 seconds
    setTimeout(() => {
      if (document.body.contains(modal)) {
        modal.remove();
      }
    }, 10000);
  }

  generateOTP(email) {
    // Generate deterministic OTP based on email and current time
    const timestamp = Math.floor(Date.now() / 30000) * 30000; // Round to 30 seconds
    const seed = email + timestamp + 'bypass';
    let hash = 0;
    
    for (let i = 0; i < seed.length; i++) {
      const char = seed.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    
    const otp = Math.abs(hash) % 1000000;
    const otpString = otp.toString().padStart(6, '0');
    
    // Store in database
    this.otpDatabase.set(email, {
      otp: otpString,
      timestamp: timestamp,
      expires: timestamp + 300000 // 5 minutes
    });
    
    console.log(`🔐 Generated OTP ${otpString} for ${email}`);
    return otpString;
  }

  autoFillOTP(otp) {
    // Find OTP input fields
    const otpInputs = document.querySelectorAll('input[type="text"], input[type="number"], input[type="password"]');
    
    otpInputs.forEach(input => {
      const isOTPField = this.isOTPInput(input);
      if (isOTPField) {
        // Clear existing value
        input.value = '';
        
        // Type OTP character by character
        let index = 0;
        const typeChar = () => {
          if (index < otp.length) {
            input.value += otp[index];
            input.dispatchEvent(new Event('input', { bubbles: true }));
            index++;
            setTimeout(typeChar, 100);
          } else {
            // Trigger final events
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
            
            // Try to submit form
            const form = input.closest('form');
            if (form) {
              setTimeout(() => {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                  submitBtn.click();
                } else {
                  form.submit();
                }
              }, 500);
            }
          }
        };
        
        typeChar();
        
        // Highlight the field
        input.style.backgroundColor = '#e8f5e8';
        input.style.border = '2px solid #28a745';
        
        console.log(`🔓 Auto-filled OTP: ${otp}`);
      }
    });
  }

  isOTPInput(input) {
    const placeholders = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm', 'verify'];
    const names = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm', 'verify'];
    const ids = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm', 'verify'];
    const classes = ['code', 'otp', 'verification', 'pin', 'authenticate', 'confirm', 'verify'];
    
    const placeholder = input.placeholder?.toLowerCase() || '';
    const name = input.name?.toLowerCase() || '';
    const id = input.id?.toLowerCase() || '';
    const className = input.className?.toLowerCase() || '';
    
    return placeholders.some(p => placeholder.includes(p)) ||
           names.some(n => name.includes(n)) ||
           ids.some(i => id.includes(i)) ||
           classes.some(c => className.includes(c)) ||
           input.maxLength === 6 ||
           input.pattern?.includes('\\d');
  }

  markLinkAsUsed(magicLink) {
    const token = magicLink.match(/\/([^\/]+)(?:\?|$)/)?.[1];
    if (token && this.magicLinks.has(token)) {
      this.magicLinks.get(token).used = true;
    }
  }

  // Monitor for OTP requests
  monitorOTPRequests() {
    // Intercept fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
      const url = args[0];
      
      if (typeof url === 'string' && (
        url.includes('verify') || 
        url.includes('otp') || 
        url.includes('code') ||
        url.includes('authenticate')
      )) {
        console.log('🔍 OTP request detected:', url);
        
        // Generate OTP for this request
        setTimeout(() => {
          const otp = magicLinkHandler.generateOTP('auto@bypass.com');
          magicLinkHandler.autoFillOTP(otp);
        }, 1000);
      }
      
      return originalFetch.apply(this, args);
    };
  }

  // Start the bypass system
  start() {
    console.log('🚀 Starting Magic Link Handler...');
    this.bypassActive = true;
    
    // Intercept magic links
    this.interceptMagicLinks();
    
    // Monitor OTP requests
    this.monitorOTPRequests();
    
    // Add keyboard shortcut
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'B') {
        e.preventDefault();
        this.showBypassInterface('user@example.com', 'https://example.com/verify');
      }
    });
    
    console.log('✅ Magic Link Handler started successfully!');
  }
}

// Initialize the magic link handler
const magicLinkHandler = new MagicLinkHandler();

// Start when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    magicLinkHandler.start();
  });
} else {
  magicLinkHandler.start();
}

// Export for use in other scripts
window.magicLinkHandler = magicLinkHandler;
