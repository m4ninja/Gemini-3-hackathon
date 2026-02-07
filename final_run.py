import cv2
import time
import json
import os
import pyttsx3
import threading
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. SETUP
load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ CRITICAL ERROR: API Key not found!")
    exit()

print(f"🔑 Using Key: ...{api_key[-4:]}")
client = genai.Client(api_key=api_key)

# 2. AUDIO SETUP
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

# 3. AUTO-DISCOVER WORKING MODEL (Fixed for New SDK)
print("\n🔍 Scanning for available models...")
valid_model = None

try:
    # --- FIX: Use client.models.list() for the new SDK ---
    for m in client.models.list():
        # We prefer 2.0 Flash if available (fastest)
        if "gemini-2.0-flash" in m.name and "lite" not in m.name:
             valid_model = m.name
             break
        # Fallback to 1.5 Flash (most reliable)
        if "gemini-1.5-flash" in m.name and "001" in m.name:
            valid_model = m.name
        
        # Capture any valid generation model as a last resort
        if "generateContent" in m.supported_generation_methods and not valid_model:
            valid_model = m.name

except Exception as e:
    print(f"❌ Error listing models: {e}")
    # Hardcoded fallback if listing fails completely
    valid_model = "gemini-1.5-flash-001"

if not valid_model:
    print("❌ No models found! Trying hardcoded fallback.")
    valid_model = "gemini-1.5-flash-001"
else:
    # Clean up the name for the API call
    valid_model = valid_model.replace("models/", "")

print(f"✅ SELECTED MODEL: {valid_model}")
print("------------------------------------------------")

# 4. MAIN LOOP
def analyze_frame(frame):
    frame_resized = cv2.resize(frame, (640, 480))
    _, buffer = cv2.imencode('.jpg', frame_resized)
    image_bytes = buffer.tobytes()
    
    prompt = "You are a Factory Safety Officer. Analyze this image. Return ONLY JSON: {'status': 'SAFE'/'DANGER', 'issue': 'short description', 'confidence': 0-100}"

    try:
        response = client.models.generate_content(
            model=valid_model, 
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
        print(f"🤖 AI: {text_data}")

        try:
            data = json.loads(text_data)
            if data.get("status") == "DANGER":
                print(f"🔊 WARNING: {data.get('issue')}")
                speak_warning(f"Violation. {data.get('issue')}")
        except:
            pass

        with open("status.json", "w") as f:
            f.write(text_data)
        cv2.imwrite("current_frame.jpg", frame_resized)

    except Exception as e:
        print(f"❌ API Error: {e}")

def start_stream(video_source):
    cap = cv2.VideoCapture(video_source)
    print("🎥 Starting Video Feed...")
    last_analysis_time = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        cv2.imshow('Factory Sentinel - Live', frame)

        if time.time() - last_analysis_time >= 15.0:
            print("📸 Scanning...")
            analyze_frame(frame)
            last_analysis_time = time.time()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_stream("factory_sample.mp4")
