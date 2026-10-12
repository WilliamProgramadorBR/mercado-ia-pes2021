"""TESTE de escrita na tabela de jogadores: troca a seta de condição de UM jogador no save da ML.

Uso:  python teste_seta.py <arquivo ML0000000X> [--aplicar]
  sem --aplicar: faz tudo numa cópia e só confere (o save não é tocado).
Passos: backup -> descriptografa -> troca a seta -> regrava o bloco -> criptografa ->
        descriptografa de novo e confere byte a byte -> (com --aplicar) substitui o save.
"""
import datetime as dt
import os
import shutil
import subprocess
import sys

import jogadores_save as js

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
DECRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe')
ENCRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'encrypter21.exe')
ALVO = (0x16b, 0x20f13)  # Senne Lammens (seta 1 no save de 09/10 14:07)
SETA_NOVA = 4            # verde para cima


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd} -> {r.stderr or r.stdout}')


def main():
    ml = sys.argv[1]
    aplicar = '--aplicar' in sys.argv
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    work = os.path.join(TOOLS, 'save_work', 'teste_seta_' + stamp)
    os.makedirs(work)
    bk = os.path.join(TOOLS, 'Backups', 'teste_seta')
    os.makedirs(bk, exist_ok=True)
    shutil.copy2(ml, os.path.join(bk, os.path.basename(ml) + '_' + stamp))
    shutil.copy2(ml, os.path.join(work, 'original'))

    run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')])
    dat = os.path.join(work, 'dec', 'data.dat')
    d = open(dat, 'rb').read()
    regs = js.registros(js.blob(d))
    antes = js.campos(regs[ALVO])
    print('antes :', antes)
    novo = js.set_seta(regs[ALVO], SETA_NOVA)
    d2 = js.regravar(d, {ALVO: novo})
    assert len(d2) == len(d)
    # conferência: só o registro do alvo mudou no blob; fora do blob, nada mudou além do bloco
    r2 = js.registros(js.blob(d2))
    diff = [k for k in regs if regs[k] != r2[k]]
    assert diff == [ALVO], diff
    print('depois:', js.campos(r2[ALVO]))
    open(dat, 'wb').write(d2)

    out = os.path.join(work, 'ML_novo')
    run([ENCRYPT, os.path.join(work, 'dec'), out])
    run([DECRYPT, out, os.path.join(work, 'check')])
    chk = open(os.path.join(work, 'check', 'data.dat'), 'rb').read()
    assert chk == d2, 'ida e volta não bateu'
    print('ida e volta OK')
    if aplicar:
        shutil.copy2(out, ml)
        print('SAVE SUBSTITUÍDO:', ml)
    else:
        print('ensaio: save NÃO foi tocado. Resultado em', out)


if __name__ == '__main__':
    main()
