"""Quatro regras demonstrativas RT-13, com dados sintéticos. Não é integração SIEM."""
from datetime import datetime

def analisar(evento):
    tipo=evento.get('tipo')
    if tipo=='vpn_login' and (evento.get('fora_janela') or evento.get('origem_incomum')):return 'VA-101 VPN anômala'
    if tipo=='http' and any(x in evento.get('query','').lower() for x in ('union select',"' or '",'--')):return 'VA-102 possível SQLi'
    if tipo=='mqtt_connect' and not evento.get('cert_valido',False):return 'VA-103 certificado inválido'
    if tipo=='atuador' and (evento.get('fora_janela') or evento.get('papel') not in ('tecnico','coordenacao')):return 'VA-104 comando não autorizado'
    return None

if __name__=='__main__':
    eventos=[{'tipo':'vpn_login','fora_janela':True},{'tipo':'http','query':"' OR '1'='1"},
             {'tipo':'mqtt_connect','cert_valido':False},{'tipo':'atuador','papel':'operador'}]
    for e in eventos:print(analisar(e))
