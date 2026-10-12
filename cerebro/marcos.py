"""MARCOS DA TEMPORADA (11/10/2026): FINAIS de copa e TÍTULO da liga — os jogos que a imprensa trata como históricos.

FINAL: jogo de mata-mata (+7 do registro: 0x40/0x50 jogado, 0x00/0x10 agendado) que é o ÚLTIMO da competição e o
único naquela data (jogo único). Vale para a Champions (comp 4) e as copas nacionais (FA Cup 23, Copa do Brasil 31...).
TÍTULO DA LIGA: pela classificação — garantido quando a vantagem sobre o 2º passa 3 x (rodadas que faltam);
campeão no fim quando todos jogaram todas as rodadas.
"""
KO = (0x40, 0x50, 0x00, 0x10)


def _dias(a, b):
    import datetime as dt
    return (dt.date(*a) - dt.date(*b)).days


def eh_final(j, todos, liga=None):
    """j: registro de jogo (comp, data, flag); todos: registros jogados e agendados. A final é o último jogo da
    competição e o ÚNICO dela num intervalo de 3 dias; nunca um jogo de volta (0x50/0x10). Copas de jogo único (FA Cup)
    usam os marcadores de liga (0x20/0x60): a final da FA Cup de 2034/35 é 16/05, como os títulos no diário."""
    if j.get('flag') in (0x50, 0x10) or j['comp'] == liga or j['comp'] in (3, 108, 0x67):
        return False
    mesma = [x for x in todos if x['comp'] == j['comp']]
    if len(mesma) < 3 or any(tuple(x['data']) > tuple(j['data']) for x in mesma):
        return False
    return sum(1 for x in mesma if abs(_dias(tuple(x['data']), tuple(j['data']))) <= 3) == 1


def final_do_time(todos, ti, liga=None):
    """A final (jogada ou agendada) do time, a mais recente/próxima: {'jogo', 'comp', 'adv', 'jogado', 'gp', 'gc', 'campeao'}."""
    out = None
    for j in todos:
        if ti in (j['time1'], j['time2']) and eh_final(j, todos, liga):
            if out is None or tuple(j['data']) > tuple(out['data']):
                out = j
    if not out:
        return None
    casa = out['time1'] == ti
    gp, gc = (out['gols1'], out['gols2']) if casa else (out['gols2'], out['gols1'])
    jogado = bool(out.get('flag', 0x60 if out.get('linhas1') else 0) & 0x40)
    return {'jogo': out, 'comp': out['comp'], 'data': tuple(out['data']), 'adv': out['time2'] if casa else out['time1'],
            'jogado': jogado, 'gp': gp, 'gc': gc, 'campeao': (gp > gc) if jogado and gp != gc else None}


def titulo_liga(tab):
    """{'campeao', 'garantido', 'restam', 'vantagem', 'lider'} pela classificação (ou None)."""
    if len(tab or []) < 8:
        return None
    n = len(tab)
    total = 2 * (n - 1)
    eu = next((t for t in tab if t.get('eu')), None)
    if not eu:
        return None
    lider, seg = tab[0], tab[1]
    restam = total - eu['j']
    fim = all(t['j'] >= total for t in tab)
    vant = lider['pts'] - seg['pts']
    garantido = vant > 3 * (total - min(lider['j'], seg['j']))
    return {'campeao': eu['pos'] == 1 and (fim or garantido), 'fim': fim, 'garantido': garantido and eu['pos'] == 1,
            'restam': restam, 'vantagem': vant if eu['pos'] == 1 else eu['pts'] - lider['pts'], 'lider': lider['time'],
            'ultima_rodada': restam == 1, 'pos': eu['pos'], 'pts': eu['pts']}
