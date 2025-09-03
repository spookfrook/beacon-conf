# SecureBox - Secure File Upload System

A secure file upload system with email-based access control and S3 storage.

## Features

- Email-based authentication (restricted access)
- Secure file upload to AWS S3
- Session-based access with time-limited tokens
- Email notifications for file uploads
- Drag-and-drop file upload interface
- Recent uploads history

## Local Development

```bash
# Run with uv
uv run conference_signup.py

# Or run with HTTPS for testing
uv run uvicorn conference_signup:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

## Environment Variables

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket_name

# Email Notifications
MAILGUN_API_KEY=your_mailgun_api_key
APP_BASE_URL=https://your-app-url.railway.app
```

## Access Control

Currently configured to only allow access to: `viviansantanna@99app.com`

To change the allowed email, modify the `ALLOWED_EMAIL` constant in `conference_signup.py`.

## Deployment

This app is configured for deployment on Railway using the included Dockerfile.

### Railway Deployment

1. Push to GitHub
2. Connect Railway to the GitHub repository
3. Set environment variables in Railway
4. Deploy

The app will automatically:
- Install dependencies using uv
- Create the SQLite database for tracking uploads
- Start the server on port 8000

## File Storage

Files are stored in AWS S3 with the following structure:
- Path: `uploads/YYYYMMDD_HHMMSS_filename`
- Metadata tracked in local SQLite database
- Email notifications sent for each upload