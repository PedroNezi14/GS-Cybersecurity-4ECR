"""Coletor de telemetria simulado, local e idempotente; HTTP somente no loopback.
Para produção: MQTT sobre mTLS, WireGuard e ACL por tópico.
"""
import json,sqlite3,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
DB=os.getenv('VA_CENTRAL_DB','central.sqlite')
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path!='/ingest':self.send_error(404);return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>4096 or size<=0:self.send_error(413);return
            payload=json.loads(self.rfile.read(size))
            assert isinstance(payload['id'],str) and len(payload['id'])<=50
            with sqlite3.connect(DB) as c:
                c.execute('CREATE TABLE IF NOT EXISTS leituras(id TEXT PRIMARY KEY,ts TEXT,temp REAL,nivel REAL)')
                c.execute('INSERT OR IGNORE INTO leituras VALUES(?,?,?,?)',(payload['id'],payload['ts'],payload['temp'],payload['nivel']))
            blob=json.dumps({'ack':payload['id']}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(blob)));self.end_headers();self.wfile.write(blob)
        except (KeyError,ValueError,TypeError,AssertionError,sqlite3.Error):self.send_error(400)
if __name__=='__main__':
    print('Coletor de laboratório: http://127.0.0.1:8765/ingest')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
