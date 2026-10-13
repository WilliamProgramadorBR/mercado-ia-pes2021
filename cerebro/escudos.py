# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Escudos oficiais dos times (os mesmos que o jogo usa) para a Central do Técnico. SOMENTE LEITURA.

O save da ML NÃO guarda o ID oficial do time (só o índice na tabela dele). O ID está na base do jogo:
  GOGOSZ/Database/common/etc/pesdb/Team.bin  (cabeçalho WESYS de 16 bytes + zlib)
  descomprimido: registros de 1532 bytes; +0 u32 ID, +360 nome (UTF-8), +874 sigla.   (09/10/2026)
Escudo: GOGOSZ/Escudos/common/render/symbol/flag/e_<ID com 6 dígitos>_r_l.png (500x500) ou variações.

Casamento save -> base (o patch/edição renomeia vários times): nome exato, nome normalizado (sem acento, sem
"FC"/"CF"...), sigla + nome parecido; empates (ex.: dois "EVERTON") são decididos pelos VIZINHOS na tabela do save,
porque o save agrupa os times por liga e os IDs de uma liga são próximos.
Resultado: historico/escudos.json {índice do time no save: {nome, id, arquivo}}.
"""
import difflib
import json
import os
import re
import struct
import unicodedata
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = __import__('caminhos').GAME_DIR
TEAM_BIN = os.path.join(GAME_DIR, 'GOGOSZ', 'Database', 'common', 'etc', 'pesdb', 'Team.bin')
FLAG = os.path.join(GAME_DIR, 'GOGOSZ', 'Escudos', 'common', 'render', 'symbol', 'flag')
ARQ = os.path.join(HERE, 'historico', 'escudos.json')
REC, ID, NOME, SIGLA = 1532, 0, 360, 874
SUFIXOS = ('_r_l', '_r', '_r_b_l', '_r_w_l', '_r_b', '_r_w')
IGNORAR = {'FC', 'CF', 'SC', 'AC', 'CD', 'CA', 'CLUB', 'DE', 'DEL', 'CLUBE', 'SV', 'AFC', 'SK', 'FK', 'BK', 'CALCIO',
           'DEPORTIVO', 'DESPORTIVO', 'ATLETICO', 'ESPORTE', 'SPORT', 'CLUBE', 'DA', 'DO', 'LA', 'EL'}


def _txt(b):
    return b.split(b'\x00')[0].decode('utf-8', 'replace').strip()


def base_do_jogo(path=TEAM_BIN):
    b = open(path, 'rb').read()
    raw = zlib.decompress(b[16:])
    ini = raw.find(b'MANCHESTER UNITED\x00') - NOME
    ini %= REC
    out = []
    for o in range(ini, len(raw) - REC + 1, REC):
        tid = struct.unpack_from('<I', raw, o + ID)[0]
        nome = _txt(raw[o + NOME:o + NOME + 70])
        if tid and nome:
            out.append((tid, nome, _txt(raw[o + SIGLA:o + SIGLA + 4])))
    return out


def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().upper()
    n = re.sub(r'[^A-Z0-9 ]', ' ', n)
    return ' '.join(p for p in n.split() if p not in IGNORAR and not p.isdigit())


def arquivo(tid):
    for suf in SUFIXOS:
        p = os.path.join(FLAG, f'e_{tid:06d}{suf}.png')
        if os.path.exists(p):
            return p
    return None


def casar(salvos, db):
    """salvos = [(índice, nome, sigla)] na ordem do save; db = [(id, nome, sigla)]. -> {índice: id}"""
    livres = {t[0]: t for t in db}
    mapa = {}

    def vizinhos(i):
        ids = []
        for j in (i - 1, i + 1, i - 2, i + 2):
            if j in mapa:
                ids.append(mapa[j])
        return ids

    def nota(i, n, sig, t):
        tid, dn, ds = t
        sim = difflib.SequenceMatcher(None, norm(n), norm(dn)).ratio()
        s = sim + (0.35 if ds and ds == sig else 0)
        viz = vizinhos(i)
        if viz:
            s += 0.4 * max(0.0, 1 - min(abs(tid - v) for v in viz) / 60)
        return s

    for passo in range(4):
        for i, n, sig in salvos:
            if i in mapa:
                continue
            if passo == 0:
                c = [t for t in livres.values() if t[1] == n]
            elif passo == 1:
                c = [t for t in livres.values() if norm(t[1]) == norm(n) and norm(n)]
            elif passo == 2:
                c = [t for t in livres.values() if t[2] == sig and set(norm(t[1]).split()) & set(norm(n).split())]
            else:
                c = [t for t in livres.values() if (t[2] == sig) or
                     difflib.SequenceMatcher(None, norm(n), norm(t[1])).ratio() >= 0.75]
            if not c:
                continue
            if passo < 3 and len(c) == 1:
                escolha = c[0]
            else:   # empate ou casamento fraco: decide pela nota (nome + sigla + vizinhos de liga)
                notas = sorted(((nota(i, n, sig, t), t) for t in c), key=lambda x: -x[0])
                if not vizinhos(i) and passo < 3:
                    continue   # sem vizinhos casados ainda: espera a próxima passada
                if notas[0][0] < 0.95 or (len(notas) > 1 and notas[0][0] - notas[1][0] < 0.1):
                    continue
                escolha = notas[0][1]
            mapa[i] = escolha[0]
            livres.pop(escolha[0])
    return mapa


def gerar(d, destino=ARQ):
    """d = data.dat do save. Grava historico/escudos.json e devolve o dicionário."""
    from save_ml import SaveML
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    salvos = []
    for i in range(1000):
        try:
            n = s.name(i)
        except Exception:  # noqa: BLE001
            break
        if not n or not n.isprintable():
            break
        a = s.team_addr(i)
        salvos.append((i, n.strip(), _txt(bytes(d[a + 70:a + 74]))))
    mapa = casar(salvos, base_do_jogo())
    out = {}
    for i, n, _ in salvos:
        tid = mapa.get(i)
        arq = arquivo(tid) if tid else None
        out[str(i)] = {'nome': n, 'id': tid, 'arquivo': os.path.basename(arq) if arq else None}
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    tmp = destino + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(tmp, destino)
    return out


def por_nome(mapa):
    """{nome: arquivo} (o primeiro índice ganha: times das ligas principais vêm antes no save)."""
    out = {}
    for _i, v in sorted(mapa.items(), key=lambda kv: int(kv[0])):
        if v['arquivo'] and v['nome'] not in out:
            out[v['nome']] = v['arquivo']
    return out


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    m = gerar(open(sys.argv[1], 'rb').read())
    com = sum(1 for v in m.values() if v['arquivo'])
    print(f'{com}/{len(m)} times com escudo')
    print('sem escudo:', [v['nome'] for v in m.values() if not v['arquivo']][:40])
