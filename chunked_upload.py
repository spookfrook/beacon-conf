#!/usr/bin/env python
"""
Alternative upload handler using chunked uploads for large files
"""
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Simple chunked upload endpoint
@app.post("/chunked-upload")
async def chunked_upload(
    chunk: UploadFile = File(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...)
):
    """Handle file upload in chunks"""
    print(f"Received chunk {chunk_number}/{total_chunks} for {filename}")
    
    # Save chunk to temp directory
    temp_dir = "/tmp/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, f"{filename}.part{chunk_number}")
    
    # Write chunk
    with open(chunk_path, "wb") as f:
        content = await chunk.read()
        f.write(content)
    
    # If this is the last chunk, combine all parts
    if chunk_number == total_chunks:
        final_path = os.path.join(temp_dir, filename)
        with open(final_path, "wb") as final_file:
            for i in range(1, total_chunks + 1):
                part_path = os.path.join(temp_dir, f"{filename}.part{i}")
                with open(part_path, "rb") as part_file:
                    final_file.write(part_file.read())
                os.remove(part_path)  # Clean up part file
        
        return {"status": "complete", "filename": filename}
    
    return {"status": "chunk_received", "chunk": chunk_number}

@app.get("/")
async def test_page():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Chunked Upload Test</title>
</head>
<body>
    <h1>Chunked Upload Test</h1>
    <input type="file" id="fileInput">
    <button onclick="uploadFile()">Upload</button>
    <div id="progress"></div>
    
    <script>
    async function uploadFile() {
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];
        if (!file) return;
        
        const chunkSize = 1024 * 1024; // 1MB chunks
        const totalChunks = Math.ceil(file.size / chunkSize);
        
        for (let i = 0; i < totalChunks; i++) {
            const start = i * chunkSize;
            const end = Math.min(start + chunkSize, file.size);
            const chunk = file.slice(start, end);
            
            const formData = new FormData();
            formData.append('chunk', chunk);
            formData.append('chunk_number', i + 1);
            formData.append('total_chunks', totalChunks);
            formData.append('filename', file.name);
            
            try {
                const response = await fetch('/chunked-upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) throw new Error('Upload failed');
                
                const progress = ((i + 1) / totalChunks * 100).toFixed(2);
                document.getElementById('progress').textContent = `Progress: ${progress}%`;
            } catch (error) {
                console.error('Error uploading chunk:', error);
                document.getElementById('progress').textContent = 'Upload failed!';
                return;
            }
        }
        
        document.getElementById('progress').textContent = 'Upload complete!';
    }
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)