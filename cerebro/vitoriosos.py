"""ELENCOS VITORIOSOS (12/10/2026): a vida de quem já ganhou tudo.

  obrigação   depois de uma temporada vencedora (liga ou Champions, ou 4+ títulos oficiais), ganhar vira OBRIGAÇÃO:
              um empate ou derrota em jogo oficial vira crise na imprensa, nas redes e no celular do presidente.
              No começo da temporada, a pergunta é se o elenco ainda tem fome.
  renovação   quem é importante (ídolo, craque, nota 85+) com contrato terminando em até 12 meses: o empresário (ou o
              próprio veterano, 32+, que quer encerrar a carreira no clube) manda mensagem. "Vamos renovar" vira
              PROMESSA conferida no save (decisoes.cobrar_promessas: contrato ou salário maior); quebrar custa caro.
  joia        o garoto da base (até 20 anos, nota 72+) que treina bem e quase não joga: a imprensa e a torcida pedem
              espaço, e o coordenador da base manda mensagem.

Devolve fatos para as capas, notícias e casos do celular; guarda car['vitoriosos'] para o Bola na Mesa, as redes e a
coletiva.
"""
import datetime as dt

import celular

ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')
NAO_OFICIAL = set(range(100, 111)) | {56}


def _d(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def _k(k):
    return f'{k[0]}:{k[1]}'


def _meses(hoje, fim):
    return (fim[0] - hoje[0]) * 12 + fim[1] - hoje[1]


def _obrigacao(ck, hoje):
    """(é obrigação?, resumo da temporada passada) pelo livro da história."""
    try:
        import destaques
        import historia
        import temporada
        ant = historia.tkey(temporada.anterior(destaques.ini_temporada(hoje)))
        T = next((t for t in historia.temporadas(ck) if t['temporada'] == ant), None)
    except Exception:  # noqa: BLE001
        return False, None
    if not T:
        return False, None
    of = [c for c in T.get('titulos') or [] if 'pré-temporada' not in c]
    liga = (T.get('liga') or {}).get('competicao')
    grande = (liga in of) or any('Champions' in c or 'Libertadores' in c for c in of)
    return grande or len(of) >= 4, {'temporada': ant.replace('-', '/'), 'titulos': of, 'n': len(of)}


def da_reuniao(car, r, hoje, rnd, log=print):
    ck = car.get('ck')
    J = r['J']
    nos = r['time']
    tec = r.get('tecnico') or 'professor'
    marcas = car.setdefault('vitoriosos_marcas', {})
    fatos, noticias, casos = [], [], []
    abertos = [c for c in car.get('casos') or [] if c['tipo'] == 'celular']

    def pode(chave, dias):
        u = marcas.get(chave)
        return not u or _d(hoje, tuple(u)) >= dias

    obrig, ant = _obrigacao(ck, hoje)
    resumo = {'obrigacao': obrig, 'anterior': ant, 'data': list(hoje)}
    # ----- obrigação de vencer: o tropeço vira crise
    jogos = [p for p in r.get('jogos') or [] if p['comp'] not in NAO_OFICIAL]
    if obrig and jogos:
        p = jogos[-1]
        casa = p['time1'] == r['ti']
        gp, gc = (p['gols1'], p['gols2']) if casa else (p['gols2'], p['gols1'])
        nm = r.get('_nomes_time') or str
        adv = nm(p['time2'] if casa else p['time1']).strip()
        chave = f'trop|{p.get("num")}|{p["data"]}'
        if gp <= gc and _d(hoje, tuple(p['data'])) <= 6 and pode(chave, 9999):
            marcas[chave] = list(hoje)
            res = 'empate' if gp == gc else 'derrota'
            resumo['tropeco'] = {'adv': adv, 'gp': gp, 'gc': gc, 'res': res, 'data': list(p['data'])}
            fatos.append({'tipo': 'obrigacao', 'sub': chave, 'peso': 3.4 if res == 'derrota' else 2.6, 'adv': adv, 'gp': gp, 'gc': gc,
                          'res': res, 'ant': ant})
            noticias.append(f'COBRANÇA: depois de {ant["n"]} títulos em {ant["temporada"]}, o {res} com o {adv} ({gp} x {gc}) virou crise.')
            if pode('pres_obrig', 21) and not any(c['sub'] == 'presidente' for c in abertos):
                marcas['pres_obrig'] = list(hoje)
                casos.append(celular._caso(f'cel|pres_obrig|{hoje}', hoje, celular.PRESIDENTE, 'presidente', '🏛️',
                    [f'{tec}, {gp} a {gc} com o {adv}?',
                     f'Depois de {ant["n"]} títulos, o torcedor não aceita menos. Ganhar virou obrigação aqui, você sabe disso.',
                     'O que aconteceu?'],
                    f'O presidente cobra depois do {res}', ['*'], ['elenco'], [
                    {'texto': 'Tropeço acontece. O grupo é o mesmo que ganhou tudo, confie.', 'efeitos': [celular.E('*', 1, 1, 'o técnico protegeu o grupo depois do tropeço')], 'eco': None},
                    {'texto': 'Tem jogador acomodado. Vou mexer no time.', 'efeitos': [celular.E('*', -2, 1, 'o técnico disse que há jogadores acomodados')],
                     'eco': ('Técnico vê acomodação no elenco', 'O recado chegou ao vestiário.')},
                    {'texto': 'O calendário pesou. Vou rodar mais o elenco.', 'efeitos': [], 'eco': None},
                    {'texto': '(visualizou e não respondeu)', 'efeitos': [], 'eco': ('Técnico ignora o presidente depois do tropeço', 'Clima esfria na diretoria.')}]))
    # ----- renovações
    for j in sorted(J, key=lambda j: -j['ovr']):
        c = j.get('contrato')
        if not c or not (j['status'] in ALTO or j['ovr'] >= 85):
            continue
        m = _meses(hoje, tuple(c))
        if not 0 <= m <= 12 or not pode(f'renov|{_k(j["k"])}', 120):
            continue
        if any(p['status'] == 'aberta' and p['tipo'] == 'renovacao' and p['jogador'] == _k(j['k']) for p in car.get('promessas', [])):
            continue
        if len(abertos) + len(casos) >= celular.MAX_ABERTOS:
            break
        marcas[f'renov|{_k(j["k"])}'] = list(hoje)
        k = _k(j['k'])
        prom = {'tipo': 'renovacao', 'jogador': k, 'nome': j['nome'], 'salario': j.get('salario', 0), 'contrato': list(c)}
        vet = j['idade'] >= 32
        idolo = j['status'] in ('Lenda', 'Ídolo')
        if vet:
            msgs = [f'Professor, aqui é o {j["nome"]}. Meu contrato termina em {m} meses.',
                    f'Tenho {j["idade"]} anos e o meu sonho é encerrar a carreira aqui. Mais um ano, para fechar do jeito certo.',
                    'Posso contar com você nessa conversa com a diretoria?']
            ops = [{'texto': 'Pode contar. Vou pedir a renovação por mais um ano. (renove no jogo em até 75 dias)', 'promessa': prom,
                    'efeitos': [celular.E(k, 8, 3, 'o técnico apoiou a renovação dele')], 'eco': (f'{j["nome"]} deve renovar', 'Técnico apoia a permanência do veterano.')},
                   {'texto': 'Chegou a hora de passar o bastão. Você vai sair pela porta da frente.',
                    'efeitos': [celular.E(k, -10, 4, 'o técnico disse que é hora de ele sair')] + ([celular.E('*', -2, 1, f'o grupo sentiu a despedida anunciada de {j["nome"]}')] if idolo else []),
                    'eco': (f'Fim da linha para {j["nome"]}?', 'O técnico não conta com o veterano para a próxima temporada.')},
                   {'texto': 'Vamos ver como você termina a temporada e conversamos.', 'efeitos': [celular.E(k, -2, 2, 'o técnico adiou a conversa sobre o futuro dele')], 'eco': None},
                   {'texto': '(visualizou e não respondeu)', 'efeitos': [celular.E(k, -5, 2, 'o técnico ignorou o pedido de renovação')], 'eco': None}]
            contato, papel, ic = j['nome'], f'renovação|{j["nome"]}', '🕰️'
        else:
            tr = set(((j.get('perfil') or {}).get('tracos')) or [])
            msgs = [f'Bom dia, {tec}. O contrato do {j["nome"]} termina em {m} meses.',
                    'Já apareceram sondagens, não vou esconder. Ele gosta do clube, mas quer saber se é prioridade.',
                    'Qual é a ideia do clube?']
            ops = [{'texto': 'Ele é prioridade. Vou pedir a renovação à diretoria. (renove no jogo em até 75 dias)', 'promessa': prom,
                    'efeitos': [celular.E(k, 7, 3, 'o técnico disse que a renovação dele é prioridade')], 'eco': (f'Prioridade: renovar com {j["nome"]}', 'O técnico quer o jogador no projeto.')},
                   {'texto': 'Renovamos, mas sem aumento. É o que o clube pode.',
                    'efeitos': [celular.E(k, -6 if 'vaidoso' in tr else -3, 2, 'ouviu que a renovação seria sem aumento')], 'eco': None},
                   {'texto': 'Ele não está nos planos. Pode procurar clube.',
                    'efeitos': [celular.E(k, -12, 4, 'o técnico disse que ele não está nos planos')] + ([celular.E('*', -2, 1, f'o grupo soube que {j["nome"]} não fica')] if idolo else []),
                    'eco': (f'{j["nome"]} fora dos planos', 'O empresário já procura outro clube.')},
                   {'texto': '(visualizou e não respondeu)', 'efeitos': [celular.E(k, -4, 2, 'o técnico deixou o empresário sem resposta')], 'eco': None}]
            contato, papel, ic = f'Empresário de {j["nome"]}', f'renovação|{j["nome"]}', '📝'
        casos.append(celular._caso(f'cel|renov|{k}|{hoje}', hoje, contato, papel, ic, msgs, f'Renovação de {j["nome"]}', [k], [j['nome']], ops))
        resumo.setdefault('renovacoes', []).append({'nome': j['nome'], 'meses': m, 'idade': j['idade'], 'veterano': vet})
        fatos.append({'tipo': 'renovacao', 'sub': k, 'peso': 2.4 + (1 if idolo else 0), 'nome': j['nome'], 'meses': m, 'idade': j['idade'], 'veterano': vet})
        noticias.append(f'CONTRATO: o vínculo de {j["nome"]} termina em {m} meses e ninguém fala em renovação.')
    # ----- joia da base
    jovens = [j for j in J if j['idade'] <= 20 and 72 <= j['ovr'] <= 83 and j['pos'] != 'GK' and j.get('r_jogos_time', 0) >= 3   # promessa, não estrela
              and j.get('r_min', 0) < 90 * j['r_jogos_time'] * 0.3]
    jovens.sort(key=lambda j: -j['ovr'])
    if jovens and pode(f'joia|{_k(jovens[0]["k"])}', 45):
        j = jovens[0]
        k = _k(j['k'])
        marcas[f'joia|{k}'] = list(hoje)
        resumo['joia'] = {'nome': j['nome'], 'idade': j['idade'], 'ovr': j['ovr'], 'pos': j['pos'], 'jogos': j['t_jogos'], 'data': list(hoje)}
        fatos.append({'tipo': 'joia_base', 'sub': k, 'peso': 2.3, **resumo['joia']})
        noticias.append(f'BASE: a torcida pede minutos para {j["nome"]}, {j["idade"]} anos, nota {j["ovr"]}.')
        if len(abertos) + len(casos) < celular.MAX_ABERTOS:
            casos.append(celular._caso(f'cel|joia|{k}|{hoje}', hoje, 'Diretor de futebol', 'base', '🌱',
                [f'{tec}, preciso te falar do {j["nome"]}. {j["idade"]} anos e está voando nos treinos.',
                 'Se ele não jogar agora, o empresário vai começar a ouvir proposta de empréstimo. O garoto quer espaço.'],
                f'Minutos para a jovem promessa {j["nome"]}', [k], [j['nome']], [
                {'texto': 'Ele vai ter minutos nos próximos jogos.', 'efeitos': [celular.E(k, 6, 2, 'o técnico prometeu minutos para a joia da base')],
                 'compromisso': {'tipo': 'jogar', 'jogos': 2,
                                 'ok': {'efeitos': [celular.E(k, 4, 2, 'ganhou os minutos prometidos')], 'noticia': f'{j["nome"]} ganha minutos e a torcida aplaude a aposta na base.'},
                                 'quebra': {'efeitos': [celular.E(k, -7, 3, 'a promessa de minutos não saiu')], 'noticia': f'{j["nome"]} não entrou em campo. O coordenador da base está incomodado.'}},
                 'eco': (f'{j["nome"]} vai ganhar chances', 'Técnico promete minutos à joia da base.')},
                {'texto': 'Ainda não é a hora. Ele vai chegar no tempo certo.', 'efeitos': [celular.E(k, -3, 2, 'ouviu que ainda não é a hora dele')], 'eco': None},
                {'texto': 'Melhor emprestar. Ele precisa de rodagem.', 'efeitos': [celular.E(k, -1, 1, 'o técnico pensou em emprestá-lo para ganhar rodagem')],
                 'eco': (f'{j["nome"]} pode ser emprestado', 'Técnico quer rodagem para o garoto.')},
                {'texto': '(visualizou e não respondeu)', 'efeitos': [celular.E(k, -2, 1, 'o técnico ignorou o pedido de minutos para ele')], 'eco': None}]))
    velho = (car.get('vitoriosos') or {}).get('joia')
    if 'joia' not in resumo and velho and not (72 <= velho.get('ovr', 0) <= 83):   # joia antiga fora da regra atual sai
        resumo['joia'] = None
    car['vitoriosos'] = {**(car.get('vitoriosos') or {}), **resumo}
    if fatos:
        log('vitoriosos: ' + '; '.join(f['tipo'] for f in fatos))
    return fatos, noticias, casos
