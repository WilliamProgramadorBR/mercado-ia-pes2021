# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Laboratório: compara saves da carreira de TESTE (copiados pelo vigia) para achar campos do jogo. SOMENTE LEITURA.

Uso:
  python laboratorio.py lista                       # cópias guardadas (por carreira) e a data do jogo de cada uma
  python laboratorio.py diff <A> <B> [--max N]       # campos que mudaram de A para B (nomes das cópias ou índices)
As cópias ficam em historico/laboratorio/<arquivo>/<data_hora>; a versão descriptografada vai para
historico/laboratorio/_dec/<arquivo>_<data_hora>.dat (feita uma vez só).
O diff ignora as áreas que mudam o tempo todo: blocos comprimidos dos jogadores e a faixa das súmulas.
"""
import glob
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, 'historico', 'laboratorio')
DEC = os.path.join(LAB, '_dec')
import caminhos  # noqa: E402
GAME_DIR = caminhos.GAME_DIR
try:   # caminho relativo à pasta do jogo (em outro disco não existe relativo: usa o completo)
    DECRYPT_REL = os.path.relpath(caminhos.DECRYPT, GAME_DIR)
except ValueError:
    DECRYPT_REL = caminhos.DECRYPT


def copias():
    out = []
    for slot in sorted(os.listdir(LAB)) if os.path.isdir(LAB) else []:
        if slot.startswith('_'):
            continue
        for f in sorted(os.listdir(os.path.join(LAB, slot))):
            out.append((slot, f, os.path.join(LAB, slot, f)))
    return out


def descriptografar(path):
    slot, nome = os.path.basename(os.path.dirname(path)), os.path.basename(path)
    destino = os.path.join(DEC, f'{slot}_{nome}.dat')
    if os.path.exists(destino):
        return destino
    tmp = os.path.join(DEC, '_tmp')
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    exe = os.path.normpath(os.path.join(GAME_DIR, DECRYPT_REL))
    r = subprocess.run([exe, os.path.abspath(path), os.path.abspath(tmp)], cwd=GAME_DIR, capture_output=True, text=True)
    dat = os.path.join(tmp, 'data.dat')
    if not os.path.exists(dat):
        raise RuntimeError(f'falhou ao descriptografar {path}: {r.stdout} {r.stderr}')
    shutil.move(dat, destino)
    shutil.rmtree(tmp, ignore_errors=True)
    return destino


def data_do_jogo(d):
    try:   # caixa em posição fixa: data da mensagem mais recente (vale também para carreira recém-criada)
        datas = [dt_ for _i, _t, dt_, _r in caixa(d)]
        if datas:
            return max(datas)
    except Exception:  # noqa: BLE001
        pass
    try:
        import mensagens_save as MS
        cx = MS.achar_caixa(d)
        return struct.unpack_from('<HBB', d, cx + MS.mais_nova(d, cx) * MS.REC + 8)
    except Exception:  # noqa: BLE001
        return None


def faixas_ignoradas(d):
    out = [(0x400000, 0x900000)]   # súmulas
    try:
        import jogadores_save as js
        for ini, tam, _raw in js.blocos(d):
            out.append((ini - 16, ini + tam))   # cabeçalho de 12 bytes + bloco zlib
    except Exception:  # noqa: BLE001
        pass
    return out


def diff(a, b, maximo=400):
    ign = faixas_ignoradas(a) + faixas_ignoradas(b)
    n = min(len(a), len(b))
    runs, i = [], 0
    while i < n:
        if a[i] != b[i] and not any(x <= i < y for x, y in ign):
            j = i
            while j < n and (a[j] != b[j] or (j + 1 < n and a[j + 1] != b[j + 1])) and j - i < 64:
                j += 1
            runs.append((i, j))
            i = j
        i += 1
    return runs[:maximo], len(runs)


CAIXA = 0xBE8B80   # caixa de mensagens: posição fixa (igual no Man Utd e na carreira de teste, 10/10/2026)


def caixa(d):
    """[(posição, tipo, data, bytes)] das mensagens (registro de 80 B; tipo = u32 em +4; data em +8)."""
    import mensagens_save as MS
    out = []
    for i in range(MS.N):
        r = d[CAIXA + i * MS.REC: CAIXA + (i + 1) * MS.REC]
        y, m, dd = struct.unpack_from('<HBB', r, 8)
        tipo = struct.unpack_from('<I', r, 4)[0]
        if 2000 <= y <= 2100 and 1 <= m <= 12 and tipo:
            out.append((i, tipo, (y, m, dd), r))
    return out


def resolver(arg, lista):
    if arg.isdigit():
        return lista[int(arg)]
    return next(c for c in lista if c[1] == arg or f'{c[0]}/{c[1]}' == arg)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    lista = copias()
    if len(sys.argv) < 2 or sys.argv[1] == 'lista':
        for i, (slot, nome, path) in enumerate(lista):
            d = open(descriptografar(path), 'rb').read()
            print(i, slot, nome, 'data do jogo:', data_do_jogo(d))
    elif sys.argv[1] == 'caixa':   # caixa <cópia> [<cópia anterior>]: lista (ou só as novas)
        import mensagens_save as MS
        A = resolver(sys.argv[2], lista)
        d = open(descriptografar(A[2]), 'rb').read()
        antes = set()
        if len(sys.argv) > 3:
            B = resolver(sys.argv[3], lista)
            antes = {r for _i, _t, _d, r in caixa(open(descriptografar(B[2]), 'rb').read())}
        for i, t, dt_, r in sorted(caixa(d), key=lambda x: x[2]):
            if r in antes:
                continue
            print(f'{i:3} tipo {t:4} {MS.TIPOS.get(t, "?"):28} {dt_[2]:02d}/{dt_[1]:02d}/{dt_[0]}  {r[12:80].hex(" ")}')
    elif sys.argv[1] == 'evolucao':   # evolucao [ARQUIVO]: uma linha por save da carreira de teste
        import mensagens_save as MS
        slot = sys.argv[2] if len(sys.argv) > 2 else 'ML00000003'
        ant_cx, ant_hist = set(), set()
        for c in [c for c in lista if c[0] == slot]:
            d = open(descriptografar(c[2]), 'rb').read()
            esp, socios, acum = d[0xB629BC], struct.unpack_from('<I', d, 0xB629A4)[0], struct.unpack_from('<I', d, 0xB62998)[0]
            cx = {r for _i, _t, _d, r in caixa(d)}
            novas = sorted((t for _i, t, _d, r in caixa(d) if r not in ant_cx))
            hist = set()
            for o in range(0xBE2264, 0xBE333C, 44):
                r = d[o:o + 44]
                i = r.find(bytes([0xEA, 0x07]))
                if i >= 0:
                    hist.add((struct.unpack_from('<I', r, 0)[0], struct.unpack_from('<HBB', r, i)))
            ev = sorted(hist - ant_hist)
            dt_ = data_do_jogo(d)
            print(f'{c[1]}  {dt_[2]:02d}/{dt_[1]:02d}/{dt_[0]}  espírito {esp:3}  sócios {socios:>10,}  acum {acum:>7}'
                  + (f'  | msgs novas: {novas}' if ant_cx and novas else '')
                  + (f'  | Diário: {[(hex(i), f"{x[2]:02d}/{x[1]:02d}") for i, x in ev]}' if ev else ''))
            ant_cx, ant_hist = cx, hist
    elif sys.argv[1] == 'diff':
        A, B = resolver(sys.argv[2], lista), resolver(sys.argv[3], lista)
        a, b = open(descriptografar(A[2]), 'rb').read(), open(descriptografar(B[2]), 'rb').read()
        mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 400
        runs, total = diff(a, b, mx)
        print(f'{A[1]} ({data_do_jogo(a)}) -> {B[1]} ({data_do_jogo(b)}): {total} trechos diferentes')
        for i, j in runs:
            print(f'  {i:#09x}+{j - i:<3} {a[i:j].hex(" ")}  ->  {b[i:j].hex(" ")}')
