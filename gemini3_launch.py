import cv2
import time
import json
import os
import pyttsx3
import threading
from google import genai
from google.genai import types
from dotenv import load_dotenv
from twilio.rest import Client

# 1. SETUP
load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3-flash-preview" # Or gemini-3-flash-preview

# Twilio (Optional)
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth = os.getenv("TWILIO_AUTH_TOKEN")
twilio_from = os.getenv("TWILIO_PHONE_NUMBER")
twilio_to = os.getenv("MY_PHONE_NUMBER")
sms_client = Client(twilio_sid, twilio_auth) if twilio_sid else None

# 2. ROBUST AUDIO SYSTEM
def speak_warning(text):
    """
    Re-initializes the engine every time to prevent crashing/freezing.
    Runs in a separate thread so it doesn't block the video.
    """
    def run_speech():
        try:
            # Re-init engine locally for stability
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.say(f"Alert! {text}")
            engine.runAndWait()
            engine.stop()
        except:
            pass # Ignore audio errors if system is busy
    
    t = threading.Thread(target=run_speech)
    t.start()

# 3. INCIDENT LOGGING SYSTEM
def log_incident(issue_text):
    """Saves the incident to a permanent history file."""
    log_file = "incident_log.json"
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "issue": issue_text,
        "location": "Camera-01"
    }
    
    # Load existing logs or start new
    history = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                history = json.load(f)
        except:
            history = []
    
    # Add new entry
    history.append(entry)
    
    # Save back
    with open(log_file, "w") as f:
        json.dump(history, f, indent=4)

# 4. SMS ALERT (With Cooldown)
last_sms_time = 0
def send_sms_alert(issue_text):
    global last_sms_time
    if time.time() - last_sms_time < 60: return 
    if sms_client:
        try:
            sms_client.messages.create(
                body=f"🚨 FACTORY ALERT: {issue_text}",
                from_=twilio_from, to=twilio_to
            )
            print("📱 SMS SENT")
            last_sms_time = time.time()
        except: pass

# 5. MAIN ANALYSIS LOOP
def analyze_frame(frame):
    # Resize to save bandwidth
    frame_resized = cv2.resize(frame, (640, 480))
    _, buffer = cv2.imencode('.jpg', frame_resized)
    image_bytes = buffer.tobytes()
    
    prompt = "Factory Safety Officer. Analyze image. JSON ONLY: {'status': 'SAFE'/'DANGER', 'issue': 'short description', 'confidence': 0-100}"

    print(f"🚀 Analyzing...", end=" ")
    try:
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        
        text_data = response.text.replace("```json", "").replace("```", "").strip()
        print(f"✅ {text_data}")
        
        # Save Current Status (For Dashboard Live View)
        with open("status.json", "w") as f:
            f.write(text_data)
        cv2.imwrite("current_frame.jpg", frame_resized)

        # Process Logic
        data = json.loads(text_data)
        if data.get("status") == "DANGER":
            issue = data.get("issue", "Unknown")
            
            # 1. Speak
            speak_warning(issue)
            
            # 2. Log to History (NEW)
            log_incident(issue)
            
            # 3. Send SMS
            send_sms_alert(issue)

    except Exception as e:
        print(f"❌ Error: {e}")

def start_stream(video_source):
    cap = cv2.VideoCapture(video_source)
    last_analysis_time = 0
    analysis_interval = 5.0 # Check every 10 seconds

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        cv2.imshow('Factory Sentinel', frame)

        if time.time() - last_analysis_time >= analysis_interval:
            analyze_frame(frame)
            last_analysis_time = time.time()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Use 0 for webcam, or filename for video
    start_stream("factory_sample.mp4")
