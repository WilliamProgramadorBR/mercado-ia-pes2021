# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""RODADA E MÊS (11/10/2026): o jornalismo de toda semana, não só o de fim de temporada.

  seleção da rodada   quando uma rodada da liga termina (todos os jogos dela disputados), o 4-3-3 dos melhores pela
                      nota da súmula daquele jogo (+ gol, assistência, jogo sem sofrer gol), o craque e a goleada da rodada
  jogador do mês      na virada do mês: o melhor da liga no mês que acabou (média, gols, assistências, mínimo 3 jogos),
                      o melhor do nosso elenco e o time que mais pontuou no mês

Gera matérias (frente 'rodada', aba Imprensa > Mundo), fatos para as capas e o resumo car['rodada_destaque'] que o
Bola na Mesa e as redes usam.
"""
import collections

import imprensa_db as db

NAO_OFICIAL = set(range(100, 111)) | {56}
GRUPOS = (('GK', ('GK',), 1), ('RB', ('RB',), 1), ('CB', ('CB',), 2), ('LB', ('LB',), 1),
          ('MEI', ('DMF', 'CMF', 'AMF', 'LMF', 'RMF'), 3), ('ATA', ('LWF', 'RWF', 'SS', 'CF'), 3))
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def _liga(todas, ti, ini):
    import temporada
    if temporada.ATUAL['liga'] is not None:
        return temporada.ATUAL['liga']
    cs = collections.Counter(p['comp'] for p in todas if ti in (p['time1'], p['time2']) and p['comp'] not in NAO_OFICIAL
                             and tuple(p['data']) >= ini)
    return cs.most_common(1)[0][0] if cs else None


def _linhas(p):
    for t, ls, sofreu in ((p['time1'], p['linhas1'], p['gols2']), (p['time2'], p['linhas2'], p['gols1'])):
        for x in ls:
            if x['minutos'] > 0:
                yield t, x, sofreu


def _nota_jogo(x, pos, sofreu):
    n = (x['nota'] or 5.5) + 0.5 * x['gols'] + 0.3 * x['assist']
    if pos in ('GK', 'CB', 'LB', 'RB') and sofreu == 0 and x['minutos'] >= 60:
        n += 0.4
    return n


def _onze(cands):
    """cands = [{nome, pos, time, nota, ...}] -> 11 no 4-3-3 (maior nota em cada vaga)."""
    out, usados = [], set()
    for slot, poss, n in GRUPOS:
        g = sorted((c for c in cands if c['pos'] in poss and c['id'] not in usados), key=lambda c: -c['sc'])[:n]
        if len(g) < n:
            return None
        for c in g:
            usados.add(c['id'])
            out.append(dict(c, slot=slot))
    return out


# ---------------------------------------------------------------- seleção da rodada
def selecao_rodada(ck, todas, ti, nos, P, nome_time, hoje, ini, liga_nome):
    liga = _liga(todas, ti, ini)
    if liga is None:
        return None, None
    lj = [p for p in todas if p['comp'] == liga and tuple(p['data']) >= ini]
    times = {t for p in lj for t in (p['time1'], p['time2'])}
    por = collections.defaultdict(list)
    for p in lj:
        por[p['rodada']].append(p)
    completas = [rd for rd, ps in por.items() if len(ps) >= max(1, len(times) // 2)]
    if not completas:
        return None, None
    rd = max(completas, key=lambda x: max(tuple(p['data']) for p in por[x]))
    chave = f'rodada|{ck}|{ini[0]}|{liga}|{rd}'
    if db.existe(ck, chave):
        return None, None
    jogos = por[rd]
    cands = []
    for p in jogos:
        for t, x, sofreu in _linhas(p):
            f = P.get((x['reg'], x['pid']))
            if not f or x['minutos'] < 30:
                continue
            cands.append({'id': (x['reg'], x['pid']), 'k': [x['reg'], x['pid']], 'nome': f.name.strip(), 'pos': f.pos, 'time': nome_time(t),
                          'nosso': t == ti, 'nota': x['nota'], 'gols': x['gols'], 'assist': x['assist'], 'sc': round(_nota_jogo(x, f.pos, sofreu), 2)})
    xi = _onze(cands)
    if not xi:
        return None, None
    craque = max(xi, key=lambda c: c['sc'])
    gol = max(jogos, key=lambda p: (abs(p['gols1'] - p['gols2']), p['gols1'] + p['gols2']))
    gtxt = f'{nome_time(gol["time1"])} {gol["gols1"]} x {gol["gols2"]} {nome_time(gol["time2"])}'
    nossos = [c['nome'] for c in xi if c['nosso']]
    for c in xi:
        c.pop('id', None)
    corpo = [f'A rodada {rd} da {liga_nome} terminou, e a redação montou o time ideal pelas notas de cada jogo.',
             f'O craque da rodada é {craque["nome"]}, do {craque["time"]}: nota {_n(craque["nota"] or 0)}'
             + (f', {craque["gols"]} gol{"s" if craque["gols"] > 1 else ""}' if craque['gols'] else '')
             + (f' e {craque["assist"]} assistência{"s" if craque["assist"] > 1 else ""}' if craque['assist'] else '') + '.',
             ('Na seleção, ' + ', '.join(f'{c["nome"]} ({c["time"]})' for c in xi) + '.'),
             (f'O {nos} colocou {len(nossos)} na seleção: {", ".join(nossos)}.' if nossos else f'Nenhum jogador do {nos} entrou na seleção desta rodada.'),
             f'O placar mais elástico foi {gtxt}.']
    m = {'chave': chave, 'frente': 'rodada', 'data': max(tuple(p['data']) for p in jogos), 'autor': 'Redação · rodada',
         'titulo': f'Seleção da rodada {rd}: {craque["nome"]} é o craque',
         'linha_fina': f'{liga_nome} · {len(nossos)} do {nos} entre os 11.',
         'corpo': corpo, 'dados': {'tipo': 'rodada', 'rodada': rd, 'competicao': liga_nome, 'craque': craque, 'goleada': gtxt,
                                   'selecao': {'time': xi, 'mencoes': [], 'jurados': None}}}
    fato = {'tipo': 'rodada', 'sub': f'rodada{rd}', 'peso': 1.6 + (1.2 if craque['nosso'] else 0) + 0.2 * len(nossos),
            'modo': 'rodada', 'rodada': rd, 'craque': craque, 'nossos': nossos, 'liga': liga_nome}
    return m, fato


# ---------------------------------------------------------------- jogador do mês
def jogador_do_mes(ck, todas, ti, nos, P, nome_time, hoje, ini, liga_nome):
    y, mth = (hoje[0], hoje[1] - 1) if hoje[1] > 1 else (hoje[0] - 1, 12)
    chave = f'mes|{ck}|{y}-{mth:02d}'
    if db.existe(ck, chave):
        return None, None
    liga = _liga(todas, ti, ini)
    if liga is None:
        return None, None
    clubes = {t for p in todas if p['comp'] == liga and tuple(p['data']) >= ini for t in (p['time1'], p['time2'])}
    mes = [p for p in todas if p['data'][0] == y and p['data'][1] == mth and p['comp'] not in NAO_OFICIAL]
    if sum(1 for p in mes if p['comp'] == liga) < len(clubes):   # mês sem liga de verdade (pré-temporada, pausa)
        return None, None
    E = collections.defaultdict(lambda: {'jogos': 0, 'gols': 0, 'assist': 0, 'notas': [], 't': None})
    pts = collections.Counter()
    for p in mes:
        if p['comp'] == liga:
            a, b = (3, 0) if p['gols1'] > p['gols2'] else (0, 3) if p['gols1'] < p['gols2'] else (1, 1)
            pts[p['time1']] += a
            pts[p['time2']] += b
        for t, x, _ in _linhas(p):
            if t not in clubes:
                continue
            e = E[(x['reg'], x['pid'])]
            e['jogos'] += 1
            e['gols'] += x['gols']
            e['assist'] += x['assist']
            e['t'] = t
            if x['nota']:
                e['notas'].append(x['nota'])
    cands, todos = [], []
    for k, e in E.items():
        f = P.get(k)
        if not f or e['jogos'] < 2 or not e['notas']:
            continue
        med = sum(e['notas']) / len(e['notas'])
        x = {'k': list(k), 'nome': f.name.strip(), 'pos': f.pos, 'time': nome_time(e['t']), 'nosso': e['t'] == ti,
             'jogos': e['jogos'], 'gols': e['gols'], 'assist': e['assist'], 'media': round(med, 2),
             'sc': round(med + 0.35 * e['gols'] + 0.25 * e['assist'] + 0.05 * e['jogos'], 2)}
        todos.append(x)
        if e['jogos'] >= 3:
            cands.append(x)
    if not cands:
        return None, None
    # a SELEÇÃO DO MÊS: o melhor 4-3-3 do mês na liga (mínimo 2 jogos no mês)
    xi = _onze([dict(x, id=tuple(x['k'])) for x in todos])
    if xi:
        for x in xi:
            x.pop('id', None)
            x['nota'] = x['media']
    cands.sort(key=lambda c: -c['sc'])
    top, nosso = cands[0], next((c for c in cands if c['nosso']), None)
    time_mes = pts.most_common(1)[0] if pts else None
    mes_txt = MESES[mth - 1]
    linha = lambda c: f'{c["gols"]} gols e {c["assist"]} assistências em {c["jogos"]} jogos, média {_n(c["media"])}'
    corpo = [f'O jogador de {mes_txt} na {liga_nome} é {top["nome"]}, do {top["time"]}: {linha(top)}.',
             'Logo atrás: ' + '; '.join(f'{c["nome"]} ({c["time"]})' for c in cands[1:4]) + '.']
    if nosso and nosso is not top:
        corpo.append(f'No {nos}, o melhor do mês foi {nosso["nome"]}: {linha(nosso)}.')
    if time_mes:
        corpo.append(f'O time do mês foi o {nome_time(time_mes[0])}, com {time_mes[1]} pontos na {liga_nome}.')
    if xi:
        por = {}
        for x in xi:
            por.setdefault(x['slot'], []).append(x)
        nm = lambda xs: ', '.join(f'{x["nome"]} ({x["time"]}, média {_n(x["media"])})' for x in xs)
        corpo.append(f'A seleção de {mes_txt}, pelas notas dos jogos: no gol, {nm(por["GK"])}; na defesa, {nm(por["RB"] + por["CB"] + por["LB"])}.')
        corpo.append(f'No meio, {nm(por["MEI"])}. No ataque, {nm(por["ATA"])}.')
        nossos_xi = [x['nome'] for x in xi if x['nosso']]
        corpo.append(f'O {nos} colocou {len(nossos_xi)} na seleção do mês: {", ".join(nossos_xi)}.' if nossos_xi else
                     f'Nenhum jogador do {nos} entrou na seleção do mês, um alerta para o técnico.')
        gol = max(xi, key=lambda x: x['gols'])
        if gol['gols']:
            corpo.append(f'Quem mais decidiu no time ideal foi {gol["nome"]}: {gol["gols"]} gols em {gol["jogos"]} jogos no mês.')
    m = {'chave': chave, 'frente': 'rodada', 'data': tuple(hoje), 'autor': 'Redação · prêmio do mês',
         'titulo': f'A seleção de {mes_txt}: {top["nome"]} é o jogador do mês' if xi else f'{top["nome"]} é o jogador de {mes_txt}', 'linha_fina': f'{liga_nome} · {linha(top)}.', 'corpo': corpo,
         'dados': {'tipo': 'mes', 'mes': mes_txt, 'ranking': cands[:5], 'nosso': nosso,
                   'selecao': {'time': xi, 'mencoes': [], 'jurados': None} if xi else None,
                   'time_mes': {'time': nome_time(time_mes[0]), 'pts': time_mes[1]} if time_mes else None}}
    fato = {'tipo': 'rodada', 'sub': f'mes{mth}', 'peso': 2.0 + (1.5 if top['nosso'] else 0), 'modo': 'mes', 'mes': mes_txt,
            'top': top, 'nosso': nosso, 'liga': liga_nome}
    return m, fato


# ---------------------------------------------------------------- na reunião
def da_reuniao(car, r, d, snap, log=print):
    """(matérias, fatos para as capas). Guarda car['rodada_destaque'] para o Bola na Mesa e as redes."""
    import destaques
    import imprensa
    ck = car.get('ck')
    if not ck:
        return [], []
    hoje = tuple(r['hoje'])
    ini = destaques.ini_temporada(hoje)
    ctx = imprensa._contexto(car, r, d, snap)
    nome_time = lambda i: ctx['s'].name(i).strip()
    todas = r.get('todas_partidas') or []
    liga_nome = (car.get('liga') or {}).get('competicao') or 'liga'
    ms, fs = [], []
    for fn in (selecao_rodada, jogador_do_mes):
        try:
            m, f = fn(ck, todas, r['ti'], r['time'], ctx['P'], nome_time, hoje, ini, liga_nome)
        except Exception as e:  # noqa: BLE001
            log(f'aviso: {fn.__name__}: {type(e).__name__}: {e}')
            continue
        if m:
            ms.append(m)
            fs.append(f)
            rd = car.setdefault('rodada_destaque', {})
            rd[f['modo']] = {k: v for k, v in f.items() if k not in ('peso',)}
            rd[f['modo']]['data'] = list(hoje)
    if ms:
        log('rodada/mês: ' + '; '.join(m['titulo'] for m in ms))
    return ms, fs
