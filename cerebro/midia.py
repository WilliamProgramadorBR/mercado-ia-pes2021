# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Mídia do clube (Central do Técnico, etapa 1 da "vida futebolística"): jornais, programa esportivo e coletiva.

A cada RODADA NOVA (aplicar_vestiario), os fatos do clube viram:
  - capas de 3 jornais fictícios, cada um com a sua linha editorial (o mesmo fato ganha manchetes diferentes);
  - o programa "Bola na Mesa" (texto, estilo mesa-redonda de TV) com apresentador e 3 comentaristas;
  - uma COLETIVA DE IMPRENSA: 2-3 perguntas sobre os assuntos quentes. As respostas (Central -> acoes.py) mexem na
    moral (=> seta de condição, escrita ao vivo no jogo) e esquentam/esfriam as polêmicas.
Tudo é determinístico pela semente da rodada (mesma rodada -> mesmo texto).

Formato de um efeito (usado pela coletiva e consumido por acoes.consumir):
  {'k': 'reg:id' | '*', 'delta': int, 'rodadas': int, 'motivo': str}   moral (k='*' = elenco todo)
  {'historia': hid, 'restam': int}                                       polêmica: +N rodadas (ou -N) na mídia
"""
import random

from clube import C as CL

JORNAIS = [
    {'id': 'diario', 'nome': 'Diário da Bola', 'tom': 'sensacionalista', 'slogan': 'O jornal que a arquibancada lê',
     'pesos': {'proximo': 2.0, 'liga': 1.6, 'disciplina': 3.4, 'conflito': 3.2, 'baixa': 2.6, 'eco': 2.8, 'derrota': 2.4, 'mercado': 1.6, 'resultado': 1.4,
               'contrato': 1.8, 'pressao': 2.6, 'apelido': 1.0, 'destaque': 1.0, 'sequencia': 1.6, 'tabela': 1.0,
               'pre': 1.0, 'revelacao': 2.4, 'bola_ouro': 2.0, 'artilheiro_mundo': 1.6, 'selecao': 2.0, 'marco': 2.4, 'rodada': 1.4, 'data_fifa': 2.0, 'rumor': 2.6, 'obrigacao': 3.2, 'renovacao': 2.0, 'joia_base': 1.6}},
    {'id': 'gazeta', 'nome': 'Gazeta Tática', 'tom': 'analítico', 'slogan': 'Futebol se explica com números',
     'pesos': {'proximo': 2.2, 'liga': 2.4, 'disciplina': 1.3, 'resultado': 3.0, 'derrota': 2.6, 'tabela': 2.8, 'sequencia': 2.6, 'destaque': 2.2, 'baixa': 1.4,
               'conflito': 1.2, 'eco': 1.4, 'pressao': 1.8, 'mercado': 1.2, 'contrato': 1.0, 'apelido': 0.6,
               'pre': 2.0, 'revelacao': 2.0, 'bola_ouro': 2.6, 'artilheiro_mundo': 2.2, 'selecao': 2.4, 'marco': 2.0, 'rodada': 2.4, 'data_fifa': 1.8, 'rumor': 1.4, 'obrigacao': 2.4, 'renovacao': 1.8, 'joia_base': 1.8}},
    {'id': 'voz', 'nome': 'A Voz de Old Trafford', 'tom': 'torcedor', 'slogan': 'A voz das arquibancadas de Manchester',
     'pesos': {'proximo': 2.6, 'liga': 1.2, 'disciplina': 1.7, 'destaque': 3.0, 'apelido': 3.2, 'resultado': 2.4, 'contrato': 2.4, 'mercado': 2.6, 'derrota': 1.8,
               'eco': 2.0, 'conflito': 1.6, 'baixa': 1.4, 'sequencia': 1.8, 'tabela': 1.4, 'pressao': 1.2,
               'pre': 2.2, 'revelacao': 1.4, 'bola_ouro': 1.8, 'artilheiro_mundo': 0.8, 'selecao': 2.6, 'marco': 3.0, 'rodada': 1.2, 'data_fifa': 2.2, 'rumor': 2.4, 'obrigacao': 1.8, 'renovacao': 2.6, 'joia_base': 2.8}},
]
REPORTERES = {'diario': 'Marcão Teixeira', 'gazeta': 'Lúcia Brandão', 'voz': 'Tom Hadley'}
PROGRAMA = {'nome': 'Bola na Mesa', 'apresentador': 'Rogério Lemos',
            'comentaristas': [
                {'id': 'carlao', 'nome': 'Carlão Pereira', 'papel': 'ex-zagueiro, sem papas na língua'},
                {'id': 'helena', 'nome': 'Helena Saraiva', 'papel': 'analista tática'},
                {'id': 'beto', 'nome': 'Beto Rocha', 'papel': 'setorista do clube'},
            ]}


def chave(k):
    return f'{k[0]}:{k[1]}'


def _dt_dias(a, b):
    import datetime as dt
    return (dt.date(*a) - dt.date(*b)).days


# ------------------------------------------------------------------ fatos da rodada
def fatos(r, car, hoje, apelido_novo=None, ecos=()):
    """Lista de fatos {tipo, peso, ...} a partir do vestiário (r), da diretoria e das respostas na coletiva."""
    F = []
    J = r['J']
    porK = {j['k']: j for j in J}
    ult = r.get('ultimos') or []
    temporada = [g for g in ult if (g['data'][0], g['data'][1]) >= ((hoje[0] if hoje[1] >= 7 else hoje[0] - 1), 7)]
    coberto = (car.get('midia') or {}).get('jogo_coberto')
    if ult and list(ult[-1]['data']) != coberto:
        g = ult[-1]
        marc, melhor = [], None
        jogo = r['jogos'][-1] if r.get('jogos') else None
        if jogo and tuple(jogo['data']) == tuple(g['data']):
            linhas = jogo['linhas1'] if jogo['time1'] == r['ti'] else jogo['linhas2']
            for x in linhas:
                j = porK.get((x['reg'], x['pid']))
                if j and x['gols']:
                    marc.append((j, x['gols']))
                if j and x['nota'] and (melhor is None or x['nota'] > melhor[1]):
                    melhor = (j, x['nota'])
        tipo = 'resultado' if g['pro'] >= g['contra'] else 'derrota'
        F.append({'tipo': tipo, 'peso': 3 + abs(g['pro'] - g['contra']) * 0.4, 'jogo': g, 'marcadores': marc,
                  'melhor': melhor})
    try:   # viradas históricas no mata-mata: a nossa (capa de todos os jornais) e as do mundo
        import viradas
        nm = r.get('_nomes_time') or (lambda i: str(i))
        v = viradas.do_time(r.get('todas_partidas') or [], r['ti'], hoje, dias=8)
        if v and v['tipo'] and list(v['data']) != coberto:
            F.append({'tipo': 'virada', 'peso': 12, 'tie': v, 'adv': nm(v['adv'])})
        for w in viradas.no_mundo(r.get('todas_partidas') or [], hoje, 8, exceto=r['ti'])[:2]:
            F.append({'tipo': 'virada_mundo', 'sub': nm(w['time']), 'peso': 2.4 + w['deficit'] * 0.3, 'tie': w,
                      'time': nm(w['time']), 'adv': nm(w['adv'])})
    except Exception as e:  # noqa: BLE001
        print('aviso: viradas fora das capas:', e)
    try:   # SAÍDAS e CHEGADAS (saidas.py): a estrela que vai embora vira capa
        import saidas
        top4 = {t['time'] for t in ((car.get('liga') or {}).get('classificacao') or [])[:4]}
        m, n = saidas.principal(r.get('movimentos'), r['J'], car.get('ck'), r['time'], top4)
        if m:
            peso = 10 if n['tipo'] in ('sombra', 'rival', 'idolo') else 5 if m['valor'] >= 30e6 else 2.5
            F.append({'tipo': 'movimento', 'sub': m['nome'], 'peso': peso, 'm': m, 'n': n})
    except Exception as e:  # noqa: BLE001
        print('aviso: movimentações fora das capas:', e)
    try:   # FINAIS e TÍTULO DA LIGA (marcos.py): capa de todos os jornais
        import marcos
        from proximo_jogo import nome_comp
        todos = (r.get('todas_partidas') or []) + (r.get('agenda') or [])
        fin = marcos.final_do_time(todos, r['ti'])
        if fin and fin['jogado'] and fin['campeao'] is not None and 0 <= (_dt_dias(hoje, fin['data'])) <= 8:
            F.append({'tipo': 'titulo', 'peso': 14, 'campeao': fin['campeao'], 'comp': nome_comp(fin['comp']),
                      'adv': (r.get('_nomes_time') or str)(fin['adv']), 'placar': f'{fin["gp"]} a {fin["gc"]}'})
        tl = marcos.titulo_liga((car.get('liga') or {}).get('classificacao'))
        temp = f'{hoje[0] if hoje[1] >= 7 else hoje[0] - 1}'
        if tl and tl['campeao'] and car.get('titulo_liga_celebrado') != temp:
            car['titulo_liga_celebrado'] = temp
            F.append({'tipo': 'titulo', 'peso': 14, 'campeao': True, 'liga': True, 'comp': (car.get('liga') or {}).get('competicao', 'liga'),
                      'restam': tl['restam'], 'pts': tl['pts']})
    except Exception as e:  # noqa: BLE001
        print('aviso: títulos fora das capas:', e)
    if len(temporada) >= 3:
        res = ['V' if g['pro'] > g['contra'] else 'E' if g['pro'] == g['contra'] else 'D' for g in temporada]
        seq_v = len(res) - len(''.join(res).rstrip('V')) if res[-1] == 'V' else 0
        sem_v = 0
        for x in reversed(res):
            if x == 'V':
                break
            sem_v += 1
        if seq_v >= 3:
            F.append({'tipo': 'sequencia', 'peso': 1.5 + seq_v * 0.3, 'bom': True, 'n': seq_v})
        elif sem_v >= 3:
            F.append({'tipo': 'sequencia', 'peso': 2 + sem_v * 0.4, 'bom': False, 'n': sem_v})
    dire = car.get('diretoria') or {}
    tab = dire.get('tabela') or []
    eu = next((t for t in tab if t.get('eu')), None)
    metas = dire.get('metas') or {}
    if eu and eu.get('j', 0) >= 3:
        lider = tab[0]
        F.append({'tipo': 'tabela', 'peso': 1.6 + (1 if eu['pos'] == 1 else 0) + (1 if metas and eu['pos'] > metas.get('liga_alvo', 20) else 0),
                  'pos': eu['pos'], 'pts': eu['pts'], 'lider': lider, 'eu': eu, 'meta': metas})
    elif not temporada:
        F.append({'tipo': 'pre', 'peso': 1.2, 'meta': metas})
    conf = dire.get('confianca')
    if conf is not None and conf < 45:
        F.append({'tipo': 'pressao', 'peso': 2 + (45 - conf) / 10, 'conf': conf, 'meta': metas})
    vistos = set()
    for tipo, txt, env in r['conflitos']:
        foco = env[1:] if tipo == 'Ego salarial' else env[:1]
        if any(chave(x['k']) in vistos for x in foco):
            continue
        vistos.update(chave(x['k']) for x in foco)
        base = {'Braçadeira': 2.8, 'Posição': 2.4, 'Insatisfeito': 2.0, 'Ego salarial': 1.8}.get(tipo, 1.5)
        alvo = env[1] if tipo == 'Ego salarial' else env[0]   # ego: o foco é quem ganha menos
        F.append({'tipo': 'conflito', 'peso': base + (0.6 if alvo['status'] in ('Lenda', 'Ídolo', 'Superastro') else 0),
                  'sub': tipo, 'env': env, 'foco': alvo, 'texto': txt, 'hid': f'{tipo}|{chave(env[0]["k"])}'})
    em_alta = [j for j in J if j['r_nota'] >= 7.0 or (j['moral'] >= 85 and j['t_gols'] + j['t_assist'] >= 3)]
    if em_alta:
        j = max(em_alta, key=lambda j: (j['r_nota'], j['t_gols'] + j['t_assist']))
        F.append({'tipo': 'destaque', 'peso': 1.6 + max(0, j['r_nota'] - 7) * 2, 'j': j})
    baixos = [j for j in J if j['moral'] < 45 and j['status'] in ('Lenda', 'Ídolo', 'Superastro', 'Craque')
              and chave(j['k']) not in vistos]
    if baixos:
        j = min(baixos, key=lambda j: j['moral'])
        F.append({'tipo': 'baixa', 'peso': 1.8 + (45 - j['moral']) / 15, 'j': j})
    for j in J:
        c = j.get('contrato')
        if c and j['status'] in ('Lenda', 'Ídolo', 'Superastro', 'Craque'):
            meses = (c[0] - hoje[0]) * 12 + c[1] - hoje[1]
            if 0 <= meses <= 8:
                F.append({'tipo': 'contrato', 'peso': 1.6 + (8 - meses) / 6, 'j': j, 'meses': meses})
                break
    fora = car.get('insatisfeitos_fora') or []
    if fora:
        alvo = random.Random(f'{hoje}').choice(fora[:5])
        F.append({'tipo': 'mercado', 'peso': 1.2, 'alvo': alvo})
    if apelido_novo:
        F.append({'tipo': 'apelido', 'peso': 1.8, 'nome': apelido_novo['nome'], 'texto': apelido_novo['texto']})
    pj = car.get('proximo_jogo')
    if pj and not pj.get('parcial'):
        continental = pj['competicao'] in ('UEFA Champions League', 'Libertadores')
        adv_tab = (pj.get('tabela') or {}).get('fora' if pj['eu_casa'] else 'casa')
        grande = continental or (adv_tab and adv_tab['pos'] <= 4)
        F.append({'tipo': 'proximo', 'peso': 3.2 if pj.get('disputa') else 2.6 if grande else 1.1, 'pj': pj,
                  'grande': bool(grande) or bool(pj.get('disputa')), 'continental': continental})
    co = car.get('corrida')
    if co and co.get('rivais'):   # 12/10/2026: a disputa do usuário na liga (disputa.py)
        F.append({'tipo': 'corrida', 'peso': 1.6 + 2.0 * co['pressao'], 'co': co})
    mo = car.get('momento') or {}   # 12/10/2026: o momento acumulado (momento.py) vira capa
    if mo and mo.get('frases') and (mo.get('clima') in ('crise', 'alerta', 'embalado') or (mo.get('liga') or {}).get('lideranca')
                                    or mo.get('semana_decisiva')):
        F.append({'tipo': 'momento', 'peso': {'crise': 4.0, 'alerta': 3.4, 'embalado': 2.6}.get(mo.get('clima'), 2.3)
                  + (0.6 if (mo.get('liga') or {}).get('lideranca') else 0), 'mo': mo})
    for e in ecos:
        if e.get('tipo') == 'liga':
            F.append(e)
            continue
        if e.get('tipo') == 'disciplina':
            c = e['caso']
            F.append({'tipo': 'disciplina', 'peso': {'leve': 1.6, 'média': 2.4, 'grave': 3.2}[c['gravidade']], 'caso': c,
                      'j': next((j for j in r['J'] if chave(j['k']) == c['envolvidos'][0]), None)})
        else:
            F.append({'tipo': 'eco', 'peso': 2.2, **e})
    try:   # o mundo: revelação, Bola de Ouro, artilheiro do mundo, seleção da temporada (jornal_extra.py)
        import jornal_extra
        F += jornal_extra.fatos_mundo(car, hoje)
    except Exception as e:  # noqa: BLE001
        print('aviso: fatos do mundo fora das capas:', e)
    return F


# ------------------------------------------------------------------ jornais
def _placar(g):
    return f'{g["pro"]} x {g["contra"]}' if g['casa'] else f'{g["contra"]} x {g["pro"]}'


def _jogo_txt(g, time=None):
    time = time or CL['curto']
    return f'{time} {g["pro"]} x {g["contra"]} {g["adversario"]}' if g['casa'] else \
        f'{g["adversario"]} {g["contra"]} x {g["pro"]} {time}'


def _manchete(f, tom, rnd):
    """(manchete, linha fina) do fato f no tom do jornal."""
    t = f['tipo']
    if t in ('revelacao', 'bola_ouro', 'artilheiro_mundo', 'selecao', 'marco', 'rodada', 'data_fifa', 'rumor', 'obrigacao', 'renovacao', 'joia_base'):
        import jornal_extra
        return jornal_extra.manchete(f, tom, rnd)
    if t == 'virada':   # virada histórica / vexame no mata-mata (viradas.py)
        v, adv = f['tie'], f['adv']
        i, a = v['ida'], v['agg']
        if v['tipo'] == 'virada':
            return {'sensacionalista': (rnd.choice(['VIRADA HISTÓRICA!!!', 'É INACREDITÁVEL!', 'MILAGRE!']),
                                        f'Depois de perder a ida por {i[1]} a {i[0]}, o {CL["nome"]} atropela o {adv} e passa: {a[0]} a {a[1]} no agregado!'),
                    'analítico': (f'A virada: {a[0]} a {a[1]} no agregado contra o {adv}',
                                  f'Desvantagem de {v["deficit"]} gols revertida com {v["volta"][0]} a {v["volta"][1]} na volta. Noite para os livros.'),
                    'torcedor': (rnd.choice(['EU ACREDITEI! VOCÊ ACREDITOU?', 'A NOITE MAIS LINDA DA NOSSA HISTÓRIA']),
                                 f'{v["volta"][0]} a {v["volta"][1]} no {adv} e a virada que ninguém vai esquecer.')}[tom]
        return {'sensacionalista': ('VEXAME HISTÓRICO!', f'O {CL["nome"]} venceu a ida por {i[0]} a {i[1]} e conseguiu ser eliminado pelo {adv}.'),
                'analítico': (f'Como o {CL["nome"]} perdeu uma vantagem de {v["deficit"]} gols', f'{a[0]} a {a[1]} no agregado: a eliminação expõe falhas graves.'),
                'torcedor': ('NÃO DÁ PARA ACEITAR', f'Eliminação para o {adv} com vantagem de {v["deficit"]} gols. Vergonha.')}[tom]
    if t == 'titulo':   # final ganha/perdida, título da liga
        c = f['comp']
        if f.get('liga'):
            extra = f' com {f["restam"]} rodadas de antecedência' if f.get('restam') else ''
            return {'sensacionalista': (f'É CAMPEÃO!!! O {CL["nome"].upper()} É DONO DA {c.upper()}!', f'Título garantido{extra}, com {f["pts"]} pontos. A festa começou!'),
                    'analítico': (f'{CL["nome"]} campeão da {c}{extra}', f'{f["pts"]} pontos: campanha para a história do campeonato.'),
                    'torcedor': ('CAMPEÃO! CAMPEÃO! CAMPEÃO!', f'A {c} é nossa! Pode soltar o grito que estava guardado.')}[tom]
        if f['campeao']:
            return {'sensacionalista': (f'É TAÇA!!! {CL["nome"].upper()} CAMPEÃO DA {c.upper()}!', f'Vitória por {f["placar"]} sobre o {f["adv"]} na final. Noite eterna!'),
                    'analítico': (f'{CL["nome"]} conquista a {c}', f'Final decidida com {f["placar"]} sobre o {f["adv"]}: o time soube jogar o jogo grande.'),
                    'torcedor': (f'A {c.upper()} É NOSSA!', f'{f["placar"]} no {f["adv"]} e a taça vem para casa!')}[tom]
        return {'sensacionalista': ('BATEU NA TRAVE!', f'O {CL["nome"]} perde a final da {c} para o {f["adv"]}. Dor e lágrimas.'),
                'analítico': (f'O vice da {c}', f'Derrota para o {f["adv"]} na final expõe o que faltou no jogo decisivo.'),
                'torcedor': ('DÓI DEMAIS', f'A final da {c} escapou. Cabeça erguida, mas dói.')}[tom]
    if t == 'movimento':   # saída/chegada (saidas.narrativa)
        m, n = f['m'], f['n']
        if m['tipo'] == 'chegada':
            return {'sensacionalista': (f'BOMBA: {m["nome"].upper()} É DO {CL["nome"].upper()}!', n['lead']),
                    'analítico': (f'O reforço: {m["nome"]}', n['lead']),
                    'torcedor': (f'Bem-vindo, {m["nome"]}!', n['lead'])}[tom]
        sens = {'sombra': f'{m["nome"].upper()} CANSOU DE SER COADJUVANTE!', 'rival': f'TRAIÇÃO! {m["nome"].upper()} VAI PARA O RIVAL',
                'idolo': f'ADEUS, {m["nome"].upper()}', 'dinheiro': f'{m["nome"].upper()} ESCOLHE O DINHEIRO'}.get(n['tipo'], f'{m["nome"].upper()} DE SAÍDA')
        torc = {'sombra': f'{m["nome"]} vai embora para ser protagonista', 'rival': f'{m["nome"]} escolhe o rival e revolta a torcida',
                'idolo': f'Obrigado por tudo, {m["nome"]}'}.get(n['tipo'], f'{m["nome"]} de saída')
        return {'sensacionalista': (sens, n['lead']), 'analítico': (n['titulo'], n['lead']), 'torcedor': (torc, n['lead'])}[tom]
    if t == 'virada_mundo':
        v = f['tie']
        return {'sensacionalista': (f'VIRADA DO {f["time"].upper()}!', f'{f["time"]} perdeu a ida para o {f["adv"]} por {v["ida"][1]} a {v["ida"][0]} e passou: {v["agg"][0]} a {v["agg"][1]}.'),
                'analítico': (f'{f["time"]} reverte desvantagem de {v["deficit"]} gols', f'Agregado de {v["agg"][0]} a {v["agg"][1]} contra o {f["adv"]}.'),
                'torcedor': (f'Que virada do {f["time"]}!', f'O {f["adv"]} tinha {v["deficit"]} gols de vantagem e caiu.')}[tom]
    if t in ('resultado', 'derrota'):
        g = f['jogo']
        marc = ', '.join(j['nome'] + (f' ({n})' if n > 1 else '') for j, n in f['marcadores']) or None
        melhor = f['melhor'][0]['nome'] if f['melhor'] else None
        if t == 'resultado' and g['pro'] > g['contra']:
            return rnd.choice({
                'sensacionalista': [(f'É DO {CL["apelido"].upper()}! {g["adversario"].upper()} CAI', f'{_jogo_txt(g)}' + (f' — {marc} decidem' if marc else '')),
                                    (f'ATROPELO!' if g['pro'] - g['contra'] >= 3 else 'VITÓRIA SUADA, MAS VITÓRIA',
                                     f'{_jogo_txt(g)}. ' + (f'{melhor} foi o dono do jogo.' if melhor else ''))],
                'analítico': [(f'Vitória com controle: {_jogo_txt(g)}', (f'{melhor} teve a melhor nota da equipe. ' if melhor else '') +
                               'O time impôs o plano de jogo desde o início.')],
                'torcedor': [(f'Que noite! {_jogo_txt(g)}', (f'{marc} na rede e ' if marc else '') + 'a torcida canta até agora.')],
            }[tom])
        if g['pro'] == g['contra']:
            return rnd.choice({
                'sensacionalista': [('EMPATE COM GOSTO AMARGO', f'{_jogo_txt(g)}. Torcida deixa o estádio desconfiada.')],
                'analítico': [(f'Empate expõe limites do time: {_jogo_txt(g)}', (f'{melhor} teve a melhor nota da equipe' if melhor else 'Ninguém se destacou')
                               + (f'; gols de {marc}.' if marc else '; o ataque passou em branco.'))],
                'torcedor': [(f'Um ponto e muita coisa a melhorar', f'{_jogo_txt(g)}' + (f' — {marc} marcou' if marc else '') + '.')],
            }[tom])
        return rnd.choice({
            'sensacionalista': [('VEXAME!' if g['contra'] - g['pro'] >= 2 else 'TROPEÇO!',
                                 f'{_jogo_txt(g)}. Vestiário em silêncio e técnico na mira.'),
                                (f'{g["adversario"].upper()} CASTIGA O {CL["apelido"].upper()}', f'{_jogo_txt(g)}. Quem vai pagar a conta?')],
            'analítico': [(f'Derrota para o {g["adversario"]} acende alerta', f'{_jogo_txt(g)}. ' + (f'{marc} marcou, mas não bastou.' if marc else 'O ataque passou em branco.'))],
            'torcedor': [('Noite para esquecer', f'{_jogo_txt(g)}. A torcida apoiou até o fim, mas cobra reação.')],
        }[tom])
    if t == 'sequencia':
        n = f['n']
        if f['bom']:
            return {'sensacionalista': (f'{n} SEGUIDAS! NINGUÉM SEGURA', f'O {CL["apelido"]} embalou e os rivais já sentem.'),
                    'analítico': (f'{n} vitórias seguidas: o que mudou', 'A regularidade de resultados virou a marca do time.'),
                    'torcedor': (f'{n} vitórias em sequência!', f'{CL["estadio_txt"]} voltou a ser um caldeirão.')}[tom]
        return {'sensacionalista': (f'{n} JOGOS SEM VENCER: CRISE?', 'Bastidores fervem e a paciência acabou.'),
                'analítico': (f'{n} jogos sem vencer: os números da queda', 'A sequência pede respostas da comissão técnica já no próximo jogo.'),
                'torcedor': (f'{n} jogos sem vitória. Até quando?', 'A torcida quer ver reação já no próximo jogo.')}[tom]
    if t == 'tabela':
        pos, lider, meta = f['pos'], f['lider'], f['meta']
        dif = lider['pts'] - f['pts']
        if pos == 1:
            return {'sensacionalista': ('LÍDER E SOBRANDO!', f'O {CL["apelido"]} está no topo com {f["pts"]} pontos.'),
                    'analítico': ('Na liderança, mas sem margem para erro', f'{f["pts"]} pontos; a regularidade é o trunfo.'),
                    'torcedor': ('No topo da tabela!', 'É o nosso lugar.')}[tom]
        fora = meta and pos > meta.get('liga_alvo', 20)
        return {'sensacionalista': (f'{pos}º LUGAR E {dif} PONTOS ATRÁS', 'Diretoria já faz contas.' if fora else 'Dá para alcançar?'),
                'analítico': (f'{pos}º colocado, {dif} pontos do líder {lider["time"]}', 'Meta da temporada: ' + (meta.get('liga_texto', '—') if meta else '—') + '.'),
                'torcedor': (f'{dif} pontos para o topo', f'Ainda dá. Ninguém desiste {CL["em_cidade"]}.')}[tom]
    if t == 'pre':
        m = (f['meta'] or {}).get('liga_texto', 'brigar no topo')
        return {'sensacionalista': ('PRÉ-TEMPORADA: QUEM FICA, QUEM SAI?', f'Diretoria quer: {m.lower()}.'),
                'analítico': (f'Pré-temporada: o desenho do novo {CL["apelido"]}', f'Meta oficial: {m.lower()}.'),
                'torcedor': ('A temporada vai começar!', f'O objetivo é claro: {m.lower()}.')}[tom]
    if t == 'pressao':
        return {'sensacionalista': ('DIRETORIA PERDE A PACIÊNCIA', f'Confiança no técnico desaba ({f["conf"]}/100).'),
                'analítico': ('Pressão por resultados aumenta', f'A diretoria avalia o trabalho mês a mês; confiança em {f["conf"]}.'),
                'torcedor': ('Diretoria cobra o técnico', 'A torcida está dividida.')}[tom]
    if t == 'conflito':
        a = f['env'][0]
        sub = f['sub']
        if sub == 'Braçadeira':
            cap = f['env'][1]
            return {'sensacionalista': (f'GUERRA PELA BRAÇADEIRA!', f'{a["nome"]} não aceita {cap["nome"]} como capitão.'),
                    'analítico': ('Liderança em xeque no vestiário', f'{a["nome"]} tem mais tempo de clube que o capitão {cap["nome"]}.'),
                    'torcedor': (f'{a["nome"]} merecia a faixa?', 'A torcida se divide na escolha do capitão.')}[tom]
        if sub == 'Posição':
            b = f['env'][1]
            return {'sensacionalista': (f'{a["nome"].upper()} NO BANCO E NERVOSO', f'Perdeu a vaga para {b["nome"]} e já fala em sair.'),
                    'analítico': (f'{b["nome"]} ganha a disputa com {a["nome"]}', 'A escolha do técnico tem lógica tática.'),
                    'torcedor': (f'Queremos {a["nome"]} em campo!', f'Mas {b["nome"]} também tem feito por merecer.')}[tom]
        if sub == 'Ego salarial':
            vit = ', '.join(x['nome'] for x in f['env'][1:3])
            return {'sensacionalista': ('FOLHA SALARIAL ABRE RACHA', f'{a["nome"]} ganha mais que {vit} e o clima azedou.'),
                    'analítico': ('Teto salarial mal distribuído', f'O salário de {a["nome"]} destoa do rendimento.'),
                    'torcedor': ('Dinheiro dividindo o grupo?', f'Bastidores falam em incômodo de {vit}.')}[tom]
        motivo = a['motivos'][0] if a['motivos'] else 'momento no clube'
        return {'sensacionalista': (f'{a["nome"].upper()} INSATISFEITO', f'Motivo: {motivo}. Empresário já se movimenta.'),
                'analítico': (f'O caso {a["nome"]}', f'Fator principal: {motivo}.'),
                'torcedor': (f'Fica, {a["nome"]}!', 'Torcida faz campanha nas redes.')}[tom]
    if t == 'destaque':
        j = f['j']
        return {'sensacionalista': (f'{j["nome"].upper()} É O CARA', f'Nota média {j["r_nota"]:.1f} e moral lá em cima.'),
                'analítico': (f'Os números de {j["nome"]}', f'{j["t_gols"]} gols e {j["t_assist"]} assistências na temporada; média {j["r_nota"]:.1f} nos últimos jogos.'),
                'torcedor': (f'{j["nome"]}, ídolo da arquibancada', 'O nome dele ecoa nas arquibancadas.')}[tom]
    if t == 'baixa':
        j = f['j']
        return {'sensacionalista': (f'{j["nome"].upper()} À BEIRA DE UM ATAQUE DE NERVOS', 'Pessoas próximas falam em insatisfação total.'),
                'analítico': (f'{j["nome"]} em baixa', f'Moral em {j["moral"]}/100: ' + '; '.join(j['motivos'][:2]) + '.'),
                'torcedor': (f'Força, {j["nome"]}!', 'A torcida não esquece o que ele já fez pelo clube.')}[tom]
    if t == 'contrato':
        j, m = f['j'], f['meses']
        return {'sensacionalista': (f'{j["nome"].upper()} DE SAÍDA?', f'Contrato acaba em {m} meses e ninguém fala em renovação.'),
                'analítico': (f'O contrato de {j["nome"]}', f'Restam {m} meses; a decisão impacta o planejamento.'),
                'torcedor': (f'Renova com {j["nome"]}!', f'Faltam {m} meses. A torcida pede a renovação.')}[tom]
    if t == 'mercado':
        a = f['alvo']
        return {'sensacionalista': (f'{CL["apelido"].upper()} NA COLA DE {a["nome"].upper()}!', f'Insatisfeito no {a["clube"]}, ele estaria ouvindo propostas.'),
                'analítico': (f'Mercado: {a["nome"]} ({a["pos"]}, {a["nota"]})', f'Situação no {a["clube"]}: {a["motivo"]}.'),
                'torcedor': (f'Traz {a["nome"]}!', f'Nota {a["nota"]}, insatisfeito no {a["clube"]}. Seria reforço de peso.')}[tom]
    if t == 'apelido':
        return {'sensacionalista': (f'NASCE "{f["texto"].upper()}"!', f'{f["nome"]} ganha apelido das arquibancadas.'),
                'analítico': (f'"{f["texto"]}": o apelido de {f["nome"]}', 'Reconhecimento da torcida pela regularidade.'),
                'torcedor': (f'{f["nome"]} agora é "{f["texto"]}"!', 'Batizado pela torcida. Merecido!')}[tom]
    if t == 'liga':
        return f['txt'][tom]
    ZT = {'titulo': ('PELO TÍTULO', 'o título', 'pelo título'), 'vaga1': ('PELA VAGA', 'a vaga principal', 'pela vaga principal'),
          'vaga2': ('PELA VAGA CONTINENTAL', 'uma vaga continental', 'por uma vaga continental'),
          'rebaixamento': ('CONTRA A QUEDA', 'a permanência', 'pela permanência')}
    if t == 'lesao':      # 12/10/2026: departamento médico (lesoes.py)
        a = f['a']
        n, g = a['nome'], (a['grandes'][0] if a['grandes'] else None)
        alvo = (g['classico'] or g['adv']) if g else None
        sub = a['sub']
        return {'sensacionalista': ((f'DRAMA! {n.upper()} FORA' + (f' ÀS VÉSPERAS DE {alvo.upper()}!' if alvo else '!')),
                                    f'{a["parte_gols"]}% dos gols do time saem dos pés dele. E agora?' if a['parte_gols'] >= 20
                                    else 'A torcida prende a respiração: o departamento médico virou o centro das atenções.'),
                'analítico': (f'Sem {n}: o que muda', (f'{sub["nome"]} (nota {sub["ovr"]}) é o substituto natural; ' if sub else '')
                              + (f'sem ele, {a["sem_ele"]["v"]}V {a["sem_ele"]["e"]}E {a["sem_ele"]["d"]}D na temporada.' if a['sem_ele']['jogos']
                                 else 'o time ainda não jogou sem ele nesta temporada.')),
                'torcedor': (f'Força, {n}!', 'A arquibancada abraça o craque. ' + (f'Agora é com você, {sub["nome"]}!' if sub else 'Todo mundo junto!'))}[tom]
    if t == 'volta_lesao':
        a = f['a']
        n = a['nome']
        return {'sensacionalista': (f'ELE VOLTOU! {n.upper()} ESTÁ LIBERADO', f'{f["dias"]} dias de angústia chegam ao fim.'),
                'analítico': (f'{n} recuperado após {f["dias"]} dias', 'A dúvida agora é o ritmo de jogo: volta entre os titulares ou aos poucos?'),
                'torcedor': (f'{n} de volta!', 'O craque está liberado. Agora é para cima!')}[tom]
    if t == 'momento':
        import momento as _mo
        mo = f['mo']
        L, s = mo.get('liga') or {}, mo.get('seq') or {}
        rv = L.get('rival') or {}
        gs = [x for x in mo.get('proximos') or [] if x['tags'] and x['dias'] <= 10]
        agenda = ' e '.join(_mo.descreve_jogo(x) for x in gs[:2])
        fr = [x for x in mo['frases'] if not x.startswith(('Pela frente', 'Próximo desafio', 'Maratona'))]
        corpo = '. '.join(fr[:2]) + ('.' if fr else '')
        ordn = {2: 'segunda', 3: 'terceira', 4: 'quarta', 5: 'quinta'}.get(s.get('d', 0), f'{s.get("d")}ª')
        if L.get('lideranca') == 'perdeu' and rv:
            return {'sensacionalista': (f'{rv["nome"].upper()} TOMA A PONTA!', (f'{ordn.capitalize()} derrota seguida e a liderança escapa. ' if s.get('d', 0) >= 2 else '')
                                        + (f'Pela frente: {agenda}.' if agenda else 'A pressão mudou de lado.')),
                    'analítico': ('A liderança mudou de mãos', corpo + (f' A agenda não alivia: {agenda}.' if agenda else '')),
                    'torcedor': ('Vamos buscar de volta!', f'O {rv["nome"]} passou, mas o campeonato é longo.' + (f' E já tem {agenda}.' if agenda else ''))}[tom]
        if s.get('d', 0) >= 2:
            return {'sensacionalista': (f'{ordn.upper()} SEGUIDA! ALERTA LIGADO', corpo + (f' E agora: {agenda}.' if agenda else '')),
                    'analítico': (f'{ordn.capitalize()} derrota seguida: o que mudou', corpo + (f' A sequência: {agenda}.' if agenda else '')),
                    'torcedor': ('Hora de reagir!', 'Fase ruim se vence juntos.' + (f' Pela frente: {agenda}.' if agenda else ''))}[tom]
        if L.get('lideranca') == 'assumiu':
            return {'sensacionalista': (f'{CL["apelido"].upper()} LÍDER!', corpo),
                    'analítico': ('Nova liderança', corpo + (f' Próximos testes: {agenda}.' if agenda else '')),
                    'torcedor': ('É o nosso lugar!', 'Líder, como tem que ser. Agora é segurar!')}[tom]
        if mo.get('clima') == 'embalado':
            return {'sensacionalista': (f'{CL["apelido"].upper()} EMBALADO!', corpo),
                    'analítico': ('O melhor momento da temporada', corpo),
                    'torcedor': ('Ninguém segura!', corpo)}[tom]
        if mo.get('clima') == 'crise':
            return {'sensacionalista': ('CRISE!', corpo), 'analítico': ('A crise em números', corpo),
                    'torcedor': ('Acorda, time!', 'A arquibancada cobra e espera reação.')}[tom]
        return {'sensacionalista': ('A SEMANA DA VERDADE', f'Pela frente: {agenda}.' if agenda else corpo),
                'analítico': ('Uma semana que pode definir a temporada', f'Pela frente: {agenda}. ' + corpo),
                'torcedor': ('Semana de decisão!', f'{agenda[0].upper() + agenda[1:]}. Todo mundo junto!' if agenda else 'Todo mundo junto!')}[tom]
    if t == 'corrida':
        co = f['co']
        r0 = co['rivais'][0]
        z = co['nome_zona']
        frente = r0['dif'] < 0
        dist = abs(r0['dif'])
        pts_txt = f'{dist} ponto{"s" if dist != 1 else ""}'
        situ = (f'{r0["nome"]} {pts_txt} atrás' if frente else f'{r0["nome"]} {pts_txt} à frente' if dist else f'{r0["nome"]} empatado em pontos')
        return {'sensacionalista': (f'GUERRA {ZT[co["zona"]][0]}!' if co['zona'] != 'rebaixamento' else 'SUFOCO NO FIM DA TABELA!',
                                    f'{situ}, {co["restantes"]} rodadas para o fim. Cada ponto vale ouro.'),
                'analítico': (f'A corrida: {z}', f'{CL["curto"]} em {co["pos"]}º com {co["pts"]} pts; {situ}. '
                              + ', '.join(f'{x["nome"]} {x["pts"]}' for x in co['rivais'][1:]) + '.'),
                'torcedor': ('Não dá mais para tropeçar!', f'{situ}. São {co["restantes"]} finais pela frente.')}[tom]
    if t == 'proximo':
        pj = f['pj']
        adv, comp = pj['adversario'], pj['competicao']
        p_v = pj['prob']['casa'] if pj['eu_casa'] else pj['prob']['fora']
        dsp = pj.get('disputa')
        if dsp and not f['continental']:
            if dsp.get('mesma_zona'):
                return {'sensacionalista': (f'JOGO DE SEIS PONTOS CONTRA O {adv.upper()}!', f'Os dois brigam pelo mesmo objetivo: quem perder, sente.'),
                        'analítico': (f'Confronto direto com o {adv}', f'Os dois disputam {ZT.get((dsp["nos"] or dsp["adv"]).get("zona"), ("", "a mesma vaga"))[1]}. {p_v}% de chance de vitória.'),
                        'torcedor': ('É FINAL!', f'Contra o {adv}, rival direto. Não tem amanhã.')}[tom]
            if dsp.get('adv'):
                return {'sensacionalista': (f'O {adv.upper()} VEM DANDO A VIDA!', f'Brigando {ZT.get(dsp["adv"].get("zona"), ("", "", "por algo grande"))[2]}, o adversário não poupa ninguém.'),
                        'analítico': (f'{adv}: adversário em disputa', f'{dsp["adv"]["texto"]}. Força máxima do outro lado; {p_v}% de chance de vitória.'),
                        'torcedor': (f'{adv} desesperado por pontos', 'Vai ser jogo pegado. Precisamos estar ligados.')}[tom]
            return {'sensacionalista': ('NÃO PODE TROPEÇAR!', f'{pj["casa"]} x {pj["fora"]}: cada ponto vale {ZT.get(dsp["nos"].get("zona"), ("", "muito"))[1]}.'),
                    'analítico': (f'Jogo-chave contra o {adv}', f'{dsp["nos"]["texto"]}. {p_v}% de chance de vitória.'),
                    'torcedor': ('Rodada decisiva!', f'Contra o {adv}, é vencer ou vencer.')}[tom]
        if f['continental']:
            return {'sensacionalista': (f'NOITE DE {comp.upper()}: {adv.upper()} PELA FRENTE!', f'{pj["casa"]} x {pj["fora"]}, {pj["data"][2]:02d}/{pj["data"][1]:02d}. A cidade já respira o jogo.'),
                    'analítico': (f'{comp}: o duelo com o {adv}', f'Pelos números, {p_v}% de chance de vitória do {CL["curto"]}. Placar provável: {pj["placar_provavel"]}.'),
                    'torcedor': (f'É dia de {comp}!', f'Contra o {adv}, a torcida promete casa cheia.')}[tom]
        return {'sensacionalista': (f'TESTE DE FOGO CONTRA O {adv.upper()}' if f['grande'] else f'{adv.upper()} NO CAMINHO', f'{pj["casa"]} x {pj["fora"]} pela {comp}.'),
                'analítico': (f'Prévia: {pj["casa"]} x {pj["fora"]}', f'{p_v}% de chance de vitória; forma recente {pj["forma"]["casa"]} x {pj["forma"]["fora"]}.'),
                'torcedor': (f'Próximo desafio: {adv}', f'Enquete: {pj["enquete"]["sim"]}% da torcida acredita na vitória.')}[tom]
    if t == 'disciplina':
        c = f['caso']
        resumo = c['relato'].split('. ')[0] + '.'
        return {'sensacionalista': (c['titulo'].upper() + '!', resumo + (' E não é a primeira vez!' if c.get('reincidente') else '')),
                'analítico': (f'Caso disciplinar: {c["titulo"].lower()}', f'Gravidade {c["gravidade"]}. A decisão do técnico vai medir a autoridade no vestiário.'),
                'torcedor': (c['titulo'], 'A torcida quer compromisso de quem veste a camisa.')}[tom]
    if t == 'eco':
        return {'sensacionalista': (f['manchete'].upper(), f['fina']),
                'analítico': (f['manchete'], f['fina']),
                'torcedor': (f['manchete'], f['fina'])}[tom]
    return (t, '')


def capas(F, hoje, rnd, r=None, car=None):
    out = []
    usadas_principal = set()   # cada jornal abre com um assunto diferente quando dá (a banca não fica repetida)
    for jn in JORNAIS:
        ordem = sorted(F, key=lambda f: -(f['peso'] * jn['pesos'].get(f['tipo'], 1) * (0.45 if (f['tipo'], f.get('sub')) in usadas_principal else 1)
                                          + rnd.random() * 0.8))
        itens, tipos = [], set()
        for f in ordem:
            chave_t = (f['tipo'], f.get('sub'))
            m = _manchete(f, jn['tom'], rnd)
            if not m or chave_t in tipos or any(m[0] == x[0] for x, _ in itens):
                continue
            tipos.add(chave_t)
            itens.append((m, f))
            if len(itens) == 5:
                break
        if not itens:
            itens = [((f'Semana tranquila {CL["em_ct"]}', 'Elenco treina com foco no próximo compromisso.'), {'tipo': 'nada'})]
        usadas_principal.add((itens[0][1]['tipo'], itens[0][1].get('sub')))
        nome_j, slogan = (CL['voz'], CL['voz_slogan']) if jn['id'] == 'voz' else (jn['nome'], jn['slogan'])
        capa = {'id': jn['id'], 'nome': nome_j, 'tom': jn['tom'], 'slogan': slogan, 'data': list(hoje),
                'manchete': itens[0][0][0], 'fina': itens[0][0][1],
                'chamadas': [{'titulo': a, 'texto': b} for (a, b), _ in itens[1:]]}
        if r is not None and car is not None:
            try:   # texto de abertura, aspas de jogador e quadros (jornal_extra.py)
                import jornal_extra
                f0 = itens[0][1]
                capa['texto'] = jornal_extra.texto(f0, r, car) if f0['tipo'] != 'nada' else ''
                a = None
                for _, f in itens:   # a fala do jogador vem do primeiro assunto que tenha alguém para falar
                    a = jornal_extra.aspas(f, r, car, rnd) if f['tipo'] != 'nada' else None
                    if a:
                        a['assunto'] = _manchete(f, jn['tom'], random.Random(0))[0]
                        break
                capa['aspas'] = a
                capa['quadros'] = jornal_extra.quadros(jn['tom'], r, car)
            except Exception as e:  # noqa: BLE001
                print('aviso: corpo do jornal:', type(e).__name__, e)
        out.append(capa)
    try:   # 12/10/2026: nomes de times como título ("Contra o FIORENTINA" -> "Contra a Fiorentina")
        import clube
        nomes = {CL.get('nome'), (r or {}).get('time')}
        pj = (car or {}).get('proximo_jogo') or {}
        nomes |= {pj.get('casa'), pj.get('fora'), pj.get('adversario')}
        nomes |= {t.get('time') for t in ((car or {}).get('liga') or {}).get('classificacao') or []}
        nomes |= {g.get('adversario') for g in (r or {}).get('ultimos') or []}
        nomes |= {f.get('adv') for f in F if isinstance(f.get('adv'), str)}
        out = clube.concordar_tudo(clube.titulo_nomes(out, {n for n in nomes if n}))
    except Exception as e:  # noqa: BLE001
        print('aviso: nomes nas capas:', e)
    return out


# ------------------------------------------------------------------ programa esportivo
def _fala(pessoa, f, rnd):
    t = f['tipo']
    nome = (f.get('j') or f.get('foco') or {}).get('nome', '')
    if pessoa == 'carlao':
        return rnd.choice({
            'resultado': ['Gostei da raça! Time com vontade ganha jogo.', 'Ganhou, mas eu quero ver contra time grande.'],
            'derrota': ['Faltou sangue! No meu tempo, depois de um jogo desses ninguém dormia.', 'Isso aí é falta de cobrança no vestiário.'],
            'conflito': ([f'Salário é contrato assinado! Quem assinou, assinou. O {nome} tem que jogar bola.',
                          'Dinheiro no vestiário é igual pólvora. Uma faísca e explode tudo.']
                         if f.get('sub') == 'Ego salarial' else
                         [f'Vestiário é igual casa: se não tem comando, vira bagunça. Resolve isso com o {nome} já!',
                          f'Eu, no lugar do técnico, chamava o {nome} na sala hoje mesmo.']),
            'baixa': [f'Jogador grande não pode se esconder. O {nome} tem que dar a volta por cima.'],
            'destaque': [f'O {nome} joga de terno! Dá gosto de ver.'],
            'sequencia': ['Fase boa é hora de apertar, não de relaxar.' if f.get('bom') else 'Sequência ruim assim derruba técnico, pode anotar.'],
            'tabela': ['Tabela não mente: tá onde merece.'],
            'pressao': ['Diretoria tem que bancar ou trocar. Meio-termo não existe.'],
            'contrato': [f'Renova com o {nome} amanhã! Jogador desse nível não se acha na esquina.'],
            'mercado': ['Contratação boa é a que resolve. Precisa de reforço, sim.'],
            'apelido': ['Apelido de torcida é o maior título que um jogador pode ter.'],
            'eco': ['Técnico tem que falar menos e ganhar mais.', 'Gostei da postura na coletiva. Tem que ter personalidade.'],
            'liga': ['Esse campeonato está pegando fogo. Quem dormir, fica para trás.', 'Isso aí é futebol de verdade!'],
            'proximo': ['Jogo grande se ganha no vestiário antes de entrar em campo. Quero ver atitude!',
                        'Esse é o tipo de jogo que separa time bom de time campeão.'],
            'disciplina': ['No meu tempo isso era resolvido no vestiário, olho no olho. Tem que punir!',
                           'Jogador profissional não pode dar esse mole. Exemplo vem de cima.'],
            'pre': ['Pré-temporada é onde se ganha o campeonato. Quero ver intensidade.'],
        }.get(t, ['É futebol, meu amigo.']))
    if pessoa == 'helena':
        return rnd.choice({
            'resultado': ['O dado que me chama atenção é a recomposição: o time perdeu a bola e voltou rápido.',
                          'Vitória construída na circulação; o meio-campo achou as linhas de passe.'],
            'derrota': ['Calma, Carlão. O problema é estrutural: espaço entre as linhas e a pressão pós-perda desorganizada.',
                        'Não é só raça. O adversário explorou o corredor que ficou aberto o jogo inteiro.'],
            'conflito': ['A questão tática é secundária aqui. Disputa interna afeta a intensidade nos treinos, e isso aparece em campo.'],
            'baixa': [f'Os números do {nome} caíram junto com a confiança. Uma coisa puxa a outra.'],
            'destaque': [f'O {nome} está ocupando melhor os espaços; não é só fase, é ajuste de função.'],
            'sequencia': ['A regularidade vem do desenho tático, não do acaso.' if f.get('bom') else 'Três jogos não são acaso: tem padrão aí.'],
            'tabela': ['Matematicamente ainda está tudo aberto, mas a margem de erro diminuiu.'],
            'pressao': ['Trocar técnico no meio do processo raramente resolve. Os dados mostram isso.'],
            'contrato': ['Planejamento: renovar agora ou vender pelo valor de mercado. Esperar é o pior cenário.'],
            'mercado': ['Antes de contratar, precisa saber qual função esse jogador vai cumprir no sistema.'],
            'apelido': ['O reconhecimento da torcida costuma vir de regularidade, e os números confirmam isso.'],
            'eco': ['A comunicação do técnico mexe com o vestiário mais do que se imagina.'],
            'liga': ['Os números da rodada mostram uma competição equilibrada, com detalhes decidindo.'],
            'proximo': ['A chave do confronto vai ser a transição: quem recompor mais rápido leva vantagem.',
                        'O retrospecto recente e a força dos elencos apontam um jogo mais apertado do que parece.'],
            'disciplina': ['Caso disciplinar mal resolvido costuma aparecer em campo: queda de intensidade e de concentração.',
                           'O que importa é a coerência: a mesma régua para titular e para reserva.'],
            'pre': ['Vou observar a compactação entre as linhas nos amistosos.'],
        }.get(t, ['Vamos aos números.']))
    return rnd.choice({   # beto: bastidores
        'resultado': ['No vestiário o clima é ótimo, teve até música depois do jogo.'],
        'derrota': ['O técnico conversou em particular com alguns jogadores depois do jogo. Clima pesado.'],
        'conflito': ([f'O estafe do {nome} acha que ele vale mais do que recebe. Vai ter conversa com a diretoria.',
                      f'No CT, o {nome} comentou com colegas sobre a diferença de salários. Pegou mal.']
                     if f.get('sub') == 'Ego salarial' else
                     [f'Apuramos que o {nome} conversou com o empresário essa semana. A situação é real.',
                      f'Fontes do CT dizem que o {nome} chegou calado e saiu calado do treino.']),
        'baixa': [f'Pessoas próximas ao {nome} dizem que ele se sente desvalorizado.'],
        'destaque': [f'O {nome} é o primeiro a chegar e o último a sair do CT. Isso não é por acaso.'],
        'sequencia': ['O grupo está fechado com o técnico.' if f.get('bom') else 'Tem gente cobrando internamente uma reunião.'],
        'tabela': ['A diretoria acompanha a tabela de perto, rodada a rodada.'],
        'pressao': ['Bastidores: o presidente já foi ao CT conversar. Não costuma ser bom sinal.'],
        'contrato': [f'Apuramos que o estafe do {nome} espera uma proposta até o fim do mês.'],
        'mercado': ['Tem dirigente viajando essa semana. Não me perguntem para onde.'],
        'apelido': ['O jogador ficou emocionado com o apelido, me disseram no CT.'],
        'eco': ['No CT, a fala do técnico foi o assunto do almoço.'],
        'liga': ['Nos bastidores dos outros clubes, o assunto é o mesmo: a tabela está apertada.'],
        'proximo': ['A comissão técnica fechou o treino hoje. Tem novidade na escalação, pode apostar.',
                    'O elenco sabe o tamanho desse jogo. O clima no CT mudou nos últimos dias.'],
        'disciplina': ['Apurei que a diretoria já sabe do caso e espera uma resposta firme do técnico.',
                       'O grupo está de olho: todo mundo quer ver se a punição vai ser igual para todos.'],
        'pre': ['O técnico pediu reforços pontuais à diretoria.'],
    }.get(t, ['Sigo apurando.']))


def programa(F, capas_, hoje, rnd):
    top, tipos = [], set()
    for f in sorted(F, key=lambda f: -(f['peso'] + rnd.random() * 0.6)):
        if (f['tipo'], f.get('sub')) not in tipos and len(top) < 3:
            tipos.add((f['tipo'], f.get('sub')))
            top.append(f)
    linhas = [{'quem': PROGRAMA['apresentador'], 'papel': 'apresentador',
               'texto': f'Boa noite! Está no ar o {PROGRAMA["nome"]}. Hoje o assunto é o {CL["nome"]}.'}]
    for f in top:
        man = _manchete(f, 'analítico', rnd)[0]
        texto, chamado = rnd.choice([
            (f'Vamos ao próximo assunto: {man}.', None), (f'A manchete de hoje: {man}. Quem começa?', None),
            (f'{man}. Carlão, você concorda?', 'carlao'), (f'Mudando de assunto: {man}. Helena, o que dizem os números?', 'helena'),
            (f'Beto, você que está no CT todo dia: {man}. O que se fala lá dentro?', 'beto')])
        linhas.append({'quem': PROGRAMA['apresentador'], 'papel': 'apresentador', 'texto': texto})
        ordem = rnd.sample(PROGRAMA['comentaristas'], 3)
        ordem.sort(key=lambda c: c['id'] != chamado)   # quem foi chamado pelo apresentador fala primeiro
        for c in ordem[:2 + (rnd.random() < 0.5)]:
            linhas.append({'quem': c['nome'], 'papel': c['papel'], 'texto': _fala(c['id'], f, rnd)})
    pct = rnd.randint(38, 81)
    pergunta = rnd.choice(['O técnico acertou nas escolhas desta rodada?', 'O elenco atual é suficiente para a meta?',
                           'O vestiário está nas mãos do técnico?'])
    linhas.append({'quem': PROGRAMA['apresentador'], 'papel': 'apresentador',
                   'texto': f'Enquete da torcida: "{pergunta}" — {pct}% disseram SIM. Até a próxima!'})
    return {'nome': PROGRAMA['nome'], 'data': list(hoje), 'linhas': linhas, 'enquete': {'pergunta': pergunta, 'sim': pct}}


# ------------------------------------------------------------------ coletiva
def _todos(J, exceto=()):
    return [chave(j['k']) for j in J if chave(j['k']) not in exceto]


def _pergunta(f, J, rnd, jornal):
    t = f['tipo']
    rep = REPORTERES[jornal]
    if t == 'conflito' or t == 'baixa':
        if t == 'conflito':
            a = f['env'][1] if f['sub'] == 'Ego salarial' else f['env'][0]   # ego: o foco é quem ganha menos
        else:
            a = f['j']
        ka = chave(a['k'])
        idolo = a['status'] in ('Lenda', 'Ídolo')
        hid = f.get('hid')
        if t == 'conflito' and f['sub'] == 'Braçadeira':
            cap = f['env'][1]
            texto = f'{a["nome"]} estaria incomodado por não ser o capitão. A braçadeira de {cap["nome"]} está garantida?'
            return {'texto': texto, 'alvo': a['nome'], 'opcoes': [
                {'texto': f'{cap["nome"]} é o meu capitão, e {a["nome"]} é um líder sem precisar de faixa.',
                 'efeitos': [{'k': chave(cap['k']), 'delta': 4, 'rodadas': 2, 'motivo': 'foi bancado como capitão na coletiva'},
                             {'k': ka, 'delta': 2, 'rodadas': 2, 'motivo': 'foi elogiado como líder na coletiva'}] +
                            ([{'historia': hid, 'restam': -1}] if hid else []),
                 'eco': ('Técnico banca capitão e afaga ' + a['nome'], 'Na coletiva, o treinador evitou criar vencedores e perdedores.')},
                {'texto': 'A braçadeira é reavaliada sempre. Ninguém tem cadeira cativa.',
                 'efeitos': [{'k': chave(cap['k']), 'delta': -5, 'rodadas': 3, 'motivo': 'teve a braçadeira questionada em público'},
                             {'k': ka, 'delta': 3, 'rodadas': 2, 'motivo': 'técnico abriu a disputa pela braçadeira'}] +
                            ([{'historia': hid, 'restam': 1}] if hid else []),
                 'eco': ('Técnico abre disputa pela braçadeira', f'{cap["nome"]} sai enfraquecido; {a["nome"]} ganha força no vestiário.')},
                {'texto': 'Assunto interno. Não vou falar de vestiário aqui.',
                 'efeitos': [],
                 'eco': ('Técnico foge do tema braçadeira', 'O silêncio só alimentou as especulações.')},
            ]}
        if t == 'conflito' and f['sub'] == 'Ego salarial':
            caro = f['env'][0]
            return {'texto': f'{a["nome"]} estaria incomodado por ganhar menos que {caro["nome"]}. Como você lida com isso?',
                    'alvo': 'folha salarial', 'opcoes': [
                {'texto': f'{a["nome"]} merece ser valorizado. Vou levar o assunto à diretoria.',
                 'efeitos': [{'k': ka, 'delta': 5, 'rodadas': 3, 'motivo': 'o técnico prometeu defender o salário dele'},
                             {'k': chave(caro['k']), 'delta': -2, 'rodadas': 2, 'motivo': 'virou o assunto da folha salarial'}] +
                            ([{'historia': hid, 'restam': -1}] if hid else []),
                 'eco': (f'Técnico compra a briga salarial de {a["nome"]}', 'Agora a bola está com a diretoria.')},
                {'texto': 'Salário é assunto do clube. Aqui dentro, quem decide é o desempenho.',
                 'efeitos': [{'k': ka, 'delta': -3, 'rodadas': 2, 'motivo': 'o técnico ignorou a queixa salarial'}],
                 'eco': ('"Quem decide é o desempenho"', f'Resposta seca do técnico não agradou o estafe de {a["nome"]}.')},
                {'texto': 'Não falo de contratos em público.',
                 'efeitos': [],
                 'eco': ('Técnico não comenta folha salarial', 'O assunto segue rendendo nos bastidores.')},
            ]}
        texto = rnd.choice([f'{a["nome"]} parece insatisfeito. O que está acontecendo?',
                            f'Há relatos de que {a["nome"]} pode pedir para sair. Ele tem futuro aqui?'])
        return {'texto': texto, 'alvo': a['nome'], 'opcoes': [
            {'texto': f'{a["nome"]} é fundamental para nós. Confio totalmente nele.',
             'efeitos': [{'k': ka, 'delta': 6, 'rodadas': 2, 'motivo': 'foi defendido pelo técnico na coletiva'}] +
                        ([{'historia': hid, 'restam': -1}] if hid else []),
             'eco': (f'Técnico blinda {a["nome"]}', 'Discurso de confiança acalma, por ora, a situação.')},
            {'texto': f'Quem quiser jogar tem que mostrar no treino. Vale para {a["nome"]} também.',
             'efeitos': [{'k': ka, 'delta': -5, 'rodadas': 3, 'motivo': 'foi cobrado publicamente na coletiva'}] +
                        [{'k': '*', 'delta': -1 if idolo else 1, 'rodadas': 1,
                          'motivo': 'o grupo não gostou da exposição de um ídolo' if idolo else 'o grupo viu pulso firme do técnico'}] +
                        ([{'historia': hid, 'restam': 1}] if hid else []),
             'eco': (f'Técnico cobra {a["nome"]} em público', 'A declaração repercutiu no vestiário' + (' e irritou parte do grupo.' if idolo else '.'))},
            {'texto': 'Isso a gente resolve dentro de casa.',
             'efeitos': [],
             'eco': (f'Silêncio sobre {a["nome"]}', 'O técnico não quis comentar; a imprensa segue especulando.')},
        ]}
    if t == 'proximo':
        pj = f['pj']
        adv = pj['adversario']
        return {'texto': rnd.choice([f'Como você enxerga o jogo contra o {adv}?',
                                     f'O {adv} vem aí pela {pj["competicao"]}. O time está pronto?',
                                     f'O que esperar do confronto com o {adv}?']), 'alvo': f'proximo|{adv}', 'opcoes': [
            {'texto': 'Vamos para vencer. Respeito, mas nenhum medo.',
             'efeitos': [{'k': '*', 'delta': 2, 'rodadas': 1, 'motivo': 'o técnico passou confiança antes do jogo grande'}],
             'eco': (f'"Vamos para vencer o {adv}"', 'Técnico transmite confiança antes do confronto.')},
            {'texto': f'O {adv} é muito forte. Precisamos de um jogo perfeito.',
             'efeitos': [{'k': '*', 'delta': -1, 'rodadas': 1, 'motivo': 'o técnico tratou o adversário como favorito'}],
             'eco': (f'Técnico exalta o {adv}', 'Discurso cauteloso divide a torcida.')},
            {'texto': f'Eles é que deveriam se preocupar com a gente.',
             'efeitos': [{'k': '*', 'delta': 3, 'rodadas': 1, 'motivo': 'o técnico provocou o adversário e inflamou o grupo'}],
             'eco': (f'Técnico provoca o {adv}', 'Declaração ousada esquenta o jogo. Agora tem que ganhar.')},
        ]}
    if t == 'disciplina' and f.get('j'):
        c, j = f['caso'], f['j']
        kj = chave(j['k'])
        serio = c['gravidade'] != 'leve'
        return {'texto': f'{c["titulo"]}. Haverá punição?', 'alvo': j['nome'], 'opcoes': [
            {'texto': 'Já conversamos. O assunto está resolvido.',
             'efeitos': [{'k': kj, 'delta': 2, 'rodadas': 1, 'motivo': 'o técnico o protegeu na coletiva'}] +
                        ([{'k': '*', 'delta': -1, 'rodadas': 1, 'motivo': 'o técnico minimizou um caso sério em público'}] if serio else []),
             'eco': (f'Técnico minimiza caso de {j["nome"]}', 'Discurso de "assunto resolvido" não convenceu todo mundo.')},
            {'texto': 'Ninguém está acima do grupo. Vai haver consequência.',
             'efeitos': [{'k': kj, 'delta': -3, 'rodadas': 2, 'motivo': 'foi exposto pelo técnico na coletiva'},
                         {'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'o técnico prometeu a mesma régua para todos'}],
             'eco': ('"Ninguém está acima do grupo"', f'Técnico promete punição no caso {j["nome"]}.')},
            {'texto': 'Não falo de disciplina em público.',
             'efeitos': [],
             'eco': (f'Silêncio sobre o caso {j["nome"]}', 'O técnico não quis comentar.')},
        ]}
    if t == 'derrota' or (t == 'sequencia' and not f.get('bom')):
        return {'texto': rnd.choice(['O resultado foi ruim. De quem é a responsabilidade?',
                                     'A torcida está impaciente. O que falta para o time reagir?']), 'alvo': 'elenco', 'opcoes': [
            {'texto': 'A responsabilidade é minha. O grupo tem todo o meu apoio.',
             'efeitos': [{'k': '*', 'delta': 2, 'rodadas': 1, 'motivo': 'o técnico assumiu a culpa na coletiva'}],
             'eco': ('Técnico assume a culpa e protege o elenco', 'Jogadores aprovaram a postura nos bastidores.')},
            {'texto': 'Alguns jogadores não estão no nível que o clube exige.',
             'efeitos': [{'k': '*', 'delta': -3, 'rodadas': 1, 'motivo': 'o técnico cobrou o elenco em público'}],
             'eco': ('Técnico detona o elenco', 'Declaração caiu mal no vestiário.')},
            {'texto': 'Calendário pesado e arbitragem complicada. Mas vamos reagir.',
             'efeitos': [],
             'eco': ('Técnico reclama de calendário e arbitragem', 'Crítica externa não convenceu a imprensa.')},
        ]}
    if t in ('destaque', 'resultado'):
        j = f.get('j') or (f['melhor'][0] if f.get('melhor') else None)
        if not j:
            return None
        kj = chave(j['k'])
        rivais = [chave(o['k']) for o in J if o['pos'] == j['pos'] and o is not j]
        return {'texto': rnd.choice([f'{j["nome"]} vive grande fase. Ele é o melhor do elenco hoje?',
                                     f'Como explicar o momento de {j["nome"]}?']), 'alvo': j['nome'], 'opcoes': [
            {'texto': f'{j["nome"]} é diferenciado. O time joga em função dele.',
             'efeitos': [{'k': kj, 'delta': 4, 'rodadas': 2, 'motivo': 'foi exaltado pelo técnico na coletiva'}] +
                        [{'k': k, 'delta': -2, 'rodadas': 1, 'motivo': f'ouviu o técnico exaltar {j["nome"]}, rival de posição'} for k in rivais],
             'eco': (f'Técnico exalta {j["nome"]}', 'Concorrentes de posição não gostaram.' if rivais else 'Elogio público fortalece o jogador.')},
            {'texto': 'O mérito é do grupo. Ninguém ganha nada sozinho.',
             'efeitos': [{'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'o técnico valorizou o grupo na coletiva'}],
             'eco': ('"O mérito é do grupo"', 'Discurso coletivo agrada o vestiário.')},
        ]}
    if t == 'contrato':
        j, kj = f['j'], chave(f['j']['k'])
        return {'texto': f'O contrato de {j["nome"]} termina em {f["meses"]} meses. Ele renova?', 'alvo': j['nome'], 'opcoes': [
            {'texto': f'Quero {j["nome"]} aqui por muitos anos. Vou pedir a renovação à diretoria.',
             'efeitos': [{'k': kj, 'delta': 5, 'rodadas': 3, 'motivo': 'o técnico pediu a renovação dele em público'}],
             'eco': (f'Técnico pede renovação de {j["nome"]}', 'Agora a pressão está na diretoria.')},
            {'texto': 'Vamos conversar no momento certo.',
             'efeitos': [{'k': kj, 'delta': -3, 'rodadas': 2, 'motivo': 'o técnico não garantiu a renovação'}],
             'eco': (f'Futuro de {j["nome"]} segue indefinido', 'O técnico evitou garantir a renovação.')},
        ]}
    if t == 'pressao':
        return {'texto': 'A diretoria está insatisfeita. Você teme pelo seu cargo?', 'alvo': 'técnico', 'opcoes': [
            {'texto': 'Tenho contrato e confiança no meu trabalho. O grupo está comigo.',
             'efeitos': [{'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'o técnico mostrou segurança na coletiva'}],
             'eco': ('Técnico garante: "o grupo está comigo"', 'Resposta firme diante da pressão.')},
            {'texto': 'Se os resultados não vierem, sou o primeiro a sair.',
             'efeitos': [{'k': '*', 'delta': -1, 'rodadas': 1, 'motivo': 'o técnico admitiu que pode sair'}],
             'eco': ('Técnico admite que pode cair', 'Fala aumenta a pressão sobre o elenco.')},
        ]}
    return None


def _tema(f, p):
    """Assunto da pergunta, para não repetir a mesma pauta rodada após rodada."""
    t = f['tipo']
    if t == 'conflito':
        return f'conflito|{f["sub"]}|{p["alvo"]}'
    if t in ('derrota', 'sequencia', 'resultado'):
        return None                     # resultado é sempre notícia nova
    return f'{t}|{p["alvo"]}'


def montar_coletiva(perguntas, hoje, rnd, ident=None):
    """Coletiva no formato da Central a partir de perguntas {texto, alvo, opcoes} (coletiva_cenarios.gerar)."""
    out = []
    for i, p in enumerate(perguntas, 1):
        jornal = rnd.choice([j['id'] for j in JORNAIS])
        out.append({'id': f'p{i}', 'jornal': jornal,
                    'jornal_nome': CL['voz'] if jornal == 'voz' else next(x['nome'] for x in JORNAIS if x['id'] == jornal),
                    'reporter': REPORTERES[jornal], 'texto': p['texto'], 'alvo': p['alvo'], 'cenario': p.get('cenario'),
                    'opcoes': [{'id': str(n + 1), **o} for n, o in enumerate(p['opcoes'])]})
    if not out:
        return None
    return {'id': ident or f'col|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}', 'data': list(hoje), 'perguntas': out}


def coletiva_contexto(r, car, hoje, rnd):
    """11/10/2026: 55 cenários ligados ao jogo (clássico, placar, súmula, tabela, vestiário, legado). None = sem contexto."""
    try:
        import coletiva_cenarios as cc
        ps = cc.gerar(cc.contexto_reuniao(r, car, hoje), n=3)
    except Exception as e:  # noqa: BLE001
        print('aviso: cenários de coletiva:', e)
        return None
    return montar_coletiva(ps, hoje, rnd) if len(ps) >= 2 else None


def coletiva(F, J, hoje, rnd, car=None):
    from vestiario import dias
    temas = (car or {}).setdefault('coletiva_temas', {})
    perguntas = []
    usados = set()
    # jogo grande no horizonte (Champions, Libertadores, topo da tabela): a imprensa sempre pergunta dele primeiro
    for f in sorted(F, key=lambda f: -(f['peso'] + (5 if f['tipo'] == 'proximo' and f.get('grande') else 0) + rnd.random() * 0.5)):
        if len(perguntas) >= 3:
            break
        jornal = rnd.choice([j['id'] for j in JORNAIS])
        p = _pergunta(f, J, rnd, jornal)
        if not p or p['alvo'] in usados:
            continue
        tema = _tema(f, p)
        if tema and tema in temas and dias(tuple(hoje), tuple(temas[tema])) < 35:
            continue                    # mesmo assunto há menos de 5 semanas: a imprensa muda de pauta
        if tema:
            temas[tema] = list(hoje)
        usados.add(p['alvo'])
        i = len(perguntas) + 1
        perguntas.append({'id': f'p{i}', 'jornal': jornal,
                          'jornal_nome': CL['voz'] if jornal == 'voz' else next(x['nome'] for x in JORNAIS if x['id'] == jornal),
                          'reporter': REPORTERES[jornal], **p,
                          'opcoes': [{'id': str(n + 1), **o} for n, o in enumerate(p['opcoes'])]})
    if not perguntas:
        return None
    return {'id': f'col|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}', 'data': list(hoje), 'perguntas': perguntas}


# ------------------------------------------------------------------ edição da rodada
def edicao(car, r, hoje, apelido_novo=None, ecos=()):
    rnd = random.Random(f'midia|{hoje}')
    F = fatos(r, car, hoje, apelido_novo, ecos)
    cp = capas(F, hoje, rnd, r, car)
    ed = {'data': list(hoje), 'capas': cp, 'programa': programa(F, cp, hoje, rnd),
          'coletiva': coletiva_contexto(r, car, hoje, rnd) or coletiva(F, r['J'], hoje, rnd, car),
          'jogo_coberto': list(r['ultimos'][-1]['data']) if r.get('ultimos') else (car.get('midia') or {}).get('jogo_coberto')}
    ed['duelo'] = (car.get('proximo_jogo') or {}).get('duelo')   # a análise do 4 x 4 também passa pelo redator
    ed['tatica'] = (car.get('proximo_jogo') or {}).get('tatica')
    try:   # redator com IA (opcional, cerebro/ia.json): só reescreve os textos, nunca os efeitos
        import redator
        contexto = '; '.join(f.get('tipo', '') for f in F[:8])
        redator.reescrever(ed, CL.get('nome', ''), contexto)
    except Exception as e:  # noqa: BLE001
        print('aviso: redator IA indisponível:', e)
    ed.pop('duelo', None)
    ed.pop('tatica', None)
    try:   # a coletiva deste jogo já aconteceu ao vivo (Central, pelo pulso)? então é ela (mesmo id, mesmas respostas)
        import coletiva_viva
        viva = coletiva_viva.ler((car.get('ck') or '|').split('|')[0])
        if viva and r.get('ultimos') and viva.get('jogo') == list(r['ultimos'][-1]['data']):
            ed['coletiva'] = viva
    except Exception as e:  # noqa: BLE001
        print('aviso: coletiva ao vivo não reaproveitada:', e)
    car['midia'] = ed
    hist = car.setdefault('midia_hist', [])
    hist.append({'data': list(hoje), 'capas': cp, 'programa': ed['programa']})
    car['midia_hist'] = hist[-8:]
    return ed
