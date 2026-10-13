# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""LEGADO (11/10/2026): a memória do futebol deste mundo, guardada no banco da imprensa (historico/imprensa.db).

O save só guarda o presente (última edição de cada prêmio, duas temporadas de súmulas). A cada reunião:
  - prêmios individuais (premios_save.ler): melhor do mundo + continentais, top 3 com votos -> tabela premios;
  - diário de carreira dos jogadores do clube (premios_save.favoritos): títulos, artilharias, assistências, melhor
    jogador, time do torneio, Bolas de Ouro desde 2029 -> tabela diario;
  - títulos do clube (pelos diários: quem estava no elenco campeão) e campeão/vice da liga quando ela termina, com o
    RETRATO dos elencos (nome, posição, nota, idade) -> tabela titulos.
Com isso: perfil de carreira de cada jogador (para a imprensa falar da carreira, não só da semana), nível de fama
(fervo de fãs e haters), comparações com lendas reais e quem "bate na trave".
"""
import collections
import json

import imprensa_db as db

COMPS = {0x11: 'Premier League', 0x17: 'FA Cup', 0x04: 'UEFA Champions League', 0x07: 'Supercopa da UEFA',
         0x69: 'Torneio de pré-temporada', 0x6B: 'Torneio de pré-temporada', 0x01: 'Mundial de Clubes (FIFA Intercontinental Cup)',
         0x56: 'FA Community Shield'}   # 11/10/2026: 0x56 (=86) é a Community Shield (16/08); 0x69/0x6B (=105/107) são pré-temporada
CATEGORIA_NOME = {'mundo': 'Bola de Ouro (melhor do mundo)', 'europa': 'Melhor jogador da Europa',
                  'america_sul': 'Melhor jogador da América do Sul', 'asia': 'Melhor jogador da Ásia'}
# fatos reais da Bola de Ouro, usados nas comparações (nada inventado)
LENDAS = [
    ('Lionel Messi', 8, 'oito Bolas de Ouro, quatro delas seguidas (2009 a 2012)'),
    ('Cristiano Ronaldo', 5, 'cinco Bolas de Ouro'),
    ('Michel Platini', 3, 'três Bolas de Ouro seguidas (1983 a 1985)'),
    ('Johan Cruyff', 3, 'três Bolas de Ouro'),
    ('Marco van Basten', 3, 'três Bolas de Ouro'),
    ('Ronaldo Fenômeno', 2, 'duas Bolas de Ouro (1997 e 2002)'),
    ('Ronaldinho Gaúcho', 1, 'a Bola de Ouro de 2005'),
    ('Kaká', 1, 'a Bola de Ouro de 2007'),
    ('Rivaldo', 1, 'a Bola de Ouro de 1999'),
    ('Zinedine Zidane', 1, 'a Bola de Ouro de 1998'),
]
BRASILEIROS = {'Ronaldo Fenômeno', 'Ronaldinho Gaúcho', 'Kaká', 'Rivaldo'}


def comp_nome(c):
    return COMPS.get(c, f'Copa {c}') if c is not None else ''


def temporada(data):
    y, m = data[0], data[1]
    return f'{y}-{str(y + 1)[-2:]}' if m >= 7 else f'{y - 1}-{str(y)[-2:]}'


# ---------------------------------------------------------------- captura (a cada reunião)
def capturar(car, r, d, s, P, log=print):
    import premios_save as ps
    ck = car.get('ck')
    nome = lambda k: P[k].name.strip() if k in P else None
    n = {'premios': 0, 'diario': 0, 'titulos': 0}
    with db.conectar() as c:
        for cat, v in ps.ler(d).items():
            for pos, x in enumerate(v['top'], 1):
                k = (x['reg'], x['pid'])
                c.execute('INSERT OR REPLACE INTO premios VALUES (?,?,?,?,?,?,?,?,?,?)',
                          (ck, v['ano'], cat, pos, x['reg'], x['pid'], nome(k), s.name(x['clube']).strip(), x['votos'], 'save'))
                n['premios'] += 1
        # prêmio de melhor técnico do mundo: o save guarda só o id do técnico. Os ids confirmados viram nome
        # (11/10/2026: o usuário mostrou o prêmio de 2034 = Filipe Luís, id 917861, carreira ML00000000)
        tec = (ps.ler(d).get('mundo') or {})
        if tec.get('tecnico'):
            ids = car.setdefault('tecnico_ids', {})
            if ck and ck.startswith('ML00000000') and r.get('tecnico') == 'Filipe Luís':
                ids.setdefault('917861', r['tecnico'])
            nome_t = ids.get(str(tec['tecnico']))
            c.execute('INSERT OR REPLACE INTO premios VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (ck, tec['ano'], 'tecnico', 1, 0, tec['tecnico'], nome_t or 'técnico de outro clube',
                       r['time'] if nome_t else None, None, 'save'))
        # prêmios OFICIAIS de fim de temporada de cada competição (artilheiro, garçom, melhor jogador, time ideal):
        # o save guarda as 2 últimas edições; o banco guarda todas (12/10/2026)
        for bl in ps.competicoes(d, set(P)):
            if bl['comp'] is None:
                continue
            ordem = collections.Counter()
            for x in bl['itens']:
                f = P.get((x['reg'], x['pid']))
                c.execute('INSERT OR REPLACE INTO premios_comp VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                          (ck, bl['comp'], bl['ano'], x['tipo'], ordem[x['tipo']], x['reg'], x['pid'], f.name.strip() if f else None,
                           f.pos if f else None, s.name(x['clube']).strip(), x['valor']))
                ordem[x['tipo']] += 1
        diarios = ps.favoritos(d, set(P))
        for f in diarios:
            k = (f['reg'], f['pid'])
            for e in f['eventos']:
                c.execute('INSERT OR IGNORE INTO diario VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (ck, f['reg'], f['pid'], nome(k), db.data_txt(e['data']), e['tipo'], e.get('comp') if e.get('comp') is not None else -1,
                           e.get('premio') or '', int(bool(e.get('titulo'))), int(bool(e.get('melhor'))), e.get('artilheiro') or 0,
                           e.get('assistencias') or 0, int(bool(e.get('time_torneio')))))
                n['diario'] += 1
                if e.get('premio') == 'melhor_do_mundo':   # Bola de Ouro de anos que o save já não guarda
                    c.execute('INSERT OR IGNORE INTO premios VALUES (?,?,?,?,?,?,?,?,?,?)',
                              (ck, e['data'][0], 'mundo', 1, f['reg'], f['pid'], nome(k), None, None, 'diario'))
        # títulos do clube pelos diários: o elenco campeão = quem tem o título no diário
        ti_nome = r['time']
        conq = collections.defaultdict(list)
        for f in diarios:
            for e in f['eventos']:
                if e.get('titulo') and e.get('comp') is not None:
                    conq[(temporada(e['data']), e['comp'], db.data_txt(e['data']))].append(nome((f['reg'], f['pid'])))
        for (temp, comp, data), elenco in conq.items():
            if len(elenco) >= 3:
                c.execute('INSERT OR IGNORE INTO titulos VALUES (?,?,?,?,?,?,?,?,?,?)',
                          (ck, temp, comp_nome(comp), ti_nome, None, None, data,
                           json.dumps(sorted(set(filter(None, elenco))), ensure_ascii=False), None, 'diario'))
                n['titulos'] += 1
        # campeão e vice da liga quando ela termina (retrato dos dois elencos)
        L = car.get('liga') or {}
        tab = L.get('classificacao') or []
        if len(tab) >= 8 and len({t['j'] for t in tab}) == 1 and tab[0]['j'] == 2 * (len(tab) - 1):
            def retrato(nome_t):
                i = s.find_team(nome_t)
                if i is None:
                    return None
                import encaixe
                out = []
                for k in s.squad(i):
                    f = P.get(k)
                    if f:
                        try:
                            nt = round(encaixe.rating(f, f.pos))
                        except Exception:  # noqa: BLE001
                            nt = None
                        out.append({'nome': f.name.strip(), 'pos': f.pos, 'nota': nt, 'idade': f.age})
                return json.dumps(sorted(out, key=lambda x: -(x['nota'] or 0)), ensure_ascii=False)
            temp = temporada(tuple(r['hoje']))
            c.execute('INSERT OR REPLACE INTO titulos VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (ck, temp, L.get('competicao') or 'Liga', tab[0]['time'], tab[1]['time'],
                       f'{tab[0]["pts"]} x {tab[1]["pts"]} pontos', db.data_txt(tuple(r['hoje'])),
                       retrato(tab[0]['time']), retrato(tab[1]['time']), 'tabela'))
            n['titulos'] += 1
    return n


# ---------------------------------------------------------------- consulta
def perfil(ck, k, nome=None):
    """Carreira do jogador pelo banco: Bolas de Ouro, pódios, continentais, títulos, artilharias, prêmios."""
    reg, pid = k
    with db.conectar() as c:
        pr = [dict(x) for x in c.execute('SELECT * FROM premios WHERE carreira = ? AND reg = ? AND pid = ?', (ck, reg, pid))]
        di = [dict(x) for x in c.execute('SELECT * FROM diario WHERE carreira = ? AND reg = ? AND pid = ? ORDER BY data', (ck, reg, pid))]
    bolas = sorted({p['ano'] for p in pr if p['categoria'] == 'mundo' and p['posicao'] == 1} |
                   {int(e['data'][:4]) for e in di if e['premio'] == 'melhor_do_mundo'})
    podios = sorted({p['ano'] for p in pr if p['categoria'] == 'mundo' and p['posicao'] in (2, 3)})
    cont = sorted({int(e['data'][:4]) for e in di if e['premio'] == 'premio_continental'} |
                  {p['ano'] for p in pr if p['categoria'] != 'mundo' and p['posicao'] == 1})
    tit = collections.Counter(comp_nome(e['comp']) for e in di if e['titulo'] and e['comp'] >= 0)
    art = [(temporada(tuple(int(x) for x in e['data'].split('-'))), comp_nome(e['comp']), e['artilheiro']) for e in di if e['artilheiro']]
    ass = [(temporada(tuple(int(x) for x in e['data'].split('-'))), comp_nome(e['comp']), e['assistencias']) for e in di if e['assistencias']]
    melhor = [(temporada(tuple(int(x) for x in e['data'].split('-'))), comp_nome(e['comp'])) for e in di if e['melhor']]
    tt = sum(1 for e in di if e['time_torneio'])
    seguidas = 0
    for i, a in enumerate(bolas):
        run = 1
        while i + run < len(bolas) and bolas[i + run] == a + run:
            run += 1
        seguidas = max(seguidas, run)
    p = {'nome': nome or (di[0]['nome'] if di else None), 'bolas': bolas, 'bolas_seguidas': seguidas, 'podios': podios,
         'continentais': cont, 'titulos': dict(tit), 'n_titulos': sum(tit.values()), 'artilharias': art,
         'assistencias': ass, 'melhor_jogador': melhor, 'time_torneio': tt}
    p['fama'] = (25 * len(bolas) + 6 * len(podios) + 8 * len(cont) + sum(tit.values()) +
                 4 * sum(1 for x in art if x[1] == 'Premier League' or 'Liga' in x[1]) + 2 * len(ass) + 3 * len(melhor) + 0.5 * tt)
    p['nivel'] = ('mito' if len(bolas) >= 4 else 'lenda' if p['fama'] >= 50 else 'craque mundial' if p['fama'] >= 25
                  else 'ídolo' if p['fama'] >= 10 else 'normal')
    return p


def resumo(p, curto=True):
    """Frase de carreira para a imprensa ('dono de 4 Bolas de Ouro e 27 títulos')."""
    partes = []
    if p['bolas']:
        partes.append(f'{len(p["bolas"])} Bola{"s" if len(p["bolas"]) > 1 else ""} de Ouro' +
                      (f', {p["bolas_seguidas"]} seguidas' if p['bolas_seguidas'] >= 2 and not curto else ''))
    if p['n_titulos'] >= 3:
        partes.append(f'{p["n_titulos"]} títulos')
    liga = [x for x in p['artilharias'] if 'Premier' in x[1] or 'Liga' in x[1] or 'Brasileirão' in x[1]]
    if len(liga) >= 2:
        partes.append(f'{len(liga)} artilharias de liga')
    if not curto and p['continentais']:
        partes.append(f'{len(p["continentais"])} prêmio{"s" if len(p["continentais"]) > 1 else ""} continenta{"is" if len(p["continentais"]) > 1 else "l"}')
    return ' e '.join([', '.join(partes[:-1]), partes[-1]]) if len(partes) > 1 else (partes[0] if partes else '')


def comparacoes(p, brasileiro=False):
    """Lendas reais com quem a imprensa/torcida compara (coerente com o número de Bolas de Ouro)."""
    n = len(p['bolas'])
    if n == 0:
        return []
    acima = [x for x in LENDAS if x[1] > n]
    igual = [x for x in LENDAS if x[1] == n]
    abaixo = [x for x in LENDAS if 0 < x[1] < n]
    out = []
    if igual:
        out.append(('igual', igual[0]))
    if acima:
        out.append(('alvo', acima[-1]))   # o próximo degrau
    if abaixo:
        br = [x for x in abaixo if x[0] in BRASILEIROS] if brasileiro else []
        out.append(('superou', (br or abaixo)[0]))
    return out


def podio_sem_vitoria(ck, minimo=2):
    """Quem 'bate na trave': pódios da Bola de Ouro sem nunca vencer."""
    with db.conectar() as c:
        rows = [dict(x) for x in c.execute('SELECT * FROM premios WHERE carreira = ? AND categoria = ?', (ck, 'mundo'))]
    por = collections.defaultdict(lambda: {'pod': [], 'venceu': False, 'nome': None})
    for x in rows:
        e = por[(x['reg'], x['pid'])]
        e['nome'] = x['nome'] or e['nome']
        if x['posicao'] == 1:
            e['venceu'] = True
        else:
            e['pod'].append(x['ano'])
    return [(v['nome'], sorted(v['pod'])) for v in por.values() if not v['venceu'] and len(v['pod']) >= minimo]


def premio_recente(ck, hoje, dias=35):
    """A apuração mais recente do melhor do mundo, se saiu há pouco (o jogo entrega em 2/dez)."""
    import datetime as dt
    with db.conectar() as c:
        ano = c.execute("SELECT MAX(ano) FROM premios WHERE carreira = ? AND categoria = 'mundo' AND fonte = 'save'", (ck,)).fetchone()[0]
        if not ano:
            return None
        top = [dict(x) for x in c.execute("SELECT * FROM premios WHERE carreira = ? AND categoria = 'mundo' AND ano = ? ORDER BY posicao", (ck, ano))]
    if not 0 <= (dt.date(*hoje) - dt.date(ano, 12, 2)).days <= dias:
        return None
    return {'ano': ano, 'top': top}


TIPO_PREMIO = {2: 'artilheiro', 12: 'garcom', 13: 'melhor'}   # 0 e 3..11 = time ideal; 14 repete o melhor; 1 = ?


def premios_oficiais(ck, comps=None, ultimos=2):
    """{(comp, ano): {'artilheiro': [...], 'garcom': [...], 'melhor': {...}, 'time': [11]}} das edições mais recentes."""
    from proximo_jogo import nome_comp
    with db.conectar() as c:
        rows = [dict(x) for x in c.execute('SELECT * FROM premios_comp WHERE carreira = ? ORDER BY ano DESC, comp, tipo, ordem', (ck,))]
    por = collections.OrderedDict()
    for x in rows:
        if comps is not None and x['comp'] not in comps:
            continue
        k = (x['comp'], x['ano'])
        e = por.setdefault(k, {'comp': x['comp'], 'nome': nome_comp(x['comp']), 'ano': x['ano'], 'artilheiro': [], 'garcom': [], 'melhor': None, 'time': []})
        j = {'nome': x['nome'], 'pos': x['pos'], 'time': x['clube'], 'valor': x['valor'], 'k': [x['reg'], x['pid']]}
        t = TIPO_PREMIO.get(x['tipo'])
        if t == 'melhor':   # o melhor jogador também é o 11º do time ideal
            if not e['melhor']:
                e['melhor'] = j
                e['time'].append(dict(j, nota=x['valor'] / 10))
        elif t:
            e[t].append(j)
        elif x['tipo'] == 0 or 3 <= x['tipo'] <= 11:
            e['time'].append(dict(j, nota=x['valor'] / 10))
    for e in por.values():
        e['artilheiro'].sort(key=lambda j: -j['valor'])
        e['garcom'].sort(key=lambda j: -j['valor'])
    anos = sorted({k[1] for k in por}, reverse=True)[:ultimos]
    return [e for k, e in por.items() if k[1] in anos]


def _oficiais_do_clube(ck):
    """Prêmios oficiais das competições que o clube disputou (liga, copas, continental)."""
    try:
        import historia
        from proximo_jogo import NOMES_COMP
        nomes = {c for t in historia.temporadas(ck) for c in (t.get('comps') or {})}
        comps = {k for k, v in NOMES_COMP.items() if v in nomes}
        return premios_oficiais(ck, comps or None)
    except Exception:  # noqa: BLE001
        return []


def hall(ck):
    """Para a Central: Bolas de Ouro por ano, títulos do clube, apuração mais recente."""
    with db.conectar() as c:
        bolas = [dict(x) for x in c.execute("SELECT ano, nome, clube, votos, fonte FROM premios WHERE carreira = ? AND categoria = 'mundo' AND posicao = 1 ORDER BY ano DESC", (ck,))]
        ult = c.execute("SELECT MAX(ano) FROM premios WHERE carreira = ? AND categoria = 'mundo' AND fonte = 'save'", (ck,)).fetchone()[0]
        apur = [dict(x) for x in c.execute("SELECT categoria, ano, posicao, nome, clube, votos FROM premios WHERE carreira = ? AND fonte = 'save' ORDER BY categoria, ano DESC, posicao", (ck,))]
        tit = [dict(x) for x in c.execute('SELECT temporada, comp, campeao, vice, placar, elenco_campeao FROM titulos WHERE carreira = ? ORDER BY temporada DESC, data DESC', (ck,))]
    for t in tit:
        t['elenco_campeao'] = json.loads(t['elenco_campeao'] or '[]')
    return {'bolas': bolas, 'apuracao': [a for a in apur if a['categoria'] == 'mundo' and a['ano'] == ult] if ult else [],
            'continentais': [a for a in apur if a['categoria'] not in ('mundo', 'tecnico') and a['posicao'] == 1], 'titulos': tit,
            'tecnicos': [a for a in apur if a['categoria'] == 'tecnico'],
            'oficiais': _oficiais_do_clube(ck),
            'na_trave': podio_sem_vitoria(ck)}
