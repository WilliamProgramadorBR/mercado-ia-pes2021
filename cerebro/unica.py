# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Instância única (11/10/2026): o JOGAR_COM_MERCADO_IA.bat aberto duas vezes subia DOIS vigias e DUAS Centrais.
Dois vigias processam o mesmo save ao mesmo tempo e brigam pelo vestiario_estado.json (WinError 32: a reunião se
perdia). Um "mutex" nomeado do Windows deixa só o primeiro rodar; o segundo avisa e sai. O Windows solta a trava
sozinho quando o processo fecha (inclusive se for derrubado pelo REINICIAR_VIGIA.bat)."""
import sys

_trava = None


def garantir(nome):
    global _trava
    if sys.platform != 'win32':
        return
    import ctypes
    k = ctypes.windll.kernel32
    k.CreateMutexW.restype = ctypes.c_void_p
    _trava = k.CreateMutexW(None, False, f'Local\\PES_cerebro_{nome}')
    if k.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
        print(f'{nome} já está aberto em outra janela. Esta cópia vai fechar (duas cópias juntas corrompem a reunião).')
        import time
        time.sleep(4)
        sys.exit(0)
