# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""50 CENÁRIOS DE COLETIVA (11/10/2026), ligados ao jogo e ao momento. Substituem as perguntas genéricas.

Cada cenário só aparece quando o contexto sustenta (resultado, placar, CLÁSSICO, súmula do jogo, tabela, sequência,
próximo jogo, vestiário, mercado, carreira/legado). Três respostas com tons diferentes (diplomático, ousado/provocador,
firme/cobrança) e efeitos próprios na moral (mesmo formato de midia._pergunta: efeitos {'k': 'reg:id' | '*', 'delta',
'rodadas', 'motivo'}, eco = manchete do dia seguinte). O contexto vem da reunião (contexto_reuniao) ou do pulso ao
vivo (contexto_vivo, coletiva no dia do jogo).
"""
import random

import classicos

ESTRELAS = ('Lenda', 'Ídolo', 'Superastro', 'Craque')


def E(k, d, rod, motivo):
    return {'k': k, 'delta': d, 'rodadas': rod, 'motivo': motivo}


def G(d, motivo, rod=1):
    return {'k': '*', 'delta': d, 'rodadas': rod, 'motivo': motivo}


def op(texto, efeitos, titulo, fina):
    return {'texto': texto, 'efeitos': efeitos, 'eco': (titulo, fina)}


def _kc(k):
    return f'{k[0]}:{k[1]}'


# ---------------------------------------------------------------- contexto
def _jog(j):
    k = j['k'] if 'k' in j else (j['reg'], j['pid'])
    tp = j.get('temporada') or {}
    return {'k': k, 'kc': _kc(k), 'nome': j['nome'], 'pos': j['pos'], 'idade': j.get('idade') or 25, 'status': j.get('status', 'Elenco'),
            'moral': j.get('moral', 60), 't_jogos': j.get('t_jogos', tp.get('jogos', 0)), 't_gols': j.get('t_gols', tp.get('gols', 0)),
            't_nota': j.get('t_nota', tp.get('nota', 0)), 'r_nota': j.get('r_nota', 0), 'condicao': j.get('condicao'),
            't_assist': j.get('t_assist', tp.get('assist', 0)), 'ovr': j.get('ovr', j.get('nota', 0)),
            'contrato': tuple(j['contrato']) if j.get('contrato') else (tuple(j['contrato_fim']) if j.get('contrato_fim') else None),
            'capitao': bool(j.get('capitao')), 'perfil': j.get('perfil')}


def _base(nos, ck, hoje, J, g, linhas, ultimos, tab, conf, prox, casos, conflitos=(), hist=None):
    adv = g['adversario'].strip()
    porK = {j['k']: j for j in J}
    ls = []
    for x in linhas or []:
        j = porK.get((x['reg'], x['pid']))
        if j and x.get('minutos', x.get('min', 0)) > 0:
            ls.append({**j, 'gols': x['gols'], 'assist': x['assist'], 'nota': x['nota'] or 0,
                       'min': x.get('minutos', x.get('min', 0)), 'titular': x.get('titular')})
    eu = next((t for t in tab or [] if t.get('eu')), None)
    if prox:
        prox['classico'] = classicos.nome(nos, prox['adv'])
    tab = tab or []
    total = 2 * (len(tab) - 1) if tab else 0
    liga_fim = bool(tab) and all(t['j'] >= total for t in tab)
    try:
        import marcos
        tl = marcos.titulo_liga(tab)
    except Exception:  # noqa: BLE001
        tl = None
    return {'liga_fim': liga_fim, 'titulo_ok': bool(tl and tl['garantido']), 'nos': nos, 'ck': ck, 'hoje': tuple(hoje), 'J': J,
            'adv': adv, 'casa': g['casa'], 'gp': g['pro'], 'gc': g['contra'],
            'res': 'V' if g['pro'] > g['contra'] else 'E' if g['pro'] == g['contra'] else 'D',
            'classico': classicos.nome(nos, adv), 'linhas': ls, 'ultimos': ultimos or [], 'tab': tab or [], 'eu': eu,
            'conf': conf, 'prox': prox, 'casos': casos or [], 'conflitos': list(conflitos), 'hist': hist or [],
            'comp': g.get('comp') or ''}


def _tie(todas, ti, p):
    """Confronto de ida e volta decidido neste jogo (viradas.py), ou None."""
    try:
        import viradas
        v = viradas.do_time(todas, ti, tuple(p['data']), dias=0)
        return v if v and v['num_volta'] == p.get('num') else None
    except Exception:  # noqa: BLE001
        return None


def _contexto_extra(X, fonte):
    """12/10/2026: o que os cenários novos (coletiva_extra.py) usam — lesão, volta, corrida, a IA adversária (o plano
    do adversário do último e do próximo jogo) e as capas do dia."""
    import json
    import os
    X['lesao'] = fonte.get('lesao_ultima') or fonte.get('lesao')
    X['lesao_volta'] = fonte.get('lesao_volta')
    X['corrida'] = fonte.get('corrida')
    X['pj_disputa'] = (fonte.get('proximo_jogo') or {}).get('disputa')
    X['capas'] = ((fonte.get('midia') or {}).get('capas')) or []
    X['momento'] = fonte.get('momento')
    X['analise'] = fonte.get('analise_porques') or []
    X['mundo'] = fonte.get('mundo') or {}
    try:
        arq = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico', 'ia_adversaria.json')
        reg = json.load(open(arq, encoding='utf-8')).get('registro') or []
    except (OSError, ValueError):
        reg = []
    up = lambda s: (s or '').strip().upper()
    X['ia_ult'] = next((x for x in reversed(reg) if up(x.get('adversario')) == up(X.get('adv'))
                        and abs(_dias(X['hoje'], tuple(x.get('data') or X['hoje']))) <= 3), None)
    p = X.get('prox') or {}
    X['ia_prox'] = next((x for x in reversed(reg) if p and up(x.get('adversario')) == up(p.get('adv'))
                         and tuple(x.get('data') or ()) == tuple(p.get('data') or ())), None)
    return X


def contexto_reuniao(r, car, hoje):
    X = _contexto_reuniao(r, car, hoje)
    if X:
        X['movimentos'] = r.get('movimentos') or []
        X['fifa'] = car.get('data_fifa')
        X['rumores'] = [x for x in car.get('rumores') or [] if x.get('ativo')]
        X['vit'] = car.get('vitoriosos') or {}
        _contexto_extra(X, car)
    if X and r.get('jogos'):
        X['tie'] = _tie(r.get('todas_partidas') or [], r['ti'], r['jogos'][-1])
        try:
            import marcos
            X['final'] = marcos.eh_final(r['jogos'][-1], (r.get('todas_partidas') or []) + (r.get('agenda') or []))
        except Exception:  # noqa: BLE001
            X['final'] = False
    return X


def _contexto_reuniao(r, car, hoje):
    if not r.get('ultimos'):
        return None
    J = [_jog(j) for j in r['J']]
    jogo = r['jogos'][-1] if r.get('jogos') else None
    g = dict(r['ultimos'][-1])
    linhas = (jogo['linhas1'] if jogo['time1'] == r['ti'] else jogo['linhas2']) if jogo and tuple(jogo['data']) == tuple(g['data']) else []
    if jogo:
        from proximo_jogo import nome_comp
        g['comp'] = nome_comp(jogo['comp'])
    hist = [(p['linhas1'] if p['time1'] == r['ti'] else p['linhas2']) for p in (r.get('jogos') or [])[-8:]]
    pj = car.get('proximo_jogo') or {}
    prox = {'adv': pj['adversario'], 'comp': pj['competicao'], 'data': tuple(pj['data']), 'final': pj.get('final')} if pj.get('adversario') else None
    conflitos = [(t, txt, [_jog(x) for x in env]) for t, txt, env in r.get('conflitos') or []]
    return _base(r['time'], car.get('ck'), hoje, J, g, linhas, r.get('ultimos'), (car.get('liga') or {}).get('classificacao'),
                 (car.get('diretoria') or {}).get('confianca'), prox, car.get('casos'), conflitos, hist)


def contexto_vivo(dados, p):
    if not p or not p.get('ultimos_jogos'):
        return None
    from proximo_jogo import nome_comp
    J = [_jog(j) for j in dados.get('jogadores') or []]
    g = dict(p['ultimos_jogos'][-1])
    uj = p.get('ultimo_jogo') or {}
    g['comp'] = nome_comp(uj['comp']) if uj.get('comp') is not None else ''
    pr = p.get('proximo')
    prox = None
    if pr:
        adv = pr['fora'] if pr['casa'] == dados.get('time') else pr['casa']
        prox = {'adv': adv, 'comp': nome_comp(pr['comp']), 'data': tuple(pr['data']), 'final': pr.get('final')}
    X = _base(dados.get('time') or '', dados.get('carreira'), g['data'], J, g, uj.get('linhas'), p.get('ultimos_jogos'),
              p.get('classificacao') or (dados.get('liga') or {}).get('classificacao'),
              (dados.get('diretoria') or {}).get('confianca'), prox, dados.get('casos'))
    X['final'] = bool(uj.get('final'))
    X['movimentos'] = [dict(m, k=tuple(m['k'])) for m in dados.get('movimentos') or []]
    X['fifa'] = dados.get('data_fifa')
    X['rumores'] = [x for x in dados.get('rumores') or [] if x.get('ativo')]
    X['vit'] = dados.get('vitoriosos') or {}
    _contexto_extra(X, dados)
    ida = uj.get('ida')
    if ida and uj.get('num') is not None:   # mata-mata: o pulso manda o jogo de ida junto
        atual = {k: uj[k] for k in ('time1', 'time2', 'gols1', 'gols2', 'comp', 'flag', 'num')}
        atual['data'] = tuple(uj['data'])
        X['tie'] = _tie([dict(ida, data=tuple(ida['data']), num=None), atual], dados.get('ti'), atual)
    return X


def _dias(a, b):
    import datetime as dt
    return (dt.date(*a) - dt.date(*b)).days


def _seq(X):
    res = ['V' if g['pro'] > g['contra'] else 'E' if g['pro'] == g['contra'] else 'D' for g in X['ultimos']]
    def conta(ok):
        n = 0
        for x in reversed(res):
            if not ok(x):
                break
            n += 1
        return n
    return {'v': conta(lambda x: x == 'V'), 'inv': conta(lambda x: x != 'D'), 'sv': conta(lambda x: x != 'V'),
            'd': conta(lambda x: x == 'D'), 'res': res}


def _perfil(X, j):
    try:
        import legado
        return legado.perfil(X['ck'], j['k'], j['nome'])
    except Exception:  # noqa: BLE001
        return None


def _peso(j):
    return (j.get('nota') or 5.5) + 0.6 * j.get('gols', 0) + 0.3 * j.get('assist', 0)


def _rivais(X, j):
    return [o['kc'] for o in X['J'] if o['pos'] == j['pos'] and o['kc'] != j['kc']]


# ---------------------------------------------------------------- os cenários
CENARIOS = []


def cen(fn):
    CENARIOS.append(fn)
    return fn


# ----- clássico
@cen
def vitoria_classico(X, rnd):
    if not X['classico'] or X['res'] != 'V':
        return None
    c, adv = X['classico'], X['adv']
    return 9.5, 'classico', rnd.choice([f'Vencer o {c} tem um sabor diferente?', f'Depois desse {c}, quem manda na rivalidade?']), [
        op('Clássico é para a torcida. Essa vitória é deles, que empurraram do primeiro ao último minuto.',
           [G(3, f'vitória no {c} dedicada à torcida', 2)], f'"Essa é da torcida": o {c} é nosso', 'Técnico divide a festa com a arquibancada.'),
        op(f'Hoje essa rivalidade tem dono. O {adv} vai ter que ouvir isso por um bom tempo.',
           [G(4, 'o técnico provocou o rival depois do clássico', 2)], f'Técnico provoca o {adv}: "a rivalidade tem dono"',
           'A declaração incendeia a rivalidade; o próximo encontro promete.'),
        op('Respeito o adversário. Foram só três pontos, e o campeonato é longo.',
           [G(1, 'o técnico manteve o grupo com os pés no chão')], 'Técnico esfria a euforia após o clássico', 'Discurso sóbrio agrada a diretoria.')]


@cen
def derrota_classico(X, rnd):
    if not X['classico'] or X['res'] != 'D':
        return None
    c = X['classico']
    return 10, 'classico', rnd.choice([f'Perder o {c} dói mais. O que dizer para a torcida?', f'A torcida não aceita perder o {c}. Quem responde por isso?']), [
        op('A responsabilidade é minha. Peço desculpas à torcida; clássico não se perde assim.',
           [G(2, 'o técnico assumiu a derrota no clássico')], f'Técnico pede desculpas após o {c}', 'Postura de líder: chamou a culpa para si.'),
        op('Faltou vontade de alguns. Clássico se ganha com sangue, e hoje teve gente que não entendeu.',
           [G(-4, 'o técnico cobrou o elenco em público após o clássico', 2)], f'Técnico detona o elenco após perder o {c}',
           'Cobrança pública divide o vestiário.'),
        op('A arbitragem pesou num jogo de detalhes. Mas vamos dar a resposta em campo.',
           [], f'Técnico reclama da arbitragem no {c}', 'A desculpa não convenceu a torcida.')]


@cen
def empate_classico(X, rnd):
    if not X['classico'] or X['res'] != 'E':
        return None
    c = X['classico']
    return 8, 'classico', f'Empate no {c}: resultado justo?', [
        op('Num clássico, ninguém se entrega. Empate justo, e o grupo mostrou caráter.',
           [G(1, 'o técnico valorizou a entrega no clássico')], f'"Ninguém se entregou": técnico aprova empate no {c}', 'Discurso equilibrado.'),
        op('Merecíamos vencer. Fomos superiores e saio com sabor de derrota.',
           [G(1, 'o técnico disse que o time foi superior no clássico')], f'Técnico: "merecíamos vencer o {c}"', 'A torcida concorda; o rival rebate.'),
        op('Clássico empatado em casa é ruim. Precisamos de mais coragem.' if X['casa'] else 'Empate fora no clássico é um bom resultado.',
           [G(-1, 'o técnico cobrou coragem no clássico')] if X['casa'] else [G(1, 'o técnico comemorou o ponto fora no clássico')],
           'Técnico cobra coragem após o clássico' if X['casa'] else 'Técnico comemora ponto no clássico', 'A leitura do técnico repercute.')]


@cen
def proximo_classico(X, rnd):
    p = X['prox']
    if not p or not p.get('classico'):
        return None
    c, adv = p['classico'], p['adv']
    return 9, 'proximo', rnd.choice([f'Vem aí o {c}. Algum recado para o {adv}?', f'A semana é de {c}. O vestiário já está no clima?']), [
        op(f'Respeito muito o {adv}. Clássico é diferente: vence quem errar menos.',
           [G(1, 'o técnico preparou o clássico com equilíbrio')], f'Técnico respeita o {adv} antes do {c}', 'Discurso cauteloso antes do clássico.'),
        op(f'O recado é simples: o {adv} vai sentir o peso da nossa camisa.',
           [G(3, 'o técnico inflamou o grupo para o clássico', 2)], f'Técnico manda recado: "vão sentir o peso da camisa"',
           f'Provocação esquenta o {c}. Agora tem que ganhar.'),
        op('Clássico se joga, não se fala. Quem quiser recado, assiste ao jogo.',
           [G(2, 'o técnico blindou o grupo antes do clássico')], 'Técnico mistério antes do clássico', 'Treinos fechados e boca fechada.')]


# ----- saídas e chegadas do elenco (saidas.py)
@cen
def saida_estrela(X, rnd):
    movs = [m for m in X.get('movimentos') or [] if m['tipo'] == 'saida']
    if not movs:
        return None
    try:
        import saidas
        m = saidas.principal(movs, X['J'], X['ck'], X['nos'])[0] or movs[0]
    except Exception:  # noqa: BLE001
        m = movs[0]
    est = next((j for j in X['J'] if j['k'] == tuple(m['k'])), None) or (dict(m['prev'], k=tuple(m['k'])) if m.get('prev') else None)
    import saidas
    dest = f'{saidas.art(m["clube"])} {m["clube"]}'
    estrela = est and est['status'] in ESTRELAS
    lenda = None
    try:   # 12/10/2026: a "sombra" é a MESMA da imprensa (saidas.narrativa): só um astro do mesmo setor do campo
        n = saidas.narrativa(m, X['J'], X['ck'], X['nos'])
        if n.get('tipo') == 'sombra' and n.get('sombra'):
            lenda = {'nome': n['sombra']}
    except Exception:  # noqa: BLE001
        pass
    texto = rnd.choice([f'{m["nome"]} está de saída para {dest}. Ele saiu para fugir da sombra de {lenda["nome"]}?' if estrela and lenda else
                        f'{m["nome"]} vai jogar {"na" if saidas.art(m["clube"]) == "a" else "no"} {m["clube"]}. Como fica o time sem ele?',
                        f'Como o grupo recebeu a saída de {m["nome"]}?'])
    return (11 if estrela else 6), m['nome'], texto, [
        op(f'Desejo toda a sorte do mundo ao {m["nome"]}. Fez história aqui e sai pela porta da frente.',
           [G(1, f'o técnico respeitou a saída de {m["nome"]}')], f'Técnico deseja sorte a {m["nome"]}', 'Despedida elegante.'),
        op('Aqui ninguém é maior que o clube. Quem quiser sair, a porta está aberta.',
           [G(2, 'o técnico disse que ninguém é maior que o clube', 2)], '"Ninguém é maior que o clube"', 'Recado duro para quem pensa em sair.'),
        op(f'Eu queria que ele ficasse. A decisão não foi minha.',
           [G(-1, 'o técnico deixou claro que não queria a saída')], 'Técnico lamenta saída e expõe a diretoria', 'Clima tenso com a cúpula.')]


@cen
def chegada_reforco(X, rnd):
    movs = [m for m in X.get('movimentos') or [] if m['tipo'] == 'chegada']
    if not movs:
        return None
    m = max(movs, key=lambda m: m['valor'])
    return 6, m['nome'], f'{m["nome"]} chegou. Ele chega para ser titular?', [
        op('Chega para somar. Aqui quem joga é quem treina melhor.', [G(1, 'o técnico manteve a disputa aberta')], 'Reforço vai ter que brigar', 'Disputa saudável.'),
        op('Sim. É um jogador para o time titular.', [G(-1, 'o técnico deu a vaga ao reforço antes do treino')], 'Reforço chega titular', 'Concorrentes de posição não gostaram.'),
        op('Ele vai ter o tempo dele de adaptação.', [], 'Técnico pede paciência com o reforço', 'Sem pressa.')]


# ----- finais e título (marcos.py)
@cen
def proximo_final(X, rnd):
    p = X['prox']
    if not p or not p.get('final'):
        return None
    return 13, 'final', rnd.choice([f'É a final da {p["comp"]} contra o {p["adv"]}. Como o grupo chega?', f'Falta um jogo para a taça da {p["comp"]}. O que você vai dizer no vestiário?']), [
        op('Final se ganha com cabeça. Vamos respeitar o adversário e jogar o nosso jogo.', [G(2, 'o técnico passou serenidade antes da final')],
           'Técnico pede cabeça fria na final', 'Serenidade antes do jogo do ano.'),
        op('Esse grupo nasceu para ganhar finais. A taça vem para casa.', [G(4, 'o técnico garantiu o título antes da final', 2)],
           '"A taça vem para casa"', 'Promessa ousada: agora não tem volta.'),
        op(f'O {p["adv"]} chegou por mérito, mas nós chegamos para ser campeões.', [G(3, 'o técnico inflamou o grupo para a final')],
           'Técnico: "chegamos para ser campeões"', 'Confiança máxima na véspera.')]


@cen
def campeao_final(X, rnd):
    if not X.get('final') or X['res'] == 'E':
        return None
    c = X['comp'] or 'competição'
    if X['res'] == 'V':
        return 16, 'titulo', rnd.choice([f'Campeão da {c}! O que esse título significa?', 'Qual o sentimento de levantar essa taça?']), [
            op('É de todos: jogadores, funcionários e principalmente da torcida. Que noite!', [G(5, 'conquistou o título com o técnico', 3)],
               'Técnico divide a taça com todos', 'Discurso emocionado na noite do título.'),
            op('Eu disse no primeiro dia que esse grupo seria campeão. Está aí.', [G(4, 'o técnico disse que sempre soube do título', 2)],
               '"Eu disse que seríamos campeões"', 'Técnico vaidoso na festa.'),
            op('Hoje a gente comemora. Amanhã já penso no próximo título.', [G(4, 'o técnico já pediu mais títulos', 2)],
               'Técnico já quer mais', 'Fome de títulos.')]
    return 14, 'titulo', f'O vice da {c} dói. O que faltou?', [
        op('Faltou detalhe. Estou orgulhoso do caminho até aqui.', [G(2, 'o técnico valorizou a campanha apesar do vice')],
           'Técnico orgulhoso apesar do vice', 'Discurso de reconstrução.'),
        op('Faltou coragem. Final se ganha com personalidade e nós não tivemos.', [G(-4, 'o técnico acusou falta de coragem na final', 2)],
           'Técnico: "faltou coragem"', 'Vestiário abalado após o vice.'),
        op('A culpa é minha. Errei na estratégia da final.', [G(3, 'o técnico assumiu a derrota na final')],
           'Técnico assume culpa no vice', 'O grupo agradece o escudo.')]


@cen
def campeao_liga(X, rnd):
    try:
        import marcos
        tl = marcos.titulo_liga(X['tab'])
    except Exception:  # noqa: BLE001
        return None
    if not tl or not tl['campeao'] or X['res'] != 'V':
        return None
    if tl['garantido'] and (tl['vantagem'] - 3) > 3 * (tl['restam'] + 1):   # já estava garantido antes deste jogo
        return None
    return 15, 'titulo', 'Campeão da liga! Qual foi o segredo da campanha?', [
        op('Regularidade e um grupo que nunca se acomodou. Esse título é de todos.', [G(5, 'conquistou a liga com o técnico', 3)],
           'Técnico: "esse título é de todos"', 'Festa coletiva.'),
        op('Trabalho, trabalho e trabalho. E um elenco que comprou a ideia desde o primeiro dia.', [G(4, 'o técnico exaltou o compromisso do elenco', 2)],
           'O segredo do título', 'Técnico exalta o comprometimento.'),
        op('Agora quero a próxima. Campeão não descansa.', [G(3, 'o técnico já mira o próximo título')], '"Campeão não descansa"', 'Ambição sem fim.')]


# ----- mata-mata: virada histórica, vexame, classificação, eliminação (viradas.py)
@cen
def virada_historica(X, rnd):
    v = X.get('tie')
    if not v or v['tipo'] != 'virada':
        return None
    i, a = v['ida'], v['agg']
    return 15, 'virada', rnd.choice([f'Virada histórica! Perderam a ida por {i[1]} a {i[0]} e passaram com {a[0]} a {a[1]} no agregado. O que você disse ao grupo?',
                                     'Uma noite para a eternidade. Em algum momento você deixou de acreditar?']), [
        op('Eu disse que a história não estava escrita. Esse grupo é feito de gigantes, e a torcida empurrou a bola para dentro.',
           [G(5, 'viveu uma virada histórica com o técnico', 3)], '"Esse grupo é feito de gigantes"', 'Técnico exalta elenco e torcida após a virada histórica.'),
        op('Nunca deixei de acreditar. Avisei a todos que íamos virar. Quem duvidou, que peça desculpas.',
           [G(4, 'o técnico disse que sempre acreditou na virada', 2)], 'Técnico: "avisei que íamos virar"', 'Confiança que vira lenda... ou provocação.'),
        op('Hoje a gente comemora. Amanhã já pensamos no próximo adversário. Não ganhamos nada ainda.',
           [G(3, 'o técnico celebrou a virada com os pés no chão', 2)], 'Técnico celebra, mas pede foco', 'Discurso equilibrado na noite mais louca.')]


@cen
def vexame_eliminacao(X, rnd):
    v = X.get('tie')
    if not v or v['tipo'] != 'vexame':
        return None
    i, a = v['ida'], v['agg']
    return 14, 'eliminacao', f'Vocês venceram a ida por {i[0]} a {i[1]} e foram eliminados. Como explicar isso?', [
        op('Não tem explicação. A culpa é minha, e eu peço desculpas à torcida.', [G(2, 'o técnico assumiu a eliminação vexatória')],
           'Técnico pede desculpas pela eliminação', 'Assume a responsabilidade no pior momento.'),
        op('Alguns jogadores entraram de salto alto. Isso não vai se repetir.', [G(-5, 'o técnico acusou jogadores de salto alto', 3)],
           'Técnico acusa elenco de salto alto', 'Vestiário em chamas após a eliminação.'),
        op('Futebol tem dessas. O adversário teve mérito.', [G(-1, 'o técnico minimizou a eliminação')],
           'Técnico: "futebol tem dessas"', 'A torcida não aceitou a resposta.')]


@cen
def classificado(X, rnd):
    v = X.get('tie')
    if not v or v['tipo'] or not v['passou']:
        return None
    return 7.5, 'classificacao', f'Classificados com {v["agg"][0]} a {v["agg"][1]} no agregado. Até onde esse time pode ir?', [
        op('Até o fim. Ninguém entra numa competição dessas para participar.', [G(3, 'o técnico assumiu o objetivo do título')],
           'Técnico mira o título', 'Ambição declarada após a classificação.'),
        op('Um passo de cada vez. O próximo adversário é o que importa.', [G(1, 'o técnico pediu foco jogo a jogo')],
           '"Um passo de cada vez"', 'Discurso cauteloso.'),
        op('Quem cruzar o nosso caminho vai ter que jogar muito.', [G(2, 'o técnico provocou os próximos adversários')],
           'Técnico manda recado aos rivais', 'Confiança em alta no mata-mata.')]


@cen
def eliminado(X, rnd):
    v = X.get('tie')
    if not v or v['tipo'] or v['passou'] is not False:
        return None
    return 9, 'eliminacao', f'Eliminados no agregado ({v["agg"][0]} a {v["agg"][1]}). Fim do sonho?', [
        op('Dói muito. Mas esse grupo vai voltar mais forte.', [G(1, 'o técnico prometeu volta por cima')], 'Técnico promete volta por cima', 'Esperança após a queda.'),
        op('Fomos superiores no conjunto. O futebol foi cruel.', [G(1, 'o técnico defendeu o desempenho apesar da queda')],
           '"O futebol foi cruel"', 'Leitura que divide opiniões.'),
        op('Precisamos de reforços para competir nesse nível. Vou conversar com a diretoria.', [G(-2, 'o técnico disse que o elenco não basta')],
           'Técnico pede reforços após eliminação', 'Recado ao elenco e à diretoria.')]


# ----- resultado e placar
@cen
def goleada_aplicada(X, rnd):
    if X['gp'] - X['gc'] < 3 or X['classico']:
        return None
    return 6.5, 'resultado', rnd.choice([f'{X["gp"]} a {X["gc"]}. Foi a melhor atuação da temporada?', 'Goleada! O time atingiu o auge?']), [
        op('Foi muito bom, mas ainda podemos crescer. Não existe jogo perfeito.',
           [G(1, 'o técnico pediu evolução mesmo após a goleada')], 'Técnico quer mais mesmo após goleada', 'Exigência que agrada a diretoria.'),
        op('Hoje o time jogou o futebol que eu sonho. Orgulho desse grupo!',
           [G(3, 'o técnico exaltou o grupo após a goleada')], '"O futebol que eu sonho"', 'Elogio rasgado ao elenco.'),
        op(f'Respeito ao {X["adv"]}. Goleada não muda nossa postura.',
           [G(1, 'o técnico pregou humildade após a goleada')], 'Técnico prega humildade após goleada', 'Discurso de respeito ao adversário.')]


@cen
def goleada_sofrida(X, rnd):
    if X['gc'] - X['gp'] < 3:
        return None
    return 9.5, 'derrota', f'{X["gc"]} gols sofridos. Foi um vexame?', [
        op('Foi um vexame, sim. Peço desculpas, e a culpa começa por mim.',
           [G(2, 'o técnico assumiu o vexame')], 'Técnico admite vexame e pede desculpas', 'Humildade em noite para esquecer.'),
        op('Tem jogador que vestiu essa camisa hoje sem merecer. Haverá mudanças.',
           [G(-5, 'o técnico ameaçou mudanças após a goleada sofrida', 2)], 'Técnico promete mudanças após vexame',
           'Clima pesado no vestiário; ninguém se sente seguro.'),
        op('Foi um dia ruim. Em futebol, um jogo assim acontece. Vamos virar a página.',
           [G(-1, 'o técnico minimizou a goleada sofrida')], 'Técnico minimiza goleada', 'A torcida não aceitou o "dia ruim".')]


@cen
def vitoria_magra(X, rnd):
    if X['res'] != 'V' or X['gp'] - X['gc'] != 1 or X['classico']:
        return None
    return 4.5, 'resultado', rnd.choice(['Vitória sofrida. O time sofreu mais do que devia?', 'Foram três pontos no sufoco. Preocupa?']), [
        op('Time campeão também ganha jogando mal. Hoje foi caráter.',
           [G(2, 'o técnico exaltou o caráter na vitória sofrida')], '"Hoje foi caráter"', 'Técnico valoriza a vitória no sufoco.'),
        op('Não gostei. Se jogarmos assim no próximo, vamos perder.',
           [G(-1, 'o técnico criticou a atuação mesmo vencendo')], 'Técnico critica atuação apesar da vitória', 'Exigência alta no vestiário.'),
        op('O adversário fez um grande jogo. Mérito também deles.',
           [], f'Técnico elogia o {X["adv"]}', 'Discurso diplomático.')]


@cen
def empate_em_casa(X, rnd):
    if X['res'] != 'E' or not X['casa'] or X['classico']:
        return None
    return 5.5, 'resultado', 'A torcida saiu irritada com o empate em casa. Faltou o quê?', [
        op('Faltou capricho no último passe. A torcida tem razão de cobrar.',
           [G(-1, 'o técnico deu razão às cobranças da torcida')], 'Técnico dá razão à torcida', 'Autocrítica após tropeço em casa.'),
        op('Faltou o adversário jogar futebol. Eles vieram só para se defender.',
           [], f'Técnico critica retranca do {X["adv"]}', 'Crítica ao adversário divide opiniões.'),
        op('Empate não é derrota. O grupo está no caminho certo.',
           [G(1, 'o técnico protegeu o grupo após o empate')], 'Técnico protege elenco após empate', 'Discurso de confiança.')]


@cen
def derrota_casa(X, rnd):
    if X['res'] != 'D' or not X['casa'] or X['classico'] or X['gc'] - X['gp'] >= 3:
        return None
    return 7.5, 'derrota', 'Derrota em casa, com vaias no fim. Como reagir?', [
        op('Vaias fazem parte. Nossa obrigação é transformar isso em aplauso no próximo jogo.',
           [G(1, 'o técnico encarou as vaias com serenidade')], 'Técnico entende as vaias', 'Postura madura após derrota em casa.'),
        op('Quem vaia no meio do jogo não ajuda. Precisamos da torcida do nosso lado.',
           [G(1, 'o técnico defendeu o elenco das vaias')], 'Técnico critica vaias da torcida', 'A declaração divide a arquibancada.'),
        op('Alguns jogadores precisam entender o tamanho desta camisa.',
           [G(-3, 'o técnico cobrou o elenco após a derrota em casa', 2)], 'Técnico cobra elenco após derrota em casa', 'Cobrança pública esquenta o vestiário.')]


@cen
def derrota_fora(X, rnd):
    if X['res'] != 'D' or X['casa'] or X['classico'] or X['gc'] - X['gp'] >= 3:
        return None
    return 6, 'derrota', f'Derrota fora para o {X["adv"]}. O time sentiu o ambiente?', [
        op('Jogar fora é difícil, mas não é desculpa. Faltou competitividade.',
           [G(-1, 'o técnico cobrou competitividade fora de casa')], 'Técnico cobra competitividade', 'Autocrítica após derrota fora.'),
        op('Fizemos um bom jogo. O resultado não refletiu o que aconteceu em campo.',
           [G(1, 'o técnico defendeu a atuação mesmo na derrota')], 'Técnico vê injustiça no resultado', 'Leitura otimista não convence todos.'),
        op('Erramos na estratégia, e a culpa é minha.', [G(2, 'o técnico assumiu o erro de estratégia')],
           'Técnico assume erro de estratégia', 'O grupo agradece o escudo.')]


@cen
def vitoria_fora_grande(X, rnd):
    if X['res'] != 'V' or X['casa'] or X['classico']:
        return None
    pos = {t['time']: t['pos'] for t in X['tab']}
    if (pos.get(X['adv']) or 99) > 6:
        return None
    return 6.5, 'resultado', f'Vencer o {X["adv"]} na casa dele é recado para o campeonato?', [
        op('É recado, sim. Quem quiser o título vai ter que passar por nós.',
           [G(3, 'o técnico mandou recado aos rivais')], 'Técnico manda recado: "vão ter que passar por nós"', 'Confiança em alta.'),
        op('São só três pontos. Ninguém ganha campeonato em fevereiro.' if X['hoje'][1] <= 3 else 'São só três pontos. O campeonato é longo.',
           [G(1, 'o técnico manteve os pés no chão')], 'Técnico evita euforia', 'Discurso de cautela.'),
        op(f'Vitória construída na semana de treino. Mérito do grupo e da comissão.',
           [G(2, 'o técnico dividiu o mérito com o grupo')], 'Técnico divide mérito com elenco e comissão', 'Grupo valorizado.')]


@cen
def recuperacao(X, rnd):
    s = _seq(X)
    if X['res'] != 'V' or len(s['res']) < 3 or s['res'][-2] == 'V' or s['res'][-3] == 'V':
        return None
    return 6, 'resultado', 'A vitória veio depois de jogos ruins. A crise acabou?', [
        op('Crise é palavra forte. Tivemos uma oscilação e o grupo reagiu.',
           [G(2, 'o técnico comemorou a reação do grupo')], 'Técnico: "não era crise, era oscilação"', 'Alívio no vestiário.'),
        op('Uma vitória não apaga nada. Quero ver sequência.',
           [G(-1, 'o técnico seguiu cobrando mesmo após vencer')], 'Técnico segue exigente após vitória', 'Pressão mantida no grupo.'),
        op('Essa vitória é de quem foi criticado nas últimas semanas.',
           [G(3, 'o técnico defendeu os criticados')], 'Técnico dedica vitória aos criticados', 'Recado para a imprensa e a torcida.')]


# ----- sequências
@cen
def sequencia_vitorias(X, rnd):
    s = _seq(X)
    if s['v'] < 5:
        return None
    return 5.5, 'sequencia', f'São {s["v"]} vitórias seguidas. O time é imbatível?', [
        op('Ninguém é imbatível. A sequência é fruto de trabalho, e o trabalho não para.',
           [G(1, 'o técnico pediu foco na sequência')], 'Técnico: "ninguém é imbatível"', 'Pé no chão na boa fase.'),
        op('Hoje, quem enfrenta a gente já entra perdendo. É a mentalidade que construímos.',
           [G(3, 'o técnico exaltou a mentalidade vencedora')], 'Técnico: "quem enfrenta a gente já entra perdendo"', 'Confiança que beira a provocação.'),
        op('O mais difícil não é chegar no topo, é ficar lá. Esse é o nosso desafio agora.',
           [G(2, 'o técnico desafiou o grupo a manter o nível')], 'O desafio de se manter no topo', 'Técnico mira a continuidade.')]


@cen
def fim_invencibilidade(X, rnd):
    res = _seq(X)['res']
    if X['res'] != 'D' or len(res) < 6 or 'D' in res[:-1][-5:]:
        return None
    return 7, 'derrota', 'A invencibilidade acabou. Qual o impacto no grupo?', [
        op('Derrota faz parte. O importante é como a gente reage.', [G(1, 'o técnico tratou a derrota com naturalidade')],
           'Técnico trata fim da invencibilidade com calma', 'Discurso sereno.'),
        op('Até que enfim alguém percebeu que a gente pode perder. Talvez seja bom para acordar.',
           [G(-1, 'o técnico usou a derrota como alerta')], 'Técnico: "derrota pode ser bom para acordar"', 'Alerta ao elenco.'),
        op('Doeu. Esse grupo odeia perder, e é isso que me deixa tranquilo.', [G(2, 'o técnico exaltou o espírito competitivo')],
           '"Esse grupo odeia perder"', 'O técnico confia na reação.')]


@cen
def jejum_vitorias(X, rnd):
    s = _seq(X)
    if s['sv'] < 3:
        return None
    return 8.5, 'pressao', f'São {s["sv"]} jogos sem vencer. Seu cargo está em risco?', [
        op('Tenho a confiança da diretoria e do grupo. Vamos sair dessa juntos.', [G(1, 'o técnico mostrou segurança na crise')],
           'Técnico garante respaldo', 'Discurso firme em meio à crise.'),
        op('Se eu for o problema, sou o primeiro a sair. Mas não acho que seja.', [G(-1, 'o técnico admitiu que pode sair')],
           'Técnico admite sair "se for o problema"', 'A frase aumenta a pressão.'),
        op('Tem jogador que precisa jogar mais. Eu não entro em campo.', [G(-4, 'o técnico jogou a culpa nos jogadores', 2)],
           'Técnico joga a culpa no elenco', 'O vestiário não gostou.')]


# ----- os jogadores do jogo
@cen
def craque_do_jogo(X, rnd):
    ls = [j for j in X['linhas'] if j['min'] >= 45]
    if not ls:
        return None
    j = max(ls, key=_peso)
    if _peso(j) < 6.3:
        return None
    rv = _rivais(X, j)
    return 5.5, j['nome'], rnd.choice([f'{j["nome"]} foi o nome do jogo. É o melhor do elenco hoje?', f'Como explicar a atuação de {j["nome"]}?']), [
        op(f'{j["nome"]} é diferenciado. O time joga em função dele.', [E(j['kc'], 4, 2, 'foi exaltado pelo técnico na coletiva')] +
           [E(k, -2, 1, f'ouviu o técnico exaltar {j["nome"]}, rival de posição') for k in rv],
           f'Técnico exalta {j["nome"]}', 'Concorrentes de posição não gostaram.' if rv else 'Elogio público fortalece o jogador.'),
        op('O mérito é do grupo. Ninguém ganha nada sozinho.', [G(1, 'o técnico valorizou o grupo na coletiva')],
           '"O mérito é do grupo"', 'Discurso coletivo agrada o vestiário.'),
        op(f'Fez o que se espera de um jogador do nível dele. Quero mais.', [E(j['kc'], -1, 1, 'o técnico disse que quer mais dele')],
           f'Técnico cobra mais de {j["nome"]}', 'Exigência até com o destaque.')]


@cen
def hat_trick(X, rnd):
    j = next((j for j in X['linhas'] if j['gols'] >= 3), None)
    if not j:
        return None
    return 8, j['nome'], f'{j["nome"]} marcou {j["gols"]} gols. Já pediu música no Fantástico?', [
        op('Pode pedir a música que quiser. Hoje o jogo foi dele.', [E(j['kc'], 5, 2, 'o técnico celebrou os gols dele')],
           f'Noite de {j["nome"]}', 'O técnico deixou o artilheiro brilhar.'),
        op(f'Gol é consequência do time. Os {j["gols"]} gols nasceram de um trabalho coletivo.', [G(1, 'o técnico dividiu os gols com o grupo')],
           'Técnico divide os gols com o elenco', 'Discurso de grupo.'),
        op('Ele sabe que pode mais. Quero esse nível todo jogo.', [E(j['kc'], 1, 1, 'o técnico desafiou a manter o nível')],
           f'Técnico desafia {j["nome"]}', 'Exigência mesmo na noite perfeita.')]


@cen
def gol_decisivo(X, rnd):
    if X['res'] != 'V' or X['gp'] - X['gc'] != 1:
        return None
    js = [j for j in X['linhas'] if j['gols'] >= 1]
    if len(js) != 1:
        return None
    j = js[0]
    return 6, j['nome'], f'{j["nome"]} fez o gol que decidiu. Ele é o homem dos jogos difíceis?', [
        op(f'Jogador decisivo é isso: aparece quando o time mais precisa. {j["nome"]} é assim.',
           [E(j['kc'], 4, 2, 'foi chamado de decisivo pelo técnico')], f'{j["nome"]}, o homem dos jogos difíceis', 'Elogio que fortalece o atacante.'),
        op('O gol foi dele, mas a vitória foi de todo mundo.', [G(1, 'o técnico dividiu o mérito')], 'Vitória coletiva', 'Grupo valorizado.'),
        op('Precisamos fazer mais gols. Não dá para depender de um só.', [G(-1, 'o técnico cobrou mais gols do time')],
           'Técnico cobra mais gols', 'Ataque sob análise.')]


@cen
def reserva_decisivo(X, rnd):
    j = next((j for j in X['linhas'] if j.get('titular') is False and (j['gols'] or j['assist'])), None)
    if not j:
        return None
    return 7, j['nome'], f'{j["nome"]} entrou e mudou o jogo. Ganhou a vaga de titular?', [
        op(f'{j["nome"]} vai ter mais oportunidades. Quem treina bem, joga.', [E(j['kc'], 5, 2, 'o técnico prometeu mais oportunidades')] +
           [E(k, -2, 1, f'viu {j["nome"]} ganhar força na disputa') for k in _rivais(X, j)[:2]],
           f'{j["nome"]} ganha moral e briga por vaga', 'Disputa de posição esquenta.'),
        op('O banco foi importante, mas a equipe titular está definida.', [E(j['kc'], -3, 2, 'decidiu o jogo e seguiu sem garantia de vaga')],
           'Técnico mantém o time titular', f'{j["nome"]} decide, mas segue no banco.'),
        op('Esse é o elenco que eu quero: quem entra resolve.', [G(2, 'o técnico valorizou o banco de reservas')],
           '"Quem entra resolve"', 'O banco ganhou moral.')]


@cen
def jovem_brilhou(X, rnd):
    j = next((j for j in X['linhas'] if j['idade'] <= 21 and (j['gols'] or _peso(j) >= 7)), None)
    if not j:
        return None
    return 6.5, j['nome'], f'{j["nome"]}, {j["idade"]} anos, brilhou. Já é titular absoluto?', [
        op(f'{j["nome"]} tem futuro enorme, mas vamos com calma. Ninguém vai queimar o garoto.',
           [E(j['kc'], 2, 2, 'o técnico protegeu o jovem da pressão')], f'Técnico protege a joia {j["nome"]}', 'Cuidado com a promessa.'),
        op('Idade não joga. Se está bem, joga. E ele está muito bem.', [E(j['kc'], 5, 2, 'o técnico confiou nele como titular')] +
           [E(k, -2, 1, f'viu o jovem {j["nome"]} ganhar espaço') for k in _rivais(X, j)[:2]],
           f'"Idade não joga": {j["nome"]} ganha espaço', 'Veteranos de olho na disputa.'),
        op('Garoto bom, mas ainda tem muito a aprender. Não vamos inflar ninguém.', [E(j['kc'], -2, 1, 'o técnico esfriou a euforia sobre ele')],
           f'Técnico freia euforia com {j["nome"]}', 'Pé no chão com a promessa.')]


@cen
def veterano_decisivo(X, rnd):
    j = next((j for j in X['linhas'] if j['idade'] >= 33 and (j['gols'] or _peso(j) >= 6.8)), None)
    if not j:
        return None
    return 5.5, j['nome'], f'{j["nome"]}, aos {j["idade"]} anos, fez grande jogo. Até quando ele aguenta?', [
        op(f'{j["nome"]} é exemplo de profissional. Enquanto render assim, joga.', [E(j['kc'], 4, 2, 'o técnico exaltou o profissionalismo dele')],
           f'Técnico exalta {j["nome"]}', 'A experiência ainda decide.'),
        op('Idade é só número para quem se cuida como ele.', [E(j['kc'], 3, 1, 'o técnico disse que a idade não pesa')],
           '"Idade é só número"', 'Veterano valorizado.'),
        op('Vamos dosar a carga. Ele é importante demais para correr riscos.', [E(j['kc'], 1, 1, 'o técnico prometeu dosar a carga dele')],
           'Técnico vai dosar veterano', 'Gestão de elenco em pauta.')]


@cen
def pior_em_campo(X, rnd):
    ls = [j for j in X['linhas'] if j['min'] >= 45 and j['nota']]
    if len(ls) < 6:
        return None
    med = sum(j['nota'] for j in ls) / len(ls)
    j = min(ls, key=_peso)
    if j['nota'] > med - 0.7 or j['pos'] == 'GK':
        return None
    estrela = j['status'] in ESTRELAS
    return 6.5 + (1 if estrela else 0), j['nome'], f'{j["nome"]} teve uma noite ruim. Ele segue titular?', [
        op(f'{j["nome"]} tem a minha confiança. Um jogo não apaga o que ele já fez.', [E(j['kc'], 4, 2, 'foi defendido pelo técnico após jogo ruim')],
           f'Técnico blinda {j["nome"]}', 'Confiança mantida.'),
        op('Ninguém tem vaga garantida. Ele sabe que precisa render mais.', [E(j['kc'], -4, 2, 'o técnico disse que ninguém tem vaga garantida')] +
           ([G(-1, 'o grupo não gostou da exposição de um ídolo')] if j['status'] in ('Lenda', 'Ídolo') else []),
           f'Técnico ameaça tirar {j["nome"]} do time', 'Recado público ao jogador.'),
        op('Não vou falar de individualidades depois de uma vitória.' if X['res'] == 'V' else 'Não vou expor jogador aqui.',
           [], 'Técnico evita críticas individuais', 'A imprensa insiste no tema.')]


@cen
def goleiro_falhou(X, rnd):
    gk = next((j for j in X['linhas'] if j['pos'] == 'GK'), None)
    if not gk or X['gc'] < 2 or (gk['nota'] or 6) > 5.5:
        return None
    return 6.5, gk['nome'], f'{gk["nome"]} falhou em gols. A posição está em aberto?', [
        op(f'{gk["nome"]} é o meu goleiro. Goleiro precisa de confiança, e ele tem a minha.', [E(gk['kc'], 4, 2, 'o técnico o bancou após falhas')],
           f'Técnico banca {gk["nome"]}', 'Goleiro segue prestigiado.'),
        op('Vou analisar. Todas as posições estão abertas.', [E(gk['kc'], -4, 2, 'o técnico abriu a disputa no gol')] +
           [E(o['kc'], 2, 1, 'viu a disputa no gol reaberta') for o in X['J'] if o['pos'] == 'GK' and o['kc'] != gk['kc']],
           'Disputa no gol reaberta', 'Reservas ganham esperança.'),
        op('Os gols nasceram antes do goleiro. A defesa inteira falhou.', [G(-1, 'o técnico cobrou o setor defensivo')],
           'Técnico cobra a defesa inteira', 'A culpa foi dividida.')]


@cen
def goleiro_paredao(X, rnd):
    gk = next((j for j in X['linhas'] if j['pos'] == 'GK'), None)
    if not gk or X['gc'] != 0 or X['res'] != 'V':
        return None
    return 4, gk['nome'], f'{gk["nome"]} não foi vazado. A defesa é o segredo do momento?', [
        op(f'{gk["nome"]} transmite segurança para todo mundo. É um líder lá atrás.', [E(gk['kc'], 4, 2, 'foi chamado de líder pelo técnico')],
           f'{gk["nome"]}, o paredão', 'Goleiro valorizado.'),
        op('Defesa começa no atacante. O time inteiro marcou.', [G(1, 'o técnico elogiou a marcação coletiva')],
           '"Defesa começa no atacante"', 'Mérito coletivo.'),
        op('Jogo sem sofrer gol é obrigação para quem quer título.', [], 'Técnico trata clean sheet como obrigação', 'Exigência alta.')]


@cen
def jejum_atacante(X, rnd):
    for j in X['J']:
        if j['pos'] not in ('CF', 'SS', 'LWF', 'RWF') or j['status'] not in ESTRELAS:
            continue
        n = 0
        for linhas in reversed(X['hist']):
            x = next((x for x in linhas if (x['reg'], x['pid']) == j['k']), None)
            if not x or x['minutos'] < 45:
                continue
            if x['gols']:
                break
            n += 1
        if n >= 4:
            return 7, j['nome'], f'{j["nome"]} está há {n} jogos sem marcar. Preocupa?', [
                op(f'Nem um pouco. {j["nome"]} trabalha para o time, e o gol vai sair naturalmente.', [E(j['kc'], 4, 2, 'o técnico o defendeu no jejum')],
                   f'Técnico defende {j["nome"]} no jejum', 'Confiança no atacante.'),
                op('Atacante vive de gol. Ele sabe que precisa voltar a marcar.', [E(j['kc'], -3, 2, 'o técnico cobrou gols dele em público')],
                   f'Técnico cobra gols de {j["nome"]}', 'Pressão sobe sobre o atacante.'),
                op('Já conversei com ele. Fica entre nós.', [E(j['kc'], 1, 1, 'o técnico protegeu a conversa privada')],
                   'Conversa reservada com o atacante', 'Bastidores preservados.')]
    return None


@cen
def craque_poupado(X, rnd):
    em_campo = {j['kc'] for j in X['linhas']}
    if not X['linhas']:
        return None
    j = next((j for j in sorted(X['J'], key=lambda j: j['status'] != 'Lenda') if j['status'] in ('Lenda', 'Ídolo', 'Superastro')
              and j['kc'] not in em_campo and j['t_jogos'] >= 5), None)
    if not j:
        return None
    return 6, j['nome'], f'{j["nome"]} não entrou em campo. Foi opção técnica?', [
        op('Foi gestão. Temos muitos jogos e ele é importante demais para estourar.', [E(j['kc'], 1, 1, 'o técnico explicou que foi poupado')],
           f'{j["nome"]} poupado por gestão', 'Explicação aceita.'),
        op('Foi opção técnica. Quem estava em campo merecia.', [E(j['kc'], -5, 2, 'ficou de fora por opção técnica, dita em público')],
           f'{j["nome"]} fora por opção técnica', 'Estrela no banco vira assunto.'),
        op('Assunto interno. Não vou detalhar.', [E(j['kc'], -1, 1, 'o técnico não explicou a ausência dele')],
           f'Mistério sobre {j["nome"]}', 'A ausência gera especulação.')]


# ----- legado (carreira)
@cen
def lenda_brilhou(X, rnd):
    for j in sorted(X['linhas'], key=lambda j: -_peso(j)):
        if _peso(j) < 6.5:
            break
        pf = _perfil(X, j)
        if pf and pf['bolas']:
            import legado
            return 7.5, j['nome'], f'Mais uma de {j["nome"]}, dono de {legado.resumo(pf)}. Ele é o maior que você já treinou?', [
                op(f'Sem dúvida. Treinar {j["nome"]} é um privilégio que poucos técnicos tiveram.', [E(j['kc'], 4, 2, 'foi chamado de o maior pelo técnico')],
                   f'"Privilégio": técnico reverencia {j["nome"]}', 'Elogio histórico.'),
                op('Comparação é com a história, e a história ainda está sendo escrita.', [E(j['kc'], 2, 1, 'o técnico disse que a história dele continua')],
                   'A história ainda está sendo escrita', 'Resposta elegante.'),
                op('Ninguém aqui é maior que o clube.', [E(j['kc'], -2, 1, 'o técnico disse que ninguém é maior que o clube'), G(1, 'o grupo gostou do discurso coletivo')],
                   '"Ninguém é maior que o clube"', 'Recado que mira até o craque.')]
    return None


@cen
def lenda_apagada(X, rnd):
    for j in X['linhas']:
        if j['min'] < 45 or (j['nota'] or 6) > 5.6 or j['gols']:
            continue
        pf = _perfil(X, j)
        if pf and pf['nivel'] in ('mito', 'lenda'):
            return 7.5, j['nome'], f'{j["nome"]} passou em branco e foi criticado. O craque está em declínio?', [
                op(f'Declínio? Ele tem crédito eterno. Quem duvidar de {j["nome"]} vai quebrar a cara.', [E(j['kc'], 5, 2, 'o técnico rebateu as críticas a ele')],
                   f'Técnico rebate críticas a {j["nome"]}', 'Blindagem total ao craque.'),
                op('Todo mundo oscila. Ele vai responder em campo, como sempre.', [E(j['kc'], 2, 1, 'o técnico confiou na reação dele')],
                   f'{j["nome"]} vai responder em campo', 'Confiança tranquila.'),
                op('Ele sabe que hoje não foi o seu dia. É o primeiro a se cobrar.', [E(j['kc'], -1, 1, 'o técnico admitiu a má atuação dele')],
                   f'Técnico admite noite ruim de {j["nome"]}', 'Sinceridade com o ídolo.')]
    return None


# ----- tabela e temporada
@cen
def lideranca(X, rnd):
    eu, tab = X['eu'], X['tab']
    if not eu or eu['pos'] != 1 or len(tab) < 2 or eu['pts'] - tab[1]['pts'] < 6:
        return None
    return 5, 'tabela', f'{eu["pts"] - tab[1]["pts"]} pontos de vantagem. Já dá para encomendar a faixa?', [
        op('Ninguém encomenda nada aqui. Faixa só no fim, matematicamente.', [G(1, 'o técnico pediu foco apesar da vantagem')],
           'Técnico proíbe "já ganhou"', 'Disciplina no topo.'),
        op(f'Se o {tab[1]["time"]} quiser alcançar, vai ter que correr muito.', [G(2, 'o técnico provocou o vice-líder')],
           f'Técnico provoca o {tab[1]["time"]}', 'Confiança na liderança.'),
        op('Vantagem confortável não existe. Um tropeço e muda tudo.', [], 'Técnico vê campeonato aberto', 'Cautela no discurso.')]


@cen
def briga_titulo(X, rnd):
    eu, tab = X['eu'], X['tab']
    if not eu or len(tab) < 2 or eu['pos'] > 3:
        return None
    rival = tab[1] if eu['pos'] == 1 else tab[0]
    dif = abs(eu['pts'] - rival['pts'])
    if dif > 3:
        return None
    return 7, 'tabela', f'A briga com o {rival["time"]} está ponto a ponto. Quem tem mais pressão?', [
        op(f'A pressão é toda do {rival["time"]}. Nós estamos tranquilos.', [G(2, 'o técnico jogou a pressão para o rival')],
           f'"A pressão é do {rival["time"]}"', 'Guerra psicológica na reta final.'),
        op('Os dois sentem. Vence quem tiver mais cabeça.', [G(1, 'o técnico pediu equilíbrio emocional')], 'Técnico prega equilíbrio', 'Discurso maduro.'),
        op('Eu só olho para o nosso jogo. Tabela é para jornalista.', [], 'Técnico ignora a tabela', 'Foco no próprio time.')]


@cen
def zona_rebaixamento(X, rnd):
    eu, tab = X['eu'], X['tab']
    if not eu or len(tab) < 8 or eu['pos'] < len(tab) - 5:
        return None
    return 9, 'tabela', f'O time é o {eu["pos"]}º. O rebaixamento é uma ameaça real?', [
        op('É uma ameaça, e eu não vou esconder. Agora é guerra, jogo a jogo.', [G(2, 'o técnico assumiu a luta contra o rebaixamento')],
           'Técnico admite luta contra a queda', 'Sinceridade que mobiliza o grupo.'),
        op('Esse elenco é bom demais para estar aí. Vamos sair, tenho certeza.', [G(1, 'o técnico demonstrou confiança na reação')],
           'Técnico garante reação', 'Confiança em meio à crise.'),
        op('Tem gente que precisa acordar. Rebaixamento mancha carreira.', [G(-3, 'o técnico ameaçou o elenco com o rebaixamento', 2)],
           '"Rebaixamento mancha carreira"', 'Recado duro ao vestiário.')]


@cen
def pressao_diretoria(X, rnd):
    if X['conf'] is None or X['conf'] >= 40:
        return None
    return 8.5, 'tecnico', 'A diretoria está insatisfeita. Você teme pela demissão?', [
        op('Tenho contrato e confiança no meu trabalho. O grupo está comigo.', [G(1, 'o técnico mostrou segurança na coletiva')],
           'Técnico garante: "o grupo está comigo"', 'Resposta firme diante da pressão.'),
        op('Se os resultados não vierem, sou o primeiro a sair.', [G(-1, 'o técnico admitiu que pode sair')],
           'Técnico admite que pode cair', 'Fala aumenta a pressão sobre o elenco.'),
        op('A diretoria precisa me dar condições. Pedi reforços e não vieram.', [G(-1, 'o técnico expôs a diretoria em público')],
           'Técnico cobra a diretoria em público', 'Crise institucional à vista.')]


@cen
def vaga_continental(X, rnd):
    eu, tab = X['eu'], X['tab']
    if not eu or len(tab) < 10 or not 3 <= eu['pos'] <= 7:
        return None
    return 5, 'tabela', f'Em {eu["pos"]}º, a vaga continental está ameaçada?', [
        op('A vaga é obrigação. Vamos brigar até o fim.', [G(1, 'o técnico tratou a vaga como obrigação')], 'Vaga continental é obrigação', 'Meta clara.'),
        op('Ainda dá para sonhar mais alto que isso.', [G(2, 'o técnico pediu ambição ao grupo')], 'Técnico sonha alto', 'Ambição no discurso.'),
        op('Estamos onde merecemos. Precisamos melhorar muito.', [G(-1, 'o técnico fez autocrítica pública')], 'Autocrítica do técnico', 'Sinceridade.')]


# ----- próximo jogo
@cen
def proximo_decisivo(X, rnd):
    p = X['prox']
    if not p or p.get('classico') or p.get('final') or not any(c in p['comp'] for c in ('Champions', 'Libertadores', 'Copa', 'Cup', 'Intercontinental')):
        return None
    return 7, 'proximo', f'Vem aí o {p["adv"]} pela {p["comp"]}. É o jogo da temporada?', [
        op('Todo jogo de copa é uma final. Vamos para vencer.', [G(2, 'o técnico tratou o jogo como final')], '"Todo jogo de copa é final"', 'Clima de decisão.'),
        op(f'O {p["adv"]} é forte, mas nós somos mais.', [G(3, 'o técnico demonstrou superioridade antes da copa')],
           f'Técnico: "somos mais que o {p["adv"]}"', 'Confiança que vira manchete.'),
        op('Prioridade é a liga. Vamos ver como o grupo chega.', [G(-1, 'o técnico deu prioridade à liga')], 'Técnico prioriza a liga', 'Torcida se divide.')]


@cen
def calendario_apertado(X, rnd):
    p = X['prox']
    if not p or _dias(p['data'], X['hoje']) > 3:
        return None
    cansados = [j for j in X['J'] if j['condicao'] is not None and j['condicao'] < 80]
    return 5.5 + min(2, len(cansados) / 3), 'calendario', f'O próximo jogo é em {_dias(p["data"], X["hoje"])} dias. Vai poupar jogadores?', [
        op('Vou rodar o elenco. Temos jogadores para isso.', [G(1, 'o técnico prometeu rodízio')] +
           [E(j['kc'], 1, 1, 'deve ganhar descanso no rodízio') for j in cansados[:3]], 'Técnico promete rodízio', 'Reservas animados.'),
        op('Quem estiver bem, joga. Cansaço é na cabeça.', [E(j['kc'], -2, 1, 'o técnico ignorou o cansaço dele') for j in cansados[:3]],
           '"Cansaço é na cabeça"', 'Elenco desgastado não gostou.'),
        op('Vou decidir no último treino, olhando os dados físicos.', [], 'Decisão no último treino', 'Mistério na escalação.')]


@cen
def proximo_lanterna(X, rnd):
    p = X['prox']
    if not p or not X['tab'] or X['tab'][-1]['time'] != p['adv']:
        return None
    return 4.5, 'proximo', f'O próximo é o lanterna, {p["adv"]}. É obrigação vencer?', [
        op('Não existe jogo fácil. Lanterna também tem orgulho.', [G(1, 'o técnico alertou contra o salto alto')],
           'Técnico alerta contra salto alto', 'Respeito ao adversário.'),
        op('É obrigação, sim. Time grande não pode tropeçar nesse jogo.', [G(-1, 'o técnico aumentou a pressão para o jogo')],
           '"É obrigação vencer"', 'Pressão total no grupo.'),
        op('Vou aproveitar para dar ritmo a quem joga menos.', [G(1, 'o técnico prometeu chances a quem joga menos')],
           'Técnico vai rodar o time', 'Oportunidade para os reservas.')]


# ----- vestiário e clube
def _conflito(X, tipo):
    return next((c for c in X['conflitos'] if c[0] == tipo), None)


@cen
def bracadeira(X, rnd):
    c = _conflito(X, 'Braçadeira')
    if not c:
        return None
    a, cap = c[2][0], c[2][1]
    return 6, a['nome'], f'{a["nome"]} estaria incomodado por não ser o capitão. A braçadeira de {cap["nome"]} está garantida?', [
        op(f'{cap["nome"]} é o meu capitão, e {a["nome"]} é um líder sem precisar de faixa.',
           [E(cap['kc'], 4, 2, 'foi bancado como capitão na coletiva'), E(a['kc'], 2, 2, 'foi elogiado como líder na coletiva')],
           'Técnico banca capitão e afaga ' + a['nome'], 'Na coletiva, o treinador evitou criar vencedores e perdedores.'),
        op('A braçadeira é reavaliada sempre. Ninguém tem cadeira cativa.',
           [E(cap['kc'], -5, 3, 'teve a braçadeira questionada em público'), E(a['kc'], 3, 2, 'técnico abriu a disputa pela braçadeira')],
           'Técnico abre disputa pela braçadeira', f'{cap["nome"]} sai enfraquecido; {a["nome"]} ganha força.'),
        op('Assunto interno. Não vou falar de vestiário aqui.', [], 'Técnico foge do tema braçadeira', 'O silêncio só alimentou as especulações.')]


@cen
def ego_salarial(X, rnd):
    c = _conflito(X, 'Ego salarial')
    if not c:
        return None
    caro, a = c[2][0], c[2][1]
    return 5, 'folha', f'{a["nome"]} estaria incomodado por ganhar menos que {caro["nome"]}. Como você lida com isso?', [
        op(f'{a["nome"]} merece ser valorizado. Vou levar o assunto à diretoria.',
           [E(a['kc'], 5, 3, 'o técnico prometeu defender o salário dele'), E(caro['kc'], -2, 2, 'virou o assunto da folha salarial')],
           f'Técnico compra a briga salarial de {a["nome"]}', 'Agora a bola está com a diretoria.'),
        op('Salário é assunto do clube. Aqui dentro, quem decide é o desempenho.', [E(a['kc'], -3, 2, 'o técnico ignorou a queixa salarial')],
           '"Quem decide é o desempenho"', f'Resposta seca não agradou o estafe de {a["nome"]}.'),
        op('Não falo de contratos em público.', [], 'Técnico não comenta folha salarial', 'O assunto segue nos bastidores.')]


@cen
def insatisfeito(X, rnd):
    j = min((j for j in X['J'] if j['moral'] < 45 and j['status'] in ESTRELAS), key=lambda j: j['moral'], default=None)
    if not j:
        return None
    return 6.5, j['nome'], rnd.choice([f'{j["nome"]} parece insatisfeito. O que está acontecendo?', f'Há relatos de que {j["nome"]} pode pedir para sair. Ele tem futuro aqui?']), [
        op(f'{j["nome"]} é fundamental para nós. Confio totalmente nele.', [E(j['kc'], 6, 2, 'foi defendido pelo técnico na coletiva')],
           f'Técnico blinda {j["nome"]}', 'Discurso de confiança acalma, por ora, a situação.'),
        op(f'Quem quiser jogar tem que mostrar no treino. Vale para {j["nome"]} também.', [E(j['kc'], -5, 3, 'foi cobrado publicamente na coletiva')],
           f'Técnico cobra {j["nome"]} em público', 'A declaração repercutiu no vestiário.'),
        op('Isso a gente resolve dentro de casa.', [], f'Silêncio sobre {j["nome"]}', 'O técnico não quis comentar; a imprensa segue especulando.')]


@cen
def contrato_fim(X, rnd):
    import datetime as dt
    for j in sorted(X['J'], key=lambda j: j['status'] not in ('Lenda', 'Ídolo')):
        c = j['contrato']
        if not c or j['status'] not in ESTRELAS:
            continue
        meses = (dt.date(*c) - dt.date(*X['hoje'])).days // 30
        if 0 <= meses <= 8:
            return 5.5, j['nome'], f'O contrato de {j["nome"]} termina em {meses} meses. Ele renova?', [
                op(f'Quero {j["nome"]} aqui por muitos anos. Vou pedir a renovação à diretoria.', [E(j['kc'], 5, 3, 'o técnico pediu a renovação dele em público')],
                   f'Técnico pede renovação de {j["nome"]}', 'Agora a pressão está na diretoria.'),
                op('Vamos conversar no momento certo.', [E(j['kc'], -3, 2, 'o técnico não garantiu a renovação')],
                   f'Futuro de {j["nome"]} indefinido', 'O técnico evitou garantir a renovação.'),
                op('Ninguém é insubstituível. Se ele quiser sair, o clube segue.', [E(j['kc'], -6, 3, 'ouviu que não é insubstituível'), G(-1, 'o grupo estranhou a frieza')],
                   '"Ninguém é insubstituível"', 'Frase dura repercute no mercado.')]
    return None


@cen
def disciplina(X, rnd):
    c = next((c for c in X['casos'] if c.get('tipo') == 'disciplina' and c.get('envolvidos')), None)
    if not c:
        return None
    k = c['envolvidos'][0]
    nome = next((j['nome'] for j in X['J'] if j['kc'] == k), 'o jogador')
    return 6, nome, f'{c["titulo"]}. Haverá punição?', [
        op('Já conversamos. O assunto está resolvido.', [E(k, 2, 1, 'o técnico o protegeu na coletiva')],
           f'Técnico minimiza caso de {nome}', 'Discurso de "assunto resolvido" não convenceu todo mundo.'),
        op('Ninguém está acima do grupo. Vai haver consequência.', [E(k, -3, 2, 'foi exposto pelo técnico na coletiva'), G(1, 'o técnico prometeu a mesma régua para todos')],
           '"Ninguém está acima do grupo"', f'Técnico promete punição no caso {nome}.'),
        op('Não falo de disciplina em público.', [], f'Silêncio sobre o caso {nome}', 'O técnico não quis comentar.')]


@cen
def crise_vestiario(X, rnd):
    c = next((c for c in X['casos'] if c.get('tipo') == 'crise'), None)
    if not c:
        return None
    return 8, 'vestiario', f'Sobre "{c["titulo"]}": o vestiário está rachado?', [
        op('Vestiário unido. Quem tenta dividir de fora vai se frustrar.', [G(2, 'o técnico defendeu a união do grupo')],
           '"Vestiário unido"', 'Técnico nega racha.'),
        op('Tem problema, sim, e vou resolver do meu jeito, olho no olho.', [G(-1, 'o técnico admitiu problemas internos')],
           'Técnico admite problemas no vestiário', 'Sinceridade que expõe o grupo.'),
        op('Não comento vazamentos. Quem vaza informação não tem lugar aqui.', [G(-2, 'o técnico ameaçou quem vaza informações')],
           'Técnico ameaça quem vaza informação', 'Caça às bruxas no CT.')]


@cen
def janela_mercado(X, rnd):
    m = X['hoje'][1]
    if m not in (1, 7, 8):
        return None
    alvo = max((j for j in X['J'] if j['status'] in ('Superastro', 'Craque') and j['idade'] <= 28), key=lambda j: j['t_gols'] + j['t_nota'], default=None)
    if not alvo:
        return None
    return 5.5, alvo['nome'], f'Clubes estrangeiros sondam {alvo["nome"]}. Ele está à venda?', [
        op(f'{alvo["nome"]} é inegociável. Pode escrever isso.', [E(alvo['kc'], 5, 3, 'foi declarado inegociável pelo técnico')],
           f'{alvo["nome"]} é inegociável', 'Recado ao mercado.'),
        op('Todo jogador tem preço. Se a proposta for absurda, a diretoria analisa.', [E(alvo['kc'], -3, 2, 'ouviu que tem preço')],
           f'"Todo jogador tem preço": {alvo["nome"]} pode sair', 'O mercado se agita.'),
        op('Mercado é com a diretoria. Eu cuido do campo.', [], 'Técnico não entra no mercado', 'Resposta protocolar.')]


@cen
def pedido_reforco(X, rnd):
    m = X['hoje'][1]
    if m not in (1, 7, 8) or not X['eu'] or X['eu']['pos'] > 6:
        return None
    return 4.5, 'reforcos', 'A janela está aberta. Vai pedir reforços?', [
        op('O elenco está fechado. Confio em quem está aqui.', [G(2, 'o técnico disse que confia no elenco atual')],
           'Técnico fecha o elenco', 'Grupo valorizado.'),
        op('Precisamos de reforços pontuais, ou vamos ficar para trás.', [G(-1, 'o técnico disse que o elenco precisa de reforços')],
           'Técnico pede reforços', 'Alguns jogadores se sentiram ameaçados.'),
        op('Se vier alguém, que seja para jogar. Não quero turista.', [G(1, 'o técnico pediu só reforços de qualidade')],
           '"Não quero turista"', 'Recado à diretoria.')]


@cen
def torcida_protesto(X, rnd):
    s = _seq(X)
    if s['d'] < 2 or not X['casa']:
        return None
    return 8, 'torcida', 'Houve protesto da torcida no fim do jogo. O que dizer a ela?', [
        op('A torcida tem todo o direito. Vamos honrar essa camisa.', [G(1, 'o técnico deu razão à torcida')], 'Técnico dá razão à torcida', 'Gesto conciliador.'),
        op('Protesto não ganha jogo. Precisamos de apoio agora, não de pressão.', [G(1, 'o técnico pediu apoio à torcida')],
           'Técnico pede apoio, não pressão', 'A arquibancada se divide.'),
        op('Quem protesta precisa saber que este grupo está morrendo em campo.', [G(2, 'o técnico defendeu o grupo da torcida')],
           'Técnico defende elenco da torcida', 'Recado que pode custar caro.')]


@cen
def capitao_lider(X, rnd):
    cap = next((j for j in X['linhas'] if j.get('capitao')), None)
    if not cap or X['res'] != 'V' or _peso(cap) < 6.5:
        return None
    return 4, cap['nome'], f'{cap["nome"]} liderou o time em campo. O que ele representa para o grupo?', [
        op(f'{cap["nome"]} é o meu braço direito. A faixa está no braço certo.', [E(cap['kc'], 4, 2, 'foi chamado de braço direito pelo técnico')],
           f'{cap["nome"]}, o braço direito do técnico', 'Capitão fortalecido.'),
        op('Liderança aqui é coletiva. Temos vários líderes.', [G(1, 'o técnico valorizou várias lideranças')], 'Liderança coletiva', 'Grupo valorizado.'),
        op('Capitão tem que dar o exemplo, e hoje ele deu.', [E(cap['kc'], 2, 1, 'foi elogiado como exemplo')], 'Capitão dá o exemplo', 'Elogio ao líder.')]


@cen
def bola_de_ouro(X, rnd):
    if X['hoje'][1] not in (11, 12):
        return None
    for j in X['J']:
        pf = _perfil(X, j)
        if pf and pf['bolas'] and j['status'] in ESTRELAS:
            return 6, j['nome'], f'A eleição de melhor do mundo se aproxima. {j["nome"]} merece mais uma?', [
                op(f'Não tenho dúvida. Ninguém no mundo faz o que {j["nome"]} faz.', [E(j['kc'], 4, 2, 'o técnico fez campanha por ele')],
                   f'Técnico faz campanha por {j["nome"]}', 'Lobby declarado pela Bola de Ouro.'),
                op('Prêmio individual é consequência do coletivo.', [G(1, 'o técnico valorizou o coletivo')], 'Prêmio é consequência', 'Discurso de grupo.'),
                op(f'Ele já tem prêmios demais. Eu quero é título.', [E(j['kc'], -2, 1, 'o técnico desdenhou do prêmio individual')],
                   '"Eu quero é título"', 'Frase repercute mal com o craque.')]
    return None


@cen
def selecao_convocados(X, rnd):
    if X['hoje'][1] not in (3, 9, 10, 11) or X['hoje'][2] < 20:
        return None
    est = [j for j in X['J'] if j['status'] in ESTRELAS]
    if len(est) < 3:
        return None
    return 4, 'selecao', 'Vem aí a data de seleções. Preocupa perder jogadores?', [
        op('É um orgulho ter tantos convocados. Mostra o nível do trabalho.', [G(2, 'o técnico celebrou as convocações')],
           'Técnico celebra convocações', 'Prestígio do elenco.'),
        op('Preocupa, sim. Voltam cansados e o calendário não perdoa.', [G(-1, 'o técnico reclamou do calendário de seleções')],
           'Técnico reclama do calendário FIFA', 'Crítica ao calendário.'),
        op('Quem fica vai trabalhar dobrado. É oportunidade para os outros.', [G(1, 'o técnico abriu oportunidade a quem fica')],
           'Oportunidade para quem fica', 'Reservas animados.')]


@cen
def arbitragem(X, rnd):
    if X['res'] != 'D' or X['gc'] - X['gp'] != 1:
        return None
    return 5, 'arbitragem', 'Derrota por um gol. Houve lances polêmicos?', [
        op('Não vou falar de arbitragem. Perdemos porque erramos.', [G(1, 'o técnico assumiu os erros sem desculpas')],
           'Técnico não culpa arbitragem', 'Postura elogiada.'),
        op('Vi lances que precisam ser revistos. Mas a responsabilidade é nossa.', [], 'Técnico questiona lances', 'Crítica moderada.'),
        op('O apito pesou para o outro lado. Isso precisa ser dito.', [G(1, 'o técnico defendeu o time contra a arbitragem')],
           'Técnico detona a arbitragem', 'Declaração pode render punição.')]


@cen
def estilo_de_jogo(X, rnd):
    if X['res'] != 'V' or X['gp'] < 2:
        return None
    return 3.5, 'estilo', 'O time joga para frente e marca muitos gols. Essa é a sua identidade?', [
        op('Sim. Meu time tem que dar espetáculo e ganhar.', [G(2, 'o técnico reafirmou o estilo ofensivo')], '"Meu time tem que dar espetáculo"', 'Identidade clara.'),
        op('Identidade é ganhar. O resto é estética.', [G(1, 'o técnico priorizou o resultado')], '"Identidade é ganhar"', 'Pragmatismo.'),
        op('Ainda estamos longe do que eu quero. Tem muito a evoluir.', [G(-1, 'o técnico disse que o time ainda está longe do ideal')],
           'Técnico quer evolução', 'Exigência no discurso.')]


@cen
def adversario_elogio(X, rnd):
    if X['res'] == 'E' or X['classico']:
        return None
    pos = {t['time']: t['pos'] for t in X['tab']}
    if (pos.get(X['adv']) or 99) > 4:
        return None
    return 4.5, 'adversario', f'O {X["adv"]} é o adversário mais forte que vocês enfrentaram?', [
        op(f'O {X["adv"]} é muito forte. Por isso o resultado tem tanto valor.' if X['res'] == 'V' else f'É forte, mas não é melhor que a gente.',
           [G(1, 'o técnico valorizou o confronto com um grande')], f'Técnico exalta o {X["adv"]}', 'Respeito ao rival direto.'),
        op('Forte é o meu time. O adversário é problema deles.', [G(2, 'o técnico exaltou a força do próprio time')],
           '"Forte é o meu time"', 'Confiança em alta.'),
        op('Cada jogo tem sua história. Não faço ranking de adversário.', [], 'Técnico evita comparações', 'Resposta diplomática.')]


@cen
def tecnico_tempo(X, rnd):
    if X['res'] != 'V' or not X['eu'] or X['eu']['pos'] > 2:
        return None
    return 3, 'tecnico', 'Seu nome é cotado em outros clubes. Pensa em sair?', [
        op('Estou feliz aqui. Meu projeto é de longo prazo.', [G(2, 'o técnico garantiu que fica')], 'Técnico garante permanência', 'Estabilidade no projeto.'),
        op('Nunca diga nunca. Mas hoje meu foco é aqui.', [G(-1, 'o técnico não descartou sair')], 'Técnico não descarta sair', 'Fala deixa a torcida apreensiva.'),
        op('Isso é especulação. Respeito quem trabalha nos outros clubes.', [], 'Técnico desconversa', 'Resposta protocolar.')]


@cen
def gol_sofrido_fim(X, rnd):
    if X['res'] != 'E' or X['gp'] == 0:
        return None
    return 4.5, 'resultado', 'O time cedeu o empate. Faltou maturidade para segurar o resultado?', [
        op('Faltou, sim. Precisamos saber matar o jogo.', [G(-1, 'o técnico cobrou maturidade')], 'Técnico cobra maturidade', 'Autocrítica.'),
        op('O adversário teve mérito. Futebol é assim.', [], 'Técnico aceita o empate', 'Discurso sereno.'),
        op('Erro meu nas substituições. Assumo.', [G(2, 'o técnico assumiu erro nas substituições')], 'Técnico assume erro nas trocas', 'O grupo agradece o escudo.')]


@cen
def artilheiro_temporada(X, rnd):
    j = max(X['J'], key=lambda j: j['t_gols'], default=None)
    if not j or j['t_gols'] < 12 or not any(x['kc'] == j['kc'] and x['gols'] for x in X['linhas']):
        return None
    return 5, j['nome'], f'{j["nome"]} chegou a {j["t_gols"]} gols na temporada. Pode bater o recorde?', [
        op('Pode, e eu vou ajudar no que puder. O time vai jogar para ele.', [E(j['kc'], 4, 2, 'o técnico prometeu ajudar no recorde')] +
           [G(-1, 'o grupo estranhou o time jogar para um só')], 'Time vai jogar para o artilheiro', 'Recorde vira meta.'),
        op('Recorde é bonito, mas título é o que importa.', [E(j['kc'], 1, 1, 'o técnico valorizou os gols, mas pediu foco no título')],
           '"Título é o que importa"', 'Foco coletivo.'),
        op('Com esse faro de gol, só depende dele.', [E(j['kc'], 3, 1, 'o técnico exaltou o faro de gol')], f'Técnico exalta faro de {j["nome"]}', 'Confiança no artilheiro.')]


@cen
def defesa_vazada(X, rnd):
    vaz = sum(1 for g in X['ultimos'][-5:] if g['contra'] >= 2)
    if vaz < 3:
        return None
    return 7, 'defesa', f'O time sofreu 2 gols ou mais em {vaz} dos últimos 5 jogos. A defesa preocupa?', [
        op('Preocupa. Vamos trabalhar a recomposição a semana inteira.', [G(-1, 'o técnico expôs problemas defensivos')], 'Técnico admite problema na defesa', 'Treinos focados atrás.'),
        op('Defesa é o time todo. Os atacantes também precisam marcar.', [G(-1, 'o técnico cobrou os atacantes na marcação')],
           'Técnico cobra marcação dos atacantes', 'Recado ao ataque.'),
        op('Estou pensando em mudar o esquema.', [G(-2, 'o técnico ameaçou mudar o esquema e o time titular')],
           'Técnico pode mudar o esquema', 'Titulares em alerta.')]


# ----- NÚMEROS (pergunta de repórter: estatística na mão)
def _n1(x):
    return f'{x:.1f}'.replace('.', ',')


def _regulares(X, minimo=8):
    return [j for j in X['J'] if j['t_jogos'] >= minimo]


@cen
def media_gols(X, rnd):
    js = [j for j in _regulares(X, 6) if j['t_gols'] / max(1, j['t_jogos']) >= 0.6]
    if not js:
        return None
    j = max(js, key=lambda j: j['t_gols'] / j['t_jogos'])
    m = j['t_gols'] / j['t_jogos']
    return 5.5, j['nome'], f'{j["nome"]} tem {j["t_gols"]} gols em {j["t_jogos"]} jogos, média de {_n1(m)} por partida. É a melhor fase da carreira dele?', [
        op(f'É um momento especial. {j["nome"]} está decidindo e o time inteiro joga para isso.', [E(j['kc'], 4, 2, 'o técnico exaltou a fase artilheira dele')],
           f'Técnico exalta a média de gols de {j["nome"]}', 'Números de artilheiro de elite.'),
        op('Números são consequência. O que me interessa é o que ele faz sem a bola também.', [E(j['kc'], 1, 1, 'o técnico pediu mais trabalho sem a bola')],
           'Técnico quer mais que gols', 'Exigência até com o artilheiro.'),
        op(f'Ele pode mais. Eu cobro {j["nome"]} todo dia para ele não se acomodar.', [E(j['kc'], -1, 1, 'o técnico disse que cobra mais dele')],
           f'Técnico: "{j["nome"]} pode mais"', 'Cobrança pública ao artilheiro.')]


@cen
def garcom(X, rnd):
    js = [j for j in X['J'] if j['t_assist'] >= 5]
    if not js:
        return None
    j = max(js, key=lambda j: j['t_assist'])
    return 5, j['nome'], f'{j["nome"]} já soma {j["t_assist"]} assistências na temporada. Ele é o cérebro desse time?', [
        op(f'É o jogador que faz os outros jogarem. Sem {j["nome"]}, o time é outro.', [E(j['kc'], 4, 2, 'foi chamado de cérebro do time')],
           f'{j["nome"]}, o cérebro', 'Garçom valorizado.'),
        op('O time tem vários jogadores que criam. Não depende de um só.', [G(1, 'o técnico dividiu o mérito da criação')],
           'Criação coletiva', 'Discurso de grupo.'),
        op('Assistência é bonito, mas eu quero ele finalizando mais também.', [E(j['kc'], -1, 1, 'o técnico pediu mais finalizações')],
           f'Técnico quer {j["nome"]} finalizando', 'Cobrança tática.')]


@cen
def dupla_ataque(X, rnd):
    at = sorted([j for j in X['J'] if j['t_gols'] >= 6], key=lambda j: -j['t_gols'])[:2]
    if len(at) < 2 or at[0]['t_gols'] + at[1]['t_gols'] < 18:
        return None
    a, b = at
    return 5, 'dupla', f'{a["nome"]} e {b["nome"]} somam {a["t_gols"] + b["t_gols"]} gols. É a melhor dupla do futebol hoje?', [
        op('Para mim, é. Eles se entendem de olhos fechados.', [E(a['kc'], 2, 2, 'formou a melhor dupla, segundo o técnico'), E(b['kc'], 2, 2, 'formou a melhor dupla, segundo o técnico')],
           'Técnico: "a melhor dupla do futebol"', 'Elogio aos artilheiros.'),
        op('Os gols nascem do time. Eles só finalizam o trabalho de todos.', [G(1, 'o técnico dividiu os gols com o grupo')],
           'Gols do coletivo', 'Grupo valorizado.'),
        op('Dupla boa é a que ganha título. Números sozinhos não enchem a sala de troféus.', [],
           'Técnico relativiza os números', 'Foco no título.')]


@cen
def gols_seguidos(X, rnd):
    for j in X['J']:
        n = 0
        for linhas in reversed(X['hist']):
            x = next((x for x in linhas if (x['reg'], x['pid']) == j['k']), None)
            if not x or x['minutos'] <= 0:
                continue
            if not x['gols']:
                break
            n += 1
        if n >= 3:
            return 6, j['nome'], f'{j["nome"]} marcou nos últimos {n} jogos seguidos. Ele está imparável?', [
                op('Está num momento de confiança total. Atacante assim, a gente só deixa jogar.', [E(j['kc'], 4, 2, 'o técnico elogiou a sequência de gols')],
                   f'{j["nome"]} imparável', 'Sequência goleadora em pauta.'),
                op('A sequência é ótima, mas o trabalho do time é que coloca ele na cara do gol.', [G(1, 'o técnico dividiu o mérito da sequência')],
                   'Técnico divide a sequência com o grupo', 'Discurso coletivo.'),
                op('Sequência acaba um dia. Quero ver como ele reage quando passar em branco.', [E(j['kc'], -1, 1, 'o técnico já falou do dia em que ele não marcar')],
                   'Técnico esfria a euforia', 'Pé no chão com o artilheiro.')]
    return None


@cen
def sem_sofrer(X, rnd):
    n = 0
    for g in reversed(X['ultimos']):
        if g['contra'] > 0:
            break
        n += 1
    if n < 3:
        return None
    return 5, 'defesa', f'São {n} jogos seguidos sem sofrer gols. Qual o segredo da defesa?', [
        op('Concentração e trabalho coletivo. Defesa começa no atacante.', [G(2, 'o técnico exaltou a defesa coletiva')],
           'O segredo da defesa invicta', 'Mérito coletivo.'),
        op('Temos os melhores zagueiros e o melhor goleiro do campeonato.', [G(2, 'o técnico exaltou o sistema defensivo')],
           'Técnico: "os melhores atrás"', 'Elogio direto ao setor.'),
        op('Não sofrer gol é obrigação. Isso não é mérito, é o mínimo.', [G(-1, 'o técnico tratou a sequência como obrigação')],
           'Técnico trata clean sheets como obrigação', 'Exigência máxima.')]


@cen
def ataque_ultimos(X, rnd):
    u = X['ultimos'][-5:]
    gols = sum(g['pro'] for g in u)
    if len(u) < 5 or gols < 12:
        return None
    return 4.5, 'ataque', f'{gols} gols nos últimos 5 jogos. Esse é o ataque mais forte que você já teve?', [
        op('É um ataque que dá prazer de ver. E ainda dá para melhorar.', [G(2, 'o técnico elogiou o momento do ataque')],
           f'{gols} gols em 5 jogos', 'Ataque em alta.'),
        op('Gol é consequência do volume de jogo. O time cria muito.', [G(1, 'o técnico valorizou a criação coletiva')],
           'Volume de jogo explica os gols', 'Leitura tática.'),
        op('Não me empolgo. Contra time grande, o jogo é outro.', [], 'Técnico não se empolga com goleadas', 'Cautela.')]


@cen
def ataque_seca(X, rnd):
    u = X['ultimos'][-4:]
    if len(u) < 4 or sum(g['pro'] for g in u) > 2:
        return None
    gols = sum(g['pro'] for g in u)
    return 6.5, 'ataque', f'Só {gols} gol{"s" if gols != 1 else ""} nos últimos 4 jogos. O ataque travou?', [
        op('É fase. Os atacantes estão criando, a bola vai voltar a entrar.', [G(1, 'o técnico defendeu o ataque na seca')],
           'Técnico defende ataque na seca', 'Confiança mantida.'),
        op('Precisamos de mais gente chegando na área. Vou mexer no time.', [G(-2, 'o técnico ameaçou mexer no ataque')],
           'Técnico promete mudanças no ataque', 'Atacantes em alerta.'),
        op('Faltou pontaria. Vamos treinar finalização a semana inteira.', [], 'Semana de treino de finalização', 'Trabalho específico.')]


@cen
def aproveitamento_fora(X, rnd):
    fora = [g for g in X['ultimos'] if not g['casa']]
    if len(fora) < 3:
        return None
    v = sum(1 for g in fora if g['pro'] > g['contra'])
    if v not in (0, len(fora)):
        return None
    if v:
        return 4, 'fora', f'O time venceu os últimos {len(fora)} jogos fora de casa. Qual o segredo longe da torcida?', [
            op('Personalidade. Esse grupo joga igual em qualquer estádio.', [G(2, 'o técnico exaltou a personalidade fora de casa')], 'Time forte fora de casa', 'Elogio ao grupo.'),
            op('Fora de casa a gente sabe sofrer e matar no contra-ataque.', [G(1, 'o técnico explicou o plano para jogos fora')], 'O plano para jogar fora', 'Leitura tática.'),
            op('Sorte também conta. Precisamos de mais controle nesses jogos.', [], 'Técnico vê sorte nas vitórias fora', 'Sinceridade.')]
    return 6, 'fora', f'O time não venceu nenhum dos últimos {len(fora)} jogos fora de casa. O que acontece longe da torcida?', [
        op('Precisamos de mais personalidade. Vou cobrar isso.', [G(-1, 'o técnico cobrou personalidade fora de casa')], 'Técnico cobra postura fora', 'Cobrança ao elenco.'),
        op('É detalhe. Os jogos foram equilibrados.', [], 'Técnico minimiza campanha fora', 'Torcida discorda.'),
        op('A responsabilidade é minha. Vou mudar a forma de jogar fora.', [G(1, 'o técnico assumiu a campanha ruim fora')], 'Técnico assume campanha fora', 'Escudo para o grupo.')]


@cen
def nota_baixa_regular(X, rnd):
    rs = [j for j in _regulares(X, 8) if j['t_nota']]
    if len(rs) < 6:
        return None
    j = min(rs, key=lambda j: j['t_nota'])
    media = sum(x['t_nota'] for x in rs) / len(rs)
    if j['t_nota'] > media - 0.4:
        return None
    return 5.5, j['nome'], f'{j["nome"]} tem a menor nota média do elenco entre os titulares ({_n1(j["t_nota"])}). Ele segue no time?', [
        op(f'{j["nome"]} faz um trabalho que a nota não mostra. Tem a minha confiança.', [E(j['kc'], 4, 2, 'foi defendido pelo técnico apesar das notas')],
           f'Técnico defende {j["nome"]}', 'Confiança além dos números.'),
        op('Os números não mentem. Ele sabe que precisa render mais.', [E(j['kc'], -4, 2, 'teve as notas baixas expostas pelo técnico')],
           f'Técnico expõe números de {j["nome"]}', 'Pressão sobre o titular.'),
        op('Não analiso jogador por nota de site.', [], 'Técnico ignora as notas', 'Resposta seca.')]


@cen
def boa_nota_pouco_jogo(X, rnd):
    js = [j for j in X['J'] if 2 <= j['t_jogos'] <= 6 and j['t_nota'] >= 6.6]
    if not js:
        return None
    j = max(js, key=lambda j: j['t_nota'])
    return 5, j['nome'], f'{j["nome"]} tem média {_n1(j["t_nota"])}, uma das melhores do elenco, mas jogou só {j["t_jogos"]} vezes. Ele merece mais chances?', [
        op(f'Merece, e vai ter. {j["nome"]} está pedindo passagem.', [E(j['kc'], 5, 2, 'o técnico prometeu mais chances a ele')] +
           [E(k, -1, 1, f'viu {j["nome"]} ganhar força na disputa') for k in _rivais(X, j)[:2]],
           f'{j["nome"]} vai ter mais chances', 'Disputa de posição esquenta.'),
        op('Amostra pequena. Nota boa em poucos jogos não define titular.', [E(j['kc'], -2, 1, 'ouviu que a amostra é pequena')],
           'Técnico pede paciência com a amostra', 'Resposta técnica.'),
        op('Todo mundo aqui merece. Eu escolho pelo que vejo no treino.', [], 'Treino decide', 'Discurso padrão.')]


@cen
def desgaste(X, rnd):
    js = [j for j in X['J'] if j['condicao'] is not None and j['condicao'] < 70 and j['t_jogos'] >= 8]
    if not js:
        return None
    j = min(js, key=lambda j: j['condicao'])
    return 5.5, j['nome'], f'{j["nome"]} chega com a condição física em {j["condicao"]}%. Vai poupar o jogador?', [
        op('Vou poupar. Prefiro perder ele um jogo do que perder por um mês.', [E(j['kc'], 2, 1, 'vai ser poupado pelo técnico')],
           f'{j["nome"]} será poupado', 'Gestão física.'),
        op('Ele é peça fundamental. Joga e depois descansa.', [E(j['kc'], -2, 1, 'vai jogar mesmo desgastado')],
           f'{j["nome"]} joga mesmo cansado', 'Risco de lesão em pauta.'),
        op('O departamento médico decide. Eu confio nos números deles.', [], 'Decisão com os médicos', 'Gestão técnica.')]


@cen
def jovem_numeros(X, rnd):
    js = [j for j in X['J'] if j['idade'] <= 21 and (j['t_gols'] >= 3 or j['t_jogos'] >= 10)]
    if not js:
        return None
    j = max(js, key=lambda j: (j['t_gols'], j['t_jogos']))
    return 5, j['nome'], f'{j["nome"]} tem {j["idade"]} anos e já soma {j["t_jogos"]} jogos e {j["t_gols"]} gols. Até onde ele pode chegar?', [
        op('O céu é o limite. Mas o caminho é trabalho, todo dia.', [E(j['kc'], 3, 2, 'o técnico projetou um grande futuro para ele')],
           f'"O céu é o limite" para {j["nome"]}', 'Joia valorizada.'),
        op('Vamos com calma. Garoto precisa de proteção, não de holofote.', [E(j['kc'], 1, 1, 'o técnico protegeu o jovem da pressão')],
           f'Técnico protege {j["nome"]}', 'Cuidado com a promessa.'),
        op('Ele ainda não ganhou nada. Os números são bons, o resto é conversa.', [E(j['kc'], -2, 1, 'ouviu que ainda não ganhou nada')],
           'Técnico esfria a promessa', 'Pé no chão.')]


@cen
def veterano_incansavel(X, rnd):
    js = [j for j in X['J'] if j['idade'] >= 33 and j['t_jogos'] >= 15]
    if not js:
        return None
    j = max(js, key=lambda j: j['t_jogos'])
    return 4, j['nome'], f'Aos {j["idade"]} anos, {j["nome"]} já fez {j["t_jogos"]} jogos na temporada. Como ele aguenta?', [
        op('Profissionalismo. Ele é o primeiro a chegar e o último a sair.', [E(j['kc'], 4, 2, 'foi exaltado pelo profissionalismo')],
           f'O exemplo de {j["nome"]}', 'Veterano valorizado.'),
        op('Vamos dosar daqui para frente. A idade cobra.', [E(j['kc'], -1, 1, 'ouviu que a idade cobra')], 'Técnico vai dosar o veterano', 'Gestão de elenco.'),
        op('Enquanto render, joga. Idade não entra em campo.', [E(j['kc'], 2, 1, 'o técnico disse que a idade não entra em campo')],
           '"Idade não entra em campo"', 'Confiança no experiente.')]


@cen
def substituto_da_estrela(X, rnd):
    saidas_ = [m for m in X.get('movimentos') or [] if m['tipo'] == 'saida']
    if not saidas_:
        return None
    m = max(saidas_, key=lambda m: (m.get('ovr', 0), m.get('valor', 0)))
    pos = m.get('pos_campo')
    cands = sorted([j for j in X['J'] if j['pos'] == pos], key=lambda j: -j['ovr'])[:2]
    if not cands:
        return None
    nomes = ' ou '.join(j['nome'] for j in cands)
    return 7, 'substituto', f'Quem ocupa o lugar de {m["nome"]}? {nomes}?', [
        op(f'{cands[0]["nome"]} está pronto. É a chance dele.', [E(cands[0]['kc'], 5, 2, f'foi apontado como substituto de {m["nome"]}')] +
           ([E(cands[1]['kc'], -2, 1, 'perdeu a disputa pela vaga na coletiva')] if len(cands) > 1 else []),
           f'{cands[0]["nome"]} herda a vaga de {m["nome"]}', 'Disputa definida em público.'),
        op('A vaga está aberta. Quem treinar melhor, joga.', [G(1, 'o técnico abriu a disputa pela vaga')],
           'Vaga aberta no time', 'Disputa saudável.'),
        op('Vamos ao mercado. Precisamos de alguém do nível dele.', [E(j['kc'], -2, 1, 'ouviu que o clube vai buscar outro') for j in cands],
           'Técnico pede reposição no mercado', 'Elenco atual se sente desvalorizado.')]


@cen
def pre_temporada(X, rnd):
    if not _amistoso(X):
        return None
    return 6, 'pretemporada', rnd.choice(['Como está a preparação para a nova temporada?', 'O que você tirou desse amistoso?']), [
        op('Gostei da intensidade. Amistoso é para testar, e testamos bastante.', [G(1, 'o técnico aprovou a pré-temporada')],
           'Técnico aprova a pré-temporada', 'Clima bom na preparação.'),
        op('Ainda falta ritmo. O time está pesado, normal nessa fase.', [], 'Time ainda sem ritmo', 'Leitura sincera.'),
        op('Quero ver os garotos da base. Essa é a hora deles.', [G(1, 'o técnico abriu espaço para a base')],
           'Técnico abre espaço para a base', 'Jovens animados.')]


@cen
def nova_temporada_meta(X, rnd):
    if not _amistoso(X) or not X.get('liga_fim'):
        return None
    return 7, 'meta', 'Depois de uma temporada histórica, qual é a meta agora?', [
        op('Ganhar tudo de novo. Aqui não existe acomodação.', [G(2, 'o técnico já mira todos os títulos')], 'Técnico quer tudo de novo', 'Ambição renovada.'),
        op('Manter o nível já é o maior desafio. Ficar no topo é mais difícil que chegar.', [G(1, 'o técnico alertou para o desafio de se manter no topo')],
           '"Ficar no topo é mais difícil"', 'O peso de defender títulos.'),
        op('Quero uma Champions a mais na sala de troféus. É o foco.', [G(2, 'o técnico definiu a Champions como foco')],
           'Champions é o foco', 'Meta clara para a temporada.')]


# 11/10/2026: coletiva fora de época ("já dá para encomendar a faixa?" com o título garantido; perguntas de tabela
# na pré-temporada; jogador que já saiu). Regras por época + histórico para não repetir a mesma pergunta.
# ----- por POSIÇÃO (12/10/2026)
@cen
def zagueiro_gols(X, rnd):
    z = max((j for j in X['J'] if j['pos'] == 'CB' and j['t_gols'] >= 2), key=lambda j: j['t_gols'], default=None)
    if not z:
        return None
    return 6, z['nome'], f'{z["nome"]} já fez {z["t_gols"]} gols como zagueiro. Ele virou arma nas bolas paradas?', [
        op(f'Treinamos muito a bola parada. O {z["nome"]} tem o tempo de bola que poucos têm.', [E(z['kc'], 4, 2, 'o técnico elogiou os gols dele na bola parada')],
           f'"{z["nome"]} tem o tempo de bola que poucos têm"', 'Técnico exalta o zagueiro-artilheiro.'),
        op('O gol é bônus. A função dele é defender, e é isso que eu cobro.', [E(z['kc'], -1, 1, 'o técnico tratou os gols dele como bônus')],
           'Técnico: "a função dele é defender"', 'Recado para não descuidar da marcação.'),
        op('Gol de zagueiro é sinal de time que treina detalhe. O mérito é de todos.', [G(1, 'o técnico valorizou o trabalho de bola parada do grupo')],
           'Bola parada vira arma do time', 'Discurso coletivo.')]


@cen
def lateral_ofensivo(X, rnd):
    l = max((j for j in X['J'] if j['pos'] in ('LB', 'RB') and j['t_assist'] >= 3), key=lambda j: j['t_assist'], default=None)
    if not l:
        return None
    return 6, l['nome'], f'{l["nome"]} tem {l["t_assist"]} assistências, mas o setor dele fica exposto quando ele sobe. Você vai segurar o lateral?', [
        op(f'Não. O {l["nome"]} é uma arma ofensiva, e o time se organiza para cobrir.', [E(l['kc'], 4, 2, 'o técnico deu liberdade para ele atacar')],
           'Técnico mantém o lateral livre para atacar', 'Coragem tática.'),
        op('Ele precisa equilibrar. Lateral também é defensor.', [E(l['kc'], -2, 2, 'o técnico cobrou equilíbrio defensivo dele')],
           'Técnico pede equilíbrio ao lateral', 'Cobrança tática em público.'),
        op('Depende do adversário. Contra time que contra-ataca, ele vai segurar mais.', [], 'Lateral: liberdade sob medida', 'Resposta técnica.')]


@cen
def volante_invisivel(X, rnd):
    v = max((j for j in X['J'] if j['pos'] in ('DMF', 'CMF') and j['t_jogos'] >= 6 and j['t_gols'] + j['t_assist'] <= 2
             and (j['t_nota'] or 0) >= 6.0), key=lambda j: j['t_jogos'], default=None)
    if not v:
        return None
    return 5, v['nome'], f'{v["nome"]} quase não aparece nas estatísticas de gol, mas não sai do time. O que ele tem que a torcida não vê?', [
        op(f'O {v["nome"]} é o equilíbrio do time. Sem ele, ninguém brilha lá na frente.', [E(v['kc'], 5, 2, 'o técnico o chamou de equilíbrio do time')],
           f'"Sem o {v["nome"]}, ninguém brilha"', 'O volante ganha moral.'),
        op('Ele precisa aparecer mais no ataque. Dá para contribuir com gols.', [E(v['kc'], -2, 2, 'o técnico pediu mais participação ofensiva')],
           'Técnico pede gols ao volante', 'Cobrança pública.'),
        op('Quem entende de futebol sabe o valor dele.', [E(v['kc'], 3, 1, 'o técnico o defendeu')], 'Técnico defende o volante', 'Recado para os críticos.')]


# ----- Data FIFA (data_fifa.py) e rumores de mercado (rumores.py)
@cen
def fifa_esquecido(X, rnd):
    F = X.get('fifa')
    if not F or not F.get('esquecidos') or _dias(X['hoje'], tuple(F['data'])) > 12:
        return None
    e = F['esquecidos'][0]
    j = next((j for j in X['J'] if j['nome'] == e['nome']), None)
    if not j:
        return None
    return 8, e['nome'], f'{e["nome"]} ficou fora da seleção ({e["selecao"].title()}). Você conversou com ele? Foi injusto?', [
        op(f'Foi injusto, sim. {e["nome"]} é dos melhores do mundo na posição e vai mostrar isso aqui.',
           [E(j['kc'], 5, 2, 'o técnico o defendeu depois de ficar fora da seleção')], f'Técnico chama de injustiça a ausência de {e["nome"]}', 'O jogador agradeceu o apoio.'),
        op('Seleção não é comigo. Aqui ele tem o meu respeito e vai jogar.',
           [E(j['kc'], 2, 2, 'o técnico manteve a confiança depois da seleção')], 'Técnico não se mete na seleção', 'Resposta diplomática.'),
        op('Ele sabe o que precisa melhorar. A resposta vem em campo.',
           [E(j['kc'], -4, 2, 'o técnico concordou com a ausência na seleção')], f'Técnico dá recado a {e["nome"]}', 'Cobrança pública depois da Data FIFA.')]


@cen
def fifa_desgaste(X, rnd):
    F = X.get('fifa')
    if not F or not F.get('cansados') or _dias(X['hoje'], tuple(F['data'])) > 8:
        return None
    c = F['cansados'][0]
    j = next((j for j in X['J'] if j['nome'] == c['nome']), None)
    if not j:
        return None
    return 6, c['nome'], f'{c["nome"]} jogou {c["min"]} minutos pela seleção e volta com condição {c["condicao"]}. Ele joga o próximo?', [
        op('Vamos poupar. A temporada é longa e ele é importante demais para arriscar.',
           [E(j['kc'], 2, 1, 'o técnico cuidou do desgaste depois da seleção')], f'{c["nome"]} será poupado', 'Comissão técnica prioriza a parte física.'),
        op('Jogador de seleção tem que aguentar. Se estiver bem, joga.',
           [E(j['kc'], -2, 1, 'o técnico ignorou o desgaste da seleção')], 'Técnico não alivia para quem volta da seleção', 'Departamento médico preocupado.'),
        op('Seleção cobra caro e quem paga é o clube. Isso precisa mudar.',
           [G(1, 'o técnico defendeu os jogadores do calendário')], 'Técnico critica o calendário das seleções', 'Declaração repercute.')]


@cen
def rumor_estrela(X, rnd):
    R = [x for x in X.get('rumores') or [] if any(j['nome'] == x['nome'] for j in X['J'])]
    if not R:
        return None
    x = max(R, key=lambda x: x['calor'])
    j = next(j for j in X['J'] if j['nome'] == x['nome'])
    vaidoso = 'vaidoso' in ((j.get('perfil') or {}).get('tracos') or [])
    return 7 + min(4, x['calor'] // 25), x['nome'], f'O {x["clube"]} estaria de olho em {x["nome"]}. Ele está à venda?', [
        op(f'{x["nome"]} não está à venda. Ponto. Ele é parte do nosso projeto.',
           [E(j['kc'], 4, 2, f'o técnico disse que ele não sai para o {x["clube"]}')], f'"{x["nome"]} não está à venda"', 'Técnico fecha a porta para o interessado.'),
        op('Todo jogador tem o seu preço. Se vier uma proposta irrecusável, a diretoria analisa.',
           [E(j['kc'], -3 if not vaidoso else 1, 2, 'o técnico abriu a porta para a venda'), G(-1, 'o técnico admitiu vender uma peça importante')],
           f'Técnico admite: {x["nome"]} tem preço', 'Bastidores agitados; empresário se mexe.'),
        op('Isso é especulação. Aqui ele está feliz e focado.',
           [E(j['kc'], 1, 1, 'o técnico tratou o rumor como especulação')], 'Técnico chama rumor de especulação', 'Ninguém confirma, ninguém desmente.')]


@cen
def obrigacao_vencer(X, rnd):
    V = X.get('vit') or {}
    t, a = V.get('tropeco'), V.get('anterior')
    if not t or not a or _dias(X['hoje'], tuple(t['data'])) > 4:
        return None
    return 10, 'obrigacao', f'Depois de {a["n"]} títulos, {"a" if t["res"] == "derrota" else "o"} {t["res"]} com o {t["adv"]} preocupa? O time está acomodado?', [
        op('Ninguém aqui está acomodado. Tropeço acontece com quem joga 60 jogos por ano.', [G(1, 'o técnico negou acomodação e protegeu o grupo')],
           'Técnico nega acomodação', 'Discurso de proteção ao elenco.'),
        op('A cobrança é justa. Quem ganhou tudo tem que querer mais, e eu vou cobrar.', [G(-1, 'o técnico cobrou o elenco em público depois do tropeço')],
           'Técnico cobra fome do elenco', 'Recado direto para o vestiário.'),
        op('Ganhar virou obrigação aqui, e é bom que seja assim. Isso é coisa de clube grande.', [G(2, 'o técnico abraçou a pressão de ser campeão', 2)],
           '"Ganhar virou obrigação, e é bom que seja"', 'O técnico abraçou a pressão.')]


@cen
def fome_titulos(X, rnd):
    V = X.get('vit') or {}
    a = V.get('anterior')
    if not V.get('obrigacao') or not a or X['res'] is None or len([g for g in X['ultimos'] if tuple(g['data']) >= (X['hoje'][0] if X['hoje'][1] >= 7 else X['hoje'][0] - 1, 7, 1)]) > 3:
        return None
    return 7, 'fome', f'Depois de {a["n"]} títulos em {a["temporada"]}, como manter a fome desse elenco?', [
        op('Títulos são passado. Eu já disse ao grupo: a próxima temporada começa do zero.', [G(2, 'o técnico zerou o passado e pediu fome nova', 2)],
           '"Títulos são passado"', 'O técnico quer um elenco faminto.'),
        op('Vou mexer no time. Quem estiver saciado vai para o banco.', [G(-1, 'o técnico ameaçou o banco para quem estiver acomodado')],
           'Técnico ameaça os acomodados', 'O vestiário recebeu o recado.'),
        op('Esse grupo é vencedor por natureza. Não preciso motivar ninguém.', [G(1, 'o técnico demonstrou confiança total no grupo')],
           'Confiança total no grupo campeão', 'Nada muda no vestiário.')]


@cen
def joia_base_col(X, rnd):
    jo = (X.get('vit') or {}).get('joia')
    if not jo or _dias(X['hoje'], tuple(jo['data'])) > 14:
        return None
    j = next((j for j in X['J'] if j['nome'] == jo['nome']), None)
    if not j:
        return None
    return 6, jo['nome'], f'A torcida pede {jo["nome"]}. Quando a jovem promessa vai ter chance?', [
        op(f'Logo. O {jo["nome"]} está pronto e vai ter minutos.', [E(j['kc'], 5, 2, 'o técnico prometeu chances em público')],
           f'{jo["nome"]} vai ter chances', 'A base comemora.'),
        op('Jogador jovem precisa de calma. Não vou queimar o garoto.', [E(j['kc'], -2, 2, 'o técnico pediu calma com ele em público')],
           'Técnico pede calma com a joia', 'A torcida queria mais.'),
        op('Aqui joga quem está melhor. Idade não é critério.', [E(j['kc'], -1, 1, 'o técnico tratou ele como mais um')],
           '"Idade não é critério"', 'Resposta seca.')]


TABELA = {'lideranca', 'briga_titulo', 'zona_rebaixamento', 'vaga_continental', 'proximo_lanterna',
          'jogo_de_seis_pontos', 'rival_na_cola', 'perseguidor', 'reta_final'}
SO_OFICIAL = TABELA | {'zero_a_zero_em_casa', 'rodizio_custou_caro', 'anulado_pela_marcacao', 'furar_ferrolho',
                       'adversario_estudou', 'adversario_dando_a_vida', 'jejum_vitorias', 'derrota_casa', 'derrota_fora', 'goleada_sofrida', 'torcida_protesto',
                       'pressao_diretoria', 'sequencia_vitorias', 'fim_invencibilidade', 'recuperacao', 'vitoria_fora_grande',
                       'adversario_elogio', 'defesa_vazada', 'sem_sofrer', 'aproveitamento_fora', 'ataque_seca'}
HIST = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'historico', 'coletiva_hist.json')
REPETE_DIAS = 21


def _amistoso(X):
    c = X.get('comp') or ''
    return c in ('Amistoso', 'Torneio de pré-temporada') or c.startswith('Competição 10')


def _hist(ck, novo=None, hoje=None):
    import json
    import os
    try:
        with open(HIST, encoding='utf-8') as f:
            h = json.load(f)
    except (OSError, ValueError):
        h = {}
    if novo:
        h.setdefault(ck or '-', {}).update({c: list(hoje) for c in novo})
        tmp = HIST + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(h, f, ensure_ascii=False)
        os.replace(tmp, HIST)
    return h.get(ck or '-', {})


def _nomes_times(X):
    ns = {X.get('nos'), X.get('adv'), (X.get('prox') or {}).get('adv')}
    ns |= {t.get('time') for t in X.get('tab') or []}
    ns |= {g.get('adversario') for g in X.get('ultimos') or []}
    ns |= {r.get('nome') for r in ((X.get('corrida') or {}).get('rivais') or [])}
    ns |= {r.get('clube') for r in X.get('rumores') or []}
    ns |= {m.get('clube') for m in X.get('movimentos') or []} | {m.get('destino') for m in X.get('movimentos') or []}
    return {(n or '').strip() for n in ns if n and len((n or '').strip()) >= 3}


def gerar(X, n=3, seed=''):
    """Até `n` perguntas no formato da coletiva (midia.coletiva): as de maior peso com variedade de assunto."""
    if not X:
        return []
    if n == 3 and (X.get('momento') or {}).get('clima') in ('crise', 'alerta'):
        n = 4   # 12/10/2026: momento quente, coletiva mais longa
    rnd = random.Random(f'cen|{X.get("ck")}|{X["hoje"]}|{seed}')
    saiu = {tuple(m['k']) for m in X.get('movimentos') or [] if m['tipo'] == 'saida'}
    if saiu:   # quem já saiu não é assunto de vestiário
        X = dict(X, J=[j for j in X['J'] if j['k'] not in saiu], linhas=[j for j in X['linhas'] if j['k'] not in saiu],
                 conflitos=[c for c in X['conflitos'] if not any(x['k'] in saiu for x in c[2])])
    fora = set()
    if _amistoso(X):
        fora |= SO_OFICIAL
    if X.get('titulo_ok') or X.get('liga_fim'):
        fora |= TABELA
    usados = _hist(X.get('ck'))
    cands = []
    for fn in CENARIOS:
        if fn.__name__ in fora:
            continue
        try:
            c = fn(X, rnd)
        except Exception as e:  # noqa: BLE001
            print(f'aviso: cenário {fn.__name__}: {type(e).__name__}: {e}')
            continue
        if c:
            peso, alvo, texto, opcoes = c
            ult = usados.get(fn.__name__)
            if ult and 0 <= _dias(X['hoje'], tuple(ult)) < REPETE_DIAS and peso < 9:
                peso -= 4   # mesma pergunta há pouco tempo: só volta se não houver assunto melhor
            cands.append((peso + rnd.uniform(0, 2.0), fn.__name__, alvo, texto, opcoes))
    cands.sort(key=lambda c: -c[0])
    out, alvos = [], set()
    for _, nome, alvo, texto, opcoes in cands:
        if alvo in alvos or len(out) >= n:
            continue
        alvos.add(alvo)
        out.append({'texto': texto, 'alvo': alvo, 'cenario': nome, 'opcoes': opcoes})
    try:   # 12/10/2026: nomes de times como título ("LIVERPOOL" -> "Liverpool") e "a Fiorentina", "da Juventus"
        import clube
        out = clube.concordar_tudo(clube.titulo_nomes(out, _nomes_times(X)))
    except Exception:  # noqa: BLE001
        pass
    try:
        _hist(X.get('ck'), [o['cenario'] for o in out], X['hoje'])
    except OSError:
        pass
    return out


import coletiva_extra  # noqa: E402,F401  12/10/2026: lote 2 de cenários (registra em CENARIOS)
import coletiva_momento  # noqa: E402,F401  12/10/2026: lote 3 — o momento acumulado (momento.py)
