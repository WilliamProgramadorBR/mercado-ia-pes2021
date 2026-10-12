"""Calendário e rodízio (etapa 2 da vida futebolística, 10/10/2026).

Fontes reais do jogo:
  - súmulas (partidas_save): datas dos jogos do time, minutos e titularidade de cada jogador;
  - CONDIÇÃO física do registro do jogador (save +120 bits 0-6; na memória, bloco de carreira +282): é o desgaste
    do próprio jogo — 100 para quem não joga, cai a cada partida (conferido 10/10: 90'x3 -> 72..88). É a barra
    verde ao lado da seta no Plano de jogo.
Gera, a cada rodada: a carga do elenco, a densidade do calendário e PEDIDOS (casos) de descanso/rodízio.
Plano de treino da semana (Central -> acoes.treino) mexe em condição e seta no jogo, ao vivo.
"""
from vestiario import dias

ESTADOS = ((90, 'descansado'), (80, 'em forma'), (70, 'cansado'), (0, 'esgotado'))
ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')


def chave(k):
    return f'{k[0]}:{k[1]}'


def _linha(p, k):
    for x in p['linhas1'] + p['linhas2']:
        if (x['reg'], x['pid']) == k:
            return x
    return None


def carga(r, hoje):
    jogos = r['jogos']
    d14 = [p for p in jogos if 0 <= dias(tuple(hoje), tuple(p['data'])) <= 14]
    d7 = [p for p in d14 if dias(tuple(hoje), tuple(p['data'])) <= 7]
    por = {}
    for j in r['J']:
        k = j['k']
        min14 = sum((_linha(p, k) or {}).get('minutos', 0) for p in d14)
        seguidos = 0
        for p in reversed(jogos[-8:]):
            x = _linha(p, k)
            if x and x['titular']:
                seguidos += 1
            else:
                break
        cond = j.get('condicao')
        estado = next(n for lim, n in ESTADOS if (cond if cond is not None else 100) >= lim)
        por[chave(k)] = {'nome': j['nome'], 'min14': min14, 'jogos14': sum(1 for p in d14 if (_linha(p, k) or {}).get('minutos')),
                         'seguidos': seguidos, 'condicao': cond, 'estado': estado, 'idade': j['idade']}
    n14 = len(d14)
    return {'jogos14': n14, 'jogos7': len(d7),
            'densidade': 'insana' if n14 >= 5 else 'pesada' if n14 >= 4 else 'normal' if n14 >= 2 else 'leve',
            'jogadores': por}


def pedidos(r, car, hoje, rnd, cg):
    """Casos de calendário da rodada (no máximo 1 de descanso e 1 de rodízio)."""
    cal = car.setdefault('calendario', {})
    espera = cal.setdefault('ultimo_pedido', {})
    abertos = {c['k'] for c in car.get('compromissos', []) if c['status'] == 'aberto'}
    pendentes = {k for c in car.get('casos', []) for k in c['envolvidos']}

    def livre(kk):
        u = espera.get(kk)
        return kk not in abertos and kk not in pendentes and (not u or dias(tuple(hoje), tuple(u)) >= 21)

    novos = []
    J = {chave(j['k']): j for j in r['J']}
    # 1) pedido de descanso: titular seguido, condição baixa (veteranos reclamam antes)
    cands = [(kk, c) for kk, c in cg['jogadores'].items() if livre(kk) and c['condicao'] is not None and
             ((c['condicao'] <= 78 and c['seguidos'] >= 3) or c['condicao'] <= 70 or (c['idade'] >= 31 and c['condicao'] <= 82 and c['seguidos'] >= 2))]
    if cands:
        kk, c = min(cands, key=lambda t: (t[1]['condicao'], -t[1]['idade']))
        j = J[kk]
        novos.append({
            'id': f'cal|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}|descanso|{kk}', 'tipo': 'calendario', 'sub': 'descanso',
            'data': list(hoje), 'gravidade': 'leve', 'envolvidos': [kk], 'nomes': [j['nome']],
            'titulo': f'{j["nome"]} pede descanso',
            'relato': f'O departamento médico avisa: {j["nome"]} está com condição {c["condicao"]}/100, '
                      f'{c["seguidos"]} jogo(s) seguido(s) como titular e {c["min14"]} minutos nos últimos 14 dias. '
                      f'Ele pediu para ser poupado.',
            'opcoes': [
                {'id': '1', 'texto': 'Poupar no próximo jogo (não começa como titular)',
                 'efeitos': [{'k': kk, 'delta': 3, 'rodadas': 2, 'motivo': 'foi poupado quando pediu'}],
                 'compromisso': {'tipo': 'descanso', 'jogos': 1,
                                 'ok': {'efeitos': [{'k': kk, 'delta': 2, 'rodadas': 1, 'motivo': 'o técnico cumpriu o descanso prometido'}],
                                        'noticia': f'{j["nome"]} foi poupado, como combinado, e volta descansado.'},
                                 'quebra': {'efeitos': [{'k': kk, 'delta': -6, 'rodadas': 3, 'motivo': 'o técnico prometeu descanso e o escalou'}],
                                            'noticia': f'{j["nome"]} pediu descanso, ouviu um "sim" e foi titular. O jogador ficou irritado.'}},
                 'eco': (f'{j["nome"]} será poupado', 'Comissão técnica prioriza a parte física.')},
                {'id': '2', 'texto': 'Sessão regenerativa agora e decide no dia (condição +8 no jogo)',
                 'efeitos': [{'k': kk, 'delta': 1, 'rodadas': 1, 'motivo': 'ganhou tratamento especial na recuperação'}],
                 'carreira': {kk: {'cond_delta': 8}},
                 'eco': (f'Recuperação especial para {j["nome"]}', 'Fisiologia trabalha para tê-lo no próximo jogo.')},
                {'id': '3', 'texto': 'Precisamos dele. Vai jogar.',
                 'efeitos': [{'k': kk, 'delta': -3, 'rodadas': 2, 'motivo': 'pediu descanso e não foi atendido'}],
                 'eco': (f'{j["nome"]} não terá descanso', 'O técnico considera o jogador insubstituível.')},
            ]})
    # 2) rodízio: calendário apertado e um jogador importante sem minutos
    if cg['densidade'] in ('pesada', 'insana'):
        cands = [j for kk, j in J.items() if livre(kk) and j['status'] in ALTO and j['r_jogos_time'] >= 3
                 and j['r_min'] < 0.3 * 90 * j['r_jogos_time'] and (j.get('condicao') or 100) >= 95
                 and kk not in {n['envolvidos'][0] for n in novos}]
        if cands:
            j = max(cands, key=lambda j: (j['ovr'], j['torcida']))
            kk = chave(j['k'])
            novos.append({
                'id': f'cal|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}|rodizio|{kk}', 'tipo': 'calendario', 'sub': 'rodizio',
                'data': list(hoje), 'gravidade': 'leve', 'envolvidos': [kk], 'nomes': [j['nome']],
                'titulo': f'{j["nome"]} quer entrar no rodízio',
                'relato': f'São {cg["jogos14"]} jogos em 14 dias e {j["nome"]} ({j["status"]}) está 100% fisicamente, mas jogou '
                          f'só {j["r_min"] / max(1, 90 * j["r_jogos_time"]):.0%} dos minutos recentes. "Com tanto jogo, por que não eu?"',
                'opcoes': [
                    {'id': '1', 'texto': 'Começa o próximo jogo como titular',
                     'efeitos': [{'k': kk, 'delta': 4, 'rodadas': 2, 'motivo': 'ganhou a promessa de ser titular'}],
                     'compromisso': {'tipo': 'titular', 'jogos': 1,
                                     'ok': {'efeitos': [{'k': kk, 'delta': 3, 'rodadas': 2, 'motivo': 'o técnico cumpriu: foi titular'}],
                                            'noticia': f'Promessa cumprida: {j["nome"]} começou jogando.'},
                                     'quebra': {'efeitos': [{'k': kk, 'delta': -8, 'rodadas': 3, 'motivo': 'prometeram titularidade e ficou no banco'}],
                                                'noticia': f'{j["nome"]} ouviu que seria titular e ficou de fora. Clima azedou.'}},
                     'eco': (f'{j["nome"]} ganha vaga no rodízio', 'Técnico promete titularidade no próximo compromisso.')},
                    {'id': '2', 'texto': 'Vai entrar durante o próximo jogo',
                     'efeitos': [{'k': kk, 'delta': 2, 'rodadas': 1, 'motivo': 'foi prometido que entra no próximo jogo'}],
                     'compromisso': {'tipo': 'jogar', 'jogos': 1,
                                     'ok': {'efeitos': [{'k': kk, 'delta': 2, 'rodadas': 1, 'motivo': 'entrou em campo como combinado'}],
                                            'noticia': f'{j["nome"]} ganhou minutos, como o técnico prometeu.'},
                                     'quebra': {'efeitos': [{'k': kk, 'delta': -5, 'rodadas': 2, 'motivo': 'prometeram minutos e não entrou'}],
                                                'noticia': f'{j["nome"]} esperou no banco o jogo todo, apesar da promessa.'}},
                     'eco': (f'{j["nome"]} terá minutos', 'Rodízio vai incluir o jogador.')},
                    {'id': '3', 'texto': 'A escalação é pelo desempenho, não pelo calendário',
                     'efeitos': [{'k': kk, 'delta': -3, 'rodadas': 2, 'motivo': 'o técnico negou espaço no rodízio'}],
                     'eco': ('Técnico não abre mão do time-base', f'{j["nome"]} segue esperando oportunidade.')},
                ]})
    for c in novos:
        espera[c['envolvidos'][0]] = list(hoje)
    return novos
