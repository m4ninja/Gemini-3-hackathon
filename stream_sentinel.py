import cv2
import time
import json
import os
import pyttsx3
import threading
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. FORCE RELOAD .ENV (The Fix for "Zombie Keys")
# override=True ensures we actually use the new key in the file
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ CRITICAL ERROR: API Key not found!")
    exit()

# 2. VERIFY KEY (Debug Print)
print(f"🔑 Loaded API Key ending in: ...{api_key[-4:]}")
if api_key[-4:] != "e3LQ":
    print("⚠️ WARNING: This does NOT match your new key (e3LQ)!")
    print("👉 Action: Check your .env file again.")

client = genai.Client(api_key=api_key)

# 3. AUDIO SETUP
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak_warning(text):
    def run_speech():
        try:
            local_engine = pyttsx3.init()
            local_engine.say(f"Alert! {text}")
            local_engine.runAndWait()
        except:
            pass
    t = threading.Thread(target=run_speech)
    t.start()

# --- SMART MODEL MANAGER ---
# Updated with EXACT OFFICIAL NAMES to fix 404 errors
MODELS_TO_TRY = [
    "gemini-2.0-flash",           # Try the new fast model first
    "gemini-1.5-flash-001",       # <--- FIXED NAME (The reliable backup)
    "gemini-1.5-pro-001"          # <--- FIXED NAME (High intelligence backup)
]
current_model_index = 0

def analyze_frame(frame):
    global current_model_index
    
    # Resize to 640x480
    frame_resized = cv2.resize(frame, (640, 480))
    _, buffer = cv2.imencode('.jpg', frame_resized)
    image_bytes = buffer.tobytes()
    
    prompt = "You are a Factory Safety Officer. Analyze this image. Return ONLY JSON: {'status': 'SAFE'/'DANGER', 'issue': 'short description', 'confidence': 0-100}"

    for attempt in range(len(MODELS_TO_TRY)):
        model_name = MODELS_TO_TRY[current_model_index]
        
        try:
            print(f"🔄 Attempting with model: {model_name}...")
            
            response = client.models.generate_content(
                model=model_name, 
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
            
            # SUCCESS!
            text_data = response.text.replace("```json", "").replace("```", "").strip()
            print(f"✅ GEMINI SAYS: {text_data}")

            try:
                data = json.loads(text_data)
                if data.get("status") == "DANGER":
                    print(f"🔊 SPEAKING: {data.get('issue')}")
                    speak_warning(f"Violation detected. {data.get('issue')}")
            except:
                pass

            with open("status.json", "w") as f:
                f.write(text_data)
            cv2.imwrite("current_frame.jpg", frame_resized)
            return 

        except Exception as e:
            print(f"⚠️ Error with {model_name}: {e}")
            # Switch to next model immediately
            current_model_index = (current_model_index + 1) % len(MODELS_TO_TRY)

def start_stream(video_source):
    cap = cv2.VideoCapture(video_source)
    print(f"✅ Processing: {video_source}")
    print("------------------------------------------------")
    
    last_analysis_time = 0
    analysis_interval = 15.0 

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        cv2.imshow('Factory Sentinel - Live', frame)

        if time.time() - last_analysis_time >= analysis_interval:
            analyze_frame(frame)
            last_analysis_time = time.time()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_stream("factory_sample.mp4")
