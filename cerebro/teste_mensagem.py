"""TESTE: coloca UMA mensagem nativa na caixa de Mensagens da Master League.

Uso:  python teste_mensagem.py <arquivo ML0000000X> <tipo> [reg:id ...] [--aplicar]
  ex.: python teste_mensagem.py ...\\ML00000000 340 355:140699 359:60512 --aplicar
       (tipo 340 = "11 melhores do mês" citando os jogadores dados)
  sem --aplicar: faz tudo numa cópia e só confere (o save não é tocado).
A data da mensagem é a da mensagem mais nova da caixa (o "hoje" do jogo).
Passos: backup -> descriptografa -> insere na próxima posição livre -> confere que só a posição e o contador
        mudaram -> criptografa -> descriptografa de novo e confere -> substitui.
"""
import datetime as dt
import os
import shutil
import struct
import subprocess
import sys

import mensagens_save as M

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
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ml, tipo = args[0], int(args[1])
    jogs = [tuple(int(x) for x in a.split(':')) for a in args[2:]]
    aplicar = '--aplicar' in sys.argv
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    work = os.path.join(TOOLS, 'save_work', 'teste_mensagem_' + stamp)
    os.makedirs(work)
    bk = os.path.join(TOOLS, 'Backups', 'teste_mensagem')
    os.makedirs(bk, exist_ok=True)
    shutil.copy2(ml, os.path.join(bk, os.path.basename(ml) + '_' + stamp))
    shutil.copy2(ml, os.path.join(work, 'original'))
    run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')])
    dat = os.path.join(work, 'dec', 'data.dat')
    d = open(dat, 'rb').read()
    ini = M.achar_caixa(d)
    hoje = struct.unpack_from('<HBB', d, ini + M.mais_nova(d, ini) * M.REC + 8)
    d2, pos = M.inserir(d, tipo, hoje, jogadores=jogs)
    dif = [i for i in range(len(d)) if d[i] != d2[i]]
    slot = range(ini + pos * M.REC, ini + (pos + 1) * M.REC)
    assert all(i in slot or i == ini + M.INDICE_REL for i in dif), 'mudou algo fora da mensagem/contador'
    print(f'mensagem tipo {tipo} ({M.TIPOS.get(tipo, "?")}) em {hoje[2]:02d}/{hoje[1]:02d}/{hoje[0]}, posição {pos}, '
          f'jogadores {jogs}; bytes alterados: {len(dif)}')
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
