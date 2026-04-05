# OTP Magic Link Bypass Extension

A powerful Chrome extension for intercepting OTP emails and generating magic links for email verification bypass.

## Features

- **Multi-Provider Support**: Works with Gmail, Outlook, Yahoo, ProtonMail, and more
- **Automatic Email Extraction**: Intelligently captures emails from web pages
- **Magic Link Generation**: Creates secure bypass links for OTP verification
- **Real-time Monitoring**: Continuously scans for new emails and OTP codes
- **Context Menu Integration**: Quick capture from any webpage
- **Persistent Storage**: Saves captured emails across browser sessions
- **Modern UI**: Beautiful gradient interface with smooth animations

## Installation

### Development Mode
1. Clone or download this repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right
4. Click "Load unpacked" and select the `otp-bypass` folder
5. The extension should now appear in your extensions list

### Production Build
1. Ensure all files are present in the `otp-bypass` folder
2. Create the required icon files (icon16.png, icon48.png, icon128.png)
3. Load as unpacked extension or package for Chrome Web Store

## Usage

### Basic Usage
1. Click the extension icon in your browser toolbar
2. Enter the target email address or let it auto-capture from the page
3. Click "Generate Magic Link" to create a bypass link
4. Click the generated link to automatically verify the email

### Auto-Capture Mode
- The extension automatically monitors email provider pages
- Emails are extracted from Gmail, Outlook, Yahoo, etc.
- Captured emails appear in the "Top 3 Captured Emails" list
- Click any captured email to use it for magic link generation

### Context Menu
- Right-click on any webpage
- Select "Capture Email from Page"
- The extension will extract emails from the current page

### Keyboard Shortcuts
- `Ctrl/Cmd + Enter`: Generate magic link (when email is entered)
- `Ctrl/Cmd + R`: Reset storage
- `Ctrl/Cmd + A`: Auto-capture from current tab

## File Structure

```
otp-bypass/
├── manifest.json          # Extension configuration
├── background.js          # Service worker for email interception
├── content.js             # Content script for page monitoring
├── popup.html             # Extension popup UI
├── popup.js               # Popup functionality
├── styles.css             # UI styling
├── icon.svg               # Icon source file
├── icon16.png             # 16x16 icon
├── icon48.png             # 48x48 icon
├── icon128.png            # 128x128 icon
└── README.md              # This file
```

## Configuration

### Email Providers
The extension supports these email providers by default:
- Gmail (mail.google.com)
- Outlook (outlook.com, office365.com)
- Yahoo Mail (mail.yahoo.com)
- ProtonMail (protonmail.com)
- iCloud Mail (icloud.com)
- Generic email providers

### Magic Link Format
Magic links are generated using this format:
```
https://auth.secure-verify.com/bypass/{hash}/{email}
```

The hash is generated using base64 encoding of the email and timestamp.

## Security Features

- **Local Storage**: All data is stored locally in the browser
- **No External Servers**: No data is sent to external servers
- **Secure Links**: Generated links use one-time hashes
- **Privacy Focused**: Only captures emails, no passwords or sensitive data

## Permissions Required

- `activeTab`: Access current tab content
- `storage`: Save captured emails locally
- `tabs`: Manage browser tabs
- `scripting`: Inject content scripts
- `contextMenus`: Add right-click menu options
- `webRequest`: Monitor network requests for email data

## Troubleshooting

### Extension Not Working
1. Check if Developer Mode is enabled
2. Ensure all files are present in the folder
3. Reload the extension from chrome://extensions/
4. Check browser console for errors

### Emails Not Capturing
1. Verify you're on a supported email provider
2. Check if the page has fully loaded
3. Try refreshing the page
4. Use the context menu option for manual capture

### Magic Links Not Working
1. Ensure the email format is correct
2. Check if the target service supports magic links
3. Verify the generated link isn't expired
4. Try generating a new link

## Development

### Adding New Email Providers
Edit `content.js` and add new patterns to `EMAIL_PATTERNS`:

```javascript
newprovider: {
  url: /newprovider\.com/i,
  selectors: ['.email-class', '[data-email]'],
  patterns: /[\w\.-]+@[\w\.-]+\.\w+/g
}
```

### Customizing Magic Links
Edit the `generateMagicLink` function in `background.js` to change the link format.

### Styling Changes
Modify `styles.css` to customize the popup appearance.

## License

This extension is for educational and testing purposes only. Use responsibly and in compliance with applicable laws and terms of service.

## Support

For issues and feature requests, please check the code comments and modify as needed for your specific use case.

---

**Disclaimer**: This tool is designed for legitimate testing and development purposes. Users are responsible for ensuring compliance with all applicable laws and regulations.
