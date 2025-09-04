# SecureBox - Secure File Upload System

A secure file upload system with email validation and S3 storage.

## Features

- Email-based access control (supports multiple authorized users)
- Two-factor authentication with PIN codes sent via email
- Secure file upload to AWS S3 with validation:
  - File size limits (100MB max)
  - File type validation (CSV, XLS, XLSX only)
  - Content validation (magic bytes verification)
  - Filename sanitization
- Session-based authentication with temporary tokens
- Email notifications for uploaded files
- Drag-and-drop file upload interface
- Mobile-friendly responsive design

## Local Development

```bash
# Run with uv
uv run conference_signup.py
```

## Environment Variables

Create a `.env` file with the following variables:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket_name

# Email Configuration
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain  # Optional, defaults to solmail.emptor-cdn.com
ADMIN_EMAIL=admin@example.com       # Email to receive notifications
ALLOWED_EMAILS=user1@example.com,user2@example.com  # Comma-separated list of allowed emails

# App Configuration
BASE_URL=https://securebox.emptor.io  # Base URL for verification links
```

## Usage

1. User enters their email address
2. System validates the email against ALLOWED_EMAILS list
3. If valid, system sends a 6-digit PIN code via email
4. User enters PIN code or clicks verification link in email
5. After successful verification, user is redirected to upload page
6. User can drag-and-drop or select a file to upload
7. System validates:
   - File size (max 100MB)
   - File extension (.csv, .xls, .xlsx)
   - File content (magic bytes)
   - Filename (sanitized for security)
8. File is uploaded to S3 bucket
9. Email notification is sent to admin

## Deployment

This app is configured for deployment on Railway using the included Dockerfile.

### Railway Deployment

1. Push to GitHub
2. Connect Railway to the GitHub repository
3. Set environment variables in Railway
4. Deploy

The app will automatically:
- Install dependencies using uv
- Start the server on port 8000