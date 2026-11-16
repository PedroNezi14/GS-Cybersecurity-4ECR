# Global Solution FIAP 2026.2 — Vila Aurora (4ECR)
**Autores:** Pedro Nezi, Gustavo Kenji e Gabriel Henrique.

## Escopo, segurança e honestidade das evidências
É um protótipo acadêmico com dados sintéticos. Os scripts Python implementam:
- aplicação Flask parametrizada por padrão, RBAC de consulta, login com senha hash e MFA TOTP;
- modo SQLi intencionalmente vulnerável **somente para laboratório local**, habilitado por `VA_DEMO_VULNERAVEL=1`;
- detecção local Isolation Forest e regras independentes para alarme da câmara fria e nível d'água;
- buffer SQLite persistente, envio HTTP no loopback, confirmação por ACK e deduplicação no coletor;
- detector demonstrativo das quatro condições da RT-13.

**Não demonstrado como implantado:** broker MQTT local mTLS, PKI com CA/CRL/rotação real, WireGuard, MFA no acesso administrativo VPN, segmentação VLAN, WAF, Wazuh/SIEM, SOAR de produção, firmware assinado. Exemplos de configuração **não são provas** de execução. A simulação no loopback HTTP **não equivale** a mTLS/MQTT real. Nenhum script tem acesso a atuadores reais.

## Preparar
Python 3.10+; instalar dependências em venv (`python -m venv .venv`, ativar e `pip install -r requirements.txt`). Nunca conectar o modo vulnerável à internet.

## Painel Flask
Gerar senha e segredo TOTP sintéticos em variáveis de ambiente. Use senha de teste forte e segredo hexadecimal aleatório de 20 bytes (por exemplo, `python -c "import secrets;print(secrets.token_hex(20))"`).

```sh
export VA_DEMO_PASSWORD='SENHA_TEMPORARIA_LOCAL'
export VA_DEMO_TOTP_HEX='COLE_40_CARACTERES_HEX'
export VA_SESSION_KEY='COLE_UMA_CHAVE_ALEATORIA_LONGA'
python app.py
```

Usuários sintéticos: `operador`, `tecnico`, `coordenacao`, `auditor`. Gerar código TOTP local com `python -c "import os,time;from app import totp_at;print(totp_at(os.environ['VA_DEMO_TOTP_HEX'],time.time()))"` (uso somente na demonstração). Banco persistente: se mudar credenciais, apagar o DB **sintético** e reiniciar para reprovisionar.

SQLi *antes*: em outro terminal, ambiente isolado, `VA_DEMO_VULNERAVEL=1 python app.py`; autenticar e submeter `%' OR '1'='1' -- ` (pode exigir URL encode). SQLi *depois*: iniciar sem a variável, mesma entrada é tratada como valor literal. A versão segura impede registros de auditor para `operador` e `tecnico`, mas a demonstração não substitui uma implementação IAM corporativa. Falta rate-limit/login lockout e CSRF robusto para produção.

## Borda e coletor
Terminal 1: `python central.py`; terminal 2: `python borda_ia.py --seconds 15 --offline-start 3 --offline-duration 7 --interval 1`. Após retomada, o coletor confirma IDs. Duplicatas são ignoradas pela chave primária. Para o teste RT-23 **real**, realizar um ensaio cronometrado de >=1800s com central indisponível e reunir logs e métricas: a simulação curta NÃO o comprova.

`python avaliar_ia.py`: mede precisão, recall, falsos positivos em dataset sintético independente, seed documentada. Não é validação operacional em sensores reais nem assegura desempenho em deriva temporal.

`python detectores.py`: quatro regras RT-13 somente demonstrativas, não integradas a SIEM. Validar em ambiente de laboratório antes de declarar RT-13 atendido.

## Evidências que ainda faltam para Excelente
1. Execução do MQTT local + autenticação mTLS com certificado próprio por dispositivo; captura do handshake aceito/rejeitado, CRL e rotação.
2. WireGuard entre VMs, MFA administrativo, firewall e segmentação com matrizes de portas e testes negativos.
3. WAF / rate-limit / SIEM com registros de detecção reais das quatro regras.
4. Gophish apenas para contas fictícias, registrar enviados/abertos/clicados/submetidos/reportados, consentimento e plano de conscientização.
5. Reprodução controlada do INC-VA-0712, aquisição forense, SHA-256 dos arquivos realmente coletados e cadeia de custódia preenchida.
6. Teste WAN offline de pelo menos 30 min; métricas mensuradas CPU, memória, banda, energia, MTTD, MTTR, uptime e perdas.
7. Vídeo dentro do tempo definido pelo professor, aprovação humana para ação crítica, documentação da participação de IA e defesa oral.

## Uso de IA (transparência)
Ferramentas de IA foram usadas como auxílio de revisão de código e redação técnica. Autores devem validar, executar os testes e assumir as conclusões antes da submissão.
