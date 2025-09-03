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
# ]
# ///

import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import httpx

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

# Allowed email
ALLOWED_EMAIL = "viviansantanna@99app.com"

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# HTML template for email validation
email_template = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecureBox - Upload Seguro</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 450px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }
        
        .logo {
            font-size: 48px;
            margin-bottom: 10px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 40px;
            font-size: 16px;
        }
        
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        
        input[type="email"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="email"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .submit-btn {
            width: 100%;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .submit-btn:hover {
            background: #5a67d8;
        }
        
        .submit-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .error-message {
            display: none;
            padding: 12px;
            background: #fee;
            color: #c33;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🔐</div>
        <h1>SecureBox</h1>
        <p class="subtitle">Upload seguro de arquivos</p>
        
        <form id="emailForm">
            <div class="form-group">
                <label for="email">Digite seu email para continuar</label>
                <input type="email" id="email" name="email" required placeholder="seu@email.com">
            </div>
            
            <button type="submit" class="submit-btn">Continuar</button>
        </form>
        
        <div class="error-message" id="errorMessage"></div>
    </div>
    
    <script>
        document.getElementById('emailForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const submitBtn = document.querySelector('.submit-btn');
            const errorMsg = document.getElementById('errorMessage');
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Verificando...';
            errorMsg.style.display = 'none';
            
            try {
                const response = await fetch('/validate-email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `email=${encodeURIComponent(email)}`
                });
                
                if (response.ok) {
                    const data = await response.json();
                    // Store session token and redirect to upload page
                    sessionStorage.setItem('upload_token', data.token);
                    window.location.href = '/upload';
                } else {
                    const error = await response.json();
                    errorMsg.textContent = error.detail;
                    errorMsg.style.display = 'block';
                }
            } catch (error) {
                errorMsg.textContent = 'Erro ao verificar email. Tente novamente.';
                errorMsg.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Continuar';
            }
        });
    </script>
</body>
</html>
"""

# HTML template for file upload
upload_template = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecureBox - Upload de Arquivo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .logo {
            font-size: 48px;
            margin-bottom: 10px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            font-size: 16px;
        }
        
        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            margin-bottom: 20px;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        
        .upload-area.drag-over {
            border-color: #667eea;
            background: #f8f9ff;
            transform: scale(1.02);
        }
        
        .upload-icon {
            font-size: 64px;
            margin-bottom: 20px;
            color: #667eea;
        }
        
        .upload-text {
            color: #666;
            margin-bottom: 10px;
        }
        
        .upload-subtext {
            color: #999;
            font-size: 14px;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .file-info {
            background: #f8f9ff;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        
        .file-info .filename {
            color: #333;
            font-weight: 500;
            margin-bottom: 5px;
        }
        
        .file-info .filesize {
            color: #666;
            font-size: 14px;
        }
        
        .submit-btn {
            width: 100%;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
            display: none;
        }
        
        .submit-btn:hover {
            background: #5a67d8;
        }
        
        .submit-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .success-message {
            display: none;
            padding: 20px;
            background: #d4edda;
            color: #155724;
            border-radius: 8px;
            text-align: center;
        }
        
        .error-message {
            display: none;
            padding: 20px;
            background: #fee;
            color: #c33;
            border-radius: 8px;
            text-align: center;
        }
        
        .progress-bar {
            display: none;
            height: 4px;
            background: #e0e0e0;
            border-radius: 2px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .progress-bar-fill {
            height: 100%;
            background: #667eea;
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">📤</div>
            <h1>Upload de Arquivo</h1>
            <p class="subtitle">Arraste ou selecione seu arquivo</p>
        </div>
        
        <form id="uploadForm">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <p class="upload-text">Arraste seu arquivo aqui</p>
                <p class="upload-subtext">ou clique para selecionar</p>
                <input type="file" id="fileInput" name="file" required>
            </div>
            
            <div class="file-info" id="fileInfo">
                <div class="filename" id="fileName"></div>
                <div class="filesize" id="fileSize"></div>
            </div>
            
            <div class="progress-bar" id="progressBar">
                <div class="progress-bar-fill" id="progressBarFill"></div>
            </div>
            
            <button type="submit" class="submit-btn" id="submitBtn">Enviar Arquivo</button>
        </form>
        
        <div class="success-message" id="successMessage">
            ✅ Arquivo enviado com sucesso!
        </div>
        
        <div class="error-message" id="errorMessage"></div>
    </div>
    
    <script>
        // Check if user has valid token
        const token = sessionStorage.getItem('upload_token');
        if (!token) {
            window.location.href = '/';
        }
        
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const submitBtn = document.getElementById('submitBtn');
        const progressBar = document.getElementById('progressBar');
        const progressBarFill = document.getElementById('progressBarFill');
        
        // Click to select file
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect(files[0]);
            }
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        function handleFileSelect(file) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.style.display = 'block';
            submitBtn.style.display = 'block';
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // Form submission
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Enviando...';
            progressBar.style.display = 'block';
            
            try {
                const response = await fetch('/upload-file', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
                
                if (response.ok) {
                    progressBarFill.style.width = '100%';
                    document.getElementById('successMessage').style.display = 'block';
                    document.getElementById('uploadForm').style.display = 'none';
                    
                    // Clear token after successful upload
                    sessionStorage.removeItem('upload_token');
                    
                    // Redirect after 3 seconds
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 3000);
                } else {
                    const error = await response.json();
                    document.getElementById('errorMessage').textContent = error.detail;
                    document.getElementById('errorMessage').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('errorMessage').textContent = 'Erro ao enviar arquivo.';
                document.getElementById('errorMessage').style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Enviar Arquivo';
                progressBar.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

# Save templates
(templates_dir / "index.html").write_text(email_template)
(templates_dir / "upload.html").write_text(upload_template)

templates = Jinja2Templates(directory=str(templates_dir))

# Simple in-memory token storage (in production, use Redis or similar)
valid_tokens = {}

async def send_upload_email(filename: str, file_size: int):
    """Send email notification for file upload"""
    if not MAILGUN_API_KEY:
        print("Mailgun API key not configured")
        return False
    
    email_content = f"""
Novo arquivo enviado ao SecureBox:

Arquivo: {filename}
Tamanho: {file_size:,} bytes
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Enviado por: {ALLOWED_EMAIL}
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
                    "subject": f"Novo arquivo: {filename}",
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
    if email.lower() != ALLOWED_EMAIL.lower():
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

@app.post("/upload-file")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload file to S3"""
    # Validate token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")
    
    token = auth_header.replace("Bearer ", "")
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    # Check token age (expire after 10 minutes)
    token_data = valid_tokens[token]
    if (datetime.now() - token_data["created"]).seconds > 600:
        del valid_tokens[token]
        raise HTTPException(status_code=401, detail="Token expirado")
    
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        
        # Upload to S3
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            filename,
            ExtraArgs={'ContentType': file.content_type}
        )
        
        # Send email notification
        await send_upload_email(file.filename, file.size or 0)
        
        # Remove used token
        del valid_tokens[token]
        
        return {
            "message": "Arquivo enviado com sucesso",
            "filename": filename,
            "size": file.size
        }
        
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credenciais AWS não configuradas")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)