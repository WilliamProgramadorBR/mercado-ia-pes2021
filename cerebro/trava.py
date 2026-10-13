# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Trava entre processos (vigia, Central, scripts): um arquivo bloqueado com msvcrt.locking.

Uso:  with trava('diario'): ...
Serve para o diário de ações da Central (append de vários processos) e para a escrita na memória do jogo
(Central e vigia nunca escrevem ao mesmo tempo).
"""
import contextlib
import msvcrt
import os
import time

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico')


@contextlib.contextmanager
def trava(nome, espera=60):
    os.makedirs(PASTA, exist_ok=True)
    f = open(os.path.join(PASTA, f'{nome}.lock'), 'a+b')
    try:
        fim = time.time() + espera
        while True:
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.time() > fim:
                    raise TimeoutError(f'trava "{nome}" ocupada há mais de {espera} s')
                time.sleep(0.1)
        try:
            yield
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        f.close()
