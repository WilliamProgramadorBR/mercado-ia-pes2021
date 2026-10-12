"""VIRADAS HISTÓRICAS em mata-mata (11/10/2026): "isso é futebol".

A súmula do PES não guarda o minuto dos gols (virada DENTRO de um jogo não dá para saber), mas os confrontos de ida
e volta dão: no registro de jogo, +7 = 0x40 (ida) / 0x50 (volta) no mata-mata (partidas_save, 'flag').
  VIRADA  = perdeu a ida por 2+ gols e passou no agregado (Barcelona 6 x 1 PSG).
  VEXAME  = venceu a ida por 2+ gols e foi eliminado.
Empate no agregado (prorrogação/pênaltis) não entra: o save não diz quem passou.
"""
import collections

# remontadas REAIS (fatos), para a imprensa comparar
REAIS = [
    ('Barcelona', 'PSG', 4, 'perdeu a ida por 4 x 0 e fez 6 x 1 na volta, na Champions de 2017'),
    ('Liverpool', 'Barcelona', 3, 'perdeu a ida por 3 x 0 e fez 4 x 0 na volta, na semifinal da Champions de 2019'),
    ('Deportivo La Coruña', 'Milan', 3, 'perdeu a ida por 4 x 1 e fez 4 x 0 na volta, na Champions de 2004'),
    ('Roma', 'Barcelona', 3, 'perdeu a ida por 4 x 1 e fez 3 x 0 na volta, na Champions de 2018'),
]


def _dias(a, b):
    import datetime as dt
    return (dt.date(*a) - dt.date(*b)).days


def confrontos(todas):
    """Confrontos de ida e volta (mata-mata): [{'comp', 'ida', 'volta', 'times'}]."""
    ko = [p for p in todas if p.get('flag') in (0x40, 0x50)]
    por = collections.defaultdict(list)
    for p in ko:
        por[(p['comp'], frozenset((p['time1'], p['time2'])))].append(p)
    out = []
    for (comp, times), js in por.items():
        js.sort(key=lambda p: p['data'])
        for i in range(len(js) - 1):
            a, b = js[i], js[i + 1]
            if 0 < _dias(tuple(b['data']), tuple(a['data'])) <= 60:
                out.append({'comp': comp, 'ida': a, 'volta': b, 'times': tuple(times)})
    return out


def _gols(p, t):
    return (p['gols1'], p['gols2']) if p['time1'] == t else (p['gols2'], p['gols1'])


def analisar(c, t):
    """Do ponto de vista do time t: ida, volta, agregado, e se foi VIRADA ou VEXAME."""
    i, v = _gols(c['ida'], t), _gols(c['volta'], t)
    agg = (i[0] + v[0], i[1] + v[1])
    adv = next(x for x in c['times'] if x != t)
    tipo = None
    if agg[0] > agg[1] and i[1] - i[0] >= 2:
        tipo = 'virada'
    elif agg[0] < agg[1] and i[0] - i[1] >= 2:
        tipo = 'vexame'
    return {'tipo': tipo, 'time': t, 'adv': adv, 'ida': i, 'volta': v, 'agg': agg, 'deficit': abs(i[1] - i[0]),
            'passou': agg[0] > agg[1] if agg[0] != agg[1] else None, 'data': tuple(c['volta']['data']),
            'comp': c['comp'], 'num_volta': c['volta']['num'], 'volta_em_casa': c['volta']['time1'] == t}


def do_time(todas, ti, hoje, dias=12):
    """O confronto decidido mais recente do time (volta nos últimos `dias`)."""
    cs = [analisar(c, ti) for c in confrontos(todas) if ti in c['times'] and 0 <= _dias(tuple(hoje), tuple(c['volta']['data'])) <= dias]
    return max(cs, key=lambda x: x['data']) if cs else None


def no_mundo(todas, hoje, dias=10, exceto=None):
    """Viradas de outros times (para a imprensa cobrir o mundo)."""
    out = []
    for c in confrontos(todas):
        if exceto in c['times'] or not 0 <= _dias(tuple(hoje), tuple(c['volta']['data'])) <= dias:
            continue
        for t in c['times']:
            a = analisar(c, t)
            if a['tipo'] == 'virada':
                out.append(a)
    return sorted(out, key=lambda a: -a['deficit'])


def comparacao(deficit):
    """A remontada real mais parecida (mesmo tamanho de desvantagem, ou a maior se for maior)."""
    igual = [r for r in REAIS if r[2] == deficit]
    if igual:
        return igual[0]
    return REAIS[0] if deficit >= 4 else REAIS[1]
