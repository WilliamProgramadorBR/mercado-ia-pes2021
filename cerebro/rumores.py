# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""RUMORES DE MERCADO sobre os NOSSOS jogadores (11/10/2026).

Clube grande "de olho" em quem está jogando muito (ou em quem anda insatisfeito). O rumor vive algumas semanas:
nasce, esquenta (o jogador segue bem, a moral cai, ele é vaidoso/jovem impaciente) ou esfria, e às vezes vira
CONSULTA FORMAL (o empresário manda mensagem no celular do técnico). Nunca vende ninguém sozinho: é narrativa, e as
respostas do técnico (coletiva, celular) mexem na moral.

car['rumores'] = [{id, nome, k, clube, desde, ate, calor 0..100, ativo, fase: 'boato'|'consulta'|'esfriou', consulta_feita}]
"""
import datetime as dt

GIGANTES = ['REAL MADRID', 'BARCELONA', 'BAYERN MÜNCHEN', 'PARIS SAINT-GERMAIN', 'JUVENTUS', 'MANCHESTER CITY', 'LIVERPOOL',
            'ARSENAL', 'CHELSEA', 'INTER', 'MILAN', 'ATLÉTICO DE MADRID', 'BORUSSIA DORTMUND', 'AL-NASSR FC', 'AL-HILAL',
            'NEWCASTLE UNITED', 'TOTTENHAM HOTSPUR']


def _d(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def _clubes(s, nos, car):
    ok = [c for c in GIGANTES if c != nos and s.find_team(c) is not None]
    if len(ok) < 5:   # nomes não licenciados no save: usa os clubes mais fortes que aparecem nos destaques do mundo
        ok += [x['time'] for x in ((car.get('mundo') or {}).get('estrelas') or []) if x['time'] != nos and x['time'] not in ok]
    return ok[:20]


def da_reuniao(car, r, d, snap, rnd, log=print):
    """Atualiza os rumores. Devolve (fatos para as capas, notícias, rumores que viraram consulta formal)."""
    import imprensa
    hoje = tuple(r['hoje'])
    R = [x for x in car.get('rumores') or [] if _d(hoje, tuple(x['desde'])) <= 120]
    J = {j['nome']: j for j in r['J']}
    fatos, noticias, consultas = [], [], []
    for x in R:
        if not x['ativo']:
            continue
        j = J.get(x['nome'])
        if not j:   # saiu do clube
            x['ativo'] = False
            continue
        tr = set(((j.get('perfil') or {}).get('tracos')) or [])
        delta = rnd.randint(-14, 10) + (8 if j['moral'] < 60 else 0) + (5 if tr & {'vaidoso', 'jovem impaciente'} else 0) \
            + (4 if j['r_nota'] >= 6.8 else 0) - x.pop('esfriar', 0)
        x['calor'] = max(0, min(100, x['calor'] + delta))
        if x['calor'] >= 65 and not x.get('consulta_feita'):
            x['consulta_feita'] = True
            x['fase'] = 'consulta'
            consultas.append(x)
            noticias.append(f'MERCADO: o {x["clube"]} fez uma consulta formal por {x["nome"]}.')
            fatos.append({'tipo': 'rumor', 'sub': x['id'] + '|consulta', 'peso': 3.2, 'x': dict(x), 'fase': 'consulta', 'j': j})
        elif x['calor'] <= 10 or hoje >= tuple(x['ate']):
            x['ativo'] = False
            x['fase'] = 'esfriou'
            noticias.append(f'MERCADO: o interesse do {x["clube"]} por {x["nome"]} esfriou.')
    ativos = [x for x in R if x['ativo']]
    if len(ativos) < 2 and rnd.random() < 0.4:
        ja = {x['nome'] for x in R if _d(hoje, tuple(x['desde'])) <= 60}
        cands = []
        for j in r['J']:
            if j['nome'] in ja or j['idade'] > 31:
                continue
            forma = j['t_gols'] + 0.7 * j['t_assist']
            sc = (j['ovr'] - 80) * 0.6 + forma * 0.5 + (j['r_nota'] - 6.3) * 6 + (6 if j['moral'] < 55 else 0)
            if j['ovr'] >= 84 and sc > 4:
                cands.append((sc * rnd.uniform(0.6, 1.4), j))
        if cands:
            _, j = max(cands, key=lambda t: t[0])
            ctx = imprensa._contexto(car, r, d, snap)
            cl = _clubes(ctx['s'], r['time'], car)
            clube = rnd.choice(cl[:7] if j['ovr'] >= 90 else cl)   # superestrela atrai os gigantes
            x = {'id': f'rum|{j["k"][0]}:{j["k"][1]}|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}', 'nome': j['nome'], 'k': list(j['k']),
                 'clube': clube, 'desde': list(hoje), 'ate': list((dt.date(*hoje) + dt.timedelta(days=rnd.randint(25, 45))).timetuple()[:3]),
                 'calor': rnd.randint(30, 50), 'ativo': True, 'fase': 'boato'}
            R.append(x)
            noticias.append(f'MERCADO: {clube} estaria de olho em {j["nome"]}.')
            fatos.append({'tipo': 'rumor', 'sub': x['id'], 'peso': 2.6 + (1 if j['status'] in ('Lenda', 'Ídolo', 'Superastro') else 0),
                          'x': dict(x), 'fase': 'boato', 'j': j})
    car['rumores'] = R
    if fatos:
        log('rumores: ' + '; '.join(f'{f["x"]["clube"]} x {f["x"]["nome"]} ({f["fase"]})' for f in fatos))
    return fatos, noticias, consultas


def esfriar(car, nome, quanto=30):
    """Resposta firme do técnico ("não está à venda"): o rumor perde força na próxima reunião."""
    for x in car.get('rumores') or []:
        if x['ativo'] and x['nome'] == nome:
            x['esfriar'] = x.get('esfriar', 0) + quanto
