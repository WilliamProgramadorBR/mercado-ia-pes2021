"""Realismo dos jogos SIMULADOS desde que o técnico da IA foi ligado (12/10/2026, data do jogo 21/10/2035).
Só leitura: save da última reunião + fichas da foto da memória. Uso: python realismo_agora.py [AAAA-MM-DD início]

Mede (comparar com 2034/35, antes do técnico da IA):
  - XI final da súmula x melhor XI possível (atenção: a súmula simulada guarda quem TERMINOU, 3 substituições);
  - favorito vence quanto, por diferença de força do XI;
  - por liga: correlação força do elenco x tabela.
Antes (2034/35): favorito 40% (0-2 pts), 47% (2-4), 54% (4-6), 70% (6-8); XI final 3,5-3,8 pontos abaixo do melhor
nos 30 maiores; correlação Premier .58, LaLiga .79, Serie A .42.
"""
import collections
import datetime as dt
import glob
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
CER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cerebro')
sys.path.insert(0, CER)
import dados
import encaixe
import partidas_save as ps
from save_ml import SaveML

ini = tuple(int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '2035-10-22').split('-'))
f = max(glob.glob(os.path.join(CER, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime)
d = open(f, 'rb').read()
s = SaveML.__new__(SaveML)
s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
P = dados.load_players(os.path.join(CER, '..', '..', 'eFootball PES 2021', 'mercado_snap.bin'))
mu = s.find_team('MANCHESTER UNITED')
J = [p for p in ps.todas(d) if tuple(p['data']) >= ini and p['time1'] < 625 and p['time2'] < 625
     and mu not in (p['time1'], p['time2']) and p['comp'] not in range(100, 111)]
hoje = max((tuple(p['data']) for p in ps.todas(d)), default=None)
print(f'save {os.path.basename(os.path.dirname(os.path.dirname(f)))} | data do jogo {hoje} | jogos IA x IA desde {ini}: {len(J)}')
if len(J) < 50:
    sys.exit('poucos jogos ainda')
r = lambda k: (encaixe.rating(P[k], P[k].pos) if P.get(k) else None)


def forca_xi(ls):
    rs = [r((x['reg'], x['pid'])) for x in ls if x['titular']]
    rs = [x for x in rs if x]
    return sum(rs) / len(rs) if len(rs) >= 10 else None


melhor = {}
for ti in {p['time1'] for p in J} | {p['time2'] for p in J}:
    rs = sorted((r(tuple(k)) or 0 for k in s.squad(ti)), reverse=True)[:11]
    if len(rs) == 11:
        melhor[ti] = sum(rs) / 11
top = sorted(melhor, key=lambda t: -melhor[t])[:30]
faixas = collections.defaultdict(lambda: [0, 0, 0])
gap = collections.defaultdict(list)
for p in J:
    a, b = forca_xi(p['linhas1']), forca_xi(p['linhas2'])
    for ti, f_ in ((p['time1'], a), (p['time2'], b)):
        if f_ and ti in melhor:
            gap['top30' if ti in top else 'resto'].append(melhor[ti] - f_)
    if a is None or b is None:
        continue
    dif = a - b
    fg, zg = (p['gols1'], p['gols2']) if dif >= 0 else (p['gols2'], p['gols1'])
    k = min(8, int(abs(dif) // 2) * 2)
    faixas[k][0 if fg > zg else 1 if fg == zg else 2] += 1
print('\nFAVORITO (XI em campo) — antes: 40% / 47% / 54% / 70%')
for k in sorted(faixas):
    v, e, z = faixas[k]
    n = v + e + z
    print(f'  {k}-{k + 2} pontos: {n:4d} jogos | favorito vence {v / n:4.0%} · empate {e / n:4.0%} · zebra {z / n:4.0%}')
print('\nXI FINAL abaixo do melhor XI (pontos de nota) — antes: top30 ~3,5-3,8, resto ~3,1 (inclui 3 substituições)')
for g, xs in gap.items():
    print(f'  {g:6s} {len(xs):5d} escalações | média {sum(xs) / len(xs):.1f}')
print('\nLIGAS: correlação força x tabela — antes: Premier .58, LaLiga .79, Serie A .42')
for comp, nome in ((17, 'Premier League'), (19, 'LaLiga'), (18, 'Serie A'), (20, 'Bundesliga'), (50, 'Ligue 1'), (29, 'Brasileirão A')):
    pts = collections.Counter()
    for p in ps.todas(d):
        if p['comp'] != comp or tuple(p['data']) < (hoje[0] - (0 if comp == 29 else (1 if hoje[1] < 7 else 0)), 1 if comp == 29 else 7, 1):
            continue
        g1, g2 = p['gols1'], p['gols2']
        pts[p['time1']] += 3 if g1 > g2 else 1 if g1 == g2 else 0
        pts[p['time2']] += 3 if g2 > g1 else 1 if g1 == g2 else 0
    ts = [t for t in pts if t in melhor]
    if len(ts) < 10:
        continue
    pos = {t: i for i, t in enumerate(sorted(ts, key=lambda t: -pts[t]))}
    frc = {t: i for i, t in enumerate(sorted(ts, key=lambda t: -melhor[t]))}
    n = len(ts)
    rho = 1 - 6 * sum((pos[t] - frc[t]) ** 2 for t in ts) / (n * (n * n - 1))
    lider = min(ts, key=lambda t: pos[t])
    print(f'  {nome:15s} {rho:+.2f} | líder {s.name(lider).strip()} ({frc[lider] + 1}º em força)')
