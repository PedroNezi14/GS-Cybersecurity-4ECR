import time
import random
import sqlite3
from datetime import datetime
import numpy as np
from sklearn.ensemble import IsolationForest

BUFFER_DB = "buffer_borda.db"

def configurar_buffer_local():
    conn = sqlite3.connect(BUFFER_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetria_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temp_camara_fria REAL,
            nivel_reservatorio REAL,
            sincronizado INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def treinar_modelo_ia():
    # Dados históricos normais: Temp câmara fria (~4.0°C) e Nível caixa d'água (~80%)
    rng = np.random.RandomState(42)
    dados_normais = np.column_stack([
        rng.normal(loc=4.0, scale=0.5, size=100),
        rng.normal(loc=80.0, scale=3.0, size=100)
    ])
    modelo = IsolationForest(contamination=0.05, random_state=42)
    modelo.fit(dados_normais)
    return modelo

def executar_simulacao():
    configurar_buffer_local()
    modelo_ia = treinar_modelo_ia()
    link_internet_ativo = True

    print("=== Iniciando Nó de Borda Autônomo (UBS & Escola - Vila Aurora) ===\n")

    for ciclo in range(1, 9):
        # Simula queda da fibra óptica entre os ciclos 3 e 6 (Teste de Caos)
        if ciclo == 3:
            link_internet_ativo = False
            print("\n[ALERTA DE REDE] Link WAN caiu! Operando em modo autônomo local (Store-and-Forward)...\n")
        elif ciclo == 7:
            link_internet_ativo = True
            print("\n[REDE RESTABELECIDA] Link WAN voltou! Iniciando reconciliação do buffer local...\n")

        # Gera leituras (no ciclo 5 simula ataque/anomalia na câmara fria e bomba)
        if ciclo == 5:
            temp = 14.8   # Temperatura crítica fora da faixa segura (2°C a 8°C)
            nivel = 18.0  # Esvaziamento rápido do reservatório
        else:
            temp = round(random.uniform(3.5, 4.8), 2)
            nivel = round(random.uniform(76.0, 84.0), 2)

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Inferência da IA Defensiva na borda (RT-16)
        predicao = modelo_ia.predict([[temp, nivel]])[0]
        status_ia = "ANOMALIA DETECTADA" if predicao == -1 else "NORMAL"

        # 2. Regra de controle local autônoma (RT-02)
        if temp > 8.0:
            print(f"[{agora}] [ALARME LOCAL UBS] Temperatura crítica ({temp}°C)! Sirene local acionada.")

        # 3. Armazenamento e encaminhamento (Store-and-Forward)
        conn = sqlite3.connect(BUFFER_DB)
        cursor = conn.cursor()
        status_sync = 1 if link_internet_ativo else 0
        cursor.execute(
            "INSERT INTO telemetria_buffer (timestamp, temp_camara_fria, nivel_reservatorio, sincronizado) VALUES (?, ?, ?, ?)",
            (agora, temp, nivel, status_sync)
        )

        if link_internet_ativo:
            cursor.execute("SELECT COUNT(*) FROM telemetria_buffer WHERE sincronizado = 0")
            pendentes = cursor.fetchone()[0]
            if pendentes > 0:
                cursor.execute("UPDATE telemetria_buffer SET sincronizado = 1 WHERE sincronizado = 0")
                print(f"[RECONCILIAÇÃO] {pendentes} registros armazenados offline foram sincronizados com a nuvem sem perda de dados.")

        conn.commit()
        conn.close()

        print(f"Ciclo {ciclo} | WAN: {'ON' if link_internet_ativo else 'OFF'} | Temp: {temp}°C | Nível Água: {nivel}% | IA: {status_ia}")
        time.sleep(1)

if __name__ == "__main__":
    executar_simulacao()