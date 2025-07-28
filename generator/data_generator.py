# data_generator.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import random

app = FastAPI(title="Motor Data Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def simulate_measurements(freq_hz=10, duration_s=2):
    n = freq_hz * duration_s
    now = datetime.utcnow()
    samples = []
    base = {
        "voltage": random.gauss(400, 5),
        "current": random.gauss(10, 1.5),
        "temp": random.gauss(60, 3),
        "vibration": random.gauss(3.0, 0.5),
        "speed": random.gauss(1500, 100),
    }
    for i in range(n):
        t = now - timedelta(seconds=(duration_s - i / freq_hz))
        sample = {
            "timestamp": t.isoformat() + "Z",
            "voltage_V_L1": base["voltage"] + random.gauss(0, 1),
            "voltage_V_L2": base["voltage"] + random.gauss(0, 1),
            "voltage_V_L3": base["voltage"] + random.gauss(0, 1),
            "current_A_L1": base["current"] + random.gauss(0, 0.3),
            "current_A_L2": base["current"] + random.gauss(0, 0.3),
            "current_A_L3": base["current"] + random.gauss(0, 0.3),
            "vibration_rms_mm_s": base["vibration"] + random.gauss(0, 0.2),
            "stator_temp_C": base["temp"] + random.gauss(0, 1),
            "speed_rpm": base["speed"] + random.gauss(0, 10),
        }
        samples.append(sample)
    return samples

@app.get("/generate")
def generate_data():
    return {"samples": simulate_measurements()}
