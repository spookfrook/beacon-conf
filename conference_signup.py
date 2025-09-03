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
    <title>SecureBox by Emptor - Upload Seguro</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #F9FAFB;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }
        
        /* Background gradient effect */
        body::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at center, rgba(124, 58, 237, 0.05) 0%, transparent 50%);
            pointer-events: none;
        }
        
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            max-width: 480px;
            width: 100%;
            padding: 48px;
            position: relative;
            z-index: 1;
        }
        
        .header {
            text-align: center;
            margin-bottom: 48px;
        }
        
        .logo-container {
            margin-bottom: 16px;
        }
        
        .emptor-logo {
            width: 100px;
            height: 24px;
            margin: 0 auto;
            display: block;
        }
        
        .sol-video-container {
            width: 80px;
            height: 80px;
            margin: 20px auto;
            border-radius: 50%;
            overflow: hidden;
            background: #F3E8FF;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .sol-video {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        .logo {
            height: 32px;
            width: auto;
        }
        
        .sol-detective {
            width: 60px;
            height: 60px;
            border-radius: 12px;
            overflow: hidden;
            background: #F3E8FF;
        }
        
        .sol-detective video {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        h1 {
            color: #111827;
            margin-bottom: 8px;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        
        .subtitle {
            color: #6B7280;
            font-size: 16px;
            font-weight: 400;
        }
        
        .emptor-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-top: 16px;
            padding: 6px 12px;
            background: #F3F4F6;
            border-radius: 20px;
            font-size: 12px;
            color: #6B7280;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #374151;
            font-weight: 500;
            font-size: 14px;
        }
        
        input[type="email"] {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.2s;
            font-family: 'Inter', sans-serif;
        }
        
        input[type="email"]:hover {
            border-color: #D1D5DB;
        }
        
        input[type="email"]:focus {
            outline: none;
            border-color: #7C3AED;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }
        
        .submit-btn {
            width: 100%;
            padding: 12px 24px;
            background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 4px 6px -1px rgba(124, 58, 237, 0.25);
            margin-top: 32px;
        }
        
        .submit-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 8px -1px rgba(124, 58, 237, 0.3);
        }
        
        .submit-btn:active {
            transform: translateY(0);
        }
        
        .submit-btn:disabled {
            background: #E5E7EB;
            color: #9CA3AF;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }
        
        .error-message {
            display: none;
            padding: 12px 16px;
            background: #FEE2E2;
            color: #DC2626;
            border-radius: 8px;
            margin-top: 16px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .security-note {
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #E5E7EB;
            text-align: center;
            font-size: 12px;
            color: #9CA3AF;
        }
        
        .security-note svg {
            width: 16px;
            height: 16px;
            display: inline-block;
            vertical-align: middle;
            margin-right: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-container">
                <img class="logo" src="https://www.emptor.io/assets/Logo-Emptor-1.svg" alt="Emptor Logo">
                <div class="sol-detective">
                    <video autoplay loop muted playsinline>
                        <source src="https://www.emptor.io/assets/sol/SOL%20LOOPS/SOL_GL04_DETECTIVE.webm" type="video/webm">
                    </video>
                </div>
            </div>
            <h1>SecureBox</h1>
            <p class="subtitle">Upload seguro de planilhas</p>
        </div>
        
        <form id="emailForm">
            <div class="form-group">
                <label for="email">Email autorizado</label>
                <input type="email" id="email" name="email" required placeholder="seu@email.com" autocomplete="email">
            </div>
            
            <button type="submit" class="submit-btn">Acessar sistema →</button>
        </form>
        
        <div class="error-message" id="errorMessage"></div>
        
        <div class="security-note">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
            Conexão segura e criptografada
        </div>
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
    <title>SecureBox by Emptor - Upload de Arquivo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #F9FAFB;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }
        
        /* Background gradient effect */
        body::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at center, rgba(168, 85, 247, 0.05) 0%, transparent 50%);
            pointer-events: none;
        }
        
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            max-width: 640px;
            width: 100%;
            padding: 48px;
            position: relative;
            z-index: 1;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .step-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 32px;
        }
        
        .step {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 600;
        }
        
        .step.completed {
            background: #10B981;
            color: white;
        }
        
        .step.completed::before {
            content: '✓';
        }
        
        .step.active {
            background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%);
            color: white;
            box-shadow: 0 4px 8px -2px rgba(124, 58, 237, 0.3);
        }
        
        .step-line {
            width: 40px;
            height: 2px;
            background: #E5E7EB;
        }
        
        h1 {
            color: #111827;
            margin-bottom: 8px;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        
        .subtitle {
            color: #6B7280;
            font-size: 16px;
            font-weight: 400;
        }
        
        .upload-area {
            border: 2px dashed #E5E7EB;
            border-radius: 12px;
            padding: 48px 24px;
            text-align: center;
            transition: all 0.2s;
            cursor: pointer;
            margin-bottom: 24px;
            background: #FAFAFA;
        }
        
        .upload-area:hover {
            border-color: #A855F7;
            background: #FAF5FF;
        }
        
        .upload-area.drag-over {
            border-color: #7C3AED;
            background: #F3E8FF;
            border-style: solid;
        }
        
        .brand-header {
            position: absolute;
            top: 24px;
            left: 24px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .brand-logo {
            height: 20px;
            width: auto;
        }
        
        .upload-icon {
            width: 64px;
            height: 64px;
            margin: 0 auto 24px;
            background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 0 8px 16px -4px rgba(124, 58, 237, 0.2);
            color: white;
        }
        
        .upload-text {
            color: #374151;
            margin-bottom: 8px;
            font-size: 16px;
            font-weight: 600;
        }
        
        .upload-subtext {
            color: #9CA3AF;
            font-size: 14px;
        }
        
        .upload-formats {
            margin-top: 16px;
            font-size: 12px;
            color: #9CA3AF;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .file-info {
            background: #F9FAFB;
            border: 1px solid #E5E7EB;
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            display: none;
            align-items: center;
            gap: 16px;
        }
        
        .file-icon {
            width: 48px;
            height: 48px;
            background: #F3E8FF;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            flex-shrink: 0;
        }
        
        .file-details {
            flex: 1;
        }
        
        .file-info .filename {
            color: #111827;
            font-weight: 600;
            margin-bottom: 4px;
            word-break: break-all;
        }
        
        .file-info .filesize {
            color: #6B7280;
            font-size: 14px;
        }
        
        .file-remove {
            padding: 8px 16px;
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 6px;
            color: #EF4444;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .file-remove:hover {
            background: #FEE2E2;
            border-color: #FECACA;
        }
        
        .submit-btn {
            width: 100%;
            padding: 12px 24px;
            background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: none;
            box-shadow: 0 4px 6px -1px rgba(124, 58, 237, 0.25);
        }
        
        .submit-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 8px -1px rgba(124, 58, 237, 0.3);
        }
        
        .submit-btn:active {
            transform: translateY(0);
        }
        
        .submit-btn:disabled {
            background: #E5E7EB;
            color: #9CA3AF;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }
        
        .success-container {
            display: none;
            text-align: center;
            padding: 48px;
        }
        
        .success-icon {
            width: 120px;
            height: 120px;
            margin: 0 auto 24px;
            background: #F3E8FF;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 8px 16px -4px rgba(124, 58, 237, 0.2);
        }
        
        .success-icon video {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        .success-title {
            color: #111827;
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        
        .success-message {
            color: #6B7280;
            font-size: 16px;
            margin-bottom: 32px;
        }
        
        .back-btn {
            padding: 12px 24px;
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            color: #374151;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .back-btn:hover {
            background: #F9FAFB;
            border-color: #D1D5DB;
        }
        
        .error-message {
            display: none;
            padding: 16px;
            background: #FEE2E2;
            color: #DC2626;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .progress-bar {
            display: none;
            height: 8px;
            background: #E5E7EB;
            border-radius: 4px;
            margin-bottom: 24px;
            overflow: hidden;
        }
        
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #7C3AED 0%, #A855F7 100%);
            width: 0%;
            transition: width 0.3s;
            border-radius: 4px;
        }
        
        .upload-info {
            margin-top: 32px;
            padding: 16px;
            background: #F3F4F6;
            border-radius: 8px;
            font-size: 12px;
            color: #6B7280;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-container">
                <svg class="emptor-logo" viewBox="0 0 100 24" xmlns="http://www.w3.org/2000/svg">
                    <text x="50" y="18" font-family="Inter, sans-serif" font-size="20" font-weight="700" fill="#7C3AED" text-anchor="middle">emptor</text>
                </svg>
            </div>
            <div class="sol-video-container">
                <video autoplay loop muted playsinline class="sol-video" src="https://www.emptor.io/assets/sol/SOL%20LOOPS/SOL_GL04_DETECTIVE.webm"></video>
            </div>
            <h1>SecureBox</h1>
            <p class="subtitle">Upload seguro de planilhas</p>
        </div>
        <div class="upload-container" id="uploadContainer">
            <div class="header">
                <div class="step-indicator">
                    <div class="step completed"></div>
                    <div class="step-line"></div>
                    <div class="step active">2</div>
                </div>
                <h1>Upload de Planilha</h1>
                <p class="subtitle">Envie sua planilha de forma segura</p>
            </div>
            
            <form id="uploadForm">
                <div class="upload-area" id="uploadArea">
                    <div class="upload-icon">📊</div>
                    <p class="upload-text">Arraste sua planilha aqui</p>
                    <p class="upload-subtext">ou clique para selecionar</p>
                    <p class="upload-formats">Formatos aceitos: CSV, XLS, XLSX</p>
                    <input type="file" id="fileInput" name="file" required accept=".csv,.xls,.xlsx">
                </div>
                
                <div class="file-info" id="fileInfo">
                    <div class="file-icon">📄</div>
                    <div class="file-details">
                        <div class="filename" id="fileName"></div>
                        <div class="filesize" id="fileSize"></div>
                    </div>
                    <button type="button" class="file-remove" id="removeFile">Remover</button>
                </div>
                
                <div class="progress-bar" id="progressBar">
                    <div class="progress-bar-fill" id="progressBarFill"></div>
                </div>
                
                <button type="submit" class="submit-btn" id="submitBtn">Enviar planilha →</button>
                
                <div class="error-message" id="errorMessage"></div>
            </form>
            
                <div class="upload-info">
                <strong>Segurança:</strong> Suas planilhas são criptografadas e armazenadas com segurança em conformidade com as normas de proteção de dados.
            </div>
        </div>
        
        <div class="success-container" id="successContainer">
            <div class="success-icon">
                <video autoplay loop muted playsinline>
                    <source src="https://www.emptor.io/assets/sol/SOL%20LOOPS/SOL_GL04_DETECTIVE.webm" type="video/webm">
                </video>
            </div>
            <h2 class="success-title">Upload concluído!</h2>
            <p class="success-message">Sua planilha foi enviada com sucesso e está segura.</p>
            <button class="back-btn" onclick="window.location.href='/'">← Voltar ao início</button>
        </div>
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
            // Update file icon based on type
            const fileIcon = document.querySelector('.file-icon');
            const extension = file.name.split('.').pop().toLowerCase();
            const iconMap = {
                'csv': '📊',
                'xls': '📊',
                'xlsx': '📊'
            };
            fileIcon.textContent = iconMap[extension] || '📄';
            
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.style.display = 'flex';
            submitBtn.style.display = 'block';
            uploadArea.style.display = 'none';
        }
        
        // Remove file
        document.getElementById('removeFile').addEventListener('click', () => {
            fileInput.value = '';
            fileInfo.style.display = 'none';
            submitBtn.style.display = 'none';
            uploadArea.style.display = 'block';
        });
        
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
            document.getElementById('errorMessage').style.display = 'none';
            
            // Simulate progress
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 30;
                if (progress > 90) progress = 90;
                progressBarFill.style.width = progress + '%';
            }, 200);
            
            try {
                const response = await fetch('/upload-file', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
                
                if (response.ok) {
                    clearInterval(progressInterval);
                    progressBarFill.style.width = '100%';
                    
                    // Short delay for visual feedback
                    setTimeout(() => {
                        // Show success screen
                        document.getElementById('uploadContainer').style.display = 'none';
                        document.getElementById('successContainer').style.display = 'block';
                    }, 500);
                    
                    // Clear token after successful upload
                    sessionStorage.removeItem('upload_token');
                } else {
                    clearInterval(progressInterval);
                    const error = await response.json();
                    document.getElementById('errorMessage').textContent = error.detail || 'Erro ao enviar arquivo.';
                    document.getElementById('errorMessage').style.display = 'block';
                    progressBarFill.style.width = '0%';
                }
            } catch (error) {
                clearInterval(progressInterval);
                document.getElementById('errorMessage').textContent = 'Erro ao enviar arquivo. Verifique sua conexão.';
                document.getElementById('errorMessage').style.display = 'block';
                progressBarFill.style.width = '0%';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Enviar arquivo →';
                setTimeout(() => {
                    progressBar.style.display = 'none';
                }, 1000);
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
    """Send email notification for spreadsheet upload"""
    if not MAILGUN_API_KEY:
        print("Mailgun API key not configured")
        return False
    
    email_content = f"""
Nova planilha enviada ao SecureBox:

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
    
    # Validate file type
    allowed_extensions = {'.csv', '.xls', '.xlsx'}
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail="Tipo de arquivo não permitido. Apenas planilhas CSV, XLS e XLSX são aceitas."
        )
    
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        
        # Upload to S3
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            filename,
            ExtraArgs={'ContentType': file.content_type or 'application/octet-stream'}
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