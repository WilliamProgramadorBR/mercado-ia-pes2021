"""HISTÓRIA DO CLUBE (11/10/2026): o livro dos recordes da sua era.

O jogo APAGA as súmulas e as estatísticas na virada da temporada. Por isso, a cada reunião, a temporada em andamento é
"fechada" no banco (historico/imprensa.db), sempre sobrescrevendo a mesma linha: a última reunião antes da virada deixa
a temporada completa guardada para sempre.

  hist_temporada  resumo do time por temporada: jogos, V/E/D, gols, maior vitória/derrota, sequências, liga
                  (posição e pontos), títulos (tabela titulos do legado.py), artilheiro, garçom, destaque
  hist_jogador    números de cada jogador do clube por temporada (só jogos oficiais do clube)
  hist_marcos     marcos já anunciados (100º jogo, 50º gol, recorde batido...), para não repetir

Daí saem: recordes (de temporada e da era), rankings históricos (artilheiro, garçom, mais jogos) e os MARCOS novos que
viram notícia, capa de jornal, pauta do Bola na Mesa e post nas redes.
"""
import collections
import datetime as dt
import json

import imprensa_db as db

NAO_OFICIAL = set(range(100, 111)) | {56}
LIMIARES = {'gols': (50, 100, 150, 200, 250, 300, 400, 500), 'jogos': (100, 200, 300, 400, 500, 600),
            'assist': (50, 100, 150, 200, 250)}
NOME_METRICA = {'gols': 'gols', 'jogos': 'jogos', 'assist': 'assistências'}


def tkey(ini):
    import temporada
    return temporada.chave(ini)   # '2027' (calendário anual) ou '2026-27'


def ttxt(k):
    return k.replace('-', '/')


def _agora():
    return dt.datetime.now().isoformat(timespec='seconds')


# ---------------------------------------------------------------- fechar uma temporada
def fechar(ck, todas, ti, nos, P, nome_time, ini, fim=None, tabela=None, parcial=False):
    """Calcula e grava a temporada [ini, fim) do clube ti. tabela = classificação da liga (do jogo) se for desta temporada."""
    jogos = sorted((p for p in todas if ti in (p['time1'], p['time2']) and p['comp'] not in NAO_OFICIAL
                    and tuple(p['data']) >= ini and (not fim or tuple(p['data']) < fim)), key=lambda p: (tuple(p['data']), p.get('num') or 0))
    if not jogos:
        return None
    from proximo_jogo import nome_comp
    T = {'temporada': tkey(ini), 'jogos': 0, 'v': 0, 'e': 0, 'd': 0, 'gp': 0, 'gc': 0, 'comps': collections.Counter()}
    seqv = seqi = mv = mi = 0
    maior_v = maior_d = None
    J = collections.defaultdict(lambda: {'jogos': 0, 'gols': 0, 'assist': 0, 'notas': [], 'min': 0})
    for p in jogos:
        casa = p['time1'] == ti
        gp, gc = (p['gols1'], p['gols2']) if casa else (p['gols2'], p['gols1'])
        adv = nome_time(p['time2'] if casa else p['time1'])
        T['jogos'] += 1
        T['gp'] += gp
        T['gc'] += gc
        T['comps'][nome_comp(p['comp'])] += 1
        r = 'v' if gp > gc else 'e' if gp == gc else 'd'
        T[r] += 1
        seqv = seqv + 1 if r == 'v' else 0
        seqi = seqi + 1 if r != 'd' else 0
        mv, mi = max(mv, seqv), max(mi, seqi)
        jogo = {'placar': f'{gp} x {gc}', 'adv': adv, 'data': list(p['data']), 'comp': nome_comp(p['comp']), 'saldo': gp - gc}
        if r == 'v' and (not maior_v or (gp - gc, gp) > (maior_v['saldo'], int(maior_v['placar'].split()[0]))):
            maior_v = jogo
        if r == 'd' and (not maior_d or gc - gp > -maior_d['saldo']):
            maior_d = jogo
        for x in p['linhas1'] if casa else p['linhas2']:
            if x['minutos'] <= 0:
                continue
            e = J[(x['reg'], x['pid'])]
            e['jogos'] += 1
            e['gols'] += x['gols']
            e['assist'] += x['assist']
            e['min'] += x['minutos']
            if x['nota']:
                e['notas'].append(x['nota'])
    T.update(seq_vitorias=mv, invencibilidade=mi, maior_vitoria=maior_v, maior_derrota=maior_d, comps=dict(T['comps']),
             ultimo_jogo=list(jogos[-1]['data']), primeiro_jogo=list(jogos[0]['data']), parcial=parcial)
    # a liga: a classificação do próprio jogo (se veio) ou a calculada pelas súmulas
    # a liga = a competição do clube com MAIS jogos no mundo na temporada (no começo, a Supercopa não vira "liga")
    nossas = {p['comp'] for p in jogos}
    tot = collections.Counter(p['comp'] for p in todas if p['comp'] in nossas and tuple(p['data']) >= ini and (not fim or tuple(p['data']) < fim))
    liga_c, n_liga = tot.most_common(1)[0]
    eu = next((t for t in tabela or [] if t.get('eu')), None)
    if n_liga < 10:   # a liga ainda não começou (só supercopas/Community Shield): sem liga, sem curva
        liga_c = None
        T['liga'] = None
    elif eu and eu.get('j'):
        T['liga'] = {'competicao': nome_comp(liga_c), 'pos': eu['pos'], 'pts': eu['pts'], 'j': eu['j'], 'fonte': 'jogo'}
    else:
        pts = collections.Counter()
        for p in todas:
            if p['comp'] == liga_c and tuple(p['data']) >= ini and (not fim or tuple(p['data']) < fim):
                a, b = (3, 0) if p['gols1'] > p['gols2'] else (0, 3) if p['gols1'] < p['gols2'] else (1, 1)
                pts[p['time1']] += a
                pts[p['time2']] += b
        ordem = [t for t, _ in pts.most_common()]
        T['liga'] = {'competicao': nome_comp(liga_c), 'pos': ordem.index(ti) + 1 if ti in ordem else None, 'pts': pts.get(ti),
                     'j': sum(1 for p in jogos if p['comp'] == liga_c), 'fonte': 'súmulas'}
    # a posição na liga depois de cada jogo do clube (gráfico da temporada na Central)
    lj = sorted((p for p in todas if p['comp'] == liga_c and tuple(p['data']) >= ini and (not fim or tuple(p['data']) < fim)),
                key=lambda p: (tuple(p['data']), p.get('num') or 0))
    times_l = {t for p in lj for t in (p['time1'], p['time2'])}
    pts_l, sal_l, serie, n = collections.Counter(), collections.Counter(), [], 0
    for p in lj:
        a, b = (3, 0) if p['gols1'] > p['gols2'] else (0, 3) if p['gols1'] < p['gols2'] else (1, 1)
        pts_l[p['time1']] += a
        pts_l[p['time2']] += b
        sal_l[p['time1']] += p['gols1'] - p['gols2']
        sal_l[p['time2']] += p['gols2'] - p['gols1']
        if ti in (p['time1'], p['time2']):
            n += 1
            ordem = sorted(times_l, key=lambda t: (-pts_l[t], -sal_l[t]))
            serie.append({'j': n, 'd': list(p['data']), 'pos': ordem.index(ti) + 1, 'pts': pts_l[ti]})
    T['serie_liga'] = serie
    with db.conectar() as c:
        T['titulos'] = [x[0] for x in c.execute('SELECT comp FROM titulos WHERE carreira = ? AND temporada = ? AND campeao = ?',
                                                (ck, tkey(ini), nos))]
    linhas = []
    for k, e in J.items():
        f = P.get(k) if P else None
        if not f:
            continue
        media = round(sum(e['notas']) / len(e['notas']), 2) if e['notas'] else None
        linhas.append((ck, tkey(ini), k[0], k[1], f.name.strip(), f.pos, e['jogos'], e['gols'], e['assist'], media, e['min']))
    top = lambda i: max(linhas, key=lambda x: (x[i], x[6]), default=None)
    art, gar = top(7), top(8)
    regs = [x for x in linhas if x[6] >= max(10, T['jogos'] // 3) and x[9]]
    dest = max(regs, key=lambda x: x[9], default=None)
    T['artilheiro'] = {'nome': art[4], 'gols': art[7]} if art and art[7] else None
    T['garcom'] = {'nome': gar[4], 'assist': gar[8]} if gar and gar[8] else None
    T['destaque'] = {'nome': dest[4], 'media': dest[9], 'jogos': dest[6]} if dest else None
    with db.conectar() as c:
        c.execute('INSERT OR REPLACE INTO hist_temporada VALUES (?, ?, ?, ?)', (ck, tkey(ini), json.dumps(T, ensure_ascii=False), _agora()))
        c.execute('DELETE FROM hist_jogador WHERE carreira = ? AND temporada = ?', (ck, tkey(ini)))
        c.executemany('INSERT INTO hist_jogador VALUES (?,?,?,?,?,?,?,?,?,?,?)', linhas)
    return T


# ---------------------------------------------------------------- leitura
def temporadas(ck):
    with db.conectar() as c:
        return [json.loads(x[0]) for x in c.execute('SELECT dados FROM hist_temporada WHERE carreira = ? ORDER BY temporada', (ck,))]


def totais(ck):
    """{(reg, pid): totais pelo clube em todas as temporadas registradas}."""
    out = {}
    with db.conectar() as c:
        for x in c.execute('SELECT reg, pid, nome, pos, SUM(jogos), SUM(gols), SUM(assist), COUNT(*), MIN(temporada), MAX(temporada) '
                           'FROM hist_jogador WHERE carreira = ? GROUP BY reg, pid', (ck,)):
            out[(x[0], x[1])] = {'nome': x[2], 'pos': x[3], 'jogos': x[4], 'gols': x[5], 'assist': x[6], 'temporadas': x[7],
                                 'de': ttxt(x[8]), 'ate': ttxt(x[9])}
    return out


def recordes(ck):
    with db.conectar() as c:
        hj = [dict(zip(('temporada', 'nome', 'pos', 'jogos', 'gols', 'assist', 'media'), x)) for x in
              c.execute('SELECT temporada, nome, pos, jogos, gols, assist, media FROM hist_jogador WHERE carreira = ?', (ck,))]
    ts = [t for t in temporadas(ck) if not t.get('parcial')]   # temporada só com parte das súmulas não conta recorde
    if not ts:
        return {}
    hj = [x for x in hj if x['temporada'] in {t['temporada'] for t in ts}]
    rec = {}

    def pega(chave, xs, val, txt):
        if xs:
            x = max(xs, key=val)
            rec[chave] = dict(x, valor=val(x), texto=txt(x))
    pega('gols_temporada', hj, lambda x: x['gols'], lambda x: f'{x["gols"]} gols ({x["nome"]}, {ttxt(x["temporada"])})')
    pega('assist_temporada', hj, lambda x: x['assist'], lambda x: f'{x["assist"]} assistências ({x["nome"]}, {ttxt(x["temporada"])})')
    pega('jogos_temporada', hj, lambda x: x['jogos'], lambda x: f'{x["jogos"]} jogos ({x["nome"]}, {ttxt(x["temporada"])})')
    pega('media_temporada', [x for x in hj if x['media'] and x['jogos'] >= 20], lambda x: x['media'],
         lambda x: f'média {str(x["media"]).replace(".", ",")} em {x["jogos"]} jogos ({x["nome"]}, {ttxt(x["temporada"])})')
    pega('time_gols', ts, lambda t: t['gp'], lambda t: f'{t["gp"]} gols marcados ({ttxt(t["temporada"])})')
    pega('time_defesa', [t for t in ts if t['jogos'] >= 30], lambda t: -t['gc'] / t['jogos'],
         lambda t: f'{t["gc"]} gols sofridos em {t["jogos"]} jogos ({ttxt(t["temporada"])})')
    pega('seq_vitorias', ts, lambda t: t['seq_vitorias'], lambda t: f'{t["seq_vitorias"]} vitórias seguidas ({ttxt(t["temporada"])})')
    pega('invencibilidade', ts, lambda t: t['invencibilidade'], lambda t: f'{t["invencibilidade"]} jogos sem perder ({ttxt(t["temporada"])})')
    ofi = lambda t: [c for c in t.get('titulos') or [] if 'pré-temporada' not in c]   # torneio de pré-temporada não conta
    pega('titulos_temporada', ts, lambda t: len(ofi(t)), lambda t: f'{len(ofi(t))} títulos oficiais ({ttxt(t["temporada"])})')
    lp = [t for t in ts if (t.get('liga') or {}).get('pts')]
    pega('pontos_liga', lp, lambda t: t['liga']['pts'], lambda t: f'{t["liga"]["pts"]} pontos na {t["liga"]["competicao"]} ({ttxt(t["temporada"])})')
    mv = [dict(t['maior_vitoria'], temporada=t['temporada']) for t in ts if t.get('maior_vitoria')]
    pega('maior_vitoria', mv, lambda x: (x['saldo'], int(x['placar'].split()[0])),
         lambda x: f'{x["placar"]} no {x["adv"]} ({x["comp"]}, {x["data"][2]:02d}/{x["data"][1]:02d}/{x["data"][0]})')
    return rec


def painel(ck, max_ranking=10):
    """O que a Central mostra na aba História."""
    ts = temporadas(ck)
    if not ts:
        return None
    tot = sorted(totais(ck).values(), key=lambda x: -x['gols'])
    with db.conectar() as c:
        marcos = [{'data': x[0], 'texto': x[1]} for x in c.execute(
            "SELECT data, texto FROM hist_marcos WHERE carreira = ? AND texto != '' ORDER BY data DESC LIMIT 12", (ck,))]
    return {'desde': ttxt(ts[0]['temporada']), 'temporadas': ts[::-1], 'recordes': recordes(ck), 'marcos': marcos,
            'artilheiros': tot[:max_ranking], 'garcons': sorted(tot, key=lambda x: -x['assist'])[:max_ranking],
            'mais_jogos': sorted(tot, key=lambda x: -x['jogos'])[:max_ranking]}


# ---------------------------------------------------------------- marcos (viram notícia)
def marcos_novos(ck, hoje, temp_atual):
    """Marcos alcançados desde a última reunião. Na 1ª vez, registra tudo em silêncio (não anuncia 10 anos de uma vez)."""
    tot = totais(ck)
    with db.conectar() as c:
        feitos = {x[0] for x in c.execute('SELECT chave FROM hist_marcos WHERE carreira = ?', (ck,))}
    silencio = not feitos
    novos = []
    for k, t in tot.items():
        for met, lims in LIMIARES.items():
            for lim in lims:
                if t[met] >= lim and f'{met}|{k[0]}:{k[1]}|{lim}' not in feitos:
                    novos.append({'chave': f'{met}|{k[0]}:{k[1]}|{lim}', 'tipo': 'marco', 'metrica': met, 'valor': lim, 'nome': t['nome'],
                                  'k': list(k), 'total': t[met], 'temporadas': t['temporadas'],
                                  'texto': f'{t["nome"]} chega a {lim} {NOME_METRICA[met]} pelo clube.'})
    # recorde de temporada batido na temporada atual (contra as temporadas anteriores)
    with db.conectar() as c:
        hj = c.execute('SELECT temporada, nome, reg, pid, gols, assist FROM hist_jogador WHERE carreira = ?', (ck,)).fetchall()
    parciais = {t['temporada'] for t in temporadas(ck) if t.get('parcial')}
    for met, i in (('gols', 4), ('assist', 5)):
        antes = [x for x in hj if x[0] != temp_atual and x[0] not in parciais]
        agora = [x for x in hj if x[0] == temp_atual]
        if not antes or not agora:
            continue
        rec = max(antes, key=lambda x: x[i])
        top = max(agora, key=lambda x: x[i])
        chave = f'recorde_{met}|{temp_atual}'
        if top[i] > rec[i] and chave not in feitos:
            novos.append({'chave': chave, 'tipo': 'recorde', 'metrica': met, 'valor': top[i], 'nome': top[1], 'k': [top[2], top[3]],
                          'anterior': {'nome': rec[1], 'valor': rec[i], 'temporada': ttxt(rec[0])},
                          'texto': f'{top[1]} bate o recorde de {NOME_METRICA[met]} numa temporada: {top[i]} (o anterior era {rec[i]}, de {rec[1]} em {ttxt(rec[0])}).'})
    if novos:
        with db.conectar() as c:
            c.executemany('INSERT OR IGNORE INTO hist_marcos VALUES (?, ?, ?, ?)',
                          [(ck, m['chave'], db.data_txt(hoje), '' if silencio else m['texto']) for m in novos])
    return [] if silencio else novos


# ---------------------------------------------------------------- na reunião
def da_reuniao(car, r, d, snap, log=print):
    """Fecha a temporada atual no banco, corrige a liga da anterior com a tabela final do jogo (na pré-temporada) e devolve
    os marcos novos. Guarda o painel em car['historia'] para a Central."""
    import destaques
    import imprensa
    ck = car.get('ck')
    if not ck:
        return []
    hoje = tuple(r['hoje'])
    ini = destaques.ini_temporada(hoje)
    ctx = imprensa._contexto(car, r, d, snap)
    nome_time = lambda i: ctx['s'].name(i).strip()
    todas = r.get('todas_partidas') or []
    tab = (car.get('diretoria') or {}).get('tabela') or []
    tem_jogo = any(r['ti'] in (p['time1'], p['time2']) and p['comp'] not in NAO_OFICIAL and tuple(p['data']) >= ini for p in todas)
    if tem_jogo:
        fechar(ck, todas, r['ti'], r['time'], ctx['P'], nome_time, ini, tabela=tab if any(t.get('j') for t in tab) else None)
    elif tab and destaques.fim_de_liga(car):   # pré-temporada: a tabela do jogo ainda é a final da temporada passada
        import temporada
        ant = tkey(temporada.anterior(ini))
        with db.conectar() as c:
            x = c.execute('SELECT dados FROM hist_temporada WHERE carreira = ? AND temporada = ?', (ck, ant)).fetchone()
            eu = next((t for t in tab if t.get('eu')), None)
            if x and eu:
                T = json.loads(x[0])
                if (T.get('liga') or {}).get('fonte') != 'jogo':
                    T['liga'] = dict(T.get('liga') or {}, pos=eu['pos'], pts=eu['pts'], j=eu['j'], fonte='jogo')
                    c.execute('UPDATE hist_temporada SET dados = ? WHERE carreira = ? AND temporada = ?', (json.dumps(T, ensure_ascii=False), ck, ant))
    novos = marcos_novos(ck, hoje, tkey(ini))
    car['historia'] = painel(ck)
    if novos:
        log('história: ' + '; '.join(m['texto'] for m in novos))
    return novos
