# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Monitor da sessão de testes (12/10/2026): imprime UMA linha só quando algo importa.
  ERRO     linha nova no historico/vigia_erros.txt (avisos de rotina ficam de fora)
  CENTRAL  a Central parou de responder (ou voltou)
  PATCH    carreira aberta e o patch do técnico da IA não está ativo
  MARCO    a data do jogo passou de mais 30 dias (hora de medir o realismo)
  JOGO     o jogo fechou / abriu
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
CER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cerebro')
sys.path.insert(0, CER)
import memoria as M

H = os.path.join(CER, 'historico')
ERROS = os.path.join(H, 'vigia_erros.txt')
ROTINA = ('avisos', 'vigia reiniciado automaticamente')


def p(*a):
    print(time.strftime('%H:%M'), *a, flush=True)


tam = os.path.getsize(ERROS) if os.path.exists(ERROS) else 0
central_ok, jogo_pid, marco, patch_aviso = True, M.pid_do_jogo(), None, 0   # não avisa o estado inicial
while True:
    try:
        # erros novos do vigia
        if os.path.exists(ERROS) and os.path.getsize(ERROS) > tam:
            with open(ERROS, encoding='utf-8', errors='replace') as f:
                f.seek(tam)
                novo = f.read()
            tam = os.path.getsize(ERROS)
            for bloco in novo.split('\n20')[0:]:
                linha = bloco.strip().splitlines()[0] if bloco.strip() else ''
                if linha and not any(r in bloco[:200] for r in ROTINA):
                    p('ERRO', linha[:160], '|', ' '.join(bloco.strip().splitlines()[-1:])[:160])
        # Central
        try:
            urllib.request.urlopen('http://127.0.0.1:8765/', timeout=5)
            if not central_ok:
                p('CENTRAL voltou')
            central_ok = True
        except Exception:  # noqa: BLE001
            if central_ok:
                p('CENTRAL não responde')
            central_ok = False
        # jogo + patch + marcos
        pid = M.pid_do_jogo()
        if pid != jogo_pid:
            p('JOGO', 'aberto' if pid else 'fechado', pid or '')
            jogo_pid = pid
        pul = json.load(open(os.path.join(H, 'pulso_ML00000000.json'), encoding='utf-8')) if os.path.exists(os.path.join(H, 'pulso_ML00000000.json')) else {}
        data = pul.get('data_jogo')
        if pid and data and data[0] > 2030:
            h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
            b = M.ler(h, 0x141332202, 1) if h else None
            M.k32.CloseHandle(h)
            if b == b'\x03' and time.time() - patch_aviso > 900:
                p('PATCH técnico da IA não está ativo (modo 3) com a carreira aberta')
                patch_aviso = time.time()
            dia = dt.date(*data)
            if marco is None:
                marco = dia
            elif (dia - marco).days >= 30:
                p('MARCO data do jogo', dia.isoformat(), '— medir realismo')
                marco = dia
    except Exception as e:  # noqa: BLE001
        p('ERRO no monitor:', e)
    time.sleep(60)
