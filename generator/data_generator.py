#!/usr/bin/env python3
import csv, random, time, argparse, os, datetime as dt

FIELDS = ["timestamp","machine_id","current_A","vibration_mm_s","temp_C"]

def rand_norm(low, high): return random.uniform(low, high)

def fake_row(machine_id, fault=False):
    if fault:        # valori anomali
        current  = rand_norm(60, 80)
        vibration= rand_norm(7, 10)
        temp     = rand_norm(90, 110)
    else:            # valori normali
        current  = rand_norm(30, 50)
        vibration= rand_norm(1, 3)
        temp     = rand_norm(40, 70)
    return [dt.datetime.utcnow().isoformat(), machine_id, current, vibration, temp]

def main(file, freq, machines):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", newline="") as f:
        w = csv.writer(f); w.writerow(FIELDS)
    fault_prob = 0.01      # 1 %
    while True:
        with open(file, "a", newline="") as f:
            w = csv.writer(f)
            for m in range(1, machines+1):
                fault = random.random() < fault_prob
                w.writerow(fake_row(m, fault))
        time.sleep(1/freq)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="/data/samples.csv")
    ap.add_argument("--freq", type=int, default=10, help="samples/sec per macchina")
    ap.add_argument("--machines", type=int, default=5)
    main(**vars(ap.parse_args()))
