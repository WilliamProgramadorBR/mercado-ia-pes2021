"""DEPARTAMENTO MÉDICO NA IMPRENSA (12/10/2026).

Pedido do usuário: o craque (William) se machucou antes de jogos importantes; a imprensa deve perceber e AVALIAR o
cenário (como o Flamengo sem o Arrascaeta num jogo grande).

O save guarda, no registro de 156 B de cada jogador, um contador de recuperação em +116 (jogadores_save 'lesao';
0 = apto; entre 24 mil jogadores só o William tinha valor, 7 -> 6). A unidade não é dita pelo jogo: a central APRENDE
os dias por unidade observando o contador cair (car['lesao_dias_por_unidade']) e só então dá previsão de volta.

atualizar() roda na reunião e devolve (matérias, fatos):
  lesão nova   -> peso do jogador (nota no elenco, % dos gols, status), substituto natural no setor, jogos que ele perde
                  (destacando Champions, final, clássico e confronto direto da corrida), campanha do time SEM ele na
                  temporada e o contexto da corrida na liga;
  volta        -> "está de volta" com o tempo fora e como o time se virou.
car['lesoes'] (em tratamento) e car['lesao_ultima'] (a análise mais recente, para coletiva e Bola na Mesa).
"""
import datetime as dt

import clube
import imprensa_db as db

GRUPO = {'GK': 'gol', 'CB': 'zaga', 'LB': 'lateral', 'RB': 'lateral', 'DMF': 'meio', 'CMF': 'meio', 'AMF': 'meio',
         'LMF': 'meio', 'RMF': 'meio', 'LWF': 'ataque', 'RWF': 'ataque', 'SS': 'ataque', 'CF': 'ataque'}
GRANDES = {3, 4, 8, 9, 10, 1, 15, 16}


def _d(x):
    return dt.date(*tuple(x)[:3])


def _kc(k):
    return f'{k[0]}:{k[1]}'


def _jogos_sem(r, k):
    """Campanha do time na temporada nos jogos em que o jogador NÃO entrou: (V, E, D, gols pró, gols contra)."""
    v = e = dd = gp = gc = 0
    for p in r.get('jogos') or []:
        nos = p['linhas1'] if p['time1'] == r['ti'] else p['linhas2']
        if any((x['reg'], x['pid']) == tuple(k) and x['minutos'] > 0 for x in nos):
            continue
        a, b = (p['gols1'], p['gols2']) if p['time1'] == r['ti'] else (p['gols2'], p['gols1'])
        gp, gc = gp + a, gc + b
        v, e, dd = v + (a > b), e + (a == b), dd + (a < b)
    return v, e, dd, gp, gc


def _analise(j, r, car, hoje, prev):
    import classicos
    from proximo_jogo import nome_comp
    J = r['J']
    rank = 1 + sum(1 for o in J if o['ovr'] > j['ovr'])
    gols_time = sum(o.get('t_gols', 0) for o in J) or 1
    parte = round(100 * j.get('t_gols', 0) / gols_time)
    setor = GRUPO.get(j['pos'], 'meio')
    subs = sorted((o for o in J if o['k'] != j['k'] and GRUPO.get(o['pos']) == setor and not o.get('lesao')),
                  key=lambda o: -o['ovr'])
    sub = subs[0] if subs else None
    ate = prev or (_d(hoje) + dt.timedelta(days=10))
    agenda = sorted((p for p in r.get('agenda') or [] if r['ti'] in (p['time1'], p['time2'])
                     and _d(hoje) < _d(p['data']) <= ate), key=lambda p: p['data'])
    nos_nome = r['time']
    jogos = []
    for p in agenda[:6]:
        adv_ti = p['time2'] if p['time1'] == r['ti'] else p['time1']
        nm = r.get('_nomes_time')
        adv = clube.nome_time(nm(adv_ti)) if callable(nm) else f'time {adv_ti}'
        grande = p['comp'] in GRANDES or bool(classicos.nome(nos_nome, adv))
        jogos.append({'data': list(p['data'][:3]), 'adv': adv, 'comp': nome_comp(p['comp']), 'grande': grande,
                      'classico': classicos.nome(nos_nome, adv)})
    v, e, d_, gp, gc = _jogos_sem(r, j['k'])
    co = car.get('corrida')
    return {'nome': j['nome'], 'k': list(j['k']), 'pos': j['pos'], 'setor': setor, 'ovr': j['ovr'], 'rank': rank,
            'gols': j.get('t_gols', 0), 'assist': j.get('t_assist', 0), 'parte_gols': parte, 'status': j.get('status'),
            'capitao': bool(j.get('capitao')), 'sub': {'nome': sub['nome'], 'ovr': sub['ovr'], 'pos': sub['pos']} if sub else None,
            'previsao': prev.isoformat() if prev else None, 'jogos': jogos, 'grandes': [x for x in jogos if x['grande']],
            'sem_ele': {'v': v, 'e': e, 'd': d_, 'gp': gp, 'gc': gc, 'jogos': v + e + d_},
            'corrida': {'zona': co['nome_zona'], 'pos': co['pos'], 'rival': co['rivais'][0]} if co and co.get('rivais') else None,
            'data': list(hoje)}


def _peso(a):
    return 2.0 + (2.0 if a['rank'] <= 3 else 1.0 if a['rank'] <= 6 else 0) + min(2.0, a['parte_gols'] / 15) + 0.7 * len(a['grandes'])


def _materia(a, ck, hoje, volta=False, dias_fora=None):
    n = a['nome']
    if volta:
        sem = a['sem_ele']
        corpo = [f'{n} está recuperado e volta a ficar à disposição'
                 + (f' depois de {dias_fora} dias fora.' if dias_fora else '.'),
                 (f'Sem ele, o time somou {sem["v"]} vitórias, {sem["e"]} empates e {sem["d"]} derrotas na temporada '
                  f'({sem["gp"]} gols feitos, {sem["gc"]} sofridos).') if sem['jogos'] else 'O elenco segurou bem a ausência.',
                 'A comissão técnica decide se ele volta direto entre os titulares ou ganha ritmo aos poucos.']
        return {'chave': f'volta|{ck}|{_kc(a["k"])}|{db.data_txt(hoje)}', 'frente': 'pos_jogo', 'data': hoje,
                'titulo': f'{n} está de volta', 'autor': 'Redação · departamento médico',
                'linha_fina': f'{a["pos"]} recuperado' + (f' após {dias_fora} dias' if dias_fora else ''), 'corpo': corpo,
                'dados': {'lesao': a, 'volta': True}}
    peso_txt = (f'{a["rank"]}º melhor jogador do elenco (nota {a["ovr"]})'
                + (f', autor de {a["parte_gols"]}% dos gols do time ({a["gols"]} gols, {a["assist"]} assistências)'
                   if a['gols'] or a['assist'] else ''))
    corpo = [f'{n} está no departamento médico. ' + (f'Previsão de volta: {_d(a["previsao"]).strftime("%d/%m")}.'
                                                      if a['previsao'] else 'O clube ainda não divulgou o prazo de recuperação.'),
             f'O peso da ausência: {peso_txt}.' + (' É o capitão do time.' if a['capitao'] else '')]
    if a['jogos']:
        corpo.append('Na agenda dentro do período: ' + '; '.join(
            f'{x["adv"]} ({x["comp"]}, {x["data"][2]:02d}/{x["data"][1]:02d})' + (' — jogo grande' if x['grande'] else '')
            for x in a['jogos'][:5]) + '.')
    if a['sub']:
        dif = a['ovr'] - a['sub']['ovr']
        corpo.append(f'O substituto natural no setor é {a["sub"]["nome"]} (nota {a["sub"]["ovr"]})'
                     + (f', {dif} pontos abaixo — a queda é sentida.' if dif >= 5 else ', sem grande perda técnica.'))
    sem = a['sem_ele']
    if sem['jogos']:
        pl = lambda x, um, varios: f'{x} {um if x == 1 else varios}'
        corpo.append(f'Sem {n} em campo nesta temporada: {sem["v"]}V {sem["e"]}E {sem["d"]}D, '
                     f'{pl(sem["gp"], "gol feito", "gols feitos")} e {pl(sem["gc"], "sofrido", "sofridos")} em {pl(sem["jogos"], "jogo", "jogos")}.')
    if a['corrida']:
        c, rv = a['corrida'], a['corrida']['rival']
        corpo.append(f'Tudo isso no meio da corrida ({c["zona"]}): {c["pos"]}º lugar, com o {rv["nome"]} '
                     + (f'{abs(rv["dif"])} pontos atrás.' if rv['dif'] < 0 else f'{rv["dif"]} pontos à frente.' if rv['dif'] else 'empatado em pontos.'))
    titulo = (f'Baixa de peso: {n} desfalca o time' if a['rank'] <= 3 else f'{n} vai para o departamento médico')
    if a['grandes']:
        g = a['grandes'][0]
        titulo = f'{n} lesionado e vira dúvida para {g["classico"] or g["adv"]}'
    return {'chave': f'lesao|{ck}|{_kc(a["k"])}|{db.data_txt(hoje)}', 'frente': 'pos_jogo', 'data': hoje, 'titulo': titulo,
            'autor': 'Redação · departamento médico', 'linha_fina': f'{a["pos"]} · {peso_txt}', 'corpo': corpo,
            'dados': {'lesao': a}}


def atualizar(car, r, hoje, log=print):
    """Acompanha as lesões do elenco do usuário. Devolve (matérias, fatos para as capas)."""
    ck = car.get('ck')
    st = car.setdefault('lesoes', {})
    taxa = car.get('lesao_dias_por_unidade')
    hj = _d(hoje)
    materias, fatos = [], []
    vistos = set()
    for j in r['J']:
        kc, v = _kc(j['k']), j.get('lesao') or 0
        vistos.add(kc)
        if v > 0:
            reg = st.get(kc)
            if reg is None:
                reg = st[kc] = {'nome': j['nome'], 'inicio': hj.isoformat(), 'v0': v, 'obs': [[hj.isoformat(), v]]}
                prev = hj + dt.timedelta(days=round(v * taxa)) if taxa else None
                a = _analise(j, r, car, hoje, prev)
                reg['analise'] = a
                car['lesao_ultima'] = a
                materias.append(_materia(a, ck, hoje))
                fatos.append({'tipo': 'lesao', 'sub': kc, 'peso': _peso(a), 'a': a})
                log(f'lesão: {j["nome"]} (contador {v})')
            elif reg['obs'][-1][1] != v:
                reg['obs'].append([hj.isoformat(), v])
                d0, v0 = reg['obs'][0]
                if v0 > v and (hj - dt.date.fromisoformat(d0)).days > 0:
                    nova = (hj - dt.date.fromisoformat(d0)).days / (v0 - v)
                    taxa = round(nova if not taxa else 0.6 * taxa + 0.4 * nova, 2)
                    car['lesao_dias_por_unidade'] = taxa
                reg['analise']['previsao'] = (hj + dt.timedelta(days=round(v * taxa))).isoformat() if taxa else None
        elif kc in st:
            reg = st.pop(kc)
            dias = (hj - dt.date.fromisoformat(reg['inicio'])).days
            if reg['v0'] and dias > 0:       # recuperou: ciclo completo = medida boa dos dias por unidade
                nova = dias / reg['v0']
                car['lesao_dias_por_unidade'] = round(nova if not taxa else 0.5 * taxa + 0.5 * nova, 2)
            a = reg.get('analise') or {'nome': reg['nome'], 'k': [int(x) for x in kc.split(':')], 'pos': '', 'sem_ele': {'jogos': 0}}
            a['sem_ele'] = _analise(j, r, car, hoje, None)['sem_ele']
            materias.append(_materia(a, ck, hoje, volta=True, dias_fora=dias))
            fatos.append({'tipo': 'volta_lesao', 'sub': kc, 'peso': 1.5 + (1.5 if a.get('rank', 9) <= 3 else 0), 'a': a, 'dias': dias})
            car['lesao_volta'] = {**a, 'dias_fora': dias, 'data': list(hoje)}
            log(f'volta de lesão: {reg["nome"]} ({dias} dias)')
    for kc in [k for k in st if k not in vistos]:      # saiu do elenco
        st.pop(kc)
    return materias, fatos
