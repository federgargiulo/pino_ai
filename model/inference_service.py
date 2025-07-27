#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inference service con FastAPI.
- Legge CSV per-asset in /data/assets
- Calcola feature su finestra (default 30s)
- Espone API:
  * GET  /assets
  * GET  /values?asset_id=...&window_s=30
  * POST /diagnosys/engine   (body: {"values":["..."]})  -> {"statusCode":"0|1","statusDescription":"HEALTHY|FAULTY"}
  * GET  /predict?asset_id=...&window_s=30               -> come sopra
  * GET  /predict_all?window_s=30
  * GET  /features?asset_id=...&window_s=30              -> feature dettagliate (debug)
Documentazione: /docs
"""
import os, math, glob
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import numpy as np
import pandas as pd

DATA_DIR = os.environ.get("DATA_DIR", "/data/assets")
DEFAULT_WINDOW_S = int(os.environ.get("WINDOW_S", "30"))
FREQ_HZ = float(os.environ.get("FREQ_HZ", "10"))

app = FastAPI(title="Industrial Demo Inference API", version="1.0.0")

# --- Java-compat DTO ---
class DiagnosysEngineRequestTO(BaseModel):
    values: List[str]

class DiagnosysResultsTO(BaseModel):
    statusCode: str
    statusDescription: str

# --- Asset discovery ---
@dataclass
class Asset:
    asset_id: str    # M1, P2, V4
    asset_type: str  # motor|pump|valve
    path: str

def list_assets() -> List[Asset]:
    files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    assets: List[Asset] = []
    for p in files:
        name = os.path.basename(p)
        try:
            prefix, rest = name.split("_", 1)
            asset_type = prefix.lower()
            asset_id = rest.rsplit(".", 1)[0]
            assets.append(Asset(asset_id=asset_id, asset_type=asset_type, path=p))
        except Exception:
            continue
    return assets

def get_asset(asset_id: str) -> Asset:
    for a in list_assets():
        if a.asset_id == asset_id:
            return a
    raise KeyError(f"Asset {asset_id} not found")

# --- Feature Engineering ---
FEATURE_NAMES = [
    "vib_hf_z", "vib_rms_z", "temp_z", "current_imbalance", "pf_low",
    "thd_i_z", "pressure_anom_z", "flow_instability", "tracking_error_z", "load_index_z"
]

NOMINAL = {
    "motor": {
        "vib_hf": (0.30, 0.06),
        "vib_rms": (1.20, 0.25),
        "temp": ("stator_temp_C", 60.0, 3.0),
        "current": (40.0, 3.0),
        "pf": (0.86, 0.02),
        "thd_i": (5.0, 0.8),
        "load_index_ref": ("current_A_L1","current_A_L2","current_A_L3"),
    },
    "pump": {
        "vib_hf": (0.25, 0.05),
        "vib_rms": (1.00, 0.2),
        "temp": ("stator_temp_C", 58.0, 3.0),
        "current": (35.0, 3.0),
        "pf": (0.84, 0.02),
        "thd_i": (4.5, 0.8),
        "pressure": ("diff_pressure_bar", 2.0, 0.3),
        "flow": ("flow_m3h", 50.0, 5.0),
        "load_index_ref": ("current_A_L1","current_A_L2","current_A_L3"),
    },
    "valve": {
        "vib_hf": (0.0, 1.0),
        "vib_rms": (0.0, 1.0),
        "temp": ("ambient_temp_C", 25.0, 2.0),
        "pf": (1.0, 0.01),
        "thd_i": (0.0, 1.0),
        "flow": ("valve_flow_m3h", 20.0, 5.0),
        "load_index_ref": None,
    }
}

def safe_std(x): return float(np.std(x)) if len(x)>1 else 0.0
def coef_var(x):
    m = float(np.mean(x)) if len(x)>0 else 0.0
    s = safe_std(x)
    return float(s/abs(m)) if m != 0 else 0.0
def zscore(val, mu, sigma): return 0.0 if sigma <= 1e-9 else float((val - mu)/sigma)

def read_window(a: Asset, window_s: int) -> pd.DataFrame:
    path = a.path
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    n = int(FREQ_HZ * window_s)
    if len(df) > n:
        df = df.iloc[-n:]
    return df

def features_for_asset(a: Asset, window_s: int) -> Dict[str, Any]:
    df = read_window(a, window_s)
    t = a.asset_type

    if t in ("motor","pump"):
        vib_hf = float(np.mean(df.get("vibration_hf_rms_mm_s", 0)))
        vib_rms = float(np.mean(df.get("vibration_rms_mm_s", 0)))
        thd_i  = float(np.mean(df.get("THD_I_pct", 0)))
        pf     = float(np.mean(df.get("power_factor", 0.0)))
        temp_col, mu_t, sig_t = NOMINAL[t]["temp"]
        temp_mean = float(np.mean(df.get(temp_col, mu_t)))
        i1 = df.get("current_A_L1", 0).to_numpy()
        i2 = df.get("current_A_L2", 0).to_numpy()
        i3 = df.get("current_A_L3", 0).to_numpy()
        imb = 0.0
        if len(df) > 0:
            last = [float(df["current_A_L1"].iloc[-1]), float(df["current_A_L2"].iloc[-1]), float(df["current_A_L3"].iloc[-1])]
            imb = (max(last) - min(last)) / max(1e-6, np.mean(last))
        press_anom = 0.0
        flow_inst = 0.0
        if t == "pump":
            dp = float(np.mean(df.get("diff_pressure_bar", NOMINAL["pump"]["pressure"][1])))
            press_anom = zscore(dp, NOMINAL["pump"]["pressure"][1], NOMINAL["pump"]["pressure"][2])
            flow_inst  = coef_var(df.get("flow_m3h", 0).to_numpy())
        # load index z
        cur_mu, cur_sig = NOMINAL[t]["current"]
        load_idx = float(np.mean((i1+i2+i3)/3.0))
        load_idx_z = zscore(load_idx, cur_mu, cur_sig)
        feats = {
            "vib_hf_z": zscore(vib_hf, *NOMINAL[t]["vib_hf"]),
            "vib_rms_z": zscore(vib_rms, *NOMINAL[t]["vib_rms"]),
            "temp_z": zscore(temp_mean, mu_t, sig_t),
            "current_imbalance": float(imb),
            "pf_low": float(max(0.0, 1.0 - pf)),
            "thd_i_z": zscore(thd_i, *NOMINAL[t]["thd_i"]),
            "pressure_anom_z": float(press_anom),
            "flow_instability": float(flow_inst),
            "tracking_error_z": 0.0,
            "load_index_z": float(load_idx_z)
        }
    elif t == "valve":
        err = df.get("position_error_pct", 0).to_numpy()
        travel = df.get("travel_time_ms", 150.0).to_numpy()
        leak = df.get("leakage_lph", 0.0).to_numpy()
        flow = df.get("valve_flow_m3h", 20.0).to_numpy()
        tracking_error = float(np.mean(np.abs(err))) if len(err)>0 else 0.0
        tracking_error_z = zscore(tracking_error, 1.0, 0.5)
        flow_inst = coef_var(flow)
        temp_mean = float(np.mean(df.get("ambient_temp_C", 25.0)))
        feats = {
            "vib_hf_z": 0.0,
            "vib_rms_z": 0.0,
            "temp_z": zscore(temp_mean, NOMINAL["valve"]["temp"][1], NOMINAL["valve"]["temp"][2]),
            "current_imbalance": 0.0,
            "pf_low": 0.0,
            "thd_i_z": 0.0,
            "pressure_anom_z": 0.0,
            "flow_instability": float(flow_inst),
            "tracking_error_z": float(tracking_error_z),
            "load_index_z": zscore(float(np.mean(travel)), 150.0, 40.0) + zscore(float(np.mean(leak)), 0.1, 2.0)*0.5
        }
    else:
        raise ValueError(f"Unsupported asset type: {t}")

    values = [str(round(float(feats[name]), 6)) for name in FEATURE_NAMES]
    return {"asset_id": a.asset_id, "asset_type": a.asset_type, "feature_names": FEATURE_NAMES, "features": feats, "values": values}

# --- Modello ML pre-addestrato (logistica leggera) ---
W = np.array([ 1.4, 1.1, 1.2, 0.8, 0.7, 0.5, 1.0, 0.9, 1.3, 0.6 ], dtype=float)
BIAS = -2.2
def sigmoid(x): return 1.0/(1.0 + math.exp(-x))
def predict_from_values(values: List[str]) -> int:
    x = np.array([float(v) for v in values], dtype=float)
    if x.shape[0] != len(FEATURE_NAMES):
        raise ValueError(f"values must have length {len(FEATURE_NAMES)}")
    z = float(np.dot(W, x) + BIAS)
    p = sigmoid(z)
    return 1 if p >= 0.5 else 0  # 1=FAULTY

# --- Routes ---
@app.get("/assets")
def api_assets():
    A = list_assets()
    return [{"asset_id": a.asset_id, "asset_type": a.asset_type, "path": a.path} for a in A]

@app.get("/values")
def api_values(asset_id: str = Query(...), window_s: Optional[int] = Query(DEFAULT_WINDOW_S)):
    try:
        a = get_asset(asset_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    feats = features_for_asset(a, window_s)
    return {"asset_id": a.asset_id, "asset_type": a.asset_type, "values": feats["values"], "feature_names": feats["feature_names"]}

@app.post("/diagnosys/engine", response_model=DiagnosysResultsTO)
def api_engine(req: DiagnosysEngineRequestTO):
    try:
        y = predict_from_values(req.values)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DiagnosysResultsTO(statusCode=str(int(y)), statusDescription=("FAULTY" if y==1 else "HEALTHY"))


@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.get("/predict")
def api_predict(asset_id: Optional[str] = Query(None), window_s: Optional[int] = Query(DEFAULT_WINDOW_S)):
    try:
        if asset_id:
            a = get_asset(asset_id)
        else:
            assets = sorted(list_assets(), key=lambda x: x.asset_id)
            if not assets:
                raise HTTPException(status_code=503, detail="No asset data yet. Generator still warming up.")
            a = assets[0]  # fallback per compatibilità con vecchi client
        feats = features_for_asset(a, window_s)
        y = predict_from_values(feats["values"])
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"asset_id": a.asset_id, "asset_type": a.asset_type,
            "statusCode": str(int(y)), "statusDescription": ("FAULTY" if y==1 else "HEALTHY")}


@app.get("/predict_all")
def api_predict_all(window_s: Optional[int] = Query(DEFAULT_WINDOW_S)):
    out = []
    for a in list_assets():
        try:
            feats = features_for_asset(a, window_s)
            y = predict_from_values(feats["values"])
            out.append({"asset_id": a.asset_id, "asset_type": a.asset_type,
                        "statusCode": str(int(y)), "statusDescription": ("FAULTY" if y==1 else "HEALTHY")})
        except Exception as e:
            out.append({"asset_id": a.asset_id, "asset_type": a.asset_type, "error": str(e)})
    return out

@app.get("/features")
def api_features(asset_id: str = Query(...), window_s: Optional[int] = Query(DEFAULT_WINDOW_S)):
    try:
        a = get_asset(asset_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return features_for_asset(a, window_s)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/faults")
def api_faults():
    """Endpoint per monitorare lo stato dei guasti nel generator"""
    try:
        # Legge il file di stato condiviso (se esiste)
        status_file = os.path.join(os.path.dirname(DATA_DIR), "demo_status.json")
        if os.path.exists(status_file):
            import json
            with open(status_file, 'r') as f:
                return json.load(f)
        else:
            return {"message": "Status file not available", "faults": []}
    except Exception as e:
        return {"message": "Error reading status", "error": str(e), "faults": []}

