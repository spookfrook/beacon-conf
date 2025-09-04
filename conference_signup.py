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
from datetime import datetime
from pathlib import Path

import re
import asyncio
from fastapi import FastAPI, Form, Request, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import httpx
import aiofiles

# FastAPI app
app = FastAPI()

# Create templates directory
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


# Mailgun configuration
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = "solmail.emptor-cdn.com"

# Allowed emails
ALLOWED_EMAILS_ENV = os.getenv("ALLOWED_EMAILS", "viviansantanna@99app.com,gabriel@emptor.io")
ALLOWED_EMAILS = set(email.strip().lower() for email in ALLOWED_EMAILS_ENV.split(','))

# Initialize S3 client
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
except Exception as e:
    print(f"Error initializing S3 client: {e}")

templates = Jinja2Templates(directory=str(templates_dir))

# Simple in-memory token storage (in production, use Redis or similar)
valid_tokens = {}

# Limits and constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 1 * 1024 * 1024      # 1MB chunks
ALLOWED_EXTENSIONS = {'.csv', '.xls', '.xlsx'}


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-.]', '_', filename)
    filename = re.sub(r'\.+', '.', filename)
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return name + ext


async def upload_to_s3_async(local_path: Path, s3_key: str):
    """Upload file to S3 in a thread executor to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()

    def _upload():
        if s3_client and S3_BUCKET_NAME:
            try:
                s3_client.upload_file(
                    str(local_path),
                    S3_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={'ContentType': 'application/octet-stream'}
                )
                return True
            except Exception as e:
                print(f"S3 upload error: {e}")
                return False
        return False

    return await loop.run_in_executor(None, _upload)

async def send_upload_email(filename: str, file_size: int, uploaded_by: str):
    """Send email notification for spreadsheet upload"""
    if not MAILGUN_API_KEY:
        print("Mailgun API key not configured")
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
                    "to": "gabriel@emptor.io",
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
        "email": email,
        "created": datetime.now()
    }
    
    return {"token": token}

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

def _extract_token(request: Request, form_token: str | None) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    if form_token:
        return form_token
    raise HTTPException(status_code=401, detail="Token inválido")


async def _handle_upload(request: Request, background_tasks: BackgroundTasks, file: UploadFile, form_token: str | None = None):
    token = _extract_token(request, form_token)
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    token_data = valid_tokens[token]
    if (datetime.now() - token_data["created"]).seconds > 600:
        del valid_tokens[token]
        raise HTTPException(status_code=401, detail="Token expirado")

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi enviado")

    original_filename = file.filename
    sanitized = sanitize_filename(original_filename)
    file_extension = Path(sanitized).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido. Apenas planilhas CSV, XLS e XLSX são aceitas.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    final_name = f"{timestamp}_{unique_id}_{sanitized}"

    # Save to temp directory streaming to disk
    temp_dir = Path(__file__).parent / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / final_name

    try:
        total_written = 0
        async with aiofiles.open(temp_path, 'wb') as f:
            while chunk := await file.read(CHUNK_SIZE):
                total_written += len(chunk)
                if total_written > MAX_FILE_SIZE:
                    # stop reading further
                    await f.flush()
                    await f.close()
                    temp_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Arquivo muito grande (limite 10MB)")
                await f.write(chunk)

        # Schedule background S3 upload if configured
        if s3_client and S3_BUCKET_NAME:
            async def do_upload_and_notify():
                success = await upload_to_s3_async(temp_path, final_name)
                try:
                    await send_upload_email(original_filename, total_written, token_data["email"])
                finally:
                    if temp_path.exists():
                        temp_path.unlink()

            background_tasks.add_task(do_upload_and_notify)
        else:
            # No S3 configured: just send email and keep file locally
            background_tasks.add_task(send_upload_email, original_filename, total_written, token_data["email"])

        # Remove used token
        del valid_tokens[token]

        return {"message": "Arquivo enviado com sucesso", "filename": final_name, "size": total_written}
    except HTTPException:
        raise
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-file")
async def upload_file(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    return await _handle_upload(request, background_tasks, file)


@app.post("/upload")
async def upload_file_alias(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), token: str | None = Form(None)):
    """Alias endpoint to accept standard POST form uploads. Token can be sent as Authorization header or form field 'token'."""
    return await _handle_upload(request, background_tasks, file, token)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
