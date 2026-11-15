import sqlite3
from flask import Flask, request, render_template_string

app = Flask(__name__)

# Altere para False para demonstrar a versão vulnerável (Antes)
# Deixe como True para a versão corrigida (Depois)
MODO_SEGURO = False

DB_NAME = "vila_aurora.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acessos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voluntario TEXT NOT NULL,
            espaco TEXT NOT NULL,
            horario TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM acessos")
    if cursor.fetchone()[0] == 0:
        dados_sinteticos = [
            ("Ana_Voluntaria", "UBS - Camara Fria", "2026-11-10 08:15", "tecnico"),
            ("Carlos_Coordenacao", "Abrigo Emergencia", "2026-11-10 09:00", "coordenacao"),
            ("Mariana_Saude", "UBS - Recepção", "2026-11-10 10:30", "operador"),
            ("Admin_Sistema", "Centro Comunitario", "2026-11-10 02:14", "auditor_secreto")
        ]
        cursor.executemany(
            "INSERT INTO acessos (voluntario, espaco, horario, perfil) VALUES (?, ?, ?, ?)",
            dados_sinteticos
        )
    conn.commit()
    conn.close()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Rede Comunitária Vila Aurora - Supervisão</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #f4f6f8; color: #1a1a1a; }
        .badge { padding: 6px 12px; border-radius: 4px; font-weight: bold; color: white; }
        .seguro { background: #1e7e34; }
        .vulneravel { background: #c82333; }
        input[type="text"] { padding: 8px; width: 300px; border: 1px solid #555; }
        button { padding: 8px 16px; background: #0056b3; color: white; border: none; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }
        th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
        th { background: #003366; color: white; }
    </style>
</head>
<body>
    <h1>Painel de Supervisão — Vila Aurora</h1>
    <p>Status de Segurança do Banco: 
        {% if modo_seguro %}
            <span class="badge seguro">MODO SEGURO (Consultas Parametrizadas)</span>
        {% else %}
            <span class="badge vulneravel">MODO VULNERÁVEL (Suscetível a SQL Injection)</span>
        {% endif %}
    </p>

    <form method="GET" action="/">
        <label for="busca"><strong>Buscar Histórico de Acessos (Voluntário):</strong></label><br><br>
        <input type="text" id="busca" name="busca" value="{{ termo }}" placeholder="Ex: Ana_Voluntaria">
        <button type="submit">Pesquisar</button>
    </form>

    {% if erro %}
        <p style="color: #c82333;"><strong>Aviso:</strong> {{ erro }}</p>
    {% endif %}

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Voluntário</th>
                <th>Espaço Comunitário</th>
                <th>Horário</th>
                <th>Perfil RBAC</th>
            </tr>
        </thead>
        <tbody>
            {% for row in resultados %}
            <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    termo = request.args.get("busca", "")
    resultados = []
    erro = None

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        if termo:
            if MODO_SEGURO:
                # RT-08: Consulta parametrizada prevenindo SQL Injection
                cursor.execute(
                    "SELECT id, voluntario, espaco, horario, perfil FROM acessos WHERE voluntario LIKE ?",
                    (f"%{termo}%",)
                )
            else:
                # Versão legada vulnerável (concatenação direta de string)
                query_vulneravel = f"SELECT id, voluntario, espaco, horario, perfil FROM acessos WHERE voluntario LIKE '%{termo}%'"
                cursor.execute(query_vulneravel)
        else:
            cursor.execute("SELECT id, voluntario, espaco, horario, perfil FROM acessos")

        resultados = cursor.fetchall()
    except Exception:
        # RT-08: Mensagem genérica sem vazar estrutura do banco de dados
        erro = "Não foi possível processar a busca. Verifique os caracteres informados."
    finally:
        conn.close()

    return render_template_string(
        HTML_TEMPLATE,
        resultados=resultados,
        termo=termo,
        modo_seguro=MODO_SEGURO,
        erro=erro
    )

if __name__ == "__main__":
    init_db()
    # Roda apenas localmente (127.0.0.1) para não expor portas na internet (RT-06)
    app.run(host="127.0.0.1", port=5000, debug=False)