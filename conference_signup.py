#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-multipart",
#     "jinja2",
#     "peewee",
#     "livekit",
#     "livekit-api",
#     "aiofiles",
#     "httpx",
# ]
# ///

import os
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import base64
import re

import peewee as pw
from fastapi import FastAPI, Form, Request, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import aiofiles
from livekit import api
import httpx

# Database initialization
db = pw.SqliteDatabase('conference_signups.db')

class BaseModelDB(pw.Model):
    class Meta:
        database = db

class Signup(BaseModelDB):
    id = pw.CharField(primary_key=True, default=lambda: str(uuid.uuid4()))
    name = pw.CharField(null=True)  # Stores the referee name
    email = pw.CharField(null=True)
    phone = pw.CharField(null=True)
    candidate = pw.CharField(null=True)
    description = pw.TextField(null=True)
    voice_memo_path = pw.CharField(null=True)
    talk_to_sol = pw.BooleanField(default=False)
    want_report_example = pw.BooleanField(default=False)
    created_at = pw.DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = "signups"

# Create tables
db.connect()
db.create_tables([Signup])

# Ensure new columns exist if database was created before updates
existing_columns = [column.name for column in db.get_columns('signups')]
if 'candidate' not in existing_columns:
    db.execute_sql("ALTER TABLE signups ADD COLUMN candidate TEXT")

# FastAPI app
app = FastAPI()

# Create templates directory and template file
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

# HTML template content
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sol by Emptor - Conference Registration</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #7B3FF2 0%, #4B1B8C 100%);
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
            max-width: 500px;
            width: 100%;
            padding: 40px;
        }
        
        @media (orientation: landscape) and (min-width: 768px) {
            .container {
                max-width: 900px;
            }
            
            form {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
            }
            
            .left-column {
                grid-column: 1;
            }
            
            .right-column {
                grid-column: 2;
            }
            
            .submit-btn {
                grid-column: 1 / -1;
            }
            
            .success-message, .error-message {
                grid-column: 1 / -1;
            }
        }
        
        .logo {
            text-align: center;
            margin-bottom: 10px;
        }
        
        .logo h1 {
            font-size: 48px;
            color: #7B3FF2;
            margin-bottom: 10px;
        }
        
        .logo .tagline {
            color: #666;
            font-size: 16px;
        }
        
        .sol-mascot {
            width: 150px;
            height: 150px;
            margin: 0 auto 20px;
            display: block;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        
        input[type="text"],
        input[type="email"],
        input[type="tel"],
        textarea {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus,
        input[type="email"]:focus,
        input[type="tel"]:focus,
        textarea:focus {
            outline: none;
            border-color: #7B3FF2;
        }
        
        textarea {
            resize: vertical;
            min-height: 100px;
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            margin: 30px 0;
            padding: 20px;
            background: #FEFEFF;
            border-radius: 12px;
            cursor: pointer;
            position: relative;
        }
        
        .checkbox-group input[type="checkbox"] {
            width: 24px;
            height: 24px;
            margin-right: 16px;
            cursor: pointer;
            flex-shrink: 0;
        }
        
        .checkbox-group:hover {
            background: #F0EBFF;
        }
        
        .checkbox-group:active {
            background: #E8E0FF;
        }
        
        .checkbox-group label {
            margin: 0;
            cursor: pointer;
            color: #7B3FF2;
            font-weight: 600;
        }
        
        .checkbox-with-animation {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }
        
        .checkbox-content {
            display: flex;
            align-items: center;
            flex: 1;
        }
        
        .mini-sol {
            width: 80px;
            height: 80px;
            margin-left: 10px;
            -webkit-mask-image: -webkit-radial-gradient(white, black);
            mask-image: radial-gradient(white, black);
        }
        
        video {
            background: transparent;
        }
        
        .submit-btn {
            width: 100%;
            padding: 16px;
            background: #7B3FF2;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .submit-btn:hover {
            background: #6B2FE2;
        }
        
        .submit-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .success-message {
            display: none;
            padding: 20px;
            background: #4CAF50;
            color: white;
            border-radius: 8px;
            text-align: center;
            margin-top: 20px;
        }
        
        .error-message {
            display: none;
            padding: 20px;
            background: #f44336;
            color: white;
            border-radius: 8px;
            text-align: center;
            margin-top: 20px;
        }
        
        .sol-feature {
            background: #FFF8E1;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
        
        .voice-controls {
            margin-top: 10px;
        }
        
        .voice-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            background: #FFF;
            border: 2px solid #7B3FF2;
            border-radius: 8px;
            color: #7B3FF2;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .voice-btn:hover:not(:disabled) {
            background: #F0EBFF;
        }
        
        .voice-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .voice-btn.recording {
            background: #FF4444;
            color: white;
            border-color: #FF4444;
        }
        
        .voice-btn.recording:hover:not(:disabled) {
            background: #CC0000;
            border-color: #CC0000;
        }
        
        .record-icon {
            font-size: 18px;
        }
        
        .recording-status {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            margin-left: 16px;
            color: #FF4444;
            font-weight: 500;
        }
        
        .recording-dot {
            width: 10px;
            height: 10px;
            background: #FF4444;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.2);
                opacity: 0.7;
            }
            100% {
                transform: scale(1);
                opacity: 1;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
        </div>
        
        <form id="signupForm">
            <div class="left-column">
                <div class="form-group">
                    <label for="referee">Referee *</label>
                    <input type="text" id="referee" name="referee" required>
                </div>
                
                <div class="form-group">
                    <label for="email">Correo electrónico</label>
                    <input type="email" id="email" name="email">
                </div>
                
                <div class="form-group">
                    <label for="phone">Teléfono *</label>
                    <input type="tel" id="phone" name="phone" required placeholder="+51 999 999 999">
                </div>

                <div class="form-group">
                    <label for="candidate">Candidato *</label>
                    <input type="text" id="candidate" name="candidate" required>
                </div>
                
                <div class="form-group">
                    <label for="description">Descripción (opcional)</label>
                    <div style="position: relative;">
                        <textarea id="description" name="description" placeholder="Cuéntanos sobre ti o tu empresa..."></textarea>
                        <div class="voice-controls">
                            <button type="button" id="recordButton" class="voice-btn">
                                <span class="record-icon">🎤</span>
                                <span class="record-text">Grabar</span>
                            </button>
                            <div id="recordingStatus" class="recording-status" style="display: none;">
                                <span class="recording-dot"></span>
                                <span>Grabando...</span>
                                <span id="recordingTime">0:00</span>
                            </div>
                            <audio id="audioPlayback" controls style="display: none; margin-top: 10px; width: 100%;"></audio>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="right-column">
                <div class="checkbox-group">
                    <div class="checkbox-with-animation">
                        <div class="checkbox-content">
                            <input type="checkbox" id="talk_to_sol" name="talk_to_sol">
                            <label for="talk_to_sol">¡Quiero hablar con Sol ahora!</label>
                        </div>
                        <video class="mini-sol" autoplay loop muted playsinline>
                            <source src="https://www.emptor.io/assets/sol/SOL%20LOOPS/GL01_PHONE.webm" type="video/webm">
                        </video>
                    </div>
                </div>
                
                <div class="checkbox-group">
                    <div class="checkbox-with-animation">
                        <div class="checkbox-content">
                            <input type="checkbox" id="want_report_example" name="want_report_example">
                            <label for="want_report_example">Quiero recibir un ejemplo de reporte de antecedentes</label>
                        </div>
                        <video class="mini-sol" autoplay loop muted playsinline>
                            <source src="https://www.emptor.io/assets/sol/SOL%20LOOPS/SOL_GL04_DETECTIVE.webm" type="video/webm">
                        </video>
                    </div>
                </div>
                
                <div class="sol-feature">
                    <strong>¿Qué hace Sol por ti?</strong><br>
                    • Procesa más candidatos en menos tiempo<br>
                    • Personaliza la contratación sin ser experto en tecnología<br>
                    • Enfoca tu energía en las relaciones humanas
                </div>
            </div>
            
            <button type="submit" class="submit-btn">Registrarme</button>
            
            <div class="success-message" id="successMessage">
                ¡Registro exitoso! {% if show_sol_message %}Sol te llamará en unos segundos...{% endif %}
            </div>
            
            <div class="error-message" id="errorMessage">
                Error al registrar. Por favor intenta nuevamente.
            </div>
        </form>
    </div>
    
    <!-- Audio recording polyfill for iOS compatibility -->
    <script src="https://cdn.jsdelivr.net/npm/recordrtc@5.6.2/RecordRTC.min.js"></script>
    <script>
        // We'll use RecordRTC which has better iOS support
        
        // Voice recording functionality
        let recorder;
        let recordingStartTime;
        let recordingInterval;
        let audioBlob;
        let audioStream;
        
        const recordButton = document.getElementById('recordButton');
        const recordingStatus = document.getElementById('recordingStatus');
        const recordingTime = document.getElementById('recordingTime');
        const audioPlayback = document.getElementById('audioPlayback');
        const descriptionTextarea = document.getElementById('description');
        
        // Check for microphone permissions on page load
        async function checkMicrophonePermissions() {
            try {
                // iOS doesn't support permissions.query for microphone
                if (navigator.permissions && navigator.permissions.query) {
                    const result = await navigator.permissions.query({ name: 'microphone' });
                    return result.state;
                }
                return 'prompt';
            } catch (error) {
                // Permissions API might not be available
                return 'prompt';
            }
        }
        
        // Check if getUserMedia is available
        function checkAudioSupport() {
            // For iOS Safari, we need to check differently
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                return true;
            }
            
            // Fallback for older browsers
            navigator.getUserMedia = navigator.getUserMedia ||
                                   navigator.webkitGetUserMedia ||
                                   navigator.mozGetUserMedia ||
                                   navigator.msGetUserMedia;
            
            return !!navigator.getUserMedia;
        }
        
        recordButton.addEventListener('click', async () => {
            if (!recorder || (recorder && recorder.getState() === 'stopped')) {
                // Start recording
                try {
                    // Update button to show requesting permissions
                    recordButton.disabled = true;
                    recordButton.querySelector('.record-text').textContent = 'Solicitando permisos...';
                    
                    // Request audio - this works on iOS Safari
                    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    
                    // Re-enable button
                    recordButton.disabled = false;
                    
                    // Use RecordRTC for cross-browser compatibility including iOS
                    recorder = new RecordRTC(audioStream, {
                        type: 'audio',
                        mimeType: 'audio/wav',
                        recorderType: RecordRTC.StereoAudioRecorder,
                        numberOfAudioChannels: 1,
                        desiredSampRate: 16000
                    });
                    
                    recorder.startRecording();
                    recordingStartTime = Date.now();
                    
                    // Update UI
                    recordButton.classList.add('recording');
                    recordButton.querySelector('.record-text').textContent = 'Detener';
                    recordingStatus.style.display = 'inline-flex';
                    
                    // Update recording time
                    recordingInterval = setInterval(() => {
                        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                        const minutes = Math.floor(elapsed / 60);
                        const seconds = elapsed % 60;
                        recordingTime.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    }, 1000);
                    
                } catch (error) {
                    console.error('Error accessing microphone:', error);
                    recordButton.disabled = false;
                    recordButton.querySelector('.record-text').textContent = 'Grabar';
                    
                    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                        alert('Acceso al micrófono denegado. Por favor, permite el acceso al micrófono cuando el navegador lo solicite.');
                    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                        alert('No se encontró ningún micrófono. Por favor, conecta un micrófono y vuelve a intentar.');
                    } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
                        alert('El micrófono está siendo usado por otra aplicación. Por favor, cierra otras aplicaciones que puedan estar usando el micrófono.');
                    } else {
                        alert('Error al acceder al micrófono. Por favor, asegúrate de estar usando HTTPS y de que tu navegador soporta grabación de audio.');
                    }
                }
            } else {
                // Stop recording
                recorder.stopRecording(function() {
                    audioBlob = recorder.getBlob();
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioPlayback.src = audioUrl;
                    audioPlayback.style.display = 'block';
                    
                    // Stop all tracks
                    if (audioStream) {
                        audioStream.getTracks().forEach(track => track.stop());
                    }
                    
                    // Destroy recorder to free up resources
                    recorder.destroy();
                    recorder = null;
                });
                
                clearInterval(recordingInterval);
                
                // Update UI
                recordButton.classList.remove('recording');
                recordButton.querySelector('.record-text').textContent = 'Grabar';
                recordingStatus.style.display = 'none';
            }
        });
        
        // Make checkbox groups clickable anywhere
        document.querySelectorAll('.checkbox-group').forEach(group => {
            group.addEventListener('click', (e) => {
                // Don't toggle if clicking directly on checkbox or label
                if (e.target.type !== 'checkbox' && e.target.tagName !== 'LABEL') {
                    const checkbox = group.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                }
            });
        });
        
        document.getElementById('signupForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.querySelector('.submit-btn');
            const successMsg = document.getElementById('successMessage');
            const errorMsg = document.getElementById('errorMessage');
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Registrando...';
            
            const formData = new FormData(e.target);
            
            // Add audio blob if exists
            if (audioBlob) {
                formData.append('voice_memo', audioBlob, 'voice_memo.wav');
            }
            
            try {
                const response = await fetch('/signup', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    e.target.reset();
                    
                    // Reset audio recording UI
                    audioPlayback.style.display = 'none';
                    audioPlayback.src = '';
                    audioBlob = null;
                    audioChunks = [];
                    
                    successMsg.style.display = 'block';
                    errorMsg.style.display = 'none';
                    
                    if (result.sol_call_initiated) {
                        successMsg.textContent = '¡Registro exitoso! Sol te llamará en unos segundos...';
                    } else {
                        successMsg.textContent = '¡Registro exitoso!';
                    }
                    
                    setTimeout(() => {
                        successMsg.style.display = 'none';
                    }, 5000);
                } else {
                    throw new Error('Registration failed');
                }
            } catch (error) {
                errorMsg.style.display = 'block';
                successMsg.style.display = 'none';
                
                setTimeout(() => {
                    errorMsg.style.display = 'none';
                }, 5000);
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Registrarme';
            }
        });
    </script>
</body>
</html>
"""

# Save template
template_file = templates_dir / "index.html"
# Commented out to prevent overwriting manual changes
# template_file.write_text(html_template)

templates = Jinja2Templates(directory=str(templates_dir))

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "ST_tUrKeAyozKMS")

# Mailgun configuration
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = "solmail.emptor-cdn.com"
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

async def send_signup_email(signup: Signup):
    """Send email notification for new signup using Mailgun"""
    if not MAILGUN_API_KEY:
        print("Mailgun API key not configured")
        return False
    
    # Prepare email content
    email_content = f"""
Nueva inscripción en conferencia:

Nombre: {signup.name}
Email: {signup.email or 'No proporcionado'}
Teléfono: {signup.phone}
Descripción: {signup.description or 'No proporcionada'}

Opciones seleccionadas:
- Hablar con Sol: {'Sí' if signup.talk_to_sol else 'No'}
- Quiere ejemplo de reporte: {'Sí' if signup.want_report_example else 'No'}

Fecha de registro: {signup.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # Add voice memo link if exists
    if signup.voice_memo_path:
        # Generate a secure token for the voice memo
        token = base64.urlsafe_b64encode(f"{signup.id}:{signup.created_at.timestamp()}".encode()).decode()
        voice_url = f"{APP_BASE_URL}/voice/{signup.id}?token={token}"
        email_content += f"\nMemo de voz: {voice_url} (válido por 24 horas)"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": f"Sol Conference <noreply@{MAILGUN_DOMAIN}>",
                    "to": "gabriel@emptor.io",
                    "subject": f"Nueva inscripción: {signup.name}",
                    "text": email_content
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

async def create_sol_call(signup: Signup):
    """Creates a SIP call with Sol for the signup"""
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        print("LiveKit credentials not configured")
        return None

    livekit_api = api.LiveKitAPI(
        LIVEKIT_URL,
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET
    )
    # Use fixed phone number for Sol
    sol_phone_number = "+56982293592"
    
    # Prepare string-safe identifiers for room/call metadata
    referee_value = signup.name or "referee"

    def _clean_label(value: str, fallback: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 ]+", "", value or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or fallback

    referee_label = _clean_label(referee_value, "referee")
    # Use the user's phone if provided, otherwise use a random identifier
    user_phone = re.sub(r"\D", "", signup.phone or "")
    phone_digits = user_phone if user_phone else str(uuid.uuid4())[:8]

    random_suffix = uuid.uuid4()
    room_name = (
        f"referenceemptorio-{referee_label}_+{phone_digits}-room-m-{random_suffix}"
    )

    participant_identity = f"identity-sip-{phone_digits}"
    participant_name = referee_label
    # Create SIP participant request
    request = api.CreateSIPParticipantRequest(
        sip_trunk_id=SIP_TRUNK_ID,
        sip_call_to=sol_phone_number,
        room_name=room_name,
        participant_identity=participant_identity,
        participant_name=participant_name,
    )
    
    try:
        # Make request to create SIP participant
        participant = await livekit_api.sip.create_sip_participant(request)
        await livekit_api.aclose()
        return participant
    except Exception as e:
        print(f"Error creating Sol call: {e}")
        await livekit_api.aclose()
        return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video", response_class=HTMLResponse)
async def video(request: Request):
    return templates.TemplateResponse("video.html", {"request": request})

@app.get("/reference", response_class=HTMLResponse)
async def reference(request: Request):
    return templates.TemplateResponse("reference.html", {"request": request})

@app.get("/voice/{signup_id}")
async def get_voice_memo(signup_id: str, token: str):
    """Serve voice memo with 24-hour expiration check"""
    try:
        # Get the signup
        signup = Signup.get(Signup.id == signup_id)
        
        if not signup.voice_memo_path:
            return HTMLResponse("No voice memo found", status_code=404)
        
        # Verify token and check expiration
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            stored_id, timestamp = decoded.split(":")
            created_time = float(timestamp)
            
            # Check if token matches and is less than 24 hours old
            if stored_id != signup_id or (datetime.now().timestamp() - created_time) > 86400:
                return HTMLResponse("Link expired or invalid", status_code=403)
        except:
            return HTMLResponse("Invalid token", status_code=403)
        
        # Serve the file
        return FileResponse(
            signup.voice_memo_path,
            media_type="audio/wav",
            filename=f"voice_memo_{signup.name.replace(' ', '_')}.wav"
        )
    except Signup.DoesNotExist:
        return HTMLResponse("Signup not found", status_code=404)

@app.post("/signup")
async def signup(
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    description: str = Form(None),
    talk_to_sol: bool = Form(False),
    want_report_example: bool = Form(False),
    voice_memo: UploadFile = File(None)
):
    voice_memo_path = None
    
    # Save voice memo if provided
    if voice_memo and voice_memo.filename:
        # Create voice_memos directory if it doesn't exist
        voice_memos_dir = Path(__file__).parent / "voice_memos"
        voice_memos_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_extension = voice_memo.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = voice_memos_dir / unique_filename
        
        # Save the file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await voice_memo.read()
            await f.write(content)
        
        voice_memo_path = str(file_path)
    
    # Save signup to database
    signup = Signup.create(
        name=name or None,
        email=email or None,
        phone=phone or None,
        candidate=None,
        description=description,
        voice_memo_path=voice_memo_path,
        talk_to_sol=talk_to_sol,
        want_report_example=want_report_example
    )
    
    sol_call_initiated = False
    
    # If user wants to talk to Sol, initiate the call
    if talk_to_sol:
        call_result = await create_sol_call(signup)
        sol_call_initiated = call_result is not None
    
    # Send email notification
    await send_signup_email(signup)
    
    return {
        "success": True,
        "id": signup.id,
        "sol_call_initiated": sol_call_initiated
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
