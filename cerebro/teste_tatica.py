"""TESTE: o computador usa o plano de jogo gravado no save? (12/10/2026)

Uso:  python teste_tatica.py <arquivo ML0000000X> <TIME> campo=valor ... [--aplicar]
  ex.: python teste_tatica.py ...\\ML00000000 BURNLEY estilo_ofensivo=1 saida_de_bola=1 linha_defensiva=10 --aplicar
  sem --aplicar: tudo numa cópia, só confere (o save não é tocado).
Passos: backup -> descriptografa -> troca SÓ os bytes do plano de jogo do time -> confere que nada mais mudou ->
        criptografa -> descriptografa de novo e confere -> substitui (troca_save: só se o jogo não salvou no meio).
"""
import datetime as dt
import os
import shutil
import subprocess
import sys

import tatica_save as T
import troca_save
from save_ml import SaveML

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
DECRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe')
ENCRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'encrypter21.exe')


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd} -> {r.stderr or r.stdout}')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ml, time_nome = sys.argv[1], sys.argv[2]
    valores = dict(a.split('=') for a in sys.argv[3:] if '=' in a)
    aplicar = '--aplicar' in sys.argv
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    work = os.path.join(TOOLS, 'save_work', 'teste_tatica_' + stamp)
    os.makedirs(work)
    bk = os.path.join(TOOLS, 'Backups', 'teste_tatica')
    os.makedirs(bk, exist_ok=True)
    troca_save.copiar_compartilhado(ml, os.path.join(work, 'original'))
    shutil.copy2(os.path.join(work, 'original'), os.path.join(bk, os.path.basename(ml) + '_' + stamp))
    run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')])
    dat = os.path.join(work, 'dec', 'data.dat')
    d = open(dat, 'rb').read()
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL' + bytes(1))
    ti = s.find_team(time_nome)
    print(f'{time_nome} (índice {ti}, técnico {T.tecnico(d, ti)})')
    print('antes :', T.ler(d, ti))
    d2 = T.com_tatica(d, ti, **valores)
    o = T.bloco(d, ti)
    diff = [i for i in range(len(d)) if d[i] != d2[i]]
    assert len(d2) == len(d) and diff and all(o <= i < o + T.TAM for i in diff), diff[:10]
    print('depois:', T.ler(d2, ti), f'({len(diff)} bytes, todos no bloco do {time_nome})')
    open(dat, 'wb').write(d2)
    out = os.path.join(work, 'ML_novo')
    run([ENCRYPT, os.path.join(work, 'dec'), out])
    run([DECRYPT, out, os.path.join(work, 'check')])
    assert open(os.path.join(work, 'check', 'data.dat'), 'rb').read() == d2, 'ida e volta não bateu'
    print('ida e volta OK')
    if aplicar:
        troca_save.substituir(ml, out, os.path.join(work, 'original'))
        print('SAVE SUBSTITUÍDO:', ml, '| backup em', bk)
    else:
        print('ensaio: save NÃO foi tocado. Resultado em', out)


if __name__ == '__main__':
    main()
