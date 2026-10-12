"""IMPRENSA da Central (11/10/2026): o noticiário do futebol em cinco frentes, gravado no banco (imprensa_db.py).

  pré-jogo        prévia do próximo jogo: possível escalação dos dois times (formação e titulares do próprio save),
                  probabilidades, forma, enquete da torcida, palpites, reforço recém-chegado do adversário.
  jogo da rodada  4 x 4 dos destaques, comparação jogador a jogador em tom de torcedor (números da temporada).
  pós-jogo        noticiário do jogo: placar, gols, atuações POR SETOR com as estatísticas do próprio jogo (nota da
                  súmula + passes/chutes/desarmes do jogo = diferença entre duas fotos das estatísticas da temporada),
                  o que a comissão técnica tinha previsto, destaque do adversário, o que vem pela frente.
  temporada       panorama do mês (atualizado a cada rodada): campanha, metas da diretoria, sequência, artilharia, copas.
  mercado         a janela de transferências do Mercado IA (negócios gravados por aplicar.py).

Todos os textos nascem de modelos com condições (funcionam sem IA). Se o redator com IA estiver ligado (ia.json), uma
única chamada por reunião reescreve as matérias novas; números que não estavam no texto original derrubam a troca.
"""
import random

import imprensa_db as db

GRUPO = {'GK': 'goleiro', 'CB': 'defesa', 'LB': 'defesa', 'RB': 'defesa', 'DMF': 'meio', 'CMF': 'meio', 'AMF': 'meio',
         'LMF': 'meio', 'RMF': 'meio', 'LWF': 'ataque', 'RWF': 'ataque', 'SS': 'ataque', 'CF': 'ataque'}
ORDEM_POS = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro',
         'novembro', 'dezembro']
CAMPOS_JOGO = ('jogos', 'gols', 'assist', 'minutos', 'chutes', 'chutes_gol', 'dribles', 'dribles_ok', 'passes',
               'passes_ok', 'aereas', 'aereas_ok', 'cruzamentos', 'cruzamentos_ok', 'interceptacoes', 'carrinhos',
               'desarmes', 'bloqueios')


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def _dia(d):
    return f'{d[2]:02d}/{d[1]:02d}'


def _lista(nomes):
    nomes = list(nomes)
    return ', '.join(nomes[:-1]) + ' e ' + nomes[-1] if len(nomes) > 1 else (nomes[0] if nomes else '')


def _de(time):
    return f'do {time}'


# ---------------------------------------------------------------- contexto
_SML = {}


def _contexto(car, r, d, snap):
    import dados
    from save_ml import SaveML
    # 12/10/2026: o mesmo save (20 MB) era copiado a cada módulo da reunião; agora a cópia (só leitura) é reaproveitada
    s = _SML.get(id(d))
    if s is None or len(s.d) != len(d):
        s = SaveML.__new__(SaveML)
        s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
        _SML.clear()
        _SML[id(d)] = s
    try:
        P = dados.load_players(snap)
    except Exception:  # noqa: BLE001
        P = {}
    return {'s': s, 'P': P, 'ck': car.get('ck'), 'ti': r['ti'], 'nos': r['time'], 'r': r, 'car': car}


def _nome(ctx, k):
    f = ctx['P'].get(k)
    return f.name.strip() if f else None


def _escalacao(ctx, idx, usuario=False):
    """Formação + 11 titulares do save (o time do usuário usa o bloco próprio; os da IA, a lista da tabela geral)."""
    import carreira
    import encaixe
    s = ctx['s']
    sq = s.squad(idx)
    if usuario:
        u = carreira.BLOCO_USUARIO
        ordem, codes = list(s.d[u:u + 11]), list(s.d[u - s.PLANS_BEFORE:u - s.PLANS_BEFORE + 11])
    else:
        ordem, codes = s.lineup(idx)[:11], s.formation(idx)
    if len(ordem) < 11 or len(codes) < 11 or any(c > 12 for c in codes):
        return None
    out = []
    for i, c in zip(ordem, codes):
        if i >= len(sq):
            return None
        f = ctx['P'].get(sq[i])
        if not f:
            continue
        try:
            nota = round(encaixe.rating(f, f.pos))
        except Exception:  # noqa: BLE001
            nota = None
        out.append({'pos': encaixe.POS_CODES[c], 'nome': f.name.strip(), 'nota': nota, 'pid': sq[i][1]})
    p = [encaixe.POS_CODES[c] for c in codes]
    df = sum(1 for x in p if x in ('CB', 'LB', 'RB'))
    at = sum(1 for x in p if x in ('CF', 'SS', 'LWF', 'RWF'))
    return {'formacao': f'{df}-{10 - df - at}-{at}', 'jogadores': out}


def _linha_escalacao(e):
    por = {}
    for j in e['jogadores']:
        por.setdefault(GRUPO.get(j['pos'], 'meio'), []).append(j['nome'])
    return '; '.join(', '.join(por[g]) for g in ('goleiro', 'defesa', 'meio', 'ataque') if por.get(g))


def _sequencia(jogos, ti):
    """('vitórias', n) / ('invicto', n) / ('sem vencer', n) / ('derrotas', n) a partir do jogo mais recente."""
    res = []
    for p in reversed(jogos):
        gp, gc = (p['gols1'], p['gols2']) if p['time1'] == ti else (p['gols2'], p['gols1'])
        res.append('V' if gp > gc else 'E' if gp == gc else 'D')
    if not res:
        return None, 0
    def conta(ok):
        n = 0
        for x in res:
            if not ok(x):
                break
            n += 1
        return n
    if res[0] == 'V':
        v, inv = conta(lambda x: x == 'V'), conta(lambda x: x != 'D')
        return ('vitórias', v) if v >= inv - 1 else ('invicto', inv)
    if res[0] == 'D':
        dd, sv = conta(lambda x: x == 'D'), conta(lambda x: x != 'V')
        return ('derrotas', dd) if dd >= sv - 1 else ('sem vencer', sv)
    inv, sv = conta(lambda x: x != 'D'), conta(lambda x: x != 'V')
    return ('invicto', inv) if inv >= sv else ('sem vencer', sv)


# ---------------------------------------------------------------- estatísticas de UM jogo
def _numeros_do_jogo(ctx, p):
    """Diferença entre a foto das estatísticas de agora e a da reunião anterior, se entre elas houve SÓ este jogo."""
    r, ck = ctx['r'], ctx['ck']
    atual = {j['k']: j.get('est_temp') for j in r['J'] if j.get('est_temp')}
    try:
        data_ant, ant = db.foto_anterior(ck, p['data'])
    except Exception:  # noqa: BLE001
        return {}
    if not data_ant or not ant:
        return {}
    entre = [x for x in r['jogos'] if tuple(data_ant) < tuple(x['data']) <= tuple(p['data'])]
    if len(entre) != 1:
        return {}
    out = {}
    for k, v in atual.items():
        a = ant.get(k)
        if not a:
            continue
        dif = {c: v.get(c, 0) - a.get(c, 0) for c in CAMPOS_JOGO}
        if any(x < 0 for x in dif.values()):   # virada de temporada: fotos não comparáveis
            return {}
        if dif['jogos'] >= 1 and dif['minutos'] > 0:
            out[k] = dif
    return out


def _frase_numeros(g, x):
    """Os números do jogo de um jogador, conforme o setor."""
    if not x:
        return ''
    partes = []
    if g == 'ataque':
        if x['chutes']:
            partes.append(f'{x["chutes"]} finalizações ({x["chutes_gol"]} no alvo)')
        if x['dribles']:
            partes.append(f'{x["dribles_ok"]} de {x["dribles"]} dribles certos')
    elif g == 'meio':
        if x['passes']:
            partes.append(f'{x["passes_ok"]} de {x["passes"]} passes certos ({round(100 * x["passes_ok"] / x["passes"])}%)')
        rb = x['desarmes'] + x['interceptacoes']
        if rb:
            partes.append(f'{rb} bolas recuperadas')
    elif g == 'defesa':
        if x['desarmes']:
            partes.append(f'{x["desarmes"]} desarmes')
        if x['interceptacoes']:
            partes.append(f'{x["interceptacoes"]} interceptações')
        if x['aereas']:
            partes.append(f'{x["aereas_ok"]} de {x["aereas"]} bolas aéreas vencidas')
    return ', '.join(partes[:3])


# ---------------------------------------------------------------- pós-jogo
def chave_pos(ctx, p):
    return f'pos|{ctx["ck"]}|{p["num"]}|{db.data_txt(p["data"])}'


def pos_jogos(ctx, prox_antigo, rnd, maximo=3):
    """Pós-jogo de TODO jogo nosso ainda sem matéria (até `maximo`, do mais antigo para o mais novo): se uma reunião
    se perder (vigia fechado/travado), o jogo não fica sem cobertura (11/10/2026: o Newcastle ficou sem pós-jogo)."""
    jogos = ctx['r'].get('jogos') or []
    faltam = [i for i in range(max(0, len(jogos) - maximo), len(jogos)) if not db.existe(ctx['ck'], chave_pos(ctx, jogos[i]))]
    out = []
    for i in faltam:
        ultimo = i == len(jogos) - 1
        m = pos_jogo(ctx, jogos[:i + 1], prox_antigo if ultimo else None, rnd, ultimo)
        if m:
            out.append(m)
    return out


def pos_jogo(ctx, jogos, prox_antigo, rnd, ultimo=True):
    """Matéria do jogo jogos[-1] (`jogos` = nossos jogos até ele). `ultimo`: é o jogo mais recente (tabela atual,
    números do jogo pelas fotos de estatísticas e "o que vem por aí" valem só para ele)."""
    r, ti, nos = ctx['r'], ctx['ti'], ctx['nos']
    p = jogos[-1]
    chave = chave_pos(ctx, p)
    from proximo_jogo import nome_comp
    s = ctx['s']
    casa = p['time1'] == ti
    adv = s.name(p['time2'] if casa else p['time1']).strip()
    gp, gc = (p['gols1'], p['gols2']) if casa else (p['gols2'], p['gols1'])
    ln_nos, ln_eles = (p['linhas1'], p['linhas2']) if casa else (p['linhas2'], p['linhas1'])
    comp = nome_comp(p['comp'])
    num = _numeros_do_jogo(ctx, p) if ultimo else {}

    def jogadores(linhas):
        out = []
        for x in linhas:
            if x['minutos'] <= 0:
                continue
            f = ctx['P'].get((x['reg'], x['pid']))
            if not f:
                continue
            out.append({'k': (x['reg'], x['pid']), 'nome': f.name.strip(), 'pos': f.pos, 'grupo': GRUPO.get(f.pos, 'meio'),
                        'nota': x['nota'], 'gols': x['gols'], 'assist': x['assist'], 'min': x['minutos'],
                        'titular': x['titular']})
        return out
    J1, J2 = jogadores(ln_nos), jogadores(ln_eles)
    if not J1:
        return None
    res = 'V' if gp > gc else 'E' if gp == gc else 'D'
    marg = gp - gc
    local = 'em casa' if casa else 'fora de casa'
    rod = f' (rodada {p["rodada"]})' if p.get('rodada') and comp != 'Amistoso' else ''
    placar = f'{gp} a {gc}' if gp >= gc else f'{gc} a {gp}'
    # peso da atuação: nota da súmula + participação em gols (no jogo SIMULADO o PES dá notas baixas a todos:
    # 11/10/2026, KAIO fez 4 gols com nota 6,5; sem isso o texto dizia que o setor "foi o menos mal")
    peso = lambda j: (j['nota'] or 5.5) + 0.6 * j['gols'] + 0.3 * j['assist']
    melhor = max(J1 + J2, key=peso)
    media = sum(j['nota'] for j in J1 if j['nota']) / max(1, sum(1 for j in J1 if j['nota']))
    corpo = []
    # 1) abertura com o resultado e o contexto
    if res == 'V':
        verbo = rnd.choice(['atropelou', 'goleou', 'passou por cima do']) if marg >= 3 else rnd.choice(['venceu', 'bateu', 'superou'])
        verbo = verbo if verbo.endswith('do') else verbo + ' o'
        abre = f'O {nos} {verbo} {adv} por {placar}, {local}, pela {comp}{rod}.'
    elif res == 'E':
        abre = f'{nos} e {adv} empataram por {gp} a {gc}, pela {comp}{rod}. O {nos} jogava {local}.'
    else:
        verbo = 'foi atropelado pelo' if marg <= -3 else rnd.choice(['perdeu para o', 'foi derrotado pelo', 'caiu diante do'])
        abre = f'O {nos} {verbo} {adv} por {placar}, {local}, pela {comp}{rod}.'
    tipo, n = _sequencia(jogos, ti)
    if tipo == 'vitórias' and n >= 3:
        abre += f' É a {n}ª vitória seguida.'
    elif tipo == 'invicto' and n >= 5:
        abre += f' São {n} jogos sem perder.'
    elif tipo == 'sem vencer' and n >= 3:
        abre += f' Já são {n} jogos sem vencer.'
    elif tipo == 'derrotas' and n >= 2:
        abre += f' É a {n}ª derrota seguida.'
    L = ctx['car'].get('liga') or {}
    eu = next((t for t in L.get('classificacao') or [] if t.get('eu')), None)
    if eu and L.get('competicao') == comp and ultimo:
        abre += f' Com o resultado, o time está em {eu["pos"]}º lugar, com {eu["pts"]} pontos.'
    import classicos
    classico = classicos.nome(nos, adv)
    if classico:   # clássico: o resultado vale mais que os três pontos
        abre = (f'Deu {nos} no {classico}! ' if res == 'V' else f'O {classico} foi do {adv}. ' if res == 'D'
                else f'Ninguém venceu o {classico}. ') + abre
    corpo.append(abre)
    # 2) gols
    def autores(js):
        return [f'{j["nome"]} ({j["gols"]})' if j['gols'] > 1 else j['nome'] for j in js if j['gols']]
    gols_txt = []
    if autores(J1):
        assist = [j['nome'] for j in J1 if j['assist']]
        gols_txt.append(f'Os gols do {nos} foram de {_lista(autores(J1))}' if gp > 1 else f'O gol do {nos} foi de {_lista(autores(J1))}')
        gols_txt[-1] += (f', com assistência de {_lista(assist)}.' if assist else '.')
    if autores(J2):
        gols_txt.append(f'Pelo {adv}, marcou {_lista(autores(J2))}.' if gc == 1 else f'Pelo {adv}, marcaram {_lista(autores(J2))}.')
    if gols_txt:
        corpo.append(' '.join(gols_txt))
    # 3) atuações por setor (nosso time), com os números do jogo
    rotulo = {'ataque': 'No ataque', 'meio': 'No meio de campo', 'defesa': 'Na defesa', 'goleiro': 'No gol'}
    setores = []
    for g in ('ataque', 'meio', 'defesa'):
        js = sorted((j for j in J1 if j['grupo'] == g and j['min'] >= 30 and j['nota']), key=lambda j: -peso(j))
        if not js:
            continue
        a = js[0]
        dupla = js[1] if len(js) > 1 and peso(js[1]) >= 7.0 and peso(a) - peso(js[1]) <= 0.6 else None
        nums = _frase_numeros(g, num.get(a['k']))
        part = ([f'{a["gols"]} gols' if a['gols'] > 1 else '1 gol'] if a['gols'] else []) + \
               ([f'{a["assist"]} assistências' if a['assist'] > 1 else '1 assistência'] if a['assist'] else [])
        if peso(a) >= 7.3:
            verbo = {'ataque': rnd.choice(['infernizou a defesa', 'decidiu', 'foi letal']),
                     'meio': rnd.choice(['comandou o meio', 'ditou o ritmo', 'foi o cérebro do time']),
                     'defesa': rnd.choice(['foi uma muralha', 'não deu espaço', 'segurou as pontas'])}[g]
        elif peso(a) >= 6.2:
            verbo = rnd.choice(['teve boa atuação', 'cumpriu bem o papel', 'foi seguro'])
        elif res == 'D':
            verbo = 'foi o menos mal do setor'
        else:
            verbo = rnd.choice(['fez o simples', 'teve atuação discreta'])
        quem = f'{a["nome"]} e {dupla["nome"]}' if dupla else a['nome']
        frase = f'{rotulo[g]}, {quem} {"comandaram as ações" if dupla else verbo}'
        frase += f': {a["nome"]} teve nota {_n(a["nota"])}' + (f', {_lista(part)}' if part else '') + (f', com {nums}' if nums else '') + '.'
        setores.append(frase)
    gk = next((j for j in J1 if j['grupo'] == 'goleiro'), None)
    if gk:
        if gc == 0:
            setores.append(f'{gk["nome"]} terminou sem ser vazado (nota {_n(gk["nota"])}).')
        elif gk['nota'] and gk['nota'] <= min(5.5, media - 0.6):
            setores.append(f'{gk["nome"]} não teve uma noite feliz no gol (nota {_n(gk["nota"])}).')
    if setores:
        corpo.append(' '.join(setores))
    # a carreira de quem decidiu (legado.py): a imprensa fala do atleta, não só do jogo
    try:
        import legado
        top_nos = max(J1, key=peso)
        pf = legado.perfil(ctx['ck'], top_nos['k'], top_nos['nome'])
        if pf['nivel'] != 'normal' and peso(top_nos) >= 6.5:
            corpo.append(rnd.choice([f'Não é novidade: {top_nos["nome"]} soma {legado.resumo(pf)} na carreira, e segue decidindo.',
                                     f'Mais um capítulo na carreira de {top_nos["nome"]}, dono de {legado.resumo(pf)}.']))
    except Exception:  # noqa: BLE001
        pass
    fraco = min((j for j in J1 if j['min'] >= 45 and j['nota']), key=peso, default=None)
    if fraco and fraco['nota'] <= min(5.8, media - 0.6) and fraco is not gk:
        corpo.append(rnd.choice([f'Ponto negativo: {fraco["nome"]} ({fraco["pos"]}) teve atuação apagada, nota {_n(fraco["nota"])}.',
                                 f'Quem destoou foi {fraco["nome"]}, nota {_n(fraco["nota"])}: noite para esquecer.']))
    # 4) a leitura tática (o que a comissão técnica tinha dito antes do jogo)
    antigos = prox_antigo if isinstance(prox_antigo, list) else [prox_antigo] if prox_antigo else []
    T = next((x.get('tatica') for x in antigos if x and x.get('adversario') == adv), None)
    if T:
        problema = next((x for x in reversed(T.get('fracos_deles') or []) if '(' not in x), None)
        arma = next((x for x in (T.get('ataque') or [])[1:2]), None)
        if res == 'V' and marg >= 2 and problema:
            corpo.append(f'A comissão técnica tinha apontado um ponto fraco do {adv}: {problema}. '
                         f'Em campo, o {nos} soube explorar a deficiência do esquema adversário.')
        elif res == 'V' and problema:
            corpo.append(f'O relatório da comissão técnica apontava: {problema}. A vitória veio, mas sem sobras.')
        elif res != 'V' and arma:
            corpo.append(f'O alerta da comissão técnica se confirmou. {arma}')
    # 5) o adversário
    top_adv = max(J2, key=peso, default=None)
    if top_adv and top_adv['nota']:
        corpo.append(f'Do lado do {adv}, o destaque foi {top_adv["nome"]} ({top_adv["pos"]}), nota {_n(top_adv["nota"])}.')
    # 6) o que vem por aí
    pj = ctx['car'].get('proximo_jogo') or {}
    if ultimo and pj.get('adversario') and pj.get('data'):
        corpo.append(f'O próximo compromisso é contra o {pj["adversario"]}, em {_dia(pj["data"])}, pela {pj["competicao"]}.')
    if res == 'V':
        titulo = rnd.choice([f'{nos} {gp} x {gc} {adv}: {melhor["nome"]} brilha', f'Vitória com a cara de {melhor["nome"]}',
                             f'{nos} vence o {adv} e segue firme']) if marg < 3 else \
            rnd.choice([f'Show em campo: {nos} {gp} x {gc} {adv}', f'Atropelo! {nos} faz {gp} no {adv}'])
    elif res == 'E':
        titulo = rnd.choice([f'Empate com o {adv}: {gp} x {gc}', f'{nos} fica no {gp} x {gc} com o {adv}'])
    else:
        titulo = rnd.choice([f'Tropeço: {nos} perde para o {adv}', f'{adv} {gc} x {gp} {nos}: noite ruim'])
    if classico:
        titulo = {'V': f'O {classico} é nosso! {nos} {gp} x {gc} {adv}', 'D': f'Dor no {classico}: {adv} {gc} x {gp} {nos}',
                  'E': f'{classico} termina empatado: {gp} x {gc}'}[res]
    try:   # FINAL: campeão ou vice (marcos.py)
        import marcos
        if (p.get('final_vivo') or marcos.eh_final(p, (r.get('todas_partidas') or []) + (r.get('agenda') or []))) and res != 'E':
            if res == 'V':
                titulo = rnd.choice([f'CAMPEÃO! {nos} conquista a {comp}', f'É TAÇA! {nos} {gp} x {gc} {adv} na final da {comp}',
                                     f'Noite de glória: {nos} é campeão da {comp}'])
                corpo.insert(0, f'Acabou! O {nos} venceu o {adv} por {placar} na final e é campeão da {comp}. '
                                f'Uma noite que fica para sempre na história do clube.')
            else:
                titulo = rnd.choice([f'Vice amargo: {adv} fica com a {comp}', f'Dor na final: {nos} perde a {comp} para o {adv}'])
                corpo.insert(0, f'Faltou o último passo. O {nos} perdeu a final da {comp} para o {adv} por {placar}. '
                                f'O vice dói, e a temporada termina com gosto amargo nessa competição.')
    except Exception as e:  # noqa: BLE001
        print('aviso: final não analisada:', e)
    try:   # VIRADA HISTÓRICA (ou vexame) no mata-mata: a imprensa vai à loucura (viradas.py)
        import viradas
        tie = viradas.do_time(r.get('todas_partidas') or [], ti, p['data'], dias=0)
        if tie and tie['num_volta'] == p['num'] and tie['tipo']:
            i, a = tie['ida'], tie['agg']
            if tie['tipo'] == 'virada':
                real = viradas.comparacao(tie['deficit'])
                titulo = rnd.choice([f'VIRADA HISTÓRICA! {nos} elimina o {adv}', f'Inacreditável! {nos} {gp} x {gc} e vira contra o {adv}',
                                     f'Remontada! O {nos} escreve uma noite para a eternidade'])
                corpo.insert(0, f'Ninguém acreditava. Depois de perder a ida por {i[1]} a {i[0]}, o {nos} fez {gp} a {gc} e virou o confronto '
                                f'no agregado ({a[0]} a {a[1]}). Uma virada para entrar na história, no nível do {real[0]}, que {real[3]}.')
            else:
                titulo = rnd.choice([f'Vexame! {nos} desperdiça vantagem e cai para o {adv}', f'Eliminação inacreditável: {adv} vira e tira o {nos}'])
                corpo.insert(0, f'Tinha tudo para passar: vitória por {i[0]} a {i[1]} na ida. Mas o {adv} fez {gc} a {gp} e virou no agregado '
                                f'({a[1]} a {a[0]}). Uma das eliminações mais doloridas da história do clube.')
    except Exception as e:  # noqa: BLE001
        print('aviso: virada não analisada:', e)
    dados = {'casa': nos if casa else adv, 'classico': classico, 'fora': adv if casa else nos, 'g1': p['gols1'], 'g2': p['gols2'],
             'competicao': comp, 'rodada': p.get('rodada'), 'data': list(p['data']),
             'destaque': {'nome': melhor['nome'], 'nota': melhor['nota']},
             'nos': [{k: j[k] for k in ('nome', 'pos', 'nota', 'gols', 'assist', 'min')} | {'pid': j['k'][1], 'numeros': num.get(j['k'])}
                     for j in sorted(J1, key=lambda j: (ORDEM_POS.index(j['pos']) if j['pos'] in ORDEM_POS else 99))],
             'eles': [{k: j[k] for k in ('nome', 'pos', 'nota', 'gols', 'assist', 'min')} | {'pid': j['k'][1]}
                      for j in sorted(J2, key=lambda j: (ORDEM_POS.index(j['pos']) if j['pos'] in ORDEM_POS else 99))],
             'numeros_do_jogo': bool(num)}
    return {'chave': chave, 'frente': 'pos_jogo', 'data': p['data'], 'titulo': titulo,
            'linha_fina': f'{melhor["nome"]} foi o melhor em campo' + (f', com {melhor["gols"]} gols' if melhor['gols'] > 1 else ', com 1 gol' if melhor['gols'] else '')
                          + f' (nota {_n(melhor["nota"])}).',
            'corpo': corpo, 'dados': dados, 'autor': 'Redação · pós-jogo'}


# ---------------------------------------------------------------- pré-jogo
def pre_jogo(ctx, rnd, pj=None):
    pj = pj or ctx['car'].get('proximo_jogo') or {}
    if not pj.get('casa') or pj.get('parcial'):
        return None
    chave = f'pre|{ctx["ck"]}|{db.data_txt(pj["data"])}|{pj["casa"]}|{pj["fora"]}'
    if db.existe(ctx['ck'], chave):
        return None
    s, nos = ctx['s'], ctx['nos']
    adv = pj['adversario']
    i_adv = s.find_team(adv) if adv else None
    esc_nos = _escalacao(ctx, ctx['ti'], usuario=True)
    esc_adv = _escalacao(ctx, i_adv) if i_adv is not None else None
    tc, tf = (pj.get('tabela') or {}).get('casa'), (pj.get('tabela') or {}).get('fora')
    corpo = [f'{pj["casa"]} e {pj["fora"]} se enfrentam em {_dia(pj["data"])}, pela {pj["competicao"]}'
             + (f' (rodada {pj["rodada"]})' if pj.get('rodada') else '') + '.'
             + (f' O {pj["casa"]} é o {tc["pos"]}º, com {tc["pts"]} pontos; o {pj["fora"]} é o {tf["pos"]}º, com {tf["pts"]}.'
                if tc and tf else '')]
    pr = pj['prob']
    fav = pj['casa'] if pr['casa'] > pr['fora'] + 8 else pj['fora'] if pr['fora'] > pr['casa'] + 8 else None
    corpo.append((f'Pelos números, o {fav} é favorito' if fav else 'Pelos números, o jogo é equilibrado')
                 + f': {pr["casa"]}% de chance para o {pj["casa"]}, {pr["empate"]}% de empate e {pr["fora"]}% para o {pj["fora"]}.'
                 + (f' Forma recente: {pj["casa"]} {pj["forma"]["casa"]}, {pj["fora"]} {pj["forma"]["fora"]}.'
                    if pj['forma']['casa'] and pj['forma']['fora'] else ''))
    if esc_nos:
        corpo.append(f'O {nos} deve ir a campo no {esc_nos["formacao"]}: {_linha_escalacao(esc_nos)}.')
    if esc_adv:
        corpo.append(f'O {adv} deve vir no {esc_adv["formacao"]}: {_linha_escalacao(esc_adv)}.')
    try:   # reforço que acabou de chegar ao adversário (Mercado IA)
        with db.conectar() as c:
            novos = [x['jogador'] for x in c.execute('SELECT jogador FROM negocios WHERE carreira = ? AND para = ? ORDER BY id DESC LIMIT 3',
                                                    (ctx['ck'], adv))]
        if novos:
            titulares = {j['nome'].strip() for j in (esc_adv or {}).get('jogadores', [])}
            n0 = novos[0].strip()
            corpo.append(f'Reforço recém-chegado ao {adv}, {n0} ' + ('já aparece entre os titulares.' if n0 in titulares
                                                                      else 'deve começar no banco.'))
    except Exception:  # noqa: BLE001
        pass
    olho = []
    try:   # os perigos do adversário pelos números da temporada (destaques.py)
        import imprensa_mundo
        txt, olho = imprensa_mundo.olho_adversario(ctx['car'].get('mundo'), adv)
        if txt:
            corpo.append(txt)
    except Exception:  # noqa: BLE001
        pass
    if pj.get('confrontos'):
        corpo.append('Últimos confrontos: ' + '; '.join(pj['confrontos']) + '.')
    corpo.append(f'Na enquete da torcida ("{pj["enquete"]["pergunta"]}"), {pj["enquete"]["sim"]}% responderam que sim. '
                 f'Placar mais provável pelos números: {pj["placar_provavel"]}.')
    titulo = rnd.choice([f'Prévia: {pj["casa"]} x {pj["fora"]}', f'Tudo sobre {pj["casa"]} x {pj["fora"]}',
                         f'{nos} encara o {adv}: o que esperar'])
    if pj.get('final'):   # FINAL: o jogo da temporada
        titulo = rnd.choice([f'FINAL DA {pj["competicao"].upper()}!', f'É dia de final: {pj["casa"]} x {pj["fora"]}',
                             f'Uma taça, noventa minutos: a final da {pj["competicao"]}'])
        corpo.insert(0, rnd.choice([f'Não existe jogo maior na temporada: é a final da {pj["competicao"]}. Ganhar é entrar para a história; perder é carregar a dor por um ano.',
                                    f'Final da {pj["competicao"]}. Jogo único, sem segunda chance. A cidade só fala disso.']))
    if pj.get('classico'):   # clássico: a prévia vira evento
        c = pj['classico']
        titulo = rnd.choice([f'É dia de {c}!', f'{c}: {pj["casa"]} x {pj["fora"]}', f'Clima de {c} toma conta da cidade'])
        corpo.insert(0, rnd.choice([f'Não é um jogo qualquer: é o {c}. Rivalidade, história e uma semana inteira de provocações.',
                                    f'Semana de {c}. A tabela importa, mas num clássico o que vale é o orgulho de quem vence.']))
    return {'chave': chave, 'frente': 'pre_jogo', 'data': pj['data'], 'titulo': titulo,
            'linha_fina': f'{pj["competicao"]} · {_dia(pj["data"])} · placar provável {pj["placar_provavel"]}',
            'corpo': corpo, 'autor': 'Redação · prévia',
            'dados': {'casa': pj['casa'], 'fora': pj['fora'], 'competicao': pj['competicao'], 'rodada': pj.get('rodada'),
                      'prob': pr, 'forma': pj['forma'], 'tabela': pj.get('tabela'), 'enquete': pj['enquete'],
                      'palpites': pj['palpites'], 'placar_provavel': pj['placar_provavel'], 'olho': olho, 'adv': adv,
                      'escalacao': {'nos': esc_nos, 'adv': esc_adv, 'nos_nome': nos, 'adv_nome': adv}}}


# ---------------------------------------------------------------- jogo da rodada (4 x 4)
def jogo_da_rodada(ctx, rnd, pj=None):
    pj = pj or ctx['car'].get('proximo_jogo') or {}
    D = pj.get('duelo')
    if not D or pj.get('parcial'):
        return None
    chave = f'4x4|{ctx["ck"]}|{db.data_txt(pj["data"])}|{pj["casa"]}|{pj["fora"]}'
    if db.existe(ctx['ck'], chave):
        return None
    A, B = D['jogadores']['casa'], D['jogadores']['fora']
    corpo = [rnd.choice([f'Chegou a hora do 4 x 4! Colocamos frente a frente os quatro destaques de {D["casa"]} e {D["fora"]}.',
                         f'Resenha da torcida: quem é melhor, o quarteto do {D["casa"]} ou o do {D["fora"]}? Vamos aos duelos.'])]
    placar = [0, 0]
    for a, b in zip(A, B):
        def ficha(j):
            t = f'{j["nome"]} ({j["pos"]}, nota {j["nota"]})'
            st = f'{j["gols"]} gols e {j["assist"]} assistências em {j["jogos"]} jogos' if j['jogos'] else 'ainda sem jogos na temporada'
            if j.get('media'):
                st += f', média {_n(j["media"])}'
            if j.get('tendencia') == 'alta':
                st += f', e vive fase em alta ({_n(j["recente"])} nos últimos jogos)'
            elif j.get('tendencia') == 'baixa':
                st += f', mas oscila ({_n(j["recente"])} nos últimos jogos)'
            return t, st
        ta, sa = ficha(a)
        tb, sb = ficha(b)
        try:   # carreira (legado.py) de quem tem história: Bolas de Ouro, títulos, artilharias
            import legado
            ks = {j['nome']: j['k'] for j in ctx['r']['J']}
            for j, lado in ((a, 'a'), (b, 'b')):
                if j['nome'] in ks:
                    pf = legado.perfil(ctx['ck'], ks[j['nome']], j['nome'])
                    if pf['nivel'] != 'normal':
                        if lado == 'a':
                            sa += f' (na carreira: {legado.resumo(pf)})'
                        else:
                            sb += f' (na carreira: {legado.resumo(pf)})'
        except Exception:  # noqa: BLE001
            pass
        pa = a['nota'] + (a.get('media') or 6) * 2 + a['gols'] * 0.5 + a['assist'] * 0.3 + (1 if a.get('tendencia') == 'alta' else -1 if a.get('tendencia') == 'baixa' else 0)
        pb = b['nota'] + (b.get('media') or 6) * 2 + b['gols'] * 0.5 + b['assist'] * 0.3 + (1 if b.get('tendencia') == 'alta' else -1 if b.get('tendencia') == 'baixa' else 0)
        if abs(pa - pb) < 1.2:
            ver = rnd.choice(['Duelo para cara ou coroa.', 'Aqui não tem favorito: empate técnico.', 'Briga de foice, sem dono.'])
        else:
            v = a if pa > pb else b
            placar[0 if v is a else 1] += 1
            ver = rnd.choice([f'Na ponta do lápis, vantagem de {v["nome"]}.', f'Pode reclamar à vontade: esse duelo é de {v["nome"]}.',
                              f'O torcedor sabe: {v["nome"]} leva essa.'])
        corpo.append(f'{ta} x {tb}. {a["nome"]} soma {sa}; {b["nome"]} soma {sb}. Ponto forte: {a["forte"]} de um lado, '
                     f'{b["forte"]} do outro. {ver}')
    if placar[0] != placar[1]:
        lider = D['casa'] if placar[0] > placar[1] else D['fora']
        corpo.append(f'Resultado do nosso 4 x 4: {lider} vence por {max(placar)} a {min(placar)} nos duelos. Agora é ver se o gramado confirma.')
    else:
        corpo.append(f'Resultado do nosso 4 x 4: empate em {placar[0]} a {placar[1]}. Vai ser decidido nos detalhes.')
    corpo += list(D.get('analise') or [])[:3]
    return {'chave': chave, 'frente': 'jogo_da_rodada', 'data': pj['data'],
            'titulo': rnd.choice([f'4 x 4: {D["casa"]} x {D["fora"]}', f'Craque contra craque: {D["casa"]} x {D["fora"]}']),
            'linha_fina': 'A comparação dos destaques, duelo por duelo, com os números da temporada.',
            'corpo': corpo, 'dados': {'duelo': D}, 'autor': 'Coluna do torcedor'}


# ---------------------------------------------------------------- temporada
def temporada(ctx, hoje, rnd):
    car, r, nos = ctx['car'], ctx['r'], ctx['nos']
    L = car.get('liga') or {}
    tab = L.get('classificacao') or []
    eu = next((t for t in tab if t.get('eu')), None)
    if not eu:
        return None
    chave = f'temp|{ctx["ck"]}|{hoje[0]:04d}-{hoje[1]:02d}'
    ja = db.data_de(ctx['ck'], chave)
    if ja and tuple(ja) >= tuple(hoje):   # o panorama do mês só é refeito com dados mais novos
        return None
    corpo = []
    campanha = f'{eu["v"]} vitórias, {eu["e"]} empates e {eu["d"]} derrotas em {eu["j"]} jogos, {eu["gp"]} gols marcados e {eu["gc"]} sofridos'
    if eu['pos'] == 1 and len(tab) > 1:
        dif = eu['pts'] - tab[1]['pts']
        corpo.append(f'Na {L["competicao"]}, o {nos} lidera com {eu["pts"]} pontos, {dif} à frente do {tab[1]["time"]}: {campanha}.')
        estado = 'na liderança'
    else:
        lider = tab[0]
        corpo.append(f'Na {L["competicao"]}, o {nos} é o {eu["pos"]}º, com {eu["pts"]} pontos, {lider["pts"] - eu["pts"]} atrás do líder {lider["time"]}: {campanha}.')
        estado = f'em {eu["pos"]}º lugar'
    metas = (car.get('diretoria') or {}).get('metas') or {}
    if metas.get('liga_texto'):
        alvo = metas.get('liga_alvo') or 1
        ok = eu['pos'] <= alvo
        conf = (car.get('diretoria') or {}).get('confianca')
        corpo.append(f'A meta da diretoria é "{metas["liga_texto"]}". ' + ('Por enquanto, está sendo cumprida.' if ok else 'Hoje, o time está abaixo do objetivo.')
                     + (f' Confiança da diretoria no técnico: {conf} de 100.' if conf is not None else ''))
    tipo, n = _sequencia(r['jogos'], ctx['ti'])
    if tipo and n >= 3:
        corpo.append({'vitórias': f'O momento é ótimo: {n} vitórias seguidas.', 'invicto': f'O time está há {n} jogos sem perder.',
                      'sem vencer': f'Sinal de alerta: {n} jogos sem vencer.', 'derrotas': f'Crise à vista: {n} derrotas seguidas.'}[tipo])
    J = sorted(r['J'], key=lambda j: -j['t_gols'])
    art = [j for j in J if j['t_gols'] > 0][:3]
    if art:
        corpo.append('Artilharia do time na temporada: ' + _lista(f'{j["nome"]} ({j["t_gols"]})' for j in art) + '.')
    la = L.get('artilheiros') or []
    if la:
        meu = next((i for i, a in enumerate(la) if a['time'] == nos), None)
        if meu == 0:
            corpo.append(f'{la[0]["nome"]} lidera a artilharia da {L["competicao"]} com {la[0]["gols"]} gols.')
        elif meu is not None:
            corpo.append(f'Na briga pela artilharia, {la[meu]["nome"]} tem {la[meu]["gols"]} gols; o líder é {la[0]["nome"]} ({la[0]["time"]}), com {la[0]["gols"]}.')
    regulares = [j for j in r['J'] if j['t_jogos'] >= 5 and j['t_nota']]
    if regulares:
        b = max(regulares, key=lambda j: j['t_nota'])
        corpo.append(f'O mais regular até aqui é {b["nome"]}: média {_n(b["t_nota"])} em {b["t_jogos"]} jogos.')
    for o in L.get('outras') or []:
        g = next((t for t in o.get('grupo') or [] if t.get('eu')), None)
        if g:
            corpo.append(f'Na {o["competicao"]}, o time é o {g["pos"]}º do grupo, com {g["pts"]} pontos em {g["j"]} jogos.')
    try:   # o mundo: artilharia, Bola de Ouro, a sensação da temporada (destaques.py)
        import imprensa_mundo
        corpo += imprensa_mundo.paragrafos_temporada(car.get('mundo'), nos)
    except Exception:  # noqa: BLE001
        pass
    titulo = f'Panorama de {MESES[hoje[1] - 1]}: {nos} {estado}'
    return {'chave': chave, 'frente': 'temporada', 'data': hoje, 'titulo': titulo,
            'linha_fina': f'{eu["pts"]} pontos em {eu["j"]} jogos na {L["competicao"]}.', 'corpo': corpo,
            'dados': {'classificacao': tab[:6] + ([eu] if eu['pos'] > 6 else []), 'artilheiros': la[:5]},
            'autor': 'Panorama da temporada'}


# ---------------------------------------------------------------- mercado
def mercado(ctx, hoje, rnd):
    try:
        ns = db.negocios_pendentes(ctx['ck'])
    except Exception:  # noqa: BLE001
        return None
    if not ns:
        return None
    nos = ctx['nos']
    total = sum(x['valor'] or 0 for x in ns)
    ano, _, tipo = (ns[0]['janela'] or '').partition('-')
    janela = f'de {tipo} de {ano}' if tipo else 'de transferências'
    corpo = [f'A janela {janela} esquentou: foram {len(ns)} negócios, somando {_n(total)} milhões.']
    top = ns[:3]
    corpo.append('Os maiores: ' + '; '.join(f'{x["para"]} contratou {x["jogador"]} ({x["pos"]}, {x["idade"]} anos) do {x["de"]} por {_n(x["valor"])} milhões'
                                            for x in top) + '.')
    if top and top[0]['motivo']:
        corpo.append(f'Bastidores do negócio mais caro: o {top[0]["para"]} buscou {top[0]["jogador"]} para {top[0]["motivo"].split(";")[0]}.')
    liga = {t['time'] for t in ((ctx['car'].get('liga') or {}).get('classificacao') or [])}
    rivais = [x for x in ns if x['para'] in liga and x['para'] != nos]
    if rivais:
        corpo.append(f'Na {(ctx["car"].get("liga") or {}).get("competicao", "liga")}, os rivais se mexeram: '
                     + _lista(f'{x["para"]} ({x["jogador"]})' for x in rivais[:5]) + '.')
    pj = ctx['car'].get('proximo_jogo') or {}
    prox = [x for x in ns if x['para'] == pj.get('adversario')]
    if prox:
        corpo.append(f'Atenção, {nos}: o próximo adversário, {pj["adversario"]}, acaba de contratar {_lista(x["jogador"] for x in prox)}.')
    jovens = [x for x in ns if (x['idade'] or 99) <= 19]
    if jovens:
        corpo.append('Apostas para o futuro: ' + _lista(f'{x["jogador"]} ({x["idade"]} anos, {x["para"]})' for x in jovens[:4]) + '.')
    saiu = [x for x in ns if x['de'] == nos]
    corpo.append(f'O {nos} não participou das negociações.' if not saiu else f'O {nos} perdeu {_lista(x["jogador"] for x in saiu)}.')
    datas = [tuple(int(x) for x in n['data'].split('-')) for n in ns if n.get('data')]
    m = {'chave': f'merc|{ctx["ck"]}|{ns[-1]["id"]}|{ns[0]["id"]}', 'frente': 'mercado', 'data': min(datas) if datas else hoje,
         'titulo': rnd.choice([f'Mercado: {top[0]["para"]} fecha o maior negócio da janela', f'{top[0]["jogador"]} é o reforço mais caro da janela']),
         'linha_fina': f'{len(ns)} negócios e {_n(total)} milhões movimentados.', 'corpo': corpo, 'autor': 'Mercado da bola',
         'dados': {'negocios': [{k: x[k] for k in ('jogador', 'idade', 'pos', 'de', 'para', 'valor', 'motivo')} for x in ns]}}
    m['_ids'] = [x['id'] for x in ns]
    return m


# ---------------------------------------------------------------- saídas, chegadas e renovações (saidas.py)
def movimentacoes(ctx, rnd):
    import saidas
    r, car, ck, nos = ctx['r'], ctx['car'], ctx['ck'], ctx['nos']
    top4 = {t['time'] for t in ((car.get('liga') or {}).get('classificacao') or [])[:4]}
    out = []
    for m in r.get('movimentos') or []:
        chave = f'mov|{ck}|{m["k"][0]}:{m["k"][1]}|{db.data_txt(m["data"])}|{m["destino"]}'
        if db.existe(ck, chave):
            continue
        n = saidas.narrativa(m, r['J'], ck, nos, top4)
        corpo = [n['lead']]
        if n.get('analogia'):
            corpo.append(rnd.choice([f'A comparação é inevitável: {n["analogia"]}.', f'O caso lembra o que aconteceu quando {n["analogia"]}.']))
        if m['tipo'] == 'saida':
            corpo.append(rnd.choice([f'Nas redes, a torcida se divide entre a gratidão e a mágoa. Agora, o {nos} precisa encontrar quem ocupe o espaço de {m["nome"]}.',
                                     f'A diretoria fala em "negócio vantajoso". A arquibancada quer saber quem chega para o lugar de {m["nome"]}.']))
        out.append({'chave': chave, 'frente': 'mercado', 'data': tuple(m['data']), 'titulo': n['titulo'],
                    'linha_fina': ({'saida': 'Saída', 'chegada': 'Chegada', 'renovacao': 'Renovação'}[m['tipo']] +
                                   (f' · R$ {saidas._mi(m["valor"])} milhões' if m['valor'] >= 1e6 else '') + f' · contrato até {m["contrato"][0]}'),
                    'corpo': corpo, 'autor': 'Mercado da bola',
                    'dados': {'negocios': [{'jogador': m['nome'], 'idade': m['idade'], 'pos': m['pos_campo'],
                                            'de': nos if m['tipo'] == 'saida' else '—', 'para': m['clube'],
                                            'valor': round(m['valor'] / 1e6, 1), 'motivo': n['tipo']}]}})
    return out


# ---------------------------------------------------------------- o mundo: premiação, revelações (imprensa_mundo.py)
def mundo(ctx, hoje, rnd, snap, log=print):
    import destaques
    import imprensa_mundo as im
    car, ck, nos = ctx['car'], ctx['ck'], ctx['nos']
    res = car.get('mundo')
    out = []
    # fim da liga (março a junho): a seleção da temporada sai ANTES da virada apagar as súmulas
    if res and destaques.fim_de_liga(car) and 3 <= hoje[1] <= 6 and not db.existe(ck, f'premios|{ck}|{res["temporada"]}'):
        m = im.premios(ck, res, nos, hoje, rnd)
        if m:
            out.append(m)
    car['_tecnico'] = ctx['r'].get('tecnico') if ctx.get('r') else None
    if 7 <= hoje[1] <= 10:   # depois da virada: a temporada que acabou, pelas cópias do save da reunião
        r0 = im.retro(car, ck, snap, ctx['ti'], nos, hoje, log)
        if r0:
            m = im.premios(ck, r0, nos, tuple(r0['data']), rnd)
            if m:
                out.append(m)
            m = im.revelacao(ck, r0, {}, tuple(r0['data']), rnd)   # e a grande revelação da temporada que acabou
            if m:
                out.append(m)
    m = im.revelacao(ck, res, car, hoje, rnd)
    if m:
        out.append(m)
    return out


# ---------------------------------------------------------------- ao vivo (sem save)
class _Nomes:
    """Imita SaveML.name() com a lista de nomes do pulso_aux (a Central não abre o save)."""
    def __init__(self, nomes):
        self.nomes = nomes

    def name(self, i):
        return self.nomes[i] if 0 <= i < len(self.nomes) else str(i)


def pos_jogo_vivo(dados, pulso, aux, snap, log=print):
    """Pós-jogo escrito pela MEMÓRIA, assim que o jogo acaba (11/10/2026): o PES não salva durante animações e a
    reunião só roda depois do save. Mesma chave da reunião (número da súmula + data): a reunião depois não repete."""
    ck = dados.get('carreira')
    uj = (pulso or {}).get('ultimo_jogo') or {}
    if not ck or not uj.get('linhas') or uj.get('num') is None:
        return None
    ti = aux['ti']
    linhas = lambda xs: [{'reg': x['reg'], 'pid': x['pid'], 'gols': x['gols'], 'assist': x['assist'], 'nota': x['nota'],
                          'minutos': x['min'], 'titular': x.get('titular'), 'funcao': 0} for x in xs]
    nosso1 = uj['time1'] == ti
    p = {'num': uj['num'], 'data': tuple(uj['data']), 'comp': uj['comp'], 'rodada': uj['rodada'], 'time1': uj['time1'],
         'time2': uj['time2'], 'gols1': uj['gols1'], 'gols2': uj['gols2'], 'flag': uj.get('flag'), 'final_vivo': uj.get('final'),
         'linhas1': linhas(uj['linhas'] if nosso1 else uj['linhas_adv']), 'linhas2': linhas(uj['linhas_adv'] if nosso1 else uj['linhas'])}
    if db.existe(ck, f'pos|{ck}|{p["num"]}|{db.data_txt(p["data"])}'):
        return None
    # jogos anteriores (só placar) para a sequência de vitórias/derrotas
    ant = []
    for g in (pulso.get('ultimos_jogos') or [])[:-1]:
        ant.append({'time1': ti if g['casa'] else -1, 'time2': -1 if g['casa'] else ti,
                    'gols1': g['pro'] if g['casa'] else g['contra'], 'gols2': g['contra'] if g['casa'] else g['pro'], 'data': tuple(g['data'])})
    import dados as _dados
    try:
        P = _dados.load_players(snap)
    except Exception:  # noqa: BLE001
        return None
    ida = uj.get('ida')   # jogo de ida do mata-mata (pulso): para detectar virada histórica
    todas = ([dict(ida, data=tuple(ida['data']), num=None)] if ida else []) + [p]
    ctx = {'s': _Nomes(aux['nomes']), 'P': P, 'ck': ck, 'ti': ti, 'nos': dados.get('time'),
           'r': {'J': [], 'jogos': ant + [p], 'todas_partidas': todas},
           'car': {'liga': dados.get('liga'), 'proximo_jogo': dados.get('proximo_jogo')}}
    m = pos_jogo(ctx, ant + [p], dados.get('proximos') or [dados.get('proximo_jogo')], random.Random(f'vivo|{ck}|{p["num"]}'), True)
    if not m:
        return None
    try:
        import redator
        redator.reescrever_materias([m], clube=dados.get('time', ''), log=log)
    except Exception as e:  # noqa: BLE001
        log(f'aviso: redator do pós-jogo ao vivo: {e}')
    m['autor'] = 'Redação · pós-jogo (ao vivo)'
    db.gravar(ck, m)
    log(f'imprensa ao vivo: pós-jogo de {m["titulo"]}')
    return m


# ---------------------------------------------------------------- a reunião
def rodada(car, r, d, hoje, snap, prox_antigo=None, log=print):
    """Gera as matérias novas desta reunião e grava no banco. Nunca levanta exceção para a reunião."""
    ck = car.get('ck')
    if not ck:
        return []
    ctx = _contexto(car, r, d, snap)
    rnd = random.Random(f'imprensa|{ck}|{hoje}')
    novas = []
    try:   # memória do futebol: prêmios, diários de carreira, títulos (legado.py)
        import legado
        n = legado.capturar(car, r, d, ctx['s'], ctx['P'], log=log)
        log(f'legado: {n}')
    except Exception as e:  # noqa: BLE001
        log(f'aviso: legado não capturado: {type(e).__name__}: {e}')
    proximos = [p for p in (car.get('proximos') or [car.get('proximo_jogo')]) if p]   # prévias dos próximos 3 jogos
    for nome, f in (('pós-jogo', lambda: pos_jogos(ctx, prox_antigo, rnd)),
                    ('pré-jogo', lambda: [m for m in (pre_jogo(ctx, rnd, pj) for pj in proximos) if m]),
                    ('jogo da rodada', lambda: [m for m in (jogo_da_rodada(ctx, rnd, pj) for pj in proximos) if m]),
                    ('temporada', lambda: temporada(ctx, hoje, rnd)),
                    ('mercado', lambda: mercado(ctx, hoje, rnd)),
                    ('movimentações', lambda: movimentacoes(ctx, rnd)),
                    ('mundo', lambda: mundo(ctx, hoje, rnd, snap, log))):
        try:
            m = f()
            if isinstance(m, list):
                novas += m
            elif m:
                novas.append(m)
        except Exception as e:  # noqa: BLE001
            log(f'aviso: imprensa ({nome}) não gerada: {type(e).__name__}: {e}')
    novas += car.pop('_imprensa_extra', None) or []   # seleção da rodada / jogador do mês (rodada_mes.py), já calculados
    # foto das estatísticas da temporada (o próximo pós-jogo tira a diferença)
    try:
        db.foto_estatisticas(ck, hoje, {j['k']: j.get('est_temp') for j in r['J'] if j.get('est_temp')})
    except Exception as e:  # noqa: BLE001
        log(f'aviso: foto das estatísticas não gravada: {e}')
    # 12/10/2026: as três chamadas ao redator com IA (matérias, Bola na Mesa pós e pré) esperavam uma pela outra;
    # agora vão juntas (cada uma espera só a própria resposta da internet)
    from concurrent.futures import ThreadPoolExecutor
    import bola_na_mesa
    import redator
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_red = ex.submit(redator.reescrever_materias, novas, clube=r['time'], log=log) if novas else None
        f_bnm = {fase: ex.submit(bola_na_mesa.materias, car, r, d, snap, ctx, log=log, fase=fase) for fase in ('pos', 'pre')}
        if f_red:
            try:
                f_red.result()
            except Exception as e:  # noqa: BLE001
                log(f'aviso: redator das matérias: {e}')
        for fase, f in f_bnm.items():   # Bola na Mesa + redes: edição pós-jogo (último jogo) e pré-jogo (próximo)
            try:
                novas += f.result()
            except Exception as e:  # noqa: BLE001
                log(f'aviso: Bola na Mesa ({fase}) não gerado: {type(e).__name__}: {e}')
    for m in novas:
        mid = db.gravar(ck, m)
        if m.get('_ids'):
            db.marcar_negocios(m['_ids'], mid)
    if novas:
        log('imprensa: ' + ', '.join(f'{m["frente"]}{" (IA)" if m.get("ia") else ""}' for m in novas))
    return novas
