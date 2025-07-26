#!/usr/bin/env python3
import sys, json, joblib, numpy as np, pathlib

MODEL_PATH = pathlib.Path(__file__).with_name('diagnosys_model.pkl')
model = joblib.load(MODEL_PATH)

if len(sys.argv)<2:
    data=json.load(sys.stdin)
else:
    with open(sys.argv[1]) as f:
        data=json.load(f)

values = list(map(float,data["values"]))
X = np.array(values).reshape(1,-1)
pred = model.predict(X)[0]

result={
    "statusCode":"0" if pred==0 else "1",
    "statusDescription":"HEALTHY" if pred==0 else "FAULT DETECTED"
}

print(json.dumps(result))
