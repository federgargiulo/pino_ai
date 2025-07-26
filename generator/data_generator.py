#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator per-asset, 10 Hz, CSV sovrascritto con finestra degli ultimi N secondi.
Crea: /data/assets/{motor_M1.csv, ..., pump_P2.csv, valve_V4.csv}
"""
import csv, os, time, math, argparse, random
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List

# ---------- Utility ----------
def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def atomic_write_csv(path: str, header: List[str], rows: List[List]):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def randn(mu, sigma):
    return random.gauss(mu, sigma)

def uni(a, b):
    return random.uniform(a, b)

def now_ts_iso():
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

# ---------- Base class ----------
@dataclass
class BaseAsset:
    asset_id: str
    asset_type: str  # 'motor' | 'pump' | 'valve'
    freq_hz: float
    window_s: int
    buffer: Deque[Dict] = field(default_factory=lambda: deque(maxlen=1))
    energy_kwh: float = 0.0
    fault: Dict = field(default_factory=lambda: {"active": False, "type": None, "t_end": 0.0})

    def __post_init__(self):
        self.buffer = deque(maxlen=int(self.freq_hz * self.window_s))

    def jitter(self, val, rel_sigma=0.01):
        return randn(val, abs(val) * rel_sigma if val != 0 else rel_sigma)

    def step(self, t: float, dt: float):
        raise NotImplementedError

    def maybe_toggle_fault(self, t: float, fault_rate_per_min: float, avg_duration_s: float, possible_types: List[str]):
        if not self.fault["active"]:
            p = fault_rate_per_min / 60.0
            if random.random() < p:
                self.fault["active"] = True
                self.fault["type"] = random.choice(possible_types)
                self.fault["t_end"] = t + max(5.0, randn(avg_duration_s, avg_duration_s*0.3))
        else:
            if t >= self.fault["t_end"]:
                self.fault = {"active": False, "type": None, "t_end": 0.0}

    def write_csv(self, out_dir: str, header: List[str]):
        path = os.path.join(out_dir, f"{self.asset_type}_{self.asset_id}.csv")
        rows = []
        for row in self.buffer:
            rows.append([row.get(col, "") for col in header])
        atomic_write_csv(path, header, rows)

# ---------- Motor ----------
class Motor(BaseAsset):
    header = [
        "timestamp","asset_id","asset_type",
        "voltage_V_L1","voltage_V_L2","voltage_V_L3",
        "current_A_L1","current_A_L2","current_A_L3",
        "freq_Hz","power_P_kW","power_Q_kvar","power_S_kVA","power_factor",
        "THD_I_pct","THD_V_pct","speed_rpm","torque_Nm",
        "vibration_rms_mm_s","vibration_hf_rms_mm_s","vibration_kurtosis",
        "bearing_temp_C","stator_temp_C","ambient_temp_C","noise_level_dBA",
        "energy_kWh_cum"
    ]
    possible_faults = ["overload","imbalance","bearing_wear","phase_loss"]

    def step(self, t: float, dt: float):
        V = [400.0, 400.0, 400.0]
        f = 50.0 + uni(-0.05, 0.05)
        speed = 1480 + uni(-3, 3)
        ambient = 25 + uni(-1.0, 1.0)
        pf = 0.86 + uni(-0.01, 0.01)
        I_nom = 40.0
        I = [self.jitter(I_nom, 0.03) for _ in range(3)]
        thd_i = 5.0 + uni(-0.5, 0.5)
        thd_v = 3.0 + uni(-0.3, 0.3)
        vib_rms = 1.2 + uni(-0.2, 0.2)
        vib_hf = 0.3 + uni(-0.05, 0.05)
        kurt = 3.0 + uni(-0.2, 0.2)
        bearing_T = 45.0 + uni(-1.5, 1.5)
        stator_T = 60.0 + uni(-2.0, 2.0)
        noise = 70 + uni(-1.5, 1.5)
        torque = 200 + uni(-10, 10)

        if self.fault["active"]:
            ft = self.fault["type"]
            if ft == "overload":
                I = [i*uni(1.2, 1.4) for i in I]
                pf = max(0.7, pf - 0.08)
                stator_T += uni(8, 15)
                bearing_T += uni(3, 6)
                vib_rms *= uni(1.2, 1.4)
                noise += uni(2, 5)
                torque *= uni(1.1, 1.2)
            elif ft == "imbalance":
                I[0] *= uni(0.9, 1.0)
                I[1] *= uni(1.0, 1.1)
                I[2] *= uni(1.05, 1.15)
                vib_rms *= uni(1.6, 2.2)
                kurt += uni(0.2, 0.6)
                noise += uni(2, 4)
            elif ft == "bearing_wear":
                vib_hf *= uni(2.5, 3.5)
                kurt += uni(1.0, 2.0)
                bearing_T += uni(5, 10)
                noise += uni(3, 6)
            elif ft == "phase_loss":
                k = random.randrange(3)
                I[k] *= uni(0.2, 0.5)
                pf = max(0.65, pf - 0.1)
                torque *= uni(0.6, 0.8)
                vib_rms *= uni(1.3, 1.8)
                noise += uni(2, 4)

        I_avg = sum(I)/3.0
        S_kVA = 1.732 * (sum(V)/3.0) * I_avg / 1000.0
        P_kW = S_kVA * pf
        Q_kvar = math.sqrt(max(S_kVA**2 - P_kW**2, 0.0))
        self.energy_kwh += max(P_kW, 0.0) * dt / 3600.0

        row = {
            "timestamp": now_ts_iso(),
            "asset_id": self.asset_id,
            "asset_type": "motor",
            "voltage_V_L1": V[0], "voltage_V_L2": V[1], "voltage_V_L3": V[2],
            "current_A_L1": I[0], "current_A_L2": I[1], "current_A_L3": I[2],
            "freq_Hz": f, "power_P_kW": P_kW, "power_Q_kvar": Q_kvar, "power_S_kVA": S_kVA,
            "power_factor": pf, "THD_I_pct": thd_i, "THD_V_pct": thd_v,
            "speed_rpm": speed, "torque_Nm": torque,
            "vibration_rms_mm_s": vib_rms, "vibration_hf_rms_mm_s": vib_hf, "vibration_kurtosis": kurt,
            "bearing_temp_C": bearing_T, "stator_temp_C": stator_T, "ambient_temp_C": ambient,
            "noise_level_dBA": noise, "energy_kWh_cum": self.energy_kwh
        }
        self.buffer.append(row)

# ---------- Pump ----------
class Pump(BaseAsset):
    header = Motor.header + [
        "suction_pressure_bar","discharge_pressure_bar","diff_pressure_bar",
        "flow_m3h","npsha_m","cavitation_index"
    ]
    possible_faults = ["cavitation","clogging","air_entrainment"]

    def step(self, t: float, dt: float):
        V = [400.0, 400.0, 400.0]
        f = 50.0 + uni(-0.05, 0.05)
        I_nom = 35.0
        I = [self.jitter(I_nom, 0.03) for _ in range(3)]
        pf = 0.84 + uni(-0.01, 0.01)
        thd_i = 4.5 + uni(-0.5, 0.5)
        thd_v = 3.0 + uni(-0.3, 0.3)
        speed = 1470 + uni(-4, 4)
        torque = 180 + uni(-10, 10)
        vib_rms = 1.0 + uni(-0.2, 0.2)
        vib_hf = 0.25 + uni(-0.05, 0.05)
        kurt = 3.0 + uni(-0.2, 0.2)
        bearing_T = 42.0 + uni(-1.5, 1.5)
        stator_T = 58.0 + uni(-2.0, 2.0)
        ambient = 25 + uni(-1.0, 1.0)
        noise = 68 + uni(-1.5, 1.5)

        suction_p = 1.5 + uni(-0.05, 0.05)
        discharge_p = 3.5 + uni(-0.05, 0.05)
        diff_p = discharge_p - suction_p
        flow = 50.0 + uni(-1.0, 1.0)
        npsha = 3.0 + uni(-0.1, 0.1)
        cav_idx = 0.1 + uni(-0.02, 0.02)

        if self.fault["active"]:
            ft = self.fault["type"]
            if ft == "cavitation":
                vib_hf *= uni(2.5, 3.5)
                suction_p -= uni(0.2, 0.5)
                flow += uni(-10.0, 10.0)
                cav_idx += uni(0.5, 1.0)
                noise += uni(3, 6)
            elif ft == "clogging":
                diff_p += uni(0.6, 1.2)
                flow -= uni(10.0, 20.0)
                I = [i*uni(1.1, 1.25) for i in I]
                pf = max(0.7, pf - 0.05)
                noise += uni(1, 3)
            elif ft == "air_entrainment":
                flow += uni(-15.0, 15.0)
                vib_rms *= uni(1.2, 1.6)
                cav_idx += uni(0.2, 0.4)
                noise += uni(1,3)

        I_avg = sum(I)/3.0
        S_kVA = 1.732 * (sum(V)/3.0) * I_avg / 1000.0
        P_kW = S_kVA * pf
        Q_kvar = math.sqrt(max(S_kVA**2 - P_kW**2, 0.0))
        self.energy_kwh += max(P_kW, 0.0) * dt / 3600.0

        row = {
            "timestamp": now_ts_iso(), "asset_id": self.asset_id, "asset_type": "pump",
            "voltage_V_L1": V[0], "voltage_V_L2": V[1], "voltage_V_L3": V[2],
            "current_A_L1": I[0], "current_A_L2": I[1], "current_A_L3": I[2],
            "freq_Hz": f, "power_P_kW": P_kW, "power_Q_kvar": Q_kvar, "power_S_kVA": S_kVA,
            "power_factor": pf, "THD_I_pct": thd_i, "THD_V_pct": thd_v,
            "speed_rpm": speed, "torque_Nm": torque,
            "vibration_rms_mm_s": vib_rms, "vibration_hf_rms_mm_s": vib_hf, "vibration_kurtosis": kurt,
            "bearing_temp_C": bearing_T, "stator_temp_C": stator_T, "ambient_temp_C": ambient,
            "noise_level_dBA": noise, "energy_kWh_cum": self.energy_kwh,
            "suction_pressure_bar": suction_p, "discharge_pressure_bar": discharge_p, "diff_pressure_bar": diff_p,
            "flow_m3h": flow, "npsha_m": npsha, "cavitation_index": cav_idx
        }
        self.buffer.append(row)

# ---------- Valve ----------
class Valve(BaseAsset):
    header = [
        "timestamp","asset_id","asset_type",
        "command_pct","position_pct","position_error_pct","travel_time_ms",
        "differential_pressure_bar","valve_flow_m3h","stem_torque_Nm",
        "leakage_lph","supply_air_bar",
        "ambient_temp_C","noise_level_dBA"
    ]
    possible_faults = ["stiction","leakage","actuator_fault"]

    last_cmd: float = 50.0
    last_pos: float = 50.0
    def step(self, t: float, dt: float):
        if random.random() < 0.05:
            self.last_cmd = clamp(self.last_cmd + uni(-10, 10), 0, 100)
        tracking_gain = 0.9
        noise = uni(-1.0, 1.0)
        pos = clamp(self.last_pos + (self.last_cmd - self.last_pos) * tracking_gain * dt + noise*0.05, 0, 100)
        travel_time_ms = 150 + uni(-20, 20)
        dp_bar = 1.0 + uni(-0.1, 0.1)
        flow = pos/100.0 * 40.0 + uni(-1.0, 1.0)
        torque = 50 + uni(-5, 5)
        leakage = max(0.0, uni(-0.5, 0.5))
        supply_air = 6.0 + uni(-0.1, 0.1)
        ambient = 25 + uni(-1.0, 1.0)
        sound = 65 + uni(-1.0, 1.0)

        if self.fault["active"]:
            ft = self.fault["type"]
            if ft == "stiction":
                pos = clamp(self.last_pos + (self.last_cmd - self.last_pos) * 0.2 * dt + noise*0.1, 0, 100)
                travel_time_ms = 350 + uni(-30, 30)
                torque += uni(10, 20)
                sound += uni(2, 4)
            elif ft == "leakage":
                leakage += uni(5.0, 20.0)
                flow += uni(2.0, 5.0)
            elif ft == "actuator_fault":
                pos = clamp(self.last_pos + (self.last_cmd - self.last_pos) * 0.1 * dt + noise*0.2, 0, 100)
                supply_air -= uni(0.5, 1.0)
                torque -= uni(5, 10)
                sound += uni(1, 2)

        self.last_pos = pos
        err = self.last_cmd - pos
        row = {
            "timestamp": now_ts_iso(), "asset_id": self.asset_id, "asset_type": "valve",
            "command_pct": self.last_cmd, "position_pct": pos, "position_error_pct": err,
            "travel_time_ms": travel_time_ms, "differential_pressure_bar": 1.0 + uni(-0.1,0.1),
            "valve_flow_m3h": flow, "stem_torque_Nm": torque, "leakage_lph": leakage,
            "supply_air_bar": supply_air, "ambient_temp_C": ambient, "noise_level_dBA": sound
        }
        self.buffer.append(row)

# ---------- Costruzione parco macchine ----------
def build_assets(n_motors: int, n_pumps: int, n_valves: int, freq_hz: float, window_s: int):
    assets: List[BaseAsset] = []
    for i in range(1, n_motors+1):
        assets.append(Motor(asset_id=f"M{i}", asset_type="motor", freq_hz=freq_hz, window_s=window_s))
    for i in range(1, n_pumps+1):
        assets.append(Pump(asset_id=f"P{i}", asset_type="pump", freq_hz=freq_hz, window_s=window_s))
    for i in range(1, n_valves+1):
        assets.append(Valve(asset_id=f"V{i}", asset_type="valve", freq_hz=freq_hz, window_s=window_s))
    return assets

def main(out_dir: str, freq: int, motors: int, pumps: int, valves: int,
         window_s: int, fault_rate_per_min: float, fault_avg_duration_s: float, seed: int):
    random.seed(seed if seed is not None else 42)
    ensure_dir(out_dir)
    assets = build_assets(motors, pumps, valves, freq, window_s)

    # Prefill buffer
    t = 0.0
    dt = 1.0/freq
    warmup_steps = int(freq * window_s)
    for _ in range(warmup_steps):
        for a in assets:
            a.maybe_toggle_fault(t, fault_rate_per_min, fault_avg_duration_s, a.possible_faults)
            a.step(t, dt)
        t += dt
    for a in assets:
        header = getattr(type(a), "header")
        a.write_csv(out_dir, header)

    while True:
        loop_start = time.time()
        for a in assets:
            a.maybe_toggle_fault(t, fault_rate_per_min, fault_avg_duration_s, a.possible_faults)
            a.step(t, dt)
        t += dt
        for a in assets:
            header = getattr(type(a), "header")
            a.write_csv(out_dir, header)
        elapsed = time.time() - loop_start
        time.sleep(max(0.0, dt - elapsed))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default="/data/assets", help="Cartella output per-asset")
    ap.add_argument("--freq", type=int, default=10, help="Hz (campioni/secondo)")
    ap.add_argument("--motors", type=int, default=4)
    ap.add_argument("--pumps", type=int, default=2)
    ap.add_argument("--valves", type=int, default=4)
    ap.add_argument("--window_s", type=int, default=30, help="Finestra da mantenere nel CSV")
    ap.add_argument("--fault_rate_per_min", type=float, default=0.08, help="Probabilità media di start guasto/min per asset (bassa)")
    ap.add_argument("--fault_avg_duration_s", type=float, default=20.0, help="Durata media guasto (s)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    main(args.out_dir, args.freq, args.motors, args.pumps, args.valves,
         args.window_s, args.fault_rate_per_min, args.fault_avg_duration_s, args.seed)
