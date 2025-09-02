# Beacon Conference Signup

Conference signup application with voice memo support for Sol by Emptor.

## Features

- User registration form with contact details
- Voice memo recording for descriptions
- Integration with Sol AI calling system
- Mobile-friendly responsive design
- Works on iOS Safari with voice recording

## Local Development

```bash
# Run with uv
uv run conference_signup.py

# Or run with HTTPS for mobile testing
uv run uvicorn conference_signup:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

## Environment Variables

```bash
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
SIP_TRUNK_ID=your_sip_trunk_id
```

## Deployment

This app is configured for deployment on Railway using the included Dockerfile.

### Railway Deployment

1. Push to GitHub
2. Connect Railway to the GitHub repository
3. Set environment variables in Railway
4. Deploy

The app will automatically:
- Install dependencies using uv
- Create the SQLite database
- Start the server on port 8000