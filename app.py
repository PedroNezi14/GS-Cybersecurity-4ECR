"""Vila Aurora: demonstração local de SQLi (antes/depois), login, MFA TOTP e RBAC.
AVISO: demonstração acadêmica, não deve operar equipamentos físicos.
"""
import os, sqlite3, hmac, hashlib, struct, time, secrets, re, json, logging
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, render_template_string, session, redirect, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = os.environ.get('VA_DB', 'vila_aurora.db')
# Seguro por padrão. Modo vulnerável somente habilitado explicitamente no laboratório local.
MODO_VULNERAVEL = os.environ.get('VA_DEMO_VULNERAVEL') == '1'
app = Flask(__name__)
app.secret_key = os.environ.get('VA_SESSION_KEY', secrets.token_hex(32))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict', PERMANENT_SESSION_LIFETIME=900)
ROLES = ('operador', 'tecnico', 'coordenacao', 'auditor')
logging.basicConfig(level=logging.INFO, format='%(message)s')


def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS acessos(id INTEGER PRIMARY KEY,voluntario TEXT NOT NULL,espaco TEXT NOT NULL,horario TEXT NOT NULL,perfil TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS usuarios(usuario TEXT PRIMARY KEY,senha_hash TEXT NOT NULL,papel TEXT NOT NULL,totp_secret TEXT NOT NULL)')
        if c.execute('SELECT COUNT(*) FROM acessos').fetchone()[0] == 0:
            c.executemany('INSERT INTO acessos(voluntario,espaco,horario,perfil) VALUES(?,?,?,?)',[
                ('Ana_Voluntaria','UBS - Camara Fria','2026-11-10 08:15','operador'),
                ('Carlos_Coordenacao','Abrigo Emergencia','2026-11-10 09:00','coordenacao'),
                ('Mariana_Saude','UBS - Recepcao','2026-11-10 10:30','tecnico'),
                ('Admin_Sistema','Centro Comunitario','2026-11-10 02:14','auditor')])
        # A provisão real deve usar gestor de identidade e segredos externos.
        password = os.environ.get('VA_DEMO_PASSWORD')
        totp = os.environ.get('VA_DEMO_TOTP_HEX')
        if password and totp and re.fullmatch(r'[0-9a-fA-F]{40,128}',totp):
            for role in ROLES:
                c.execute('INSERT OR IGNORE INTO usuarios VALUES(?,?,?,?)',
                          (role,generate_password_hash(password),role,totp))


def totp_at(secret_hex, moment):
    key = bytes.fromhex(secret_hex)
    counter = struct.pack('>Q',int(moment)//30)
    digest = hmac.new(key,counter,hashlib.sha1).digest()
    offset = digest[-1]&15
    n = struct.unpack('>I',digest[offset:offset+4])[0]&0x7fffffff
    return str(n%1000000).zfill(6)


def valid_totp(secret_hex,code):
    return isinstance(code,str) and re.fullmatch(r'\d{6}',code) is not None and any(
        hmac.compare_digest(totp_at(secret_hex,time.time()+30*i),code) for i in (-1,0,1))


def audit(event, outcome, user='anonymous'):
    logging.info(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'event':event,
                             'result':outcome,'user':user},ensure_ascii=False))


def login_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if 'papel' not in session: return redirect(url_for('login'))
        return func(*args,**kwargs)
    return inner

HTML='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vila Aurora | Supervisão</title><style>
body{font:17px system-ui,Arial;color:#172233;background:#f6f8fa;max-width:950px;margin:35px auto;padding:18px}main{background:white;padding:25px;border-radius:12px}input,button{font:inherit;padding:9px;margin:8px 0}button{background:#004f8a;color:white;border:0;border-radius:5px}button:focus,input:focus,a:focus{outline:3px solid #ffb700}table{width:100%;border-collapse:collapse}th,td{border:1px solid #9098a2;padding:10px;text-align:left}th{background:#123653;color:white}.erro{color:#a50000}.ok{color:#075c28}
</style></head><body><main><h1>Rede Vila Aurora — Painel de supervisão</h1><p>Usuário: {{ usuario }} | Papel: {{ papel }} | <a href="/sair">Sair</a></p><p>Consulta SQL: <strong>{{ 'DEMONSTRAÇÃO VULNERÁVEL' if vulneravel else 'SEGURA (parametrizada)' }}</strong></p><form method="get"><label for="busca">Buscar voluntário (até 60 caracteres)</label><p><input id="busca" name="busca" maxlength="60" value="{{ termo }}"><button type="submit">Buscar</button></p></form>{% if erro %}<p class="erro" role="alert">{{ erro }}</p>{% endif %}<table><caption>Registros autorizados de acesso</caption><thead><tr><th>ID</th><th>Voluntário</th><th>Espaço</th><th>Horário</th><th>Perfil</th></tr></thead><tbody>{% for r in rows %}<tr>{% for v in r %}<td>{{ v }}</td>{% endfor %}</tr>{% endfor %}</tbody></table></main></body></html>'''
LOGIN='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Vila Aurora | Login</title><main style="max-width:440px;margin:50px auto;font:18px system-ui"><h1>Vila Aurora</h1><p>Laboratório acadêmico com dados sintéticos</p><form method="post"><label>Usuário <input name="usuario" required></label><p><label>Senha <input type="password" name="senha" required></label></p><p><label>Código MFA (TOTP) <input name="codigo" inputmode="numeric" maxlength="6" required></label></p><button>Entrar</button></form>{% if erro %}<p role="alert">Credenciais inválidas.</p>{% endif %}</main>'''

@app.route('/login',methods=['GET','POST'])
def login():
    error=False
    if request.method=='POST':
        user=request.form.get('usuario','')[:40]
        with db() as c:
            record=c.execute('SELECT senha_hash,papel,totp_secret FROM usuarios WHERE usuario=?',(user,)).fetchone()
        if record and check_password_hash(record[0],request.form.get('senha','')) and valid_totp(record[2],request.form.get('codigo','')):
            session.clear();session['usuario']=user;session['papel']=record[1]
            audit('login','success',user)
            return redirect(url_for('index'))
        error=True; audit('login','failed',user)
    return render_template_string(LOGIN,erro=error)

@app.get('/sair')
def sair():
    session.clear();return redirect(url_for('login'))

@app.get('/')
@login_required
def index():
    termo=request.args.get('busca','')
    error=None; rows=[]
    if len(termo)>60 or any(ord(ch)<32 for ch in termo):
        error='Busca inválida: use até 60 caracteres imprimíveis.'
    else:
        with db() as c:
            try:
                # Somente auditor e coordenação podem consultar todos os perfis.
                if not MODO_VULNERAVEL:
                    if session['papel'] in ('auditor','coordenacao'):
                        rows=c.execute('SELECT id,voluntario,espaco,horario,perfil FROM acessos WHERE voluntario LIKE ? ORDER BY id LIMIT 100',('%'+termo+'%',)).fetchall()
                    else:
                        rows=c.execute('SELECT id,voluntario,espaco,horario,perfil FROM acessos WHERE voluntario LIKE ? AND perfil != ? ORDER BY id LIMIT 100',('%'+termo+'%','auditor')).fetchall()
                else:
                    # Exemplo vulnerável didático: não publicar esta configuração na rede.
                    query=f"SELECT id,voluntario,espaco,horario,perfil FROM acessos WHERE voluntario LIKE '%{termo}%'"
                    rows=c.execute(query).fetchall()
                audit('search','success',session['usuario'])
            except sqlite3.Error:
                audit('search','error',session['usuario']); error='Não foi possível concluir a pesquisa.'
    return render_template_string(HTML,rows=rows,erro=error,termo=termo,
                                  usuario=session['usuario'],papel=session['papel'],vulneravel=MODO_VULNERAVEL)

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"
    return response

if __name__=='__main__':
    init_db()
    app.run(host='127.0.0.1',port=5000,debug=False)
