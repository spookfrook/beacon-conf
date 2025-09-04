#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-multipart",
#     "aiofiles",
# ]
# ///

import os
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
import json

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
CHUNKS_DIR = Path("chunks")
CHUNKS_DIR.mkdir(exist_ok=True)

# Upload limits
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
CHUNK_SIZE = 1 * 1024 * 1024  # 1MB chunks

# HTML with chunked upload support
CHUNKED_UPLOAD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Robust File Upload</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .upload-area {
            border: 2px dashed #4285f4;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f8f9fa;
        }
        .upload-area:hover {
            border-color: #1a73e8;
            background: #e8f0fe;
        }
        .upload-area.dragging {
            border-color: #1a73e8;
            background: #e8f0fe;
        }
        input[type="file"] {
            display: none;
        }
        .file-info {
            margin: 20px 0;
            padding: 15px;
            background: #e8f0fe;
            border-radius: 5px;
            display: none;
        }
        .upload-btn {
            background: #4285f4;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
            display: none;
        }
        .upload-btn:hover {
            background: #1a73e8;
        }
        .upload-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .progress-container {
            margin: 20px 0;
            display: none;
        }
        .progress {
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #4285f4, #1a73e8);
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
            font-weight: bold;
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info {
            background: #cce5ff;
            color: #004085;
            border: 1px solid #b8daff;
        }
        .stats {
            margin-top: 20px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Robust File Upload</h1>
        
        <div class="upload-area" id="uploadArea">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <p style="margin-top: 15px; color: #666;">Drop files here or click to select</p>
            <p style="font-size: 14px; color: #999;">Maximum file size: 500MB</p>
            <input type="file" id="fileInput" multiple>
        </div>
        
        <div class="file-info" id="fileInfo">
            <strong>Selected file:</strong> <span id="fileName"></span> 
            (<span id="fileSize"></span>)
        </div>
        
        <button class="upload-btn" id="uploadBtn">Upload File</button>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress">
                <div class="progress-bar" id="progressBar">0%</div>
            </div>
            <div class="stats" id="stats"></div>
        </div>
        
        <div class="status" id="status"></div>
    </div>

    <script>
        const CHUNK_SIZE = 1 * 1024 * 1024; // 1MB chunks
        const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB
        
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const uploadBtn = document.getElementById('uploadBtn');
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const status = document.getElementById('status');
        const stats = document.getElementById('stats');
        
        let selectedFile = null;
        
        // Click to select
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragging');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragging');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragging');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
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
            if (file.size > MAX_FILE_SIZE) {
                showStatus('error', `File too large. Maximum size is ${formatSize(MAX_FILE_SIZE)}`);
                return;
            }
            
            selectedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatSize(file.size);
            fileInfo.style.display = 'block';
            uploadBtn.style.display = 'inline-block';
            status.style.display = 'none';
        }
        
        function formatSize(bytes) {
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            if (bytes === 0) return '0 Bytes';
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function showStatus(type, message) {
            status.className = 'status ' + type;
            status.textContent = message;
            status.style.display = 'block';
        }
        
        // Upload button click
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            uploadBtn.disabled = true;
            progressContainer.style.display = 'block';
            status.style.display = 'none';
            
            try {
                // For small files, use simple upload
                if (selectedFile.size < 10 * 1024 * 1024) { // 10MB
                    await simpleUpload(selectedFile);
                } else {
                    await chunkedUpload(selectedFile);
                }
            } catch (error) {
                showStatus('error', `Upload failed: ${error.message}`);
            } finally {
                uploadBtn.disabled = false;
            }
        });
        
        async function simpleUpload(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    progressBar.textContent = percent + '%';
                }
            });
            
            return new Promise((resolve, reject) => {
                xhr.addEventListener('load', () => {
                    if (xhr.status === 200) {
                        showStatus('success', 'File uploaded successfully!');
                        resolve();
                    } else {
                        reject(new Error(`Server error: ${xhr.status}`));
                    }
                });
                
                xhr.addEventListener('error', () => {
                    reject(new Error('Network error'));
                });
                
                xhr.open('POST', '/upload/simple');
                xhr.send(formData);
            });
        }
        
        async function chunkedUpload(file) {
            const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
            const uploadId = generateId();
            let startTime = Date.now();
            
            for (let i = 0; i < totalChunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                const chunk = file.slice(start, end);
                
                const formData = new FormData();
                formData.append('chunk', chunk);
                formData.append('filename', file.name);
                formData.append('upload_id', uploadId);
                formData.append('chunk_index', i);
                formData.append('total_chunks', totalChunks);
                
                try {
                    const response = await fetch('/upload/chunk', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error(`Chunk ${i + 1} upload failed`);
                    }
                    
                    // Update progress
                    const percent = Math.round(((i + 1) / totalChunks) * 100);
                    progressBar.style.width = percent + '%';
                    progressBar.textContent = percent + '%';
                    
                    // Update stats
                    const elapsed = (Date.now() - startTime) / 1000;
                    const speed = (end / elapsed) / (1024 * 1024); // MB/s
                    const remaining = ((file.size - end) / (end / elapsed)) / 60; // minutes
                    
                    stats.textContent = `Speed: ${speed.toFixed(2)} MB/s | ` +
                        `Remaining: ${remaining.toFixed(1)} min`;
                    
                } catch (error) {
                    throw error;
                }
            }
            
            // Complete the upload
            const response = await fetch('/upload/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    upload_id: uploadId,
                    filename: file.name,
                    total_chunks: totalChunks
                })
            });
            
            if (response.ok) {
                showStatus('success', 'File uploaded successfully!');
            } else {
                throw new Error('Failed to complete upload');
            }
        }
        
        function generateId() {
            return Date.now().toString(36) + Math.random().toString(36).substr(2);
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return CHUNKED_UPLOAD_HTML

@app.post("/upload/simple")
async def simple_upload(file: UploadFile = File(...)):
    """Simple upload for small files"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Validate file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        extension = Path(file.filename).suffix
        new_filename = f"{timestamp}_{file_id}{extension}"
        
        # Save file
        file_path = UPLOAD_DIR / new_filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(contents)
        
        return {
            "filename": new_filename,
            "original_name": file.filename,
            "size": len(contents),
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/chunk")
async def chunked_upload(
    chunk: UploadFile = File(...),
    filename: str = Form(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...)
):
    """Handle chunked file upload"""
    try:
        # Create directory for this upload
        upload_dir = CHUNKS_DIR / upload_id
        upload_dir.mkdir(exist_ok=True)
        
        # Save chunk
        chunk_path = upload_dir / f"chunk_{chunk_index}"
        async with aiofiles.open(chunk_path, 'wb') as f:
            content = await chunk.read()
            await f.write(content)
        
        return {
            "status": "chunk_received",
            "chunk_index": chunk_index,
            "total_chunks": total_chunks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/complete")
async def complete_upload(request: Request):
    """Complete the chunked upload by combining all chunks"""
    try:
        data = await request.json()
        upload_id = data['upload_id']
        filename = data['filename']
        total_chunks = data['total_chunks']
        
        # Generate final filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        extension = Path(filename).suffix
        new_filename = f"{timestamp}_{file_id}{extension}"
        final_path = UPLOAD_DIR / new_filename
        
        # Combine chunks
        upload_dir = CHUNKS_DIR / upload_id
        
        async with aiofiles.open(final_path, 'wb') as final_file:
            for i in range(total_chunks):
                chunk_path = upload_dir / f"chunk_{i}"
                if not chunk_path.exists():
                    raise HTTPException(status_code=400, detail=f"Missing chunk {i}")
                
                async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                    content = await chunk_file.read()
                    await final_file.write(content)
                
                # Remove chunk after combining
                chunk_path.unlink()
        
        # Remove upload directory
        upload_dir.rmdir()
        
        # Get file size
        file_size = final_path.stat().st_size
        
        return {
            "filename": new_filename,
            "original_name": filename,
            "size": file_size,
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    return {"message": "Server is running", "time": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting robust upload server...")
    print(f"Uploads will be saved to: {UPLOAD_DIR.absolute()}")
    print(f"Temporary chunks will be saved to: {CHUNKS_DIR.absolute()}")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")