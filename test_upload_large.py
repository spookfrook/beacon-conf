#!/usr/bin/env python
import requests
import os

# Test script to upload the large CSV file
base_url = "http://localhost:8000"

# Step 1: Login with email
print("Step 1: Validating email...")
login_response = requests.post(
    f"{base_url}/validate-email",
    data={"email": "gabriel@emptor.io"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code} - {login_response.text}")
    exit(1)

token = login_response.json()["token"]
print(f"Login successful! Token: {token[:8]}...")

# Step 2: Upload the file
print("\nStep 2: Uploading test_data.csv...")
with open("large_test_data.csv", "rb") as f:
    files = {"file": ("large_test_data.csv", f, "text/csv")}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        upload_response = requests.post(
            f"{base_url}/upload-file",
            files=files,
            headers=headers
        )
        
        print(f"Upload response status: {upload_response.status_code}")
        print(f"Upload response: {upload_response.text}")
        
        if upload_response.status_code == 200:
            print("\nUpload successful!")
        else:
            print(f"\nUpload failed with status {upload_response.status_code}")
            
    except Exception as e:
        print(f"Upload error: {e}")