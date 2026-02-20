import serial
import math
import time
from openai import OpenAI
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse , JSONResponse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

ser = serial.Serial("COM3", 115200, timeout=1)  

app=FastAPI()

client = OpenAI(api_key="")

CALL_COOLDOWN = 600  # 10 minutes
last_call_time = 0

latest_data = {
    "tilt": 0.0,
    "change": 0.0,
    "confidence": 0,
    "state": "CALIBRATING"
}

def read_tilt():
    while True:
        line = ser.readline().decode(errors="ignore").strip()   #.decode Converts bytes → string , .decode cant decode all bytes so i use errors="ignore" skips invalid ones to prevent crashes

        if not line:        #sometimes .readline() somtimes return empty so we this to handle the crash 
            continue            
        try:
            ax, ay, az = map(float, line.split(","))    #convers str into float

            tilt_rad = math.atan2(
                math.sqrt(ax*ax + ay*ay),az     #trigonometry
            )
            return math.degrees(tilt_rad)   
        except ValueError:
            continue


# -------------------------------
# CALIBRATION (baseline)
# -------------------------------
print("Keep plant stable for calibration...")
time.sleep(2)

samples = []
for _ in range(20):
    samples.append(read_tilt())
    time.sleep(0.05)

baseline = sum(samples) / len(samples)  #average
print(f"Baseline tilt set to: {baseline:.2f}°\n")


CALL_AGENT_URL = "http://127.0.0.1:5050/make-call"

def trigger_ai_call():
    try:
        r = requests.post(CALL_AGENT_URL, timeout=3)
        print("AI call triggered:", r.json())
    except Exception as e:
        print("Failed to trigger AI call:", e)


# -------------------------------
# MONITORING
# -------------------------------
def monitor_plant_motion(baseline, window=5, sleep_time=0.1):
    recent = []
    global last_call_time
    email_sent = False
    
    while True:
        current = read_tilt()
        recent.append(current)

        # keep sliding window size fixed
        if len(recent) > window:
            recent.pop(0)

        avg_tilt = sum(recent) / len(recent)
        change = abs(avg_tilt - baseline)

        if change < 4:
            state = "NORMAL"
        elif change < 10:
            state = "STRESS"
        else:
            state = "FALL_RISK"

        confidence = min(100, int(change * 10))

        print(
            f"Tilt(avg): {avg_tilt:.2f}° | "
            f"Change: {change:.2f}° | "
            f"Confidence: {confidence}% | "
            f"State: {state}"
        )

        latest_data["tilt"] = round(avg_tilt, 2)
        latest_data["change"] = round(change, 2)
        latest_data["confidence"] = confidence
        latest_data["state"] = state
        
        if state in ["STRESS", "FALL_RISK"] and not email_sent:
            status = send_email_alert(state, confidence)
            print("📧 Email:", status)
    
            email_sent = True
        
        if state in ["STRESS", "FALL_RISK"]:
            now = time.time()
            if now - last_call_time >= CALL_COOLDOWN:
                trigger_ai_call()
                last_call_time = now
                print("📞 AI Call triggered")
            else:
                remaining = int(CALL_COOLDOWN - (now - last_call_time))
                print(f"⏳ Call cooldown active ({remaining}s left)")
                
        time.sleep(sleep_time)

def generate_email_content(state,confidence):
    prompt = f"""
You are an IoT assistant for plant monitoring.

Write a plain-text email alert.
Do NOT use markdown.
Do NOT use **, *, bullets with formatting, or emojis.
Use simple text with hyphens (-) only.

State: {state}
Confidence: {confidence} percent

Explain the situation and suggest actions clearly and calmly.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text



def send_email_alert(state, confidence):
    if state not in ["STRESS", "FALL_RISK"]:
        return "no alert needed"
    
    subject = f"PlantMotion AI Alert: {state}"

    content = generate_email_content(state, confidence)

    sender_email = "ftwphineas508@gmail.com"
    receiver_email = "mdthahoor312@gmail.com"
    app_password = "zcsypisjudxioqit"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(content, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return "email sent"
    except Exception as e:
        return f"email failed: {e}"
    

threading.Thread(
    target=monitor_plant_motion,
    args=(baseline,),
    daemon=True
).start()


@app.get("/")
def home():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
  <title>PlantMotion AI</title>
  <style>
    body { font-family: Arial; background:#0f172a; color:white; text-align:center; }
    .card { background:#1e293b; padding:20px; margin:40px auto; width:300px; border-radius:12px; }
    .NORMAL { color:#22c55e; }
    .STRESS { color:#facc15; }
    .FALL_RISK { color:#ef4444; }
  </style>
</head>
<body>
  <h1>🌱 PlantMotion AI</h1>
  <div class="card">
    <p>Tilt: <span id="tilt">--</span>°</p>
    <p>Change: <span id="change">--</span>°</p>
    <p>Confidence: <span id="confidence">--</span>%</p>
    <h2 id="state">CALIBRATING</h2>
  </div>

<script>
async function update() {
  const res = await fetch("/status");
  const d = await res.json();
  document.getElementById("tilt").innerText = d.tilt;
  document.getElementById("change").innerText = d.change;
  document.getElementById("confidence").innerText = d.confidence;
  const s = document.getElementById("state");
  s.innerText = d.state;
  s.className = d.state;
}
setInterval(update, 200);
</script>
</body>
</html>
""")

@app.get("/status")
def status():
    return JSONResponse(latest_data)

