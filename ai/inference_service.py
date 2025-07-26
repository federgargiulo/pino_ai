#!/usr/bin/env python3
import sys, json, joblib, numpy as np, os
MODEL_PATH=os.getenv("MODEL_PATH","ai/diagnosys_model.pkl")
clf=joblib.load(MODEL_PATH)
data=json.load(open(sys.argv[1]))
X=np.array(list(map(float,data["values"]))).reshape(1,-1)
pred=clf.predict(X)[0]
print(json.dumps({"statusCode":"0" if pred==0 else "1",
                  "statusDescription":"HEALTHY" if pred==0 else "FAULT DETECTED"}))
