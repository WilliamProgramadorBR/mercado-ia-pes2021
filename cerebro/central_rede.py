# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""CENTRAL NO CELULAR (12/10/2026): a Central aceita conexões da rede de casa (Wi-Fi), protegida por PIN.

  - No próprio PC (127.0.0.1) nada muda: abre direto.
  - Outro aparelho na rede vê primeiro a tela do PIN (4 dígitos). Acertou: recebe um cookie (HttpOnly, SameSite=Strict)
    e o aparelho fica lembrado. 5 erros seguidos bloqueiam aquele endereço por 5 minutos.
  - O PIN e o endereço para digitar no celular ficam em historico/central_rede.json e aparecem no rodapé da Central no PC.
  - Para voltar a ser só no PC: "rede": false no central_rede.json (e reiniciar a Central).
"""
import hashlib
import json
import os
import secrets
import socket
import time

ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico', 'central_rede.json')
_falhas = {}   # ip -> [quantas, desde]


def config():
    try:
        with open(ARQ, encoding='utf-8') as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    if not c.get('pin') or not c.get('segredo'):
        c = {'rede': True, 'pin': f'{secrets.randbelow(10000):04d}', 'segredo': secrets.token_hex(16), **{k: v for k, v in c.items() if k == 'rede'}}
        os.makedirs(os.path.dirname(ARQ), exist_ok=True)
        with open(ARQ, 'w', encoding='utf-8') as f:
            json.dump(c, f, indent=1)
    return c


def token(c=None):
    c = c or config()
    return hashlib.sha256((c['segredo'] + c['pin']).encode()).hexdigest()[:40]


def ip_local():
    """IP do PC na rede de casa (nenhum pacote é enviado: o connect UDP só escolhe a interface)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def eh_local(ip):
    return ip in ('127.0.0.1', '::1', '::ffff:127.0.0.1')


def autorizado(ip, cookies):
    if eh_local(ip):
        return True
    return _cookie(cookies, 'cpin') == token()


def _cookie(cab, nome):
    for parte in (cab or '').split(';'):
        k, _, v = parte.strip().partition('=')
        if k == nome:
            return v
    return None


def tentar_pin(ip, pin):
    """(ok, mensagem). 5 erros seguidos = 5 minutos de bloqueio para aquele endereço."""
    n, desde = _falhas.get(ip, (0, 0.0))
    if time.time() - desde >= 300:   # janela de 5 minutos zerada
        n, desde = 0, time.time()
    if n >= 5:
        return False, 'Muitas tentativas. Espere 5 minutos.'
    if str(pin).strip() == config()['pin']:
        _falhas.pop(ip, None)
        return True, 'ok'
    _falhas[ip] = (n + 1, desde)
    return False, 'PIN errado.'


PAGINA_PIN = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Central do Técnico</title><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b100d;color:#e8efe9;font:16px system-ui,Segoe UI,Roboto,sans-serif}
.caixa{width:min(92vw,340px);background:#151d18;border:1px solid #26332b;border-radius:16px;padding:24px;text-align:center}
h1{font-size:20px;letter-spacing:1px;margin:0 0 6px}p{color:#8fa196;font-size:14px;margin:0 0 16px}
input{width:100%;box-sizing:border-box;font-size:28px;letter-spacing:12px;text-align:center;padding:10px;border-radius:10px;border:1px solid #26332b;background:#0b100d;color:#f5c542}
button{margin-top:12px;width:100%;padding:12px;border:0;border-radius:10px;background:#da291c;color:#fff;font-size:16px;font-weight:700}
#msg{color:#eb5757;min-height:20px;margin-top:10px;font-size:14px}</style></head><body>
<form class="caixa" id="f"><h1>⚽ Central do Técnico</h1><p>Digite o PIN que aparece no rodapé da Central, no computador.</p>
<input id="pin" inputmode="numeric" maxlength="4" autocomplete="one-time-code" autofocus><button>Entrar</button><div id="msg"></div></form>
<script>document.getElementById('f').onsubmit=async e=>{e.preventDefault();
const r=await fetch('/api/pin',{method:'POST',headers:{'Content-Type':'application/json','X-Central':'1'},body:JSON.stringify({pin:document.getElementById('pin').value})});
if(r.ok)location.reload();else document.getElementById('msg').textContent=await r.text();};</script></body></html>"""
