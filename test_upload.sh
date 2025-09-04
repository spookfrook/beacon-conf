#!/bin/bash

echo "=== File Upload Test Script ==="
echo

# Create test files if they don't exist
if [ ! -f "test_small.txt" ]; then
    echo "Creating test_small.txt (1KB)..."
    head -c 1024 /dev/urandom | base64 > test_small.txt
fi

if [ ! -f "test_medium.csv" ]; then
    echo "Creating test_medium.csv (5MB)..."
    echo "id,name,value,timestamp" > test_medium.csv
    for i in {1..100000}; do
        echo "$i,Test User $i,$RANDOM,$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> test_medium.csv
    done
fi

echo
echo "=== Testing Simple Upload Server (port 8001) ==="
echo

# Test 1: Simple upload
echo "Test 1: Simple file upload"
curl -X POST http://localhost:8001/upload \
  -F "file=@test_small.txt" \
  -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\n"

echo
echo "Test 2: CSV file upload"
curl -X POST http://localhost:8001/upload \
  -F "file=@test_medium.csv" \
  -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\n"

echo
echo "=== Testing Robust Upload Server (port 8002) ==="
echo

# Test 3: Simple endpoint on robust server
echo "Test 3: Simple upload endpoint"
curl -X POST http://localhost:8002/upload/simple \
  -F "file=@test_small.txt" \
  -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\n"

echo
echo "Test 4: Health check"
curl http://localhost:8002/health

echo
echo
echo "=== Testing Original Server (port 8000) ==="
echo

# First get auth token
echo "Test 5: Validate email"
RESPONSE=$(curl -s -X POST http://localhost:8000/validate-email \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=gabriel@emptor.io")
TOKEN=$(echo $RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    echo "Got token: $TOKEN"
    echo
    echo "Test 6: Upload with authentication"
    curl -X POST http://localhost:8000/upload-file \
      -H "Authorization: Bearer $TOKEN" \
      -F "file=@test_small.txt" \
      -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\n"
else
    echo "Failed to get auth token"
fi

echo
echo "=== Manual CURL Examples ==="
echo
echo "# Simple upload (no auth required):"
echo "curl -X POST http://localhost:8001/upload -F 'file=@yourfile.csv'"
echo
echo "# With progress bar:"
echo "curl -X POST http://localhost:8001/upload -F 'file=@yourfile.csv' --progress-bar | cat"
echo
echo "# Robust upload server:"
echo "curl -X POST http://localhost:8002/upload/simple -F 'file=@yourfile.xlsx'"
echo
echo "# Original server with auth:"
echo "# Step 1: Get token"
echo "curl -X POST http://localhost:8000/validate-email -d 'email=your@email.com'"
echo "# Step 2: Upload with token"
echo "curl -X POST http://localhost:8000/upload-file -H 'Authorization: Bearer YOUR_TOKEN' -F 'file=@yourfile.csv'"