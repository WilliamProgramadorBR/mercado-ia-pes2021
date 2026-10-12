"""TESTE: dá um APELIDO a um jogador (campo +80 do registro) e manda a mensagem nativa "Apelido do X" (tipo 89).

Uso:  python teste_apelido.py <arquivo ML0000000X> <reg:id> <código do apelido> [--aplicar]
  ex.: python teste_apelido.py ...\\ML00000000 3665712035:116314 728 --aplicar   (Justin Omoregie -> "El Diablo")
Códigos: historico/apelidos_catalogo.json (trechos da lista de apelidos do jogo, ancorados em apelidos reais).
Formato (09/10/2026): +80 do registro do jogador = u32 (0x1D << 16) | código; 0 = sem apelido.
A mensagem tipo 89 leva o mesmo u32 em +64 e o jogador em +40.
"""
import datetime as dt
import os
import shutil
import struct
import subprocess
import sys

import jogadores_save as js
import mensagens_save as M

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
DECRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe')
ENCRYPT = os.path.join(TOOLS, 'pesXdecrypter', 'encrypter21.exe')
GRUPO = 0x1D


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd} -> {r.stderr or r.stdout}')


def com_apelido(r, codigo):
    r = bytearray(r)
    struct.pack_into('<I', r, 80, (GRUPO << 16) | codigo)
    return bytes(r)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ml, k, codigo = args[0], tuple(int(x) for x in args[1].split(':')), int(args[2])
    aplicar = '--aplicar' in sys.argv
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    work = os.path.join(TOOLS, 'save_work', 'teste_apelido_' + stamp)
    os.makedirs(work)
    bk = os.path.join(TOOLS, 'Backups', 'teste_apelido')
    os.makedirs(bk, exist_ok=True)
    shutil.copy2(ml, os.path.join(bk, os.path.basename(ml) + '_' + stamp))
    shutil.copy2(ml, os.path.join(work, 'original'))
    run([DECRYPT, os.path.join(work, 'original'), os.path.join(work, 'dec')])
    dat = os.path.join(work, 'dec', 'data.dat')
    d = open(dat, 'rb').read()
    regs = js.registros(js.blob(d))
    antes = struct.unpack_from('<I', regs[k], 80)[0]
    print('apelido antes:', antes & 0xFFFF if antes else 'nenhum')
    # 1) apelido no registro do jogador (parte comprimida)
    d2 = js.regravar(d, {k: com_apelido(regs[k], codigo)})
    r2 = js.registros(js.blob(d2))
    assert [x for x in regs if regs[x] != r2[x]] == [k], 'mudou outro jogador'
    # 2) mensagem nativa "Apelido do X"
    cx = M.achar_caixa(d2)
    hoje = struct.unpack_from('<HBB', d2, cx + M.mais_nova(d2, cx) * M.REC + 8)
    d3, pos = M.inserir(d2, 89, hoje, jogadores=[k], extra={64: ('<I', (GRUPO << 16) | codigo)})
    a, b = cx + pos * M.REC, cx + (pos + 1) * M.REC
    idx = cx + M.INDICE_REL
    assert d2[:a] == d3[:a] and d2[b:idx] == d3[b:idx] and d2[idx + 1:] == d3[idx + 1:], 'mensagem: mudou algo fora'
    print(f'apelido {codigo} gravado; mensagem "Apelido do X" em {hoje[2]:02d}/{hoje[1]:02d}/{hoje[0]}, posição {pos}')
    open(dat, 'wb').write(d3)
    out = os.path.join(work, 'ML_novo')
    run([ENCRYPT, os.path.join(work, 'dec'), out])
    run([DECRYPT, out, os.path.join(work, 'check')])
    assert open(os.path.join(work, 'check', 'data.dat'), 'rb').read() == d3, 'ida e volta não bateu'
    print('ida e volta OK')
    if aplicar:
        shutil.copy2(out, ml)
        print('SAVE SUBSTITUÍDO:', ml)
    else:
        print('ensaio: save NÃO foi tocado. Resultado em', out)


if __name__ == '__main__':
    main()
