"""TESTE de escrita do orçamento de transferências no save da ML (etapa 3b da Central do Técnico).

Uso:  python teste_orcamento.py <arquivo ML0000000X> <delta em R$> [--aplicar]
  ex.: python teste_orcamento.py ...\\ML00000000 10000000 --aplicar   (+R$ 10 milhões)
  sem --aplicar: faz tudo numa cópia e só confere (o save não é tocado).
Passos: backup -> descriptografa -> troca SÓ o orçamento (+0 do bloco de finanças, fora da parte comprimida)
        -> confere que só 4 bytes mudaram -> criptografa -> descriptografa de novo e confere -> substitui.
"""
import datetime as dt
import os
import shutil
import subprocess
import sys

import financas_save as F
from save_ml import SaveML

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
DECRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe')
ENCRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'encrypter21.exe')
TIME = 'MANCHESTER UNITED'


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd} -> {r.stderr or r.stdout}')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ml, delta = sys.argv[1], int(sys.argv[2])
    aplicar = '--aplicar' in sys.argv
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    work = os.path.join(TOOLS, 'save_work', 'teste_orcamento_' + stamp)
    os.makedirs(work)
    bk = os.path.join(TOOLS, 'Backups', 'teste_orcamento')
    os.makedirs(bk, exist_ok=True)
    shutil.copy2(ml, os.path.join(bk, os.path.basename(ml) + '_' + stamp))
    shutil.copy2(ml, os.path.join(work, 'original'))
    run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')])
    dat = os.path.join(work, 'dec', 'data.dat')
    d = open(dat, 'rb').read()
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL' + bytes(1))
    ti = s.find_team(TIME)
    antes = F.ler(d, ti)
    print('antes :', antes)
    d2 = F.com_orcamento(d, ti, antes['orcamento_transf'] + delta)
    diff = [i for i in range(len(d)) if d[i] != d2[i]]
    assert len(d2) == len(d) and diff and max(diff) - min(diff) < 4 and min(diff) >= antes['pos'], diff[:10]
    print('depois:', F.ler(d2, ti))
    open(dat, 'wb').write(d2)
    out = os.path.join(work, 'ML_novo')
    run([ENCRYPT, os.path.join(work, 'dec'), out])
    run([DECRYPT, out, os.path.join(work, 'check')])
    assert open(os.path.join(work, 'check', 'data.dat'), 'rb').read() == d2, 'ida e volta não bateu'
    print('ida e volta OK')
    if aplicar:
        shutil.copy2(out, ml)
        print('SAVE SUBSTITUÍDO:', ml)
    else:
        print('ensaio: save NÃO foi tocado. Resultado em', out)


if __name__ == '__main__':
    main()
