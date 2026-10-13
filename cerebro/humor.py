# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Modificadores de humor (etapa 3 da vida futebolística, 10/10/2026).

1) FATOS REAIS (automáticos, das súmulas e do registro do jogador): sequência de gols, jejum de atacante,
   primeiro gol pelo clube, marcos de gols na temporada, aniversário de clube. Mexem na moral (histórias com
   duração -> seta de condição) e viram manchete. Cada fato acontece uma vez só (car['humor_hist']).
2) VIDA PESSOAL (casos com decisão, como disciplina): nascimento de filho, dificuldade de adaptação de
   recém-chegado, problema familiar. Decisões podem virar compromisso de descanso (cobrado pela súmula) ou custo no
   orçamento de transferências (escrito ao vivo no jogo).
"""
from vestiario import dias

ATAQUE = ('CF', 'SS', 'LWF', 'RWF')
ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')


def chave(k):
    return f'{k[0]}:{k[1]}'


def _linha(p, k):
    for x in p['linhas1'] + p['linhas2']:
        if (x['reg'], x['pid']) == k:
            return x
    return None


def _jogos_do(j, jogos):
    """[(partida, linha)] em que o jogador entrou em campo, em ordem."""
    out = []
    for p in jogos:
        x = _linha(p, j['k'])
        if x and x['minutos'] > 0:
            out.append((p, x))
    return out


def fatos(r, car, hoje):
    """Fatos reais novos desta rodada: [{'id', 'k', 'noticia', 'efeitos', 'eco'}] (no máximo 3)."""
    primeira = 'humor_hist' not in car          # carreira em andamento: fatos antigos entram sem alarde
    feitos = car.setdefault('humor_hist', {})
    out = []

    def novo(fid, j, noticia, delta, rodadas, motivo, eco):
        if fid in feitos:
            return
        kk = chave(j['k'])
        out.append({'id': fid, 'k': kk, 'noticia': noticia, 'eco': eco,
                    'efeitos': [{'k': kk, 'delta': delta, 'rodadas': rodadas, 'motivo': motivo}]})

    temporada = (hoje[0] if hoje[1] >= 7 else hoje[0] - 1)
    for j in r['J']:
        jg = [(p, x) for p, x in _jogos_do(j, r['jogos']) if tuple(p['data']) >= tuple(j['chegada'])]
        if not jg:
            continue
        ult = jg[-1][0]['data']
        # sequência de gols
        seq = 0
        for _p, x in reversed(jg):
            if x['gols']:
                seq += 1
            else:
                break
        if seq >= 3:
            novo(f'seq|{chave(j["k"])}|{ult}', j, f'{j["nome"]} marcou em {seq} jogos seguidos. Vive a melhor fase.',
                 4, 2, f'marcou em {seq} jogos seguidos', (f'{j["nome"]} não para de marcar', f'{seq} jogos seguidos com gol.'))
        # jejum de atacante titular
        if j['pos'] in ATAQUE:
            jejum = 0
            for _p, x in reversed(jg):
                if x['gols']:
                    break
                if x['titular']:
                    jejum += 1
            if jejum in (6, 10, 15):
                novo(f'jejum|{chave(j["k"])}|{jejum}|{temporada}', j,
                     f'{j["nome"]} está há {jejum} jogos como titular sem marcar. A cobrança aumentou.',
                     -4 if j['status'] in ALTO else -3, 2, f'jejum de {jejum} jogos sem gol',
                     (f'Jejum de {j["nome"]} chega a {jejum} jogos', 'A torcida já pede outro atacante.'))
        # primeiro gol pelo clube
        gols_clube = [p for p, x in jg if x['gols']]
        if len(gols_clube) >= 1 and dias(tuple(hoje), tuple(gols_clube[0]['data'])) <= 21 and \
                dias(tuple(gols_clube[0]['data']), tuple(j['chegada'])) <= 365:
            novo(f'primeiro|{chave(j["k"])}', j, f'{j["nome"]} marcou o primeiro gol com a camisa do clube.',
                 5, 3, 'marcou o primeiro gol pelo clube', (f'Primeiro gol de {j["nome"]}', 'O desabafo veio na comemoração.'))
        # marcos de gols na temporada
        for m in (30, 20, 10):
            if j['t_gols'] >= m:
                for m2 in (10, 20, 30):               # os marcos menores ficam registrados sem notícia
                    if m2 < m:
                        feitos.setdefault(f'marco|{chave(j["k"])}|{m2}|{temporada}', list(hoje))
                novo(f'marco|{chave(j["k"])}|{m}|{temporada}', j, f'{j["nome"]} chegou a {m} gols na temporada.',
                     3, 2, f'chegou a {m} gols na temporada', (f'{j["nome"]} alcança {m} gols', 'Marca expressiva na temporada.'))
                break
        # aniversário de clube
        anos = int(j['anos'])
        if anos in (5, 10, 15) and j['anos'] - anos < 0.1:
            novo(f'aniv|{chave(j["k"])}|{anos}', j, f'{j["nome"]} completa {anos} anos de clube. A torcida prepara homenagem.',
                 4, 3, f'completou {anos} anos de clube', (f'{anos} anos de {j["nome"]}', 'Homenagem da torcida antes do jogo.'))
    for f in out:
        feitos[f['id']] = list(hoje)
    return [] if primeira else out[:3]


# ------------------------------------------------------------------ vida pessoal
def pessoais(r, car, hoje, rnd):
    """0 ou 1 caso de vida pessoal por rodada."""
    import dificuldade
    if rnd.random() > dificuldade.chance(0.22, 0.6):
        return []
    J = r['J']
    hist = car.setdefault('pessoal_hist', {})
    pendentes = {k for c in car.get('casos', []) for k in c['envolvidos']}

    def livre(j):
        kk = chave(j['k'])
        u = hist.get(kk)
        return kk not in pendentes and (not u or dias(tuple(hoje), tuple(u)) >= 120)

    cands = []
    for j in J:
        if not livre(j):
            continue
        if 24 <= j['idade'] <= 35:
            cands.append((1.0, 'filho', j))
        if dias(tuple(hoje), tuple(j['chegada'])) <= 150 and j['r_jogos_time'] >= 2 and \
                j['r_min'] < 0.5 * 90 * j['r_jogos_time']:
            cands.append((1.6, 'adaptacao', j))
        cands.append((0.4, 'familia', j))
    if not cands:
        return []
    tot = sum(c[0] for c in cands)
    x = rnd.random() * tot
    for peso, sub, j in cands:
        x -= peso
        if x <= 0:
            break
    kk = chave(j['k'])
    hist[kk] = list(hoje)
    n = j['nome']
    base = {'id': f'pess|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}|{sub}|{kk}', 'tipo': 'pessoal', 'sub': sub,
            'data': list(hoje), 'gravidade': 'leve', 'envolvidos': [kk], 'nomes': [n]}
    descanso = lambda ok_txt, quebra_txt: {
        'tipo': 'afastamento', 'jogos': 1,
        'ok': {'efeitos': [{'k': kk, 'delta': 3, 'rodadas': 2, 'motivo': 'o clube respeitou a folga combinada'}], 'noticia': ok_txt},
        'quebra': {'efeitos': [{'k': kk, 'delta': -7, 'rodadas': 3, 'motivo': 'a folga prometida não foi respeitada'}], 'noticia': quebra_txt}}
    if sub == 'filho':
        return [{**base, 'titulo': f'{n} vai ser pai', 'perfil': ['vida pessoal'],
                 'relato': f'{n} contou à comissão técnica que o filho deve nascer nos próximos dias. Ele pede para '
                           f'ficar fora do próximo jogo para acompanhar o parto.',
                 'opcoes': [
                     {'id': '1', 'texto': 'Liberar: ele fica fora do próximo jogo (não escale)',
                      'efeitos': [{'k': kk, 'delta': 6, 'rodadas': 3, 'motivo': 'foi liberado para o nascimento do filho'},
                                  {'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'o grupo aprovou a liberação do companheiro'}],
                      'compromisso': descanso(f'{n} acompanhou o nascimento do filho e volta motivado.',
                                              f'{n} foi liberado para o parto, mas acabou escalado. Pegou muito mal.'),
                      'eco': (f'{n} é pai!', 'Liberado pelo clube, acompanhou o nascimento do filho.')},
                     {'id': '2', 'texto': 'Precisamos dele: ele joga e viaja depois',
                      'efeitos': [{'k': kk, 'delta': -6, 'rodadas': 3, 'motivo': 'não foi liberado para o nascimento do filho'}],
                      'eco': (f'{n} perde o nascimento do filho', 'O clube não liberou o jogador; a decisão dividiu opiniões.')},
                 ]}]
    if sub == 'adaptacao':
        return [{**base, 'titulo': f'{n} tem dificuldade de adaptação', 'perfil': ['vida pessoal'],
                 'relato': f'Contratado há pouco tempo, {n} sente falta da família e ainda não se firmou no time. '
                           f'O departamento de apoio ao atleta sugere trazer os familiares e pagar aulas de idioma.',
                 'opcoes': [
                     {'id': '1', 'texto': 'Pagar a estrutura para a família (R$ 1,5 mi do orçamento de transferências)',
                      'efeitos': [{'k': kk, 'delta': 7, 'rodadas': 4, 'motivo': 'o clube trouxe a família dele'}],
                      'orcamento': -1_500_000,
                      'eco': ('Clube dá estrutura para família de ' + n, 'Investimento em adaptação deve render em campo.')},
                     {'id': '2', 'texto': 'Ele precisa se adaptar sozinho',
                      'efeitos': [{'k': kk, 'delta': -4, 'rodadas': 3, 'motivo': 'segue com dificuldade de adaptação'}],
                      'eco': (f'{n} segue isolado', 'Bastidores falam em saudade de casa.')},
                 ]}]
    return [{**base, 'titulo': f'{n} enfrenta problema familiar', 'perfil': ['vida pessoal'],
             'relato': f'{n} recebeu uma notícia difícil da família e pediu alguns dias para resolver a situação.',
             'opcoes': [
                 {'id': '1', 'texto': 'Liberar por um jogo (não escale)',
                  'efeitos': [{'k': kk, 'delta': 5, 'rodadas': 3, 'motivo': 'o clube o apoiou num momento difícil'}],
                  'compromisso': descanso(f'{n} resolveu a questão familiar e agradeceu o apoio do clube.',
                                          f'{n} foi liberado por motivos pessoais, mas acabou escalado. O grupo estranhou.'),
                  'eco': (f'Clube apoia {n}', 'Jogador foi liberado por motivos pessoais.')},
                 {'id': '2', 'texto': 'Conversar e mantê-lo à disposição',
                  'efeitos': [{'k': kk, 'delta': -3, 'rodadas': 2, 'motivo': 'não foi liberado num momento difícil'}],
                  'eco': (f'{n} segue à disposição', 'Apesar do problema pessoal, o jogador não foi liberado.')},
             ]}]
