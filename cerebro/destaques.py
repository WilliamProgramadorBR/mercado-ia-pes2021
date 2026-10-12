"""DESTAQUES DO MUNDO (11/10/2026): os números da temporada de TODOS os jogadores, para a imprensa ir além do clube.

Fonte: as súmulas do próprio save (partidas_save: o save guarda os jogos do mundo todo, com gols, assistências, nota e
minutos de cada jogador). Só jogos oficiais de clube contam (amistosos e pré-temporada fora); jogos por seleção são
contados à parte (convocação).

Produz um RESUMO pequeno (JSON) guardado na carreira (car['mundo']) a cada reunião:
  artilheiros   artilharia mundial (todas as competições oficiais de clube)
  garcons       líderes de assistências
  regulares     melhores médias de nota (mínimo de jogos)
  revelacoes    quem joga MUITO acima do que se esperava (nota baixa, clube pequeno ou muito jovem): o "Igor Thiago"
                que ninguém conhecia, faz gol toda rodada e acaba convocado para a seleção
  bola_de_ouro  a corrida pelo prêmio de melhor do mundo
  selecao       a SELEÇÃO DA TEMPORADA (4-3-3) votada por 30 jornalistas; vira oficial no fim da temporada
  clubes        os 3 destaques de cada clube que interessa (liga + próximos adversários)
"""
import collections
import random

NAO_OFICIAL = set(range(100, 111)) | {56}   # amistosos/pré-temporada e seleções (midia_liga.NAO_LIGA)
JURADOS = 30
GRUPOS = (('GK', ('GK',), 1), ('RB', ('RB',), 1), ('CB', ('CB',), 2), ('LB', ('LB',), 1),
          ('MEI', ('DMF', 'CMF', 'AMF', 'LMF', 'RMF'), 3), ('ATA', ('LWF', 'RWF', 'SS', 'CF'), 3))
ATA = ('CF', 'SS', 'LWF', 'RWF')
MEI = ('DMF', 'CMF', 'AMF', 'LMF', 'RMF')


def temporada_txt(ini):
    import temporada
    return temporada.rotulo(ini)


def ini_temporada(hoje):
    import temporada   # 12/10/2026: definido pela reunião (1ª rodada da liga); reserva: julho
    return temporada.ini_de(hoje)


def _ovr(f):
    try:
        import encaixe
        return round(encaixe.rating(f, f.pos))
    except Exception:  # noqa: BLE001
        return None


def estatisticas(todas, n_clubes, ini, fim=None):
    """{(reg, pid): números da temporada} a partir das súmulas (jogos oficiais de clube + seleção à parte)."""
    E = collections.defaultdict(lambda: {'jogos': 0, 'min': 0, 'gols': 0, 'assist': 0, 'notas': [], 'sg': 0,
                                         'clubes': collections.Counter(), 'sel_jogos': 0, 'sel_gols': 0,
                                         'sel': collections.Counter(), 'ult': None})
    for p in todas:
        dt = tuple(p['data'])
        if dt < ini or (fim and dt >= fim):
            continue
        # seleções (comps 34, 35, 56 no save): os dois times são seleções. Clube x "World Selection" é amistoso.
        n_sel = (p['time1'] >= n_clubes) + (p['time2'] >= n_clubes)
        selecao_jogo = n_sel == 2
        if n_sel == 1 or (p['comp'] in NAO_OFICIAL and not selecao_jogo):
            continue
        for t, linhas, sofreu in ((p['time1'], p['linhas1'], p['gols2']), (p['time2'], p['linhas2'], p['gols1'])):
            for x in linhas:
                if x['minutos'] <= 0:
                    continue
                e = E[(x['reg'], x['pid'])]
                if selecao_jogo:
                    e['sel_jogos'] += 1
                    e['sel_gols'] += x['gols']
                    e['sel'][t] += 1
                    continue
                e['jogos'] += 1
                e['min'] += x['minutos']
                e['gols'] += x['gols']
                e['assist'] += x['assist']
                if x['nota']:
                    e['notas'].append(x['nota'])
                if sofreu == 0 and x['minutos'] >= 60:
                    e['sg'] += 1
                e['clubes'][t] += 1
                e['ult'] = dt
    return E


def _media(e):
    return round(sum(e['notas']) / len(e['notas']), 2) if e['notas'] else None


def _ficha(k, e, f, nome_time, ti, rank):
    clube = e['clubes'].most_common(1)[0][0] if e['clubes'] else None
    sel = e['sel'].most_common(1)[0][0] if e['sel'] else None
    return {'k': list(k), 'nome': f.name.strip(), 'pos': f.pos, 'idade': f.age, 'ovr': _ovr(f),
            'time': nome_time(clube) if clube is not None else None, 'ti': clube, 'rank': rank.get(clube),
            'nosso': clube == ti, 'jogos': e['jogos'], 'gols': e['gols'], 'assist': e['assist'], 'media': _media(e),
            'sg': e['sg'], 'min': e['min'], 'selecao': nome_time(sel) if sel is not None else None,
            'sel_jogos': e['sel_jogos'], 'sel_gols': e['sel_gols']}


def _producao(x):
    """Contribuição esperada pela posição: atacante vive de gol; meia de passe; defesa de jogo sem sofrer gol."""
    m = (x['media'] or 6.0) - 6.0
    taxa_sg = x['sg'] / max(1, x['jogos'])   # jogo sem sofrer gol é mérito do time inteiro: conta a taxa, não o volume
    if x['pos'] == 'GK':
        return (x['ovr'] or 70) * 0.15 + taxa_sg * 15 + m * 14
    if x['pos'] in ('CB', 'LB', 'RB'):
        return (x['ovr'] or 70) * 0.1 + taxa_sg * 10 + x['gols'] * 0.5 + x['assist'] * 0.5 + m * 14
    if x['pos'] in MEI:
        return x['gols'] * 0.7 + x['assist'] * 0.9 + m * 14
    return x['gols'] * 1.0 + x['assist'] * 0.6 + m * 12


def _nota_selecao(x):
    return (x['ovr'] or 70) * 0.35 + _producao(x) + max(0, 15 - (x['rank'] or 99)) * 0.3


def _revelacao(x):
    """Quanto o jogador rende ACIMA do que a nota dele prometia (gols+assist por jogo x esperado pela nota)."""
    if x['nosso'] or x['jogos'] < 6 or x['pos'] == 'GK':
        return None
    ovr = x['ovr'] or 99   # "ninguém conhecia": nota modesta, ou muito jovem, ou de clube pequeno
    desconhecido = ovr <= 78 or (x['idade'] <= 21 and ovr <= 84) or ((x['rank'] or 999) > 60 and ovr <= 82)
    if not desconhecido:
        return None
    prod = x['gols'] + 0.7 * x['assist']
    if x['pos'] in ATA:
        esperado = max(0.06, ((x['ovr'] or 70) - 64) * 0.022) * x['jogos']
    elif x['pos'] in MEI:
        esperado = max(0.04, ((x['ovr'] or 70) - 64) * 0.014) * x['jogos']
    else:
        esperado = max(0.02, ((x['ovr'] or 70) - 64) * 0.006) * x['jogos']
    sobra = prod - esperado
    media = x['media'] or 6.0
    if prod < 5 and media < 7.1:
        return None
    sc = sobra + (media - 6.6) * 4 + (3 if x['sel_jogos'] else 0) + max(0, 21 - x['idade']) * 0.4
    return round(sc, 2) if sc > 2 else None


def _bola(x):
    if (x['ovr'] or 0) < 84 or x['jogos'] < 6 or (x['rank'] or 999) > 40:
        return None
    gk = x['pos'] == 'GK'
    return round((x['ovr'] or 80) * 0.6 + (0 if gk else x['gols'] + x['assist'] * 0.6) + ((x['media'] or 6) - 6) * 12
                 + max(0, 12 - (x['rank'] or 99)) * 0.4, 2)


def votacao(fichas, semente, jurados=JURADOS):
    """Seleção 4-3-3: cada jornalista monta o seu time (ruído de opinião); quem tem mais votos em cada vaga entra."""
    rnd = random.Random(semente)
    minimo = max(8, int(0.35 * max([x['jogos'] for x in fichas] or [0])))
    out, mencoes = [], []
    for slot, poss, n in GRUPOS:
        cands = [x for x in fichas if x['pos'] in poss and x['jogos'] >= minimo]
        if len(cands) < n:
            return None
        cands.sort(key=lambda x: -_nota_selecao(x))
        cands = cands[:12]
        votos = collections.Counter()
        for _ in range(jurados):
            ordem = sorted(cands, key=lambda x: -_nota_selecao(x) * rnd.uniform(0.9, 1.1))
            for x in ordem[:n]:
                votos[x['nome'], x['time']] += 1
        ganhos = sorted(cands, key=lambda x: (-votos[x['nome'], x['time']], -_nota_selecao(x)))
        for x in ganhos[:n]:
            out.append(dict(x, slot=slot, votos=votos[x['nome'], x['time']]))
        for x in ganhos[n:n + 2]:
            if votos[x['nome'], x['time']]:
                mencoes.append(dict(x, slot=slot, votos=votos[x['nome'], x['time']]))
    return {'time': out, 'mencoes': mencoes, 'jurados': jurados}


def calcular(todas, s, P, hoje, ti, nos, n_clubes=None, forca=None, interesse=(), ini=None, fim=None, tecnico=None):
    """Resumo da temporada do mundo (JSON). interesse = nomes de clubes cujos destaques a imprensa quer (liga, adversários)."""
    n_clubes = n_clubes or s.find_team('ALBÂNIA') or 625
    ini = ini or ini_temporada(hoje)
    E = estatisticas(todas, n_clubes, ini, fim)
    if forca is None:
        import proximo_jogo
        forca = {}
        clubes = {t for e in E.values() for t in e['clubes']} | {t for p in todas for t in (p['time1'], p['time2']) if t < n_clubes}
        for i in clubes:
            try:
                v = proximo_jogo._forca(s, i, P)
            except Exception:  # noqa: BLE001
                v = None
            if v:
                forca[i] = v
    rank = {i: n + 1 for n, i in enumerate(sorted(forca, key=lambda i: -forca[i]))}
    nome_time = lambda i: s.name(i).strip()
    fichas = []
    for k, e in E.items():
        if e['jogos'] < 1:
            continue
        f = P.get(k) if P else None
        if f is None:
            continue
        fichas.append(_ficha(k, e, f, nome_time, ti, rank))
    if not fichas:
        return None
    max_j = max(x['jogos'] for x in fichas)
    corte = lambda x: x['jogos'] >= max(5, int(0.3 * max_j))
    art = sorted(fichas, key=lambda x: (-x['gols'], x['jogos']))[:10]
    gar = sorted(fichas, key=lambda x: (-x['assist'], x['jogos']))[:6]
    reg = sorted((x for x in fichas if corte(x) and x['media']), key=lambda x: -x['media'])[:6]
    rev = sorted(((sc, x) for x in fichas for sc in [_revelacao(x)] if sc), key=lambda t: -t[0])[:6]
    bola = sorted(((sc, x) for x in fichas for sc in [_bola(x)] if sc), key=lambda t: -t[0])[:5] if max_j >= 12 else []
    sel = votacao(fichas, f'selecao|{ini}|{ti}')
    clubes = {}
    for nome in interesse:
        i = s.find_team(nome) if nome else None
        if i is None:
            continue
        js = [x for x in fichas if x['ti'] == i]
        js.sort(key=lambda x: -(x['gols'] * 1.0 + x['assist'] * 0.7 + ((x['media'] or 6) - 6) * 3 * min(1, x['jogos'] / 5)))
        if js:
            clubes[nome] = js[:4]
    jogos_temp = sum(1 for p in todas if tuple(p['data']) >= ini and (not fim or tuple(p['data']) < fim) and p['comp'] not in NAO_OFICIAL)
    # as estrelas (maiores notas com jogos): a revelação é comparada com elas ("mais gols que fulano, nota 90")
    estrelas = sorted((x for x in fichas if x['jogos'] >= 8 and x['pos'] != 'GK'), key=lambda x: -(x['ovr'] or 0))[:30]
    return {'temporada': temporada_txt(ini), 'data': list(hoje), 'jogos': jogos_temp, 'max_jogos': max_j,
            'artilheiros': art, 'garcons': gar, 'regulares': reg, 'estrelas': estrelas,
            'revelacoes': [dict(x, score=sc) for sc, x in rev], 'bola_de_ouro': [dict(x, score=sc) for sc, x in bola],
            'selecao': sel, 'clubes': clubes,
            'tecnicos': tecnicos(todas, n_clubes, ini, fim, rank, nome_time, ti, tecnico)}


# ---------------------------------------------------------------- técnico do ano (imprensa)
# o save não guarda o nome dos técnicos da IA: a liga é reconhecida por um clube conhecido dela
LIGA_POR_CLUBE = {'MANCHESTER UNITED': 'Premier League', 'BARCELONA': 'LaLiga', 'REAL MADRID': 'LaLiga', 'JUVENTUS': 'Serie A',
                  'INTER': 'Serie A', 'MILAN': 'Serie A', 'BAYERN MÜNCHEN': 'Bundesliga', 'BORUSSIA DORTMUND': 'Bundesliga',
                  'PARIS SAINT-GERMAIN': 'Ligue 1', 'OLYMPIQUE DE MARSEILLE': 'Ligue 1', 'AJAX': 'Eredivisie', 'PSV EINDHOVEN': 'Eredivisie',
                  'BENFICA': 'Liga Portugal', 'PORTO': 'Liga Portugal', 'FLAMENGO': 'Brasileirão', 'PALMEIRAS': 'Brasileirão',
                  'BOCA JUNIORS': 'Liga Argentina', 'RIVER PLATE': 'Liga Argentina', 'GALATASARAY': 'Süper Lig', 'FENERBAHÇE': 'Süper Lig',
                  'CELTIC': 'Scottish Premiership', 'AL-NASSR FC': 'Saudi Pro League', 'AL-HILAL': 'Saudi Pro League'}


def tecnicos(todas, n_clubes, ini, fim, rank, nome_time, ti, tecnico_nome=None):
    """Top 5 de técnicos pela temporada do clube: aproveitamento, posição na liga, mata-mata da Champions e quanto o
    time rendeu ACIMA da força do elenco (o 8º elenco da liga terminando em 2º pesa muito)."""
    T = collections.defaultdict(lambda: {'j': 0, 'pts': 0, 'gp': 0, 'gc': 0, 'ko': 0})
    liga = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))   # comp -> time -> [pts, saldo, jogos]
    for p in todas:
        dt_ = tuple(p['data'])
        if dt_ < ini or (fim and dt_ >= fim) or p['comp'] in NAO_OFICIAL or p['time1'] >= n_clubes or p['time2'] >= n_clubes:
            continue
        for t, gp, gc in ((p['time1'], p['gols1'], p['gols2']), (p['time2'], p['gols2'], p['gols1'])):
            x = T[t]
            pts = 3 if gp > gc else 1 if gp == gc else 0
            x['j'] += 1
            x['pts'] += pts
            x['gp'] += gp
            x['gc'] += gc
            if p['comp'] == 4:
                x['ko'] += 1
            L = liga[p['comp']][t]
            L[0] += pts
            L[1] += gp - gc
            L[2] += 1
    # ligas = competições de pontos corridos (muitos times, todos com muitos jogos)
    ligas = {c: ts for c, ts in liga.items() if len(ts) >= 10 and sum(v[2] for v in ts.values()) >= len(ts) * (len(ts) - 1) * 0.5}
    pos_de, nome_liga, n_liga = {}, {}, {}
    for c, ts in ligas.items():
        ordem = sorted(ts, key=lambda t: (-ts[t][0], -ts[t][1]))
        nomes = {nome_time(t) for t in ordem}
        rot = next((v for k, v in LIGA_POR_CLUBE.items() if k in nomes), None)
        forca_ord = sorted(ordem, key=lambda t: rank.get(t, 999))
        for i, t in enumerate(ordem):
            if t not in pos_de or ts[t][2] > T[t].get('_lj', 0):
                pos_de[t] = (i + 1, forca_ord.index(t) + 1, c)
                T[t]['_lj'] = ts[t][2]
                nome_liga[t] = rot or 'liga nacional'
                n_liga[t] = len(ordem)
    out = []
    for t, x in T.items():
        if x['j'] < 25 or t not in pos_de:
            continue
        pos, esperado, _ = pos_de[t]
        if x.get('_lj', 0) < 0.7 * 2 * (n_liga[t] - 1):   # liga ainda pela metade (calendário anual: Brasil, Japão)
            continue
        apr = x['pts'] / (3 * x['j'])
        acima = esperado - pos
        sc = apr * 60 + (15 if pos == 1 else 6 if pos <= 3 else 0) + min(10, max(0, acima) * 1.2) + x['ko'] * 1.5 \
            + max(0, 40 - (rank.get(t) or 99)) * 0.25
        out.append({'nome': tecnico_nome if t == ti and tecnico_nome else f'técnico do {nome_time(t)}', 'time': nome_time(t),
                    'nosso': t == ti, 'liga': nome_liga[t], 'pos': pos, 'times_liga': n_liga[t], 'esperado': esperado,
                    'jogos': x['j'], 'aproveitamento': round(100 * apr), 'mata_mata_champions': x['ko'], 'score': round(sc, 1)})
    return sorted(out, key=lambda x: -x['score'])[:5]


# ---------------------------------------------------------------- na reunião
def interesse_de(car, nos):
    nomes = {t['time'] for t in ((car.get('liga') or {}).get('classificacao') or [])}
    for pj in car.get('proximos') or [car.get('proximo_jogo')]:
        if pj and pj.get('adversario'):
            nomes.add(pj['adversario'])
    nomes.discard(nos)
    return sorted(nomes)


def da_reuniao(car, r, d, snap, log=print):
    """Calcula o resumo da temporada com o save desta reunião e guarda em car['mundo']."""
    import imprensa
    ctx = imprensa._contexto(car, r, d, snap)
    hoje = tuple(r['hoje'])
    res = calcular(r.get('todas_partidas') or [], ctx['s'], ctx['P'], hoje, r['ti'], r['time'],
                   interesse=interesse_de(car, r['time']), tecnico=r.get('tecnico'))
    if res:
        car['mundo'] = res
        log(f'destaques do mundo: {res["jogos"]} jogos na temporada, {len(res["revelacoes"])} revelações')
    return res


def fim_de_liga(car):
    """A liga da temporada acabou? (todos os times jogaram todas as rodadas)."""
    tab = (car.get('liga') or {}).get('classificacao') or []
    return bool(tab) and all(t.get('j', 0) >= 2 * (len(tab) - 1) for t in tab)
