#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-multipart",
# ]
# ///

import os
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Simple HTML upload form
UPLOAD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Simple File Upload</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
        }
        .upload-form {
            border: 2px dashed #ccc;
            padding: 40px;
            text-align: center;
            border-radius: 10px;
        }
        input[type="file"] {
            margin: 20px 0;
        }
        button {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #45a049;
        }
        .status {
            margin-top: 20px;
            padding: 10px;
            border-radius: 5px;
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
        .progress {
            width: 100%;
            height: 20px;
            background: #f0f0f0;
            border-radius: 10px;
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background: #4CAF50;
            border-radius: 10px;
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <h1>Simple File Upload</h1>
    <div class="upload-form">
        <form id="uploadForm" enctype="multipart/form-data">
            <p>Select a file to upload:</p>
            <input type="file" name="file" id="fileInput" accept=".csv,.xls,.xlsx,.txt,.pdf" required>
            <br>
            <button type="submit">Upload File</button>
        </form>
        <div class="progress" id="progressBar">
            <div class="progress-bar" id="progressBarFill"></div>
        </div>
        <div id="status"></div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            const status = document.getElementById('status');
            const progressBar = document.getElementById('progressBar');
            const progressBarFill = document.getElementById('progressBarFill');
            
            if (!file) {
                status.className = 'status error';
                status.textContent = 'Please select a file';
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            // Show progress bar
            progressBar.style.display = 'block';
            progressBarFill.style.width = '0%';
            status.className = '';
            status.textContent = 'Uploading...';
            
            try {
                // Using fetch API for simplicity
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    progressBarFill.style.width = '100%';
                    status.className = 'status success';
                    status.textContent = `Success! File uploaded: ${result.filename}`;
                    fileInput.value = '';
                } else {
                    const error = await response.json();
                    status.className = 'status error';
                    status.textContent = `Error: ${error.detail}`;
                }
            } catch (error) {
                status.className = 'status error';
                status.textContent = `Error: ${error.message}`;
            } finally {
                setTimeout(() => {
                    progressBar.style.display = 'none';
                }, 2000);
            }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return UPLOAD_HTML

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Simple file upload endpoint"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        extension = Path(file.filename).suffix
        new_filename = f"{timestamp}_{file_id}{extension}"
        
        # Save file
        file_path = UPLOAD_DIR / new_filename
        
        # Read and write in chunks to handle large files
        CHUNK_SIZE = 1024 * 1024  # 1MB chunks
        
        with open(file_path, "wb") as f:
            while chunk := await file.read(CHUNK_SIZE):
                f.write(chunk)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        return {
            "filename": new_filename,
            "original_name": file.filename,
            "size": file_size,
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting simple upload server...")
    print(f"Uploads will be saved to: {UPLOAD_DIR.absolute()}")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")