# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Compromissos do técnico cobrados pelas SÚMULAS do jogo (etapa 2 da vida futebolística, 10/10/2026).

O jogo não deixa ninguém "proibir" uma escalação. Então, quando o técnico promete algo na Central, a promessa vira um
compromisso e a reunião do vestiário confere nas súmulas dos jogos seguintes:
  afastamento  N jogos sem entrar em campo (disciplina)          quebra = jogou qualquer minuto
  descanso     1 jogo sem começar como titular (calendário)      quebra = foi titular
  titular      começar o próximo jogo como titular (rodízio)     quebra = não foi titular
  jogar        entrar em campo no próximo jogo (rodízio)         quebra = não jogou
Cumprido ou quebrado, o compromisso aplica os efeitos combinados (moral com duração) e vira notícia.
Limite conhecido: súmulas com gol contra não são lidas (partidas_save); um jogo assim fica de fora da conferência.
"""


def chave(k):
    return f'{k[0]}:{k[1]}'


def historias(car, efeitos, todos, hoje, base):
    """Efeitos de moral -> histórias do vestiário (mesmo formato das polêmicas). Devolve quantas criou."""
    n = 0
    for i, ef in enumerate(efeitos):
        if 'historia' in ef:
            h = car['historias'].get(ef['historia'])
            if h:
                h['restam'] = max(0, h.get('restam', 0) + ef['restam'])
            continue
        car['historias'][f'{base}|{i}|{ef["k"]}'] = {
            'data': list(hoje), 'restam': ef['rodadas'], 'peso': ef['delta'], 'motivo': ef['motivo'],
            'envolvidos': todos if ef['k'] == '*' else [ef['k']]}
        n += 1
    return n


def _linha(p, k):
    for x in p['linhas1'] + p['linhas2']:
        if (x['reg'], x['pid']) == k:
            return x
    return None


def verificar(car, r, hoje):
    """Confere os compromissos abertos contra as súmulas. Devolve as notícias geradas."""
    todos = [chave(j['k']) for j in r['J']]
    noticias = []
    for c in car.get('compromissos', []):
        if c['status'] != 'aberto' or c['tipo'] == 'posto':   # 'posto' é conferido pelo save (exigencias.py)
            continue
        k = tuple(int(v) for v in c['k'].split(':'))
        jogos = [p for p in r['jogos'] if tuple(p['data']) > tuple(c['desde'])][:c['jogos']]
        quebra = None
        for p in jogos:
            x = _linha(p, k)
            jogou = bool(x and x['minutos'] > 0)
            tit = bool(x and x['titular'])
            if (c['tipo'] == 'afastamento' and jogou) or (c['tipo'] == 'descanso' and tit) or \
                    (c['tipo'] == 'titular' and not tit) or (c['tipo'] == 'jogar' and not jogou):
                quebra = p
                break
        if quebra:
            c['status'], c['fechado'] = 'quebrado', list(hoje)
            fim = c['quebra']
        elif len(jogos) >= c['jogos']:
            c['status'], c['fechado'] = 'cumprido', list(hoje)
            fim = c['ok']
        else:
            continue
        historias(car, fim.get('efeitos', []), todos, hoje, f'Compromisso|{c["id"]}|{c["status"]}')
        if fim.get('noticia'):
            noticias.append(fim['noticia'])
        car.setdefault('compromissos_ecos', []).append({'manchete': fim.get('manchete', fim.get('noticia', '')),
                                                        'fina': fim.get('noticia', ''), 'status': c['status']})
    car['compromissos'] = [c for c in car.get('compromissos', []) if c['status'] == 'aberto'] + \
        [c for c in car.get('compromissos', []) if c['status'] != 'aberto'][-20:]
    return noticias
