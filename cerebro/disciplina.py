# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Disciplina no vestiário (etapa 2 da vida futebolística, 10/10/2026).

A cada rodada pode surgir 0-2 casos (atraso, noitada, briga no treino, corpo mole, redes sociais, declaração contra
o clube). Quem se mete em confusão depende do momento de cada um: moral, idade, status, minutos, conflitos abertos.
Reincidente (outro caso nos últimos 120 dias) sobe um nível de gravidade.

Decisões (Central -> acoes 'caso'):
  advertência   conversa reservada (leve; em caso médio/grave o grupo acha branda)
  multa         % do salário MENSAL real do jogador (save x 430); o dinheiro entra no ORÇAMENTO, ao vivo no jogo
  afastamento   N jogos fora; vira compromisso conferido nas súmulas (escalou mesmo assim = "dois pesos")
  deixar passar o jogador gosta; o grupo, em caso médio/grave, não
Os efeitos de moral viram histórias com duração e, se a seta mudar, ela é escrita no jogo na hora.
"""
from vestiario import dias

SALARIO_X = 430
NIVEIS = ('leve', 'média', 'grave')
MULTA_PCT = {'leve': 10, 'média': 25, 'grave': 50}
AFASTA = {'leve': 1, 'média': 1, 'grave': 2}
ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')


def chave(k):
    return f'{k[0]}:{k[1]}'


def _sobe(g):
    return NIVEIS[min(2, NIVEIS.index(g) + 1)]


def _texto(sub, a, b, rnd):
    n = a['nome']
    if sub == 'atraso':
        return (f'{n} chega atrasado ao treino', rnd.choice([
            f'{n} chegou 40 minutos atrasado ao CT e perdeu a parte tática. Alegou trânsito; ninguém acreditou.',
            f'{n} se apresentou depois do horário e ainda deixou a academia mais cedo. O preparador físico reclamou com a comissão.']))
    if sub == 'balada':
        return (f'{n} flagrado em noitada', rnd.choice([
            f'Fotos de {n} numa casa noturna às 3h da manhã circulam nas redes, dois dias antes do jogo.',
            f'Um torcedor filmou {n} saindo de uma festa de madrugada. O vídeo viralizou e a diretoria quer explicações.']))
    if sub == 'briga':
        return (f'Briga no treino: {n} x {b["nome"]}', rnd.choice([
            f'Uma dividida mais forte no coletivo terminou em empurra-empurra entre {n} e {b["nome"]}. Os dois tiveram de ser separados.',
            f'{n} e {b["nome"]} discutiram feio no vestiário depois do treino. A disputa por espaço passou do limite.']))
    if sub == 'corpo_mole':
        return (f'{n} faz corpo mole no treino', rnd.choice([
            f'A comissão técnica relata que {n} treina abaixo da intensidade há dias. Os colegas perceberam.',
            f'{n} se recusou a fazer a parte física completa. "Não vejo motivo, se não jogo", teria dito.']))
    if sub == 'redes':
        return (f'{n} provoca nas redes sociais', rnd.choice([
            f'{n} publicou uma indireta depois de ficar fora do time: "Tem gente que só enxerga o que quer". Apagou minutos depois.',
            f'{n} curtiu comentários de torcedores pedindo a demissão do técnico. Os prints já estão em todo lugar.']))
    return (f'{n} critica o clube em entrevista', rnd.choice([
        f'Em entrevista a uma rádio do país dele, {n} disse que "não é valorizado" e que "pode ouvir propostas".',
        f'{n} declarou à imprensa estrangeira que o projeto do clube "não está à altura" das ambições dele.']))


GRAV = {'atraso': 'leve', 'balada': 'média', 'briga': 'média', 'corpo_mole': 'leve', 'redes': 'média', 'declaracao': 'grave'}


def gerar(r, car, hoje, rnd):
    """0-2 casos novos na rodada (probabilidade cresce com moral baixa e resultados ruins)."""
    J = r['J']
    hist = car.setdefault('disciplina_hist', [])
    pendentes = {k for c in car.get('casos', []) for k in c['envolvidos']}
    afastados = {c['k'] for c in car.get('compromissos', []) if c['status'] == 'aberto' and c['tipo'] == 'afastamento'}
    livres = [j for j in J if chave(j['k']) not in pendentes and chave(j['k']) not in afastados]
    baixos = sum(1 for j in J if j['moral'] < 45)
    ult = r.get('ultimos') or []
    derrotas = sum(1 for g in ult[-3:] if g['pro'] < g['contra'])
    import dificuldade
    p = dificuldade.chance(0.28 + 0.07 * baixos + 0.08 * derrotas, 0.92)   # técnico novo + espírito baixo = mais casos
    pesos = []   # (peso, sub, a, b)
    for j in livres:
        pouco = j['r_jogos_time'] >= 2 and j['r_min'] < 0.3 * 90 * j['r_jogos_time']
        pesos.append((1.0 + (1.5 if j['moral'] < 60 else 0) + (1 if j['idade'] <= 24 else 0), 'atraso', j, None))
        if j['idade'] <= 29:
            pesos.append((0.6 + (1.5 if j['moral'] >= 85 else 0) + (1.2 if j['status'] in ALTO else 0) +
                          (1 if j['moral'] < 45 else 0), 'balada', j, None))
        if pouco and j['moral'] < 55:
            pesos.append((2.0, 'corpo_mole', j, None))
        if j['moral'] < 50 and j['idade'] <= 27:
            pesos.append((1.6, 'redes', j, None))
        if j['moral'] < 42 and j['status'] in ALTO:
            pesos.append((2.2, 'declaracao', j, None))
    porK = {chave(j['k']): j for j in livres}
    for tipo, _txt, env in r['conflitos']:
        if tipo in ('Posição', 'Braçadeira') and len(env) >= 2 and all(chave(x['k']) in porK for x in env[:2]):
            pesos.append((2.5, 'briga', env[0], env[1]))
    novos = []
    usados = set()
    for _ in range(3 if dificuldade.M['m'] >= 1.6 else 2):
        if not pesos or rnd.random() > p:
            break
        tot = sum(w for w, *_r in pesos)
        x = rnd.random() * tot
        for w, sub, a, b in pesos:
            x -= w
            if x <= 0:
                break
        pesos = [t for t in pesos if chave(t[2]['k']) not in {chave(a['k'])} | ({chave(b['k'])} if b else set())]
        if chave(a['k']) in usados:
            continue
        usados |= {chave(a['k'])} | ({chave(b['k'])} if b else set())
        novos.append(_caso(sub, a, b, hoje, hist, rnd))
        p *= 0.45
    return novos


def _caso(sub, a, b, hoje, hist, rnd):
    env = [a] + ([b] if b else [])
    ks = [chave(x['k']) for x in env]
    g = GRAV[sub]
    reinc = [x['nome'] for x in env if any(h['k'] == chave(x['k']) and dias(tuple(hoje), tuple(h['data'])) <= 120 for h in hist)]
    if reinc:
        g = _sobe(g)
    titulo, relato = _texto(sub, a, b, rnd)
    if reinc:
        relato += f' Reincidente: {", ".join(reinc)} já teve problema disciplinar nos últimos meses.'
    pct = MULTA_PCT[g]
    multa = {chave(x['k']): round(x['salario'] * SALARIO_X / 12 * pct / 100 / 1000) * 1000 for x in env}
    total = sum(multa.values())
    n_afasta = AFASTA[g]
    nomes = ' e '.join(x['nome'] for x in env)
    grave_ou_media = g != 'leve'
    idolo = any(x['status'] in ('Lenda', 'Ídolo') for x in env)

    def todos(d, rod, motivo):
        return [{'k': '*', 'delta': d, 'rodadas': rod, 'motivo': motivo}]
    opcoes = [
        {'id': '1', 'texto': 'Advertência: conversa reservada',
         'efeitos': [{'k': k, 'delta': -1, 'rodadas': 1, 'motivo': 'levou uma advertência do técnico'} for k in ks] +
                    (todos(-1, 1, 'o grupo achou a punição branda') if grave_ou_media else []),
         'eco': (f'Caso {nomes} resolvido internamente', 'O técnico preferiu uma conversa reservada.')},
        {'id': '2', 'texto': f'Multa de {pct}% do salário mensal (R$ {total / 1e6:.2f} mi para o orçamento)'.replace('.', ','),
         'efeitos': [{'k': k, 'delta': -6 if g == 'grave' else -4, 'rodadas': 2, 'motivo': f'foi multado ({pct}% do salário)'} for k in ks] +
                    (todos(1, 1, 'o grupo viu pulso firme com a disciplina') if grave_ou_media else todos(-1, 1, 'o grupo achou a multa exagerada')),
         'multa': multa,
         'eco': (f'{nomes} multado' + ('s' if len(env) > 1 else ''), f'O clube descontou {pct}% do salário mensal.')},
        {'id': '3', 'texto': f'Afastar por {n_afasta} jogo{"s" if n_afasta > 1 else ""} (não pode entrar em campo)',
         'efeitos': [{'k': k, 'delta': -7, 'rodadas': 3, 'motivo': f'foi afastado por {n_afasta} jogo(s)'} for k in ks] +
                    (todos(2, 1, 'o grupo apoiou o afastamento') if g == 'grave' else
                     todos(-1, 1, 'o grupo achou o afastamento duro demais') if g == 'leve' else []),
         'compromissos': [{'k': k, 'nome': x['nome'], 'tipo': 'afastamento', 'jogos': n_afasta,
                           'ok': {'efeitos': todos(1, 1, 'o técnico manteve a palavra no afastamento'),
                                  'noticia': f'{x["nome"]} cumpriu o afastamento e volta a ficar à disposição.'},
                           'quebra': {'efeitos': todos(-3, 3, 'dois pesos, duas medidas: o afastado jogou') +
                                      [{'k': k, 'delta': 3, 'rodadas': 1, 'motivo': 'o afastamento não valeu'}],
                                      'noticia': f'{x["nome"]} estava afastado e entrou em campo. No vestiário, o comentário é de "dois pesos, duas medidas".'}}
                          for k, x in zip(ks, env)],
         'eco': (f'{nomes} afastado' + ('s' if len(env) > 1 else ''), f'Fora por {n_afasta} jogo(s), por decisão do técnico.')},
        {'id': '4', 'texto': 'Deixar passar',
         'efeitos': [{'k': k, 'delta': 2, 'rodadas': 1, 'motivo': 'o técnico relevou o caso'} for k in ks] +
                    (todos(-3 if idolo else -2, 2, 'o grupo viu privilégio no caso disciplinar') if grave_ou_media else []),
         'eco': ('Técnico passa pano', f'Nenhuma punição para {nomes}; parte do grupo não gostou.' if grave_ou_media else f'Caso {nomes} encerrado sem punição.')},
    ]
    return {'id': f'disc|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}|{sub}|{ks[0]}', 'tipo': 'disciplina', 'sub': sub,
            'data': list(hoje), 'gravidade': g, 'reincidente': bool(reinc), 'envolvidos': ks,
            'nomes': [x['nome'] for x in env], 'titulo': titulo, 'relato': relato, 'opcoes': opcoes}


def expirar(car, hoje):
    """Casos sem resposta por mais de 1 rodada: resolve como advertência e o grupo nota a omissão."""
    vivos, mortos = [], []
    for c in car.get('casos', []):
        (mortos if dias(tuple(hoje), tuple(c['data'])) >= 10 and c['tipo'] == 'disciplina' else vivos).append(c)
    car['casos'] = vivos
    return mortos
