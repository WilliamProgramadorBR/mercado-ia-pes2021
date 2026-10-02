"""Vigia do Mercado IA: roda em segundo plano junto com o jogo.

Espera o pedido do overlay (mercado_pedido.txt, criado pela tecla 8 do módulo MercadoIA) e, quando
um save de Master League for gravado DEPOIS do pedido, roda o aplicar.py nesse save.
Comunica com o overlay por mercado_status.txt (pasta do jogo). Encerra sozinho quando o jogo fecha.
"""
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.normpath(os.environ.get(
    'PES2021_GAME_DIR', os.path.join(HERE, '..', '..', 'eFootball PES 2021')))
REQUEST = os.path.join(GAME_DIR, 'mercado_pedido.txt')
SNAP = os.path.join(GAME_DIR, 'mercado_snap.bin')
STATUS = os.path.join(GAME_DIR, 'mercado_status.txt')
SAVE_GLOBS = [
    os.path.expandvars(r'%USERPROFILE%\OneDrive\Documentos\KONAMI\eFootball PES 2021 SEASON UPDATE\*\save'),
    os.path.expandvars(r'%USERPROFILE%\OneDrive\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\*\save'),
    os.path.expandvars(r'%USERPROFILE%\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\*\save'),
]


def status(msg):
    with open(STATUS, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def save_dirs():
    configured = os.environ.get('PES2021_SAVE_DIR')
    if configured:
        return [os.path.normpath(configured)] if os.path.isdir(configured) else []
    out = []
    for g in SAVE_GLOBS:
        out += glob.glob(g)
    return out


def ml_files():
    return [f for d in save_dirs() for f in glob.glob(os.path.join(d, 'ML0000000?'))]


def game_running():
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq PES2021.exe'], capture_output=True, text=True)
    return 'PES2021.exe' in r.stdout


def wait_stable(path, secs=3):
    last = None
    while True:
        cur = (os.path.getsize(path), os.path.getmtime(path))
        if cur == last:
            return
        last = cur
        time.sleep(secs)


def main():
    print('Vigia do Mercado IA iniciado. Pastas de save:', save_dirs() or 'NENHUMA ENCONTRADA', flush=True)
    if os.path.exists(STATUS):
        os.remove(STATUS)
    seen_game = False
    idle_since = time.time()
    while True:
        running = game_running()
        if running:
            seen_game, idle_since = True, time.time()
        elif seen_game or time.time() - idle_since > 600:
            print('jogo fechado: vigia encerrado', flush=True)
            return
        if os.path.exists(REQUEST):
            t_req = os.path.getmtime(REQUEST)
            newer = [f for f in ml_files() if os.path.getmtime(f) > t_req + 1]
            if not newer:
                status('Aguardando você SALVAR a carreira...')
            else:
                ml = max(newer, key=os.path.getmtime)
                status('Save detectado. Aplicando o mercado (pode levar 1-3 minutos)...')
                wait_stable(ml)
                os.remove(REQUEST)
                r = subprocess.run([sys.executable, os.path.join(HERE, 'aplicar.py'), ml, SNAP],
                                   capture_output=True, text=True, cwd=HERE)
                if r.returncode == 0 and 'SAVE ATUALIZADO' in r.stdout:
                    status('PRONTO! Volte ao menu e CARREGUE a carreira (sem salvar antes).')
                elif r.returncode == 0:
                    status('Nenhuma transferência aplicada nesta janela.')
                else:
                    status('ERRO no mercado (save não alterado). Veja cerebro\\historico.')
                    print(r.stdout, r.stderr, flush=True)
        time.sleep(3)


if __name__ == '__main__':
    main()
