# SecureBox - Secure File Upload System

A secure file upload system with email validation and S3 storage.

## Features

- Email-based access control (restricted to specific email)
- Secure file upload to AWS S3
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

# Email Notifications
MAILGUN_API_KEY=your_mailgun_api_key
```

## Usage

1. User enters their email address
2. System validates the email (only `viviansantanna@99app.com` is allowed)
3. If valid, user receives a temporary token and is redirected to upload page
4. User can drag-and-drop or select a file to upload
5. File is uploaded to S3 bucket
6. Email notification is sent to admin

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