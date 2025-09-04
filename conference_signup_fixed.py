#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-multipart",
#     "jinja2",
#     "boto3",
#     "httpx",
#     "python-dotenv",
#     "aiofiles",
# ]
# ///

import os
import uuid
import re
from datetime import datetime
from pathlib import Path
import asyncio

from fastapi import FastAPI, Form, Request, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import httpx
import aiofiles

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File upload security constants
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'.csv', '.xls', '.xlsx'}
CHUNK_SIZE = 1 * 1024 * 1024  # 1MB chunks for streaming

# Create directories
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
temp_dir = Path(__file__).parent / "temp_uploads"
temp_dir.mkdir(exist_ok=True)

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Mailgun configuration
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "solmail.emptor-cdn.com")

# Allowed emails
ALLOWED_EMAILS_ENV = os.getenv("ALLOWED_EMAILS", "viviansantanna@99app.com,gabriel@emptor.io,gissele@emptor.io,claudia@emptor.io")
ALLOWED_EMAILS = set(email.strip().lower() for email in ALLOWED_EMAILS_ENV.split(','))

# Initialize S3 client
try:
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("WARNING: AWS credentials not configured")
        s3_client = None
    else:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        print(f"S3 client initialized for bucket: {S3_BUCKET_NAME}")
except Exception as e:
    print(f"Error initializing S3 client: {e}")
    s3_client = None

# Templates
templates = Jinja2Templates(directory=str(templates_dir))

# Simple in-memory token storage
valid_tokens = {}

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and other issues"""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-.]', '_', filename)
    filename = re.sub(r'\.+', '.', filename)
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return name + ext

async def upload_to_s3_async(file_path: Path, s3_key: str):
    """Upload file to S3 in a separate thread to avoid blocking"""
    loop = asyncio.get_event_loop()
    
    def upload():
        if s3_client and S3_BUCKET_NAME:
            try:
                s3_client.upload_file(
                    str(file_path),
                    S3_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={'ContentType': 'application/octet-stream'}
                )
                return True
            except Exception as e:
                print(f"S3 upload error: {e}")
                return False
        return False
    
    return await loop.run_in_executor(None, upload)

async def send_upload_email(filename: str, file_size: int, uploaded_by: str):
    """Send email notification for spreadsheet upload"""
    if not MAILGUN_API_KEY:
        return False
    
    email_content = f"""
Nova planilha enviada ao SecureBox:

Arquivo: {filename}
Tamanho: {file_size:,} bytes
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Enviado por: {uploaded_by}
Bucket S3: {S3_BUCKET_NAME}
"""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": f"SecureBox <noreply@{MAILGUN_DOMAIN}>",
                    "to": os.getenv("ADMIN_EMAIL", "gabriel@emptor.io"),
                    "subject": f"Nova planilha: {filename}",
                    "text": email_content
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/validate-email")
async def validate_email(email: str = Form(...)):
    """Validate email and create session token"""
    if email.lower() not in ALLOWED_EMAILS:
        raise HTTPException(
            status_code=403, 
            detail="Email não autorizado. Acesso restrito."
        )
    
    # Generate token
    token = str(uuid.uuid4())
    valid_tokens[token] = {
        "email": email.lower(),
        "created": datetime.now()
    }
    
    return {"token": token}

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload-file")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Improved file upload endpoint with streaming and background S3 upload"""
    print(f"=== Upload request received ===")
    print(f"File: {file.filename if file else 'No file'}")
    print(f"Content-Type: {file.content_type if file else 'Unknown'}")
    
    # Validate token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")
    
    token = auth_header.replace("Bearer ", "")
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    # Check token age
    token_data = valid_tokens[token]
    if (datetime.now() - token_data["created"]).seconds > 600:
        del valid_tokens[token]
        raise HTTPException(status_code=401, detail="Token expirado")
    
    # Validate file
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi enviado")
    
    # Basic filename validation
    original_filename = file.filename
    sanitized_filename = sanitize_filename(original_filename)
    file_extension = Path(sanitized_filename).suffix.lower()
    
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail="Tipo de arquivo não permitido. Apenas planilhas CSV, XLS e XLSX são aceitas."
        )
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_id = str(uuid.uuid4())[:8]
    final_filename = f"{timestamp}_{file_id}_{sanitized_filename}"
    
    # Save file to temp directory first (streaming to avoid memory issues)
    temp_file_path = temp_dir / final_filename
    
    try:
        # Stream file to disk to handle large files
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while chunk := await file.read(CHUNK_SIZE):
                await f.write(chunk)
        
        file_size = temp_file_path.stat().st_size
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            temp_file_path.unlink()  # Delete temp file
            raise HTTPException(status_code=413, detail="Arquivo muito grande")
        
        print(f"File saved to temp: {temp_file_path}, size: {file_size}")
        
        # Schedule background S3 upload if configured
        if s3_client and S3_BUCKET_NAME:
            background_tasks.add_task(
                upload_to_s3_and_cleanup,
                temp_file_path,
                final_filename,
                valid_tokens[token]["email"]
            )
        else:
            # Just send email notification
            user_email = valid_tokens[token]["email"]
            background_tasks.add_task(
                send_upload_email,
                sanitized_filename,
                file_size,
                user_email
            )
        
        # Remove used token
        del valid_tokens[token]
        
        # Return success immediately
        return {
            "message": "Arquivo enviado com sucesso",
            "filename": final_filename,
            "size": file_size
        }
        
    except Exception as e:
        # Clean up temp file if it exists
        if temp_file_path.exists():
            temp_file_path.unlink()
        
        print(f"Upload error: {type(e).__name__}: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Erro ao processar arquivo")

async def upload_to_s3_and_cleanup(temp_file_path: Path, s3_key: str, user_email: str):
    """Background task to upload to S3 and clean up"""
    try:
        print(f"Starting background S3 upload for {s3_key}")
        
        # Upload to S3
        success = await upload_to_s3_async(temp_file_path, s3_key)
        
        if success:
            print(f"S3 upload successful: {s3_key}")
            # Send email notification
            await send_upload_email(
                temp_file_path.name,
                temp_file_path.stat().st_size,
                user_email
            )
        else:
            print(f"S3 upload failed: {s3_key}")
        
    finally:
        # Always clean up temp file
        if temp_file_path.exists():
            temp_file_path.unlink()
            print(f"Cleaned up temp file: {temp_file_path}")

@app.post("/upload-file-form")
async def upload_file_form(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    token: str = Form(...)
):
    """Handle regular HTML form upload - returns redirect instead of JSON"""
    try:
        # Validate token
        if token not in valid_tokens:
            return RedirectResponse(url="/upload?error=Token%20inválido", status_code=303)
        
        # Check token age
        token_data = valid_tokens[token]
        if (datetime.now() - token_data["created"]).seconds > 600:
            del valid_tokens[token]
            return RedirectResponse(url="/upload?error=Token%20expirado", status_code=303)
        
        # Validate file
        if not file or not file.filename:
            return RedirectResponse(url="/upload?error=Nenhum%20arquivo%20foi%20enviado", status_code=303)
        
        # Basic filename validation
        original_filename = file.filename
        sanitized_filename = sanitize_filename(original_filename)
        file_extension = Path(sanitized_filename).suffix.lower()
        
        if file_extension not in ALLOWED_EXTENSIONS:
            return RedirectResponse(
                url="/upload?error=Tipo%20de%20arquivo%20não%20permitido", 
                status_code=303
            )
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        final_filename = f"{timestamp}_{file_id}_{sanitized_filename}"
        
        # Save file to temp directory first
        temp_file_path = temp_dir / final_filename
        
        # Stream file to disk
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while chunk := await file.read(CHUNK_SIZE):
                await f.write(chunk)
        
        file_size = temp_file_path.stat().st_size
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            temp_file_path.unlink()
            return RedirectResponse(url="/upload?error=Arquivo%20muito%20grande", status_code=303)
        
        # Schedule background S3 upload if configured
        if s3_client and S3_BUCKET_NAME:
            background_tasks.add_task(
                upload_to_s3_and_cleanup,
                temp_file_path,
                final_filename,
                valid_tokens[token]["email"]
            )
        else:
            # Just send email notification
            user_email = valid_tokens[token]["email"]
            background_tasks.add_task(
                send_upload_email,
                sanitized_filename,
                file_size,
                user_email
            )
        
        # Remove used token
        del valid_tokens[token]
        
        # Redirect to success page
        return RedirectResponse(url="/upload?success=true", status_code=303)
        
    except Exception as e:
        print(f"Form upload error: {type(e).__name__}: {str(e)}")
        return RedirectResponse(
            url=f"/upload?error=Erro%20ao%20processar%20arquivo", 
            status_code=303
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "s3_configured": s3_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting fixed conference signup server...")
    print(f"Temp uploads directory: {temp_dir.absolute()}")
    
    # Run with better configuration
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=30,  # Reduced from 300 to 30 seconds
        limit_concurrency=100,  # Limit concurrent connections
    )