#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-multipart",
#     "jinja2",
#     "peewee",
#     "aiofiles",
#     "httpx",
#     "boto3",
#     "python-dotenv",
# ]
# ///

import os
import uuid
from datetime import datetime
from pathlib import Path
import base64

import peewee as pw
from fastapi import FastAPI, Form, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import aiofiles
import httpx
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database initialization
db = pw.SqliteDatabase('file_uploads.db')

class BaseModelDB(pw.Model):
    class Meta:
        database = db

class FileUpload(BaseModelDB):
    id = pw.CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    email = pw.CharField(null=False)
    filename = pw.CharField(null=False)
    s3_key = pw.CharField(null=False)
    file_size = pw.IntegerField(null=True)
    content_type = pw.CharField(null=True)
    uploaded_at = pw.DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = "file_uploads"

# Create tables
db.connect()
db.create_tables([FileUpload])

# FastAPI app
app = FastAPI(title="Secure File Upload")

# Create templates directory
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(templates_dir))

# Add custom filter for file size formatting
def filesizeformat(value):
    """Format file size in human readable format"""
    if not value:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"

templates.env.filters['filesizeformat'] = filesizeformat

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Mailgun configuration
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = "solmail.emptor-cdn.com"
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

# Allowed email
ALLOWED_EMAIL = "viviansantanna@99app.com"

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

async def send_upload_notification(file_upload: FileUpload):
    """Send email notification for new file upload using Mailgun"""
    if not MAILGUN_API_KEY:
        print("Mailgun API key not configured")
        return False
    
    email_content = f"""
New file uploaded to SecureBox:

Email: {file_upload.email}
Filename: {file_upload.filename}
File Size: {file_upload.file_size:,} bytes
Content Type: {file_upload.content_type}
Uploaded At: {file_upload.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}
S3 Key: {file_upload.s3_key}

Access the file management system at: {APP_BASE_URL}
"""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": f"SecureBox <noreply@{MAILGUN_DOMAIN}>",
                    "to": "gabriel@emptor.io",
                    "subject": f"New file upload: {file_upload.filename}",
                    "text": email_content
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Show email validation form"""
    return templates.TemplateResponse("email_validation.html", {"request": request})

@app.post("/validate-email")
async def validate_email(request: Request, email: str = Form(...)):
    """Validate email and redirect to upload page if valid"""
    if email != ALLOWED_EMAIL:
        return templates.TemplateResponse(
            "email_validation.html", 
            {
                "request": request,
                "error": "Access denied. This email is not authorized.",
                "email": email
            }
        )
    
    # Generate a session token
    session_token = base64.urlsafe_b64encode(f"{email}:{datetime.now().timestamp()}".encode()).decode()
    
    # Redirect to upload page with token
    response = RedirectResponse(url=f"/upload?token={session_token}", status_code=303)
    return response

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, token: str):
    """Show file upload page if token is valid"""
    try:
        # Decode and validate token
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        email, timestamp = decoded.split(":")
        
        # Check if token is less than 1 hour old
        if (datetime.now().timestamp() - float(timestamp)) > 3600:
            return RedirectResponse(url="/", status_code=303)
        
        if email != ALLOWED_EMAIL:
            return RedirectResponse(url="/", status_code=303)
        
        # Get recent uploads for this email
        recent_uploads = (FileUpload
                         .select()
                         .where(FileUpload.email == email)
                         .order_by(FileUpload.uploaded_at.desc())
                         .limit(10))
        
        return templates.TemplateResponse(
            "upload.html", 
            {
                "request": request,
                "email": email,
                "token": token,
                "recent_uploads": recent_uploads
            }
        )
    except Exception as e:
        print(f"Token validation error: {e}")
        return RedirectResponse(url="/", status_code=303)

@app.post("/upload-file")
async def upload_file(
    token: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a file to S3"""
    try:
        # Validate token
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        email, timestamp = decoded.split(":")
        
        if (datetime.now().timestamp() - float(timestamp)) > 3600:
            raise HTTPException(status_code=403, detail="Session expired")
        
        if email != ALLOWED_EMAIL:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Generate S3 key
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"uploads/{timestamp_str}_{file.filename}"
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or 'application/octet-stream'
        )
        
        # Save to database
        file_upload = FileUpload.create(
            email=email,
            filename=file.filename,
            s3_key=s3_key,
            file_size=file_size,
            content_type=file.content_type
        )
        
        # Send notification email
        await send_upload_notification(file_upload)
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "size": file_size,
            "id": file_upload.id
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
async def list_files(token: str):
    """List uploaded files"""
    try:
        # Validate token
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        email, timestamp = decoded.split(":")
        
        if (datetime.now().timestamp() - float(timestamp)) > 3600:
            raise HTTPException(status_code=403, detail="Session expired")
        
        if email != ALLOWED_EMAIL:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Get files for this email
        files = (FileUpload
                .select()
                .where(FileUpload.email == email)
                .order_by(FileUpload.uploaded_at.desc()))
        
        return JSONResponse({
            "files": [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "size": f.file_size,
                    "uploaded_at": f.uploaded_at.isoformat(),
                    "content_type": f.content_type
                }
                for f in files
            ]
        })
    except Exception as e:
        raise HTTPException(status_code=403, detail="Invalid session")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)