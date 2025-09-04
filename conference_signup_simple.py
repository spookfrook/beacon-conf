#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-multipart",
#     "jinja2",
#     "python-dotenv",
# ]
# ///

import os
import uuid
import re
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
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

# File upload settings
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'.csv', '.xls', '.xlsx'}

# Create directories
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(templates_dir))

# Simple in-memory token storage
valid_tokens = {}

# Allowed emails
ALLOWED_EMAILS_ENV = os.getenv("ALLOWED_EMAILS", "viviansantanna@99app.com,gabriel@emptor.io,gissele@emptor.io,claudia@emptor.io")
ALLOWED_EMAILS = set(email.strip().lower() for email in ALLOWED_EMAILS_ENV.split(','))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename"""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-.]', '_', filename)
    filename = re.sub(r'\.+', '.', filename)
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return name + ext

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

@app.post("/upload-file-form")
async def upload_file_form(
    file: UploadFile = File(...),
    token: str = Form(...)
):
    """Simple form upload handler"""
    try:
        # Validate token
        if token not in valid_tokens:
            return RedirectResponse(url="/upload?error=Token%20inválido", status_code=303)
        
        # Validate file
        if not file or not file.filename:
            return RedirectResponse(url="/upload?error=Nenhum%20arquivo%20foi%20enviado", status_code=303)
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            return RedirectResponse(
                url="/upload?error=Tipo%20de%20arquivo%20não%20permitido", 
                status_code=303
            )
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        sanitized_name = sanitize_filename(file.filename)
        final_filename = f"{timestamp}_{file_id}_{sanitized_name}"
        file_path = uploads_dir / final_filename
        
        # Save file directly - simple and fast
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            return RedirectResponse(url="/upload?error=Arquivo%20muito%20grande", status_code=303)
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        print(f"File saved: {file_path}, size: {len(content)} bytes")
        
        # Remove used token
        del valid_tokens[token]
        
        # Redirect to success
        return RedirectResponse(url="/upload?success=true", status_code=303)
        
    except Exception as e:
        print(f"Upload error: {e}")
        return RedirectResponse(
            url="/upload?error=Erro%20ao%20processar%20arquivo", 
            status_code=303
        )

@app.post("/upload-file")
async def upload_file_ajax(
    request: Request,
    file: UploadFile = File(...)
):
    """AJAX upload endpoint for backwards compatibility"""
    # Get token from header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")
    
    token = auth_header.replace("Bearer ", "")
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    # Validate file
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi enviado")
    
    # Check file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail="Tipo de arquivo não permitido"
        )
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_id = str(uuid.uuid4())[:8]
    sanitized_name = sanitize_filename(file.filename)
    final_filename = f"{timestamp}_{file_id}_{sanitized_name}"
    file_path = uploads_dir / final_filename
    
    # Save file
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande")
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Remove used token
    del valid_tokens[token]
    
    return {
        "message": "Arquivo enviado com sucesso",
        "filename": final_filename,
        "size": len(content)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("Starting simple conference signup server...")
    print(f"Uploads will be saved to: {uploads_dir.absolute()}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")