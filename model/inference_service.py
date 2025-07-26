#!/usr/bin/env python3
from flask import Flask, jsonify
import pandas as pd, numpy as np, argparse, os

app = Flask(__name__)
ARGS = None

# pesi logistic semplicissimi (NO retraining)
W_VIB = 0.7
W_TMP = 0.05
BIAS  = -6.0

def predict_row(row):
    z = W_VIB*row["vibration_mm_s"] + W_TMP*row["temp_C"] + BIAS
    prob = 1/(1+np.exp(-z))
    return 1 if prob >= 0.5 else 0   # 1 = FAULT

def read_last():
    df = pd.read_csv(ARGS.file)
    last = df.tail(1).iloc[0]
    return predict_row(last)

@app.route("/predict", methods=["GET"])
def predict():
    y = read_last()
    status = "1" if y==1 else "0"
    desc   = "FAULT" if y==1 else "OK"
    return jsonify({"statusCode": status, "statusDescription": desc})

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", default="/data/samples.csv")
    p.add_argument("--port", type=int, default=5000)
    ARGS = p.parse_args()
    app.run(host="0.0.0.0", port=ARGS.port)
