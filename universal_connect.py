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

print(f"🔑 Key: ...{api_key[-4:]}")
client = genai.Client(api_key=api_key)

# 2. LEGACY MODEL SELECTOR
# We are dropping down to 1.0 because 2.0/1.5 are blocked
LEGACY_MODELS = [
    "gemini-pro",         # The classic (Gemini 1.0)
    "gemini-1.0-pro",     # Alternate name
    "gemini-1.0-pro-001"  # Specific version
]

valid_model = None

print("\n🔌 CONNECTING TO LEGACY SERVERS...")
for model_name in LEGACY_MODELS:
    try:
        print(f"   👉 Testing: {model_name}...", end=" ")
        # Tiny test
        client.models.generate_content(
            model=model_name,
            contents="Hi"
        )
        print("✅ ALIVE!")
        valid_model = model_name
        break 
    except Exception as e:
        print("❌ Dead.")

if not valid_model:
    print("\n❌ ALL MODELS BLOCKED. YOU MUST ENABLE BILLING.")
    print("Go to AI Studio > Billing and add a card (You won't be charged).")
    print("This verifies you are a human and unlocks the Free Tier.")
    exit()

print(f"\n🚀 LAUNCHING SENTINEL WITH: {valid_model}")
print("------------------------------------------------")

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

# 4. MAIN LOOP
def analyze_frame(frame):
    # Resize to 640x480
    frame_resized = cv2.resize(frame, (640, 480))
    _, buffer = cv2.imencode('.jpg', frame_resized)
    image_bytes = buffer.tobytes()
    
    # Gemini 1.0 Pro is text-only usually, but we try sending image
    # If it fails, we fall back to text simulation for the video
    prompt = "You are a Safety Officer. Analyze this factory scene. Return ONLY JSON: {'status': 'SAFE'/'DANGER', 'issue': 'short description'}"

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
