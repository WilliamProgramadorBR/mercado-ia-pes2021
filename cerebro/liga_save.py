# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Classificação da liga guardada pelo próprio jogo no save da Master League (SOMENTE LEITURA).

Descoberto em 09/10/2026 (save de 28/01/2034, Premier League: Man Utd 59, Liverpool 55, City 43...).
Registro de 20 bytes por clube, em ordem de posição:
  +0  u32 código do clube (índice na tabela de times = valor & 0x3FFF)
  +4  u32 posição (1, 2, 3...)
  +8  64 bits compactados: bits 0-7 pontos, 8-13 vitórias, 14-19 derrotas, 20-25 empates,
      32-38 gols pró, 44-50 gols contra   (conferido: 3V+E = pontos nos 20 clubes; V+E+D = 24 jogos em todos;
      soma dos gols pró = soma dos gols contra na liga = 575)
  +16 u32 ? (não é o saldo)
Antes/depois da tabela há registros vazios (0x2b, 0xFFFFFFFF...). Outras ligas ficam em tabelas parecidas.
"""
import struct

REC = 20


def _f(v, b, n):
    return (v >> b) & ((1 << n) - 1)


def _linha(d, a):
    tc, pos = struct.unpack_from('<II', d, a)
    v = int.from_bytes(d[a + 8:a + 16], 'little')
    return {'time': tc & 0x3FFF, 'codigo': tc, 'pos': pos, 'pts': _f(v, 0, 8), 'v': _f(v, 8, 6),
            'd': _f(v, 14, 6), 'e': _f(v, 20, 6), 'gp': _f(v, 32, 7), 'gc': _f(v, 44, 7)}


def _valida(x):
    j = x['v'] + x['e'] + x['d']
    return 1 <= x['pos'] <= 30 and x['pts'] == 3 * x['v'] + x['e'] and j <= 60


def tabelas(d, time_idx, ini=0xC00000, fim=None):
    """Todas as classificações (ligas, temporadas antigas inclusive) em que `time_idx` aparece."""
    fim = fim or len(d) - REC
    achadas, vistas = [], set()
    # o código do time tem bits altos de marcação (0x4000...): procura todas as variantes (10/10/2026, Brasileirão)
    ocorr = set()
    for flag in (0, 0x4000, 0x8000, 0xC000):
        alvo = struct.pack('<H', time_idx | flag)
        k = d.find(alvo, ini, fim)
        while k >= 0:
            ocorr.add(k)
            k = d.find(alvo, k + 1, fim)
    for o in sorted(ocorr):
        if o % 2 == 0 and o + REC <= len(d):
            x = _linha(d, o)
            if x['time'] == time_idx and _valida(x):
                # volta até o 1º da tabela. Posições podem EMPATAR (ex.: dois em 5º, 10/10/2026), então anda
                # enquanto a linha anterior é válida e tem posição menor ou igual.
                a = o
                while a - REC >= 0:
                    y = _linha(d, a - REC)
                    if not _valida(y) or y['pos'] > _linha(d, a)['pos'] or _linha(d, a)['pos'] == 1:
                        break
                    a -= REC
                if a not in vistas:
                    vistas.add(a)
                    linhas = []
                    while a + REC <= len(d):
                        y = _linha(d, a)
                        n = len(linhas)
                        if not _valida(y) or y['pos'] > n + 1 or (linhas and y['pos'] < linhas[-1]['pos']) or                                 (not linhas and y['pos'] != 1):
                            break
                        linhas.append(y)
                        a += REC
                    jogos = {y['v'] + y['e'] + y['d'] for y in linhas}
                    if len(linhas) >= 8 and any(y['time'] == time_idx for y in linhas) and max(jogos) - min(jogos) <= 3:
                        achadas.append(linhas)
    return achadas


def tabela(d, time_idx, ini=0xC00000, fim=None, times=None):
    """Classificação ATUAL da liga do time.
    O save guarda DUAS tabelas por temporada (a atual e a da rodada anterior) e também as da temporada passada.
    Ex. (28/01/2034): jogos = [38, 37, 24, 23] -> passada (final e rodada 37), atual (24) e rodada anterior (23).
    Regra: as tabelas vêm em PARES por temporada (na ordem do arquivo). A temporada em andamento é o par com
    menos jogos (empate, como no fim da temporada: o último par no arquivo); dentro do par, a de MAIS jogos."""
    ts = tabelas(d, time_idx, ini, fim)
    if times:   # só as tabelas da LIGA principal (a copa continental também tem tabela com o time; 10/10/2026)
        boas = [t for t in ts if len({y['time'] for y in t} & set(times)) >= 0.7 * len(t)]
        ts = boas or ts
    if not ts:
        return []
    jogos = [max(y['v'] + y['e'] + y['d'] for y in t) for t in ts]
    pares = [list(range(i, min(i + 2, len(ts)))) for i in range(0, len(ts), 2)]
    par = min(reversed(pares), key=lambda p: max(jogos[i] for i in p))
    return ts[max(par, key=lambda i: jogos[i])]
