# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""DATA FIFA (11/10/2026): os nossos jogadores nas seleções.

As súmulas guardam os jogos de seleção (os dois times são seleções: índices >= find_team('ALBÂNIA'); comps 34/35/56).
Quando uma janela termina (nenhum jogo de seleção nos últimos 2 dias), a imprensa conta:
  convocados   quem jogou pela seleção, minutos, gols, assistências e nota
  esquecidos   jogador de nível (nota >= 85) que já defendeu a seleção antes e desta vez ficou de fora, com o país jogando
  desgaste     quem volta com muitos minutos e condição baixa (a condição vem do jogo)
A nacionalidade é aprendida ao longo da carreira (car['nacionalidade']): o save não diz o país, mas diz por quem ele joga.
Gera matéria (frente 'selecoes'), fato para as capas e car['data_fifa'] para o Bola na Mesa, as redes e o celular.
"""
import collections
import datetime as dt

import imprensa_db as db


def _d(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def da_reuniao(car, r, d, snap, log=print):
    import imprensa
    ck = car.get('ck')
    if not ck:
        return [], []
    hoje = tuple(r['hoje'])
    ctx = imprensa._contexto(car, r, d, snap)
    s = ctx['s']
    n_cl = s.find_team('ALBÂNIA') or 625
    todas = r.get('todas_partidas') or []
    nt = [p for p in todas if p['time1'] >= n_cl and p['time2'] >= n_cl]
    nossos = {j['k']: j for j in r['J']}
    nac = car.setdefault('nacionalidade', {})
    for p in nt:   # aprende a seleção de cada jogador do elenco
        for t, ls in ((p['time1'], p['linhas1']), (p['time2'], p['linhas2'])):
            for x in ls:
                k = (x['reg'], x['pid'])
                if k in nossos and x['minutos'] > 0:
                    nac[f'{k[0]}:{k[1]}'] = s.name(t).strip()
    ate = tuple(car.get('data_fifa_ate') or (0, 0, 0))
    if ate == (0, 0, 0):
        ate = tuple((dt.date(*hoje) - dt.timedelta(days=30)).timetuple()[:3])
    novos = [p for p in nt if tuple(p['data']) > ate and tuple(p['data']) <= hoje]
    if not novos:
        return [], []
    fim = max(tuple(p['data']) for p in novos)
    if _d(hoje, fim) < 2:   # a janela ainda pode ter jogo
        return [], []
    car['data_fifa_ate'] = list(fim)
    ini = min(tuple(p['data']) for p in novos)
    E = collections.defaultdict(lambda: {'jogos': 0, 'min': 0, 'gols': 0, 'assist': 0, 'notas': [], 'sel': None})
    paises = set()
    for p in novos:
        paises.update((s.name(p['time1']).strip(), s.name(p['time2']).strip()))
        for t, ls in ((p['time1'], p['linhas1']), (p['time2'], p['linhas2'])):
            for x in ls:
                k = (x['reg'], x['pid'])
                if k not in nossos or x['minutos'] <= 0:
                    continue
                e = E[k]
                e['jogos'] += 1
                e['min'] += x['minutos']
                e['gols'] += x['gols']
                e['assist'] += x['assist']
                e['sel'] = s.name(t).strip()
                if x['nota']:
                    e['notas'].append(x['nota'])
    conv = []
    for k, e in E.items():
        j = nossos[k]
        conv.append({'nome': j['nome'], 'pos': j['pos'], 'k': list(k), 'selecao': e['sel'], 'jogos': e['jogos'], 'min': e['min'],
                     'gols': e['gols'], 'assist': e['assist'], 'media': round(sum(e['notas']) / len(e['notas']), 1) if e['notas'] else None,
                     'condicao': j.get('condicao')})
    conv.sort(key=lambda x: (-x['gols'], -x['min']))
    esquec = []
    for j in r['J']:
        pais = nac.get(f'{j["k"][0]}:{j["k"][1]}')
        if j['k'] not in E and pais and pais in paises and j['ovr'] >= 85:
            esquec.append({'nome': j['nome'], 'pos': j['pos'], 'selecao': pais, 'ovr': j['ovr']})
    cansados = [x for x in conv if x['min'] >= 150 and (x['condicao'] or 100) < 80]
    if not conv and not esquec:
        return [], []
    nos = r['time']
    tit = lambda x: x.title()
    corpo = [f'Fim da Data FIFA ({ini[2]:02d}/{ini[1]:02d} a {fim[2]:02d}/{fim[1]:02d}). '
             + (f'O {nos} cedeu {len(conv)} jogador{"es" if len(conv) > 1 else ""} às seleções.' if conv else f'Nenhum jogador do {nos} entrou em campo pelas seleções.')]
    for x in conv[:6]:
        corpo.append(f'{x["nome"]} ({tit(x["selecao"])}): {x["jogos"]} jogo{"s" if x["jogos"] > 1 else ""}, {x["min"]} minutos'
                     + (f', {x["gols"]} gol{"s" if x["gols"] > 1 else ""}' if x['gols'] else '')
                     + (f', {x["assist"]} assistência{"s" if x["assist"] > 1 else ""}' if x['assist'] else '')
                     + (f', média {_n(x["media"])}' if x['media'] else '') + '.')
    if esquec:
        corpo.append('Ficaram de fora: ' + ', '.join(f'{x["nome"]} ({tit(x["selecao"])}, nota {x["ovr"]})' for x in esquec[:3])
                     + '. A ausência vira assunto: foi opção técnica ou recado?')
    if cansados:
        corpo.append('Preocupação para o clube: ' + ', '.join(f'{x["nome"]} ({x["min"]} minutos, condição {x["condicao"]})' for x in cansados[:3])
                     + ' volta desgastado e pode precisar de descanso.')
    art = max(conv, key=lambda x: x['gols'], default=None)
    titulo = (f'Data FIFA: {art["nome"]} marca {art["gols"]} pela seleção' if art and art['gols'] else
              (f'Data FIFA: {len(conv)} do {nos} defenderam as seleções' if len(conv) > 1 else f'Data FIFA: {conv[0]["nome"]} defende a seleção') if conv else f'Data FIFA: {esquec[0]["nome"]} fica de fora')
    m = {'chave': f'fifa|{ck}|{db.data_txt(fim)}', 'frente': 'selecoes', 'data': fim, 'titulo': titulo, 'autor': 'Redação · seleções',
         'linha_fina': (f'{len(conv)} convocado{"s" if len(conv) != 1 else ""}, {sum(x["gols"] for x in conv)} gol{"s" if sum(x["gols"] for x in conv) != 1 else ""}'
                        + (f', {len(esquec)} ausência{"s" if len(esquec) > 1 else ""} sentida{"s" if len(esquec) > 1 else ""}.' if esquec else '.')),
         'corpo': corpo, 'dados': {'convocados': conv, 'esquecidos': esquec, 'cansados': cansados}}
    resumo = {'data': list(fim), 'convocados': conv, 'esquecidos': esquec, 'cansados': cansados}
    car['data_fifa'] = resumo
    fato = {'tipo': 'data_fifa', 'sub': db.data_txt(fim), 'peso': 2.2 + 0.4 * sum(x['gols'] for x in conv) + (1 if esquec else 0), **resumo}
    log(f'data FIFA: {titulo}')
    return [m], [fato]
