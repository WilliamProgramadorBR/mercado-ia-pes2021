"""O MOMENTO DO TIME (12/10/2026): o que se acumulou nas últimas semanas, não só o último jogo.

Pedido do usuário: "perdemos duas seguidas, o rival encostou, precisamos nos recuperar na Champions e no campeonato, o
clássico está chegando" — a imprensa, as coletivas e as redes precisam enxergar a SEQUÊNCIA. Tudo sai do save:
  sequência    derrotas seguidas, jogos sem vencer, vitórias seguidas, invencibilidade (jogos oficiais da temporada),
               e a sequência só na liga;
  a tabela     a tabela da liga agora x antes das duas últimas rodadas do usuário: o rival que encostou ou abriu,
               liderança perdida ou conquistada (calculada pelas súmulas, vale desde a 1ª rodada, sem esperar a
               "pressão" do diretor de campeonato);
  a agenda     os próximos compromissos (prévias da reunião): Champions/Libertadores, clássico, final, jogo que vale
               disputa, adversário do topo; "semana decisiva" quando vêm dois desses em até 10 dias;
  o clima      crise / alerta / embalado / normal, para dar o tom.
car['momento'] -> coletivas (coletiva_momento.py), análise pós-jogo, redes e Central.
"""
import collections
import datetime as dt

GRANDES = {3, 4, 8, 9, 10, 1, 15, 16}   # Champions, Libertadores, Mundial, AFC
ORD = {2: 'segunda', 3: 'terceira', 4: 'quarta', 5: 'quinta', 6: 'sexta', 7: 'sétima', 8: 'oitava', 9: 'nona', 10: 'décima'}
EXTENSO = {2: 'duas', 3: 'três', 4: 'quatro', 5: 'cinco', 6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove', 10: 'dez'}


def _d(a, b):
    return (dt.date(*tuple(a)[:3]) - dt.date(*tuple(b)[:3])).days


def _res(p, ti):
    gp, gc = (p['gols1'], p['gols2']) if p['time1'] == ti else (p['gols2'], p['gols1'])
    return gp, gc, 'V' if gp > gc else 'E' if gp == gc else 'D'


def _conta(rs, ok):
    n = 0
    for x in reversed(rs):
        if not ok(x):
            break
        n += 1
    return n


def _tabela(todas, comp, ini, ate):
    pts, jg, sg, gp = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    times = set()
    for p in todas:
        if p['comp'] != comp or not ini <= tuple(p['data']) <= ate:
            continue
        a, b, g1, g2 = p['time1'], p['time2'], p['gols1'], p['gols2']
        times.update((a, b))
        pts[a] += 3 if g1 > g2 else 1 if g1 == g2 else 0
        pts[b] += 3 if g2 > g1 else 1 if g1 == g2 else 0
        jg[a] += 1
        jg[b] += 1
        sg[a] += g1 - g2
        sg[b] += g2 - g1
        gp[a] += g1
        gp[b] += g2
    tab = sorted(times, key=lambda t: (-pts[t], -sg[t], -gp[t]))
    return [{'t': t, 'pos': i + 1, 'pts': pts[t], 'j': jg[t], 'sg': sg[t]} for i, t in enumerate(tab)]


def _ultimos_liga(todas, comp, t, ini, n=5):
    rs = [_res(p, t)[2] for p in sorted(todas, key=lambda p: tuple(p['data']))
          if p['comp'] == comp and t in (p['time1'], p['time2']) and tuple(p['data']) >= ini]
    return rs[-n:]


def _tabelas(car, todas, liga, ini, hoje, corte, nm_up, eu):
    """(agora, antes): listas [{'t': NOME, 'pos', 'pts', 'j'}]. AGORA = a tabela oficial do jogo (car['liga']; as súmulas
    às vezes não trazem um jogo — 12/10/2026: faltava a rodada 1 do United e o "perdeu a liderança" saiu errado);
    ANTES = agora menos os pontos ganhos nas súmulas a partir de `corte` (empate mantém a ordem oficial)."""
    of = (car.get('liga') or {}).get('classificacao') or (car.get('diretoria') or {}).get('tabela') or []
    if len(of) >= 10:
        agora = [{'t': x['time'].strip().upper(), 'pts': x['pts'], 'j': x.get('j', 0)} for x in sorted(of, key=lambda x: x['pos'])]
    else:
        agora = [{'t': nm_up(x['t']), 'pts': x['pts'], 'j': x['j']} for x in _tabela(todas, liga, ini, hoje)]
    ganho, jog = collections.Counter(), collections.Counter()
    for p in todas:
        if p['comp'] != liga or not corte <= tuple(p['data']) <= hoje:
            continue
        g1, g2 = p['gols1'], p['gols2']
        a, b = nm_up(p['time1']), nm_up(p['time2'])
        ganho[a] += 3 if g1 > g2 else 1 if g1 == g2 else 0
        ganho[b] += 3 if g2 > g1 else 1 if g1 == g2 else 0
        jog[a] += 1
        jog[b] += 1
    antes = sorted(({'t': x['t'], 'pts': x['pts'] - ganho[x['t']], 'j': x['j'] - jog[x['t']]} for x in agora), key=lambda x: -x['pts'])
    for tab in (agora, antes):
        for i, x in enumerate(tab):
            x['pos'] = i + 1
    return agora, antes


def calcular(r, car, hoje):
    """car['momento'] para a reunião (r = vestiario.analisar com agenda; car já com 'proximos')."""
    import clube
    import temporada
    from proximo_jogo import nome_comp
    ti = r['ti']
    hoje = tuple(hoje)
    todas = r.get('todas_partidas') or []
    nomes = lambda t: clube.nome_time((r.get('_nomes_time') or str)(t).strip())
    liga = temporada.liga(todas, ti, r.get('agenda') or [])
    ini = temporada.inicio(todas, liga, hoje)
    meus = sorted((p for p in r.get('jogos') or [] if p['comp'] not in temporada.NAO_LIGA and tuple(p['data']) >= ini),
                  key=lambda p: tuple(p['data']))
    rs = [_res(p, ti)[2] for p in meus]
    out = {'data': list(hoje), 'forma': ''.join(rs[-6:]), 'jogos': len(rs),
           'seq': {'d': _conta(rs, lambda x: x == 'D'), 'sv': _conta(rs, lambda x: x != 'V'),
                   'v': _conta(rs, lambda x: x == 'V'), 'inv': _conta(rs, lambda x: x != 'D')}}
    if meus:
        u = meus[-1]
        gp, gc, res = _res(u, ti)
        out['ultimos'] = [{'adv': nomes(p['time2'] if p['time1'] == ti else p['time1']), 'gp': _res(p, ti)[0], 'gc': _res(p, ti)[1],
                           'res': _res(p, ti)[2], 'casa': p['time1'] == ti} for p in meus[-5:]]
        out['ultimo'] = {'adv': nomes(u['time2'] if u['time1'] == ti else u['time1']), 'gp': gp, 'gc': gc, 'res': res,
                         'comp': nome_comp(u['comp']), 'continental': u['comp'] in GRANDES, 'data': list(u['data'])}
        # derrota que encerrou uma série longa sem perder
        if res == 'D':
            antes = _conta(rs[:-1], lambda x: x != 'D')
            if antes >= 6:
                out['fim_invencibilidade'] = antes
    # ----- a liga: agora x antes das duas últimas rodadas do usuário
    if liga is not None:
        ml = [p for p in meus if p['comp'] == liga]
        out['liga_seq'] = {'d': _conta([_res(p, ti)[2] for p in ml], lambda x: x == 'D'),
                           'sv': _conta([_res(p, ti)[2] for p in ml], lambda x: x != 'V')}
        if len(ml) >= 3:
            nm_up = lambda t: (r.get('_nomes_time') or str)(t).strip().upper()
            idx = {}
            for p in todas:
                if p['comp'] == liga:
                    idx.setdefault(nm_up(p['time1']), p['time1'])
                    idx.setdefault(nm_up(p['time2']), p['time2'])
            eu = nm_up(ti)
            t1, t0 = _tabelas(car, todas, liga, ini, hoje, tuple(ml[-2]['data']), nm_up, eu)
            pos1 = {x['t']: x for x in t1}
            pos0 = {x['t']: x for x in t0}
            eu1, eu0 = pos1.get(eu), pos0.get(eu)
            if eu1 and eu0:
                L = {'nome': nome_comp(liga), 'pos': eu1['pos'], 'pos_antes': eu0['pos'], 'pts': eu1['pts'], 'j': eu1['j']}
                if eu1['pos'] == 1:
                    rv = t1[1]['t'] if len(t1) > 1 else None
                elif t1:
                    rv = t1[0]['t']
                else:
                    rv = None
                if rv is not None and rv in pos0:
                    dif1 = eu1['pts'] - pos1[rv]['pts']           # >0 = estamos à frente
                    dif0 = eu0['pts'] - pos0[rv]['pts']
                    L['rival'] = {'nome': clube.nome_time(rv), 'pos': pos1[rv]['pos'], 'dif': dif1, 'dif_antes': dif0,
                                  'forma': ''.join(_ultimos_liga(todas, liga, idx[rv], ini)) if rv in idx else ''}
                    if dif0 >= 0 > dif1 or (dif0 > 0 and dif1 == 0 and eu1['pos'] != 1):
                        L['rival']['movimento'] = 'ultrapassou'
                    elif dif1 >= 0 and dif0 - dif1 >= 2:
                        L['rival']['movimento'] = 'encostou'
                    elif dif1 > 0 and dif1 - dif0 >= 3:
                        L['rival']['movimento'] = 'ficou_para_tras'
                    elif dif1 < 0 and dif0 - dif1 >= 3:
                        L['rival']['movimento'] = 'disparou'
                    elif dif1 < 0 and dif1 - dif0 >= 2:
                        L['rival']['movimento'] = 'aproximamos'
                if eu0['pos'] == 1 and eu1['pos'] != 1:
                    L['lideranca'] = 'perdeu'
                elif eu0['pos'] != 1 and eu1['pos'] == 1:
                    L['lideranca'] = 'assumiu'
                L['topo'] = [clube.nome_time(x['t']) for x in t1[:4]]
                top6 = {x['t'] for x in t1[:7] if x['t'] != eu}
                ct, cs = collections.Counter(), collections.Counter()
                for p in ml:
                    adv = nm_up(p['time2'] if p['time1'] == ti else p['time1'])
                    rr = _res(p, ti)[2]
                    if adv in top6:
                        ct[rr] += 1
                    if p['time1'] == ti:
                        cs[rr] += 1
                L['contra_topo'] = {'v': ct['V'], 'e': ct['E'], 'd': ct['D']}
                L['em_casa'] = {'v': cs['V'], 'e': cs['E'], 'd': cs['D']}
                out['liga'] = L
    # ----- a agenda
    topo = {n.upper() for n in (out.get('liga') or {}).get('topo') or []}
    prox = []
    for x in car.get('proximos') or []:
        if not x or not x.get('data'):
            continue
        dias = _d(x['data'], hoje)
        if dias < 0 or dias > 21:
            continue
        adv = clube.nome_time(x.get('adversario') or '')
        tags = []
        comp = x.get('competicao') or ''
        if any(k in comp for k in ('Champions', 'Libertadores', 'Mundial', 'AFC')):
            tags.append('continental')
        if x.get('classico'):
            tags.append('classico')
        if x.get('final'):
            tags.append('final')
        if (x.get('disputa') or {}).get('mesma_zona'):
            tags.append('direto')
        if adv.upper() in topo and 'continental' not in tags:
            tags.append('topo')
        prox.append({'adv': adv, 'comp': comp, 'dias': dias, 'data': list(x['data']), 'casa': x.get('eu_casa'),
                     'classico': x.get('classico'), 'tags': tags})
    out['proximos'] = prox
    grandes = [x for x in prox if x['tags'] and x['dias'] <= 10]
    out['semana_decisiva'] = len(grandes) >= 2
    if len(prox) >= 3 and prox[2]['dias'] <= 8:
        out['maratona'] = {'jogos': 3, 'dias': prox[2]['dias']}
    # ----- o clima
    s, L = out['seq'], out.get('liga') or {}
    rv = L.get('rival') or {}
    if s['d'] >= 3 or s['sv'] >= 4:
        clima = 'crise'
    elif s['d'] == 2 or s['sv'] == 3 or L.get('lideranca') == 'perdeu' or (rv.get('movimento') == 'encostou' and s['sv'] >= 1):
        clima = 'alerta'
    elif s['v'] >= 4 or (L.get('lideranca') == 'assumiu' and s['v'] >= 2):
        clima = 'embalado'
    else:
        clima = 'normal'
    out['clima'] = clima
    out['frases'] = frases(out)
    return clube.concordar_tudo(out)


def _quando(dias):
    return 'hoje' if dias == 0 else 'amanhã' if dias == 1 else f'em {dias} dias'


def descreve_jogo(x):
    if 'classico' in x['tags']:
        return f'o {x["classico"]} contra o {x["adv"]}'
    if 'continental' in x['tags']:
        return f'a {x["comp"].replace("UEFA ", "")} contra o {x["adv"]}'
    if 'final' in x['tags']:
        return f'a final da {x["comp"]} contra o {x["adv"]}'
    if 'direto' in x['tags']:
        return f'o confronto direto com o {x["adv"]}'
    return f'o {x["adv"]} ({x["comp"]})'


def frases(m):
    """Frases factuais do momento (em ordem de importância) para matérias, coletivas e redes."""
    out = []
    s = m['seq']
    if s['d'] >= 2:
        out.append(f'{ORD.get(s["d"], str(s["d"]) + "ª").capitalize()} derrota seguida')
    elif s['sv'] >= 3:
        out.append(f'{EXTENSO.get(s["sv"], s["sv"]).capitalize()} jogos sem vencer')
    elif s['v'] >= 3:
        out.append(f'{ORD.get(s["v"], str(s["v"]) + "ª").capitalize()} vitória seguida')
    elif s['inv'] >= 8:
        out.append(f'Invicto há {s["inv"]} jogos')
    if m.get('fim_invencibilidade'):
        out.append(f'A derrota encerrou uma série de {m["fim_invencibilidade"]} jogos sem perder')
    L = m.get('liga') or {}
    rv = L.get('rival') or {}
    mv = rv.get('movimento')
    if L.get('lideranca') == 'perdeu':
        out.append(f'O time perdeu a liderança da {L["nome"]} para o {rv.get("nome", "rival")}'
                   + (f': eram {rv["dif_antes"]} pontos de vantagem há duas rodadas, agora são {abs(rv["dif"])} atrás'
                      if rv.get('dif', 0) < 0 and rv.get('dif_antes', 0) > 0 else ''))
        if mv == 'ultrapassou':
            mv = None   # a liderança perdida já conta a história
    elif L.get('lideranca') == 'assumiu':
        out.append(f'O time assumiu a liderança da {L["nome"]}')
    if mv == 'ultrapassou':
        out.append(f'O {rv["nome"]} ultrapassou: o time estava {rv["dif_antes"]} ponto{"s" if rv["dif_antes"] != 1 else ""} à frente '
                   f'e agora está {abs(rv["dif"])} atrás' if rv['dif'] < 0 else f'O {rv["nome"]} passou à frente no saldo')
    elif mv == 'encostou':
        out.append(f'O {rv["nome"]} encostou: a vantagem caiu de {rv["dif_antes"]} para {rv["dif"]} ponto{"s" if rv["dif"] != 1 else ""} em duas rodadas'
                   if rv['dif'] > 0 else f'O {rv["nome"]} alcançou o time na pontuação')
    elif mv == 'ficou_para_tras':
        out.append(f'A vantagem sobre o {rv["nome"]} subiu de {rv["dif_antes"]} para {rv["dif"]} pontos')
    elif mv == 'disparou':
        out.append(f'O {rv["nome"]} disparou: agora são {abs(rv["dif"])} pontos de distância (eram {abs(rv["dif_antes"])})')
    elif mv == 'aproximamos':
        out.append(f'A distância para o {rv["nome"]} caiu de {abs(rv["dif_antes"])} para {abs(rv["dif"])} pontos')
    gs = [x for x in m.get('proximos') or [] if x['tags'] and x['dias'] <= 10]
    if len(gs) >= 2:
        out.append('Pela frente: ' + ' e '.join(f'{descreve_jogo(x)} ({_quando(x["dias"])})' for x in gs[:2]))
    elif gs:
        out.append(f'Próximo desafio grande: {descreve_jogo(gs[0])} ({_quando(gs[0]["dias"])})')
    if m.get('maratona'):
        out.append(f'Maratona: três jogos em {m["maratona"]["dias"]} dias')
    return out
