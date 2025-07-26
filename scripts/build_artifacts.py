#!/usr/bin/env python3
"""
Rigenera:
  ai/diagnosys_model.pkl
  ai/inference_service.py
  ai/sample_request.json
Usando gli stessi parametri che ti ho fornito.
"""
import os, json, random, numpy as np, joblib, textwrap
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

WINDOW = 100
FIELDS = ["current","voltage","vibration","temperature","pressure","rpm"]
def gen_sample(fault):
    base = {"current":10,"voltage":400,"vibration":1,"temperature":50,"pressure":3,"rpm":1500}
    seq=[]
    for _ in range(WINDOW):
        cur={f:base[f]+np.random.normal(0,base[f]*0.02) for f in FIELDS}
        if fault:
            cur["vibration"]+=np.random.uniform(2,5)
            cur["temperature"]+=np.random.uniform(10,20)
        seq.extend([cur[f] for f in FIELDS])
    return seq

X=np.array([gen_sample(0) for _ in range(1000)]+[gen_sample(1) for _ in range(1000)])
y=np.array([0]*1000+[1]*1000)
Xt,Xv,yt,yv=train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
clf=RandomForestClassifier(n_estimators=100,random_state=42).fit(Xt,yt)

os.makedirs("ai",exist_ok=True)
joblib.dump(clf,"ai/diagnosys_model.pkl")

# inference script
open("ai/inference_service.py","w").write(textwrap.dedent("""\
#!/usr/bin/env python3
import sys, json, joblib, numpy as np, os
MODEL_PATH=os.getenv("MODEL_PATH","ai/diagnosys_model.pkl")
clf=joblib.load(MODEL_PATH)
data=json.load(open(sys.argv[1]))
X=np.array(list(map(float,data["values"]))).reshape(1,-1)
pred=clf.predict(X)[0]
print(json.dumps({"statusCode":"0" if pred==0 else "1",
                  "statusDescription":"HEALTHY" if pred==0 else "FAULT DETECTED"}))
"""))
os.chmod("ai/inference_service.py",0o755)

json.dump({"values":[str(v) for v in gen_sample(0)]},
          open("ai/sample_request.json","w"))
print("✅  Artifact generati sotto ./ai/")
