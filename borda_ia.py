"""Simulador edge-first com persistência SQLite, entrega confirmada e IA defensiva.
Não controla equipamentos físicos. Não declara MQTT, VPN ou mTLS implementados.
"""
import argparse,json,sqlite3,time,uuid,random,urllib.request,urllib.error,os
from datetime import datetime,timezone
import numpy as np
from sklearn.ensemble import IsolationForest
DB=os.getenv('VA_BUFFER_DB','buffer_borda.sqlite')
URL=os.getenv('VA_CENTRAL_URL','http://127.0.0.1:8765/ingest')

def setup():
    with sqlite3.connect(DB) as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE IF NOT EXISTS buffer(id TEXT PRIMARY KEY, ts TEXT NOT NULL, temp REAL NOT NULL, nivel REAL NOT NULL, confirmado INTEGER NOT NULL DEFAULT 0, tentativas INTEGER NOT NULL DEFAULT 0)')

def modelo():
    rng=np.random.default_rng(42)
    X=np.column_stack((rng.normal(4,0.5,400),rng.normal(80,3,400)))
    return IsolationForest(contamination=0.05,random_state=42,n_estimators=100).fit(X)

def store(temp,nivel):
    event={'id':str(uuid.uuid4()),'ts':datetime.now(timezone.utc).isoformat(), 'temp':float(temp),'nivel':float(nivel)}
    with sqlite3.connect(DB) as c:
        c.execute('INSERT INTO buffer(id,ts,temp,nivel) VALUES(?,?,?,?)',(event['id'],event['ts'],event['temp'],event['nivel']))
    return event

def sync(url=URL):
    count=0
    with sqlite3.connect(DB) as c:
        pending=c.execute('SELECT id,ts,temp,nivel FROM buffer WHERE confirmado=0 ORDER BY ts,id').fetchall()
    for ident,ts,temp,nivel in pending:
        payload=json.dumps({'id':ident,'ts':ts,'temp':temp,'nivel':nivel}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(url,payload,{'Content-Type':'application/json'},method='POST'),timeout=1.5) as res:
                ack=json.loads(res.read(4096)).get('ack')
            if ack!=ident:continue
            with sqlite3.connect(DB) as c:c.execute('UPDATE buffer SET confirmado=1,tentativas=tentativas+1 WHERE id=?',(ident,))
            count+=1
        except (urllib.error.URLError,TimeoutError,ValueError,OSError):
            with sqlite3.connect(DB) as c:c.execute('UPDATE buffer SET tentativas=tentativas+1 WHERE id=?',(ident,))
            break
    return count

def simulate(duration,interval,offline_start,offline_duration,central):
    setup();m=modelo();random.seed(42)
    start=time.monotonic();readings=0;anomalies=0;delivered=0;duration=max(0,duration)
    while time.monotonic()-start<duration:
        elapsed=time.monotonic()-start
        temp=14.8 if readings==5 else round(random.uniform(3.5,4.8),2)
        nivel=18.0 if readings==5 else round(random.uniform(76,84),2)
        if m.predict([[temp,nivel]])[0]==-1:anomalies+=1;print('IA: anomalia detectada',flush=True)
        if temp>8 or nivel<20:print('ALARME LOCAL: condição crítica (simulada)',flush=True)
        store(temp,nivel);readings+=1
        wan_up=not(offline_start<=elapsed<offline_start+offline_duration)
        if wan_up:delivered+=sync(central)
        time.sleep(interval)
    if not (offline_start<=time.monotonic()-start<offline_start+offline_duration):delivered+=sync(central)
    with sqlite3.connect(DB) as c:
        total,pending=c.execute('SELECT COUNT(*),SUM(CASE WHEN confirmado=0 THEN 1 ELSE 0 END) FROM buffer').fetchone()
    result={'elapsed_seconds':round(time.monotonic()-start,2),'generated_this_run':readings,
            'anomaly_events':anomalies,'acks_this_run':delivered,'buffer_total':total,'pending':pending,
            'central_url':central,'proof':'HTTP POST + idempotent ACK; MQTT/mTLS not implemented'}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=15)
    p.add_argument('--interval',type=float,default=1)
    p.add_argument('--offline-start',type=float,default=3)
    p.add_argument('--offline-duration',type=float,default=7)
    p.add_argument('--central',default=URL)
    a=p.parse_args();simulate(a.seconds,max(.1,a.interval),a.offline_start,a.offline_duration,a.central)
