"""Métricas reproduzíveis em dados sintéticos com holdout separado do treinamento."""
import json,time
import numpy as np
from sklearn.metrics import precision_score,recall_score,confusion_matrix
from borda_ia import modelo
rng=np.random.default_rng(20261115)
normal=np.column_stack((rng.normal(4,.5,2000),rng.normal(80,3,2000)))
abnormal=np.column_stack((rng.uniform(9,16,200),rng.uniform(5,30,200)))
X=np.vstack((normal,abnormal));y=np.r_[np.zeros(len(normal),dtype=int),np.ones(len(abnormal),dtype=int)]
m=modelo();start=time.perf_counter();pred=(m.predict(X)==-1).astype(int);runtime=time.perf_counter()-start
tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
print(json.dumps({'dataset':'synthetic; iid holdout; seeded','normal':len(normal),'anomaly':len(abnormal),
                  'tp':int(tp),'tn':int(tn),'fp':int(fp),'fn':int(fn),
                  'precision':round(precision_score(y,pred,zero_division=0),5),
                  'recall':round(recall_score(y,pred,zero_division=0),5),'fpr':round(fp/(fp+tn),5),
                  'batch_inference_seconds':round(runtime,5)},indent=2))
