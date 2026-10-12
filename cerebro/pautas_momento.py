"""BOLA NA MESA — pautas do MOMENTO (12/10/2026).

O programa passa a discutir o que se acumulou (momento.py), a leitura dos analistas (analise_jogo.py) e o plano que o
próximo adversário preparou (ia_adversaria): rival que encostou ou disparou, liderança trocada, duas derrotas seguidas,
semana decisiva (poupar ou não?), "a Mesa Tática explicou" e "como o rival vem". Registradas em bola_na_mesa.PAUTAS.
"""
import clube
from bola_na_mesa import pauta, _enquete, _torc, _dias


def _nos(M):
    return clube.C.get('nome') or clube.nome_time(M['nos'])


def _mo(M):
    mo = M.get('momento') or {}
    u = M.get('ult') or {}
    # o momento é da última reunião: no pós-jogo ao vivo (antes da reunião) ele ainda não conhece o jogo novo
    if mo.get('ultimo') and u and list(mo['ultimo']['data']) != list(u['p']['data']):
        return {}
    return mo


@pauta
def corrida_liga(M, rnd):
    mo = _mo(M)
    L = mo.get('liga') or {}
    rv = L.get('rival') or {}
    mv = rv.get('movimento')
    if not rv or not (mv or L.get('lideranca')):
        return None
    nos, r = _nos(M), rv['nome']
    forma_r = ' '.join(rv.get('forma') or '')
    if L.get('lideranca') == 'perdeu':
        titulo, abre = f'O {r} na ponta', f'Mudou a liderança: o {r} passou o {nos}. Eram {rv["dif_antes"]} pontos de vantagem há duas rodadas.'
    elif L.get('lideranca') == 'assumiu':
        titulo, abre = f'{nos} assume a ponta', f'O {nos} é o novo líder, e o {r} está a {abs(rv["dif"])} ponto(s).'
    elif mv == 'encostou':
        titulo, abre = f'O {r} encostou', f'Eram {rv["dif_antes"]} pontos de vantagem, agora {"é só 1" if rv["dif"] == 1 else "são " + str(rv["dif"])}. O {r} está chegando?'
    elif mv == 'disparou':
        titulo, abre = f'O {r} disparou', f'O {r} abriu {abs(rv["dif"])} pontos. A liga está escapando do {nos}?'
    elif mv in ('ficou_para_tras', 'aproximamos'):
        titulo, abre = f'{nos} x {r}: a distância mudou', f'Em duas rodadas, a diferença para o {r} foi de {abs(rv["dif_antes"])} para {abs(rv["dif"])} pontos.'
    else:
        return None
    ruim = mv in ('encostou', 'disparou') or L.get('lideranca') == 'perdeu'
    falas = [('rogerio', abre),
             ('helena', f'O {r} nos últimos jogos da liga: {forma_r}. ' + ('Regularidade de quem quer o título.' if forma_r.count('V') >= 3 else 'Não é um time imbatível.')
              if forma_r else f'Os números mostram uma liga apertada entre {nos} e {r}.'),
             ('carlao', 'Isso é falta de atitude! Quem lidera não pode dar espaço!' if ruim else 'É assim que se faz: jogo a jogo, sem olhar para o lado!'),
             ('beto', 'No CT o assunto é um só: a tabela. O técnico pediu para ninguém falar do rival na semana.' if ruim
              else 'O clima no CT é leve. Os jogadores sabem que a fase é boa.'),
             ('toninho', f'O torcedor do {r} já está imprimindo a faixa de campeão! Calma, gente, ainda é {["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"][M["hoje"][1] - 1]}!' if ruim
              else f'O {r} tá olhando a tabela de binóculo!')]
    return {'id': 'corrida_liga', 'cat': 'tabela', 'peso': 8.5 if ruim else 6.5, 'titulo': titulo, 'falas': falas,
            'enquete': _enquete(f'Quem termina na frente: {nos} ou {r}?', [(nos, 1.2 if not ruim else 0.9), (r, 0.9 if not ruim else 1.1)], rnd),
            'posts': [(_torc(M), f'{titulo}. ' + ('Acorda, time! ⏰' if ruim else 'Segue o líder! 🔝'))]}


@pauta
def duas_derrotas(M, rnd):
    mo = _mo(M)
    s = mo.get('seq') or {}
    u = M.get('ult') or {}
    if s.get('d') != 2 or not u.get('recente'):
        return None
    advs = [x['adv'] for x in (mo.get('ultimos') or [])[-2:]]
    nos = _nos(M)
    return {'id': 'duas_derrotas', 'cat': 'momento', 'peso': 8, 'titulo': 'Duas derrotas seguidas',
            'falas': [('rogerio', f'{" e ".join(advs)}: duas derrotas seguidas do {nos}. Acendeu o alerta?' if len(advs) == 2 else f'Duas derrotas seguidas do {nos}. Acendeu o alerta?'),
                      ('carlao', 'Acendeu, e tem que acender! Time grande não perde dois seguidos sem dar explicação!'),
                      ('helena', 'Calma. Duas derrotas em uma temporada longa acontecem. O que preocupa é se o padrão de jogo mudou.'),
                      ('beto', 'Depois do jogo, o técnico ficou quase uma hora no vestiário com os jogadores. Ninguém saiu falando.'),
                      ('toninho', f'O torcedor do {nos} acordou hoje e foi conferir se não era pesadelo!')],
            'enquete': _enquete('Duas derrotas seguidas: é crise?', [('Não, é fase', 1.0), ('Sim, é crise', 0.8), ('Ainda não, mas preocupa', 1.1)], rnd),
            'posts': [(_torc(M), 'Duas seguidas. Não dá pra normalizar. Bora reagir! 😤')]}


@pauta
def semana_decisiva(M, rnd):
    import momento
    mo = M.get('momento') or {}
    gs = [x for x in mo.get('proximos') or [] if x['tags'] and 0 <= _dias(tuple(x['data']), M['hoje']) <= 10]
    if len(gs) < 2:
        return None
    a, b = gs[0], gs[1]
    ca = a['comp'].replace('UEFA ', '')
    nb = b['classico'] or b['adv']
    return {'id': 'semana_decisiva', 'cat': 'proximo', 'peso': 8, 'titulo': 'A semana da verdade',
            'falas': [('rogerio', f'Que semana: {momento.descreve_jogo(a)} e, logo depois, {momento.descreve_jogo(b)}. Poupar ou ir com tudo?'),
                      ('carlao', 'Com tudo nos dois! Jogador profissional aguenta! Esse papo de poupar é invenção moderna!'),
                      ('helena', f'Os dados físicos dizem o contrário: quem joga os dois jogos em sequência chega ao segundo com menos intensidade. Eu pouparia alguns na {ca}.'),
                      ('beto', f'No CT, a comissão já trabalha com dois times. A ideia é chegar inteiro no {nb}.'),
                      ('toninho', 'Se poupar e perder, a culpa é do técnico. Se não poupar e perder, a culpa é do técnico. Profissão ingrata!')],
            'enquete': _enquete(f'Poupar titulares na {ca} pensando no {nb}?', [('Sim, prioridade é o próximo', 1.0), ('Não, força máxima nos dois', 1.0),
                                                                                 ('Só os mais cansados', 1.2)], rnd),
            'posts': [(_torc(M), f'{ca} e {nb} na mesma semana. Coração não aguenta! 😰')]}


@pauta
def mesa_tatica_explica(M, rnd):
    u = M.get('ult') or {}
    an = [a for a in M.get('analise') or [] if a['chave'] not in ('corrida', 'momento', 'destaque')]
    if not u.get('recente') or len(an) < 2 or list(M.get('analise_data') or []) != list(u['p']['data']):
        return None
    t1, t2 = an[0]['texto'], an[1]['texto']
    return {'id': 'mesa_tatica_explica', 'cat': 'jogo', 'peso': 6.5, 'titulo': 'O que a prancheta explica',
            'falas': [('rogerio', 'A turma da Mesa Tática destrinchou o jogo. Helena, o que eles viram?'),
                      ('helena', f'Dois pontos. Primeiro: {t1[0].lower() + t1[1:]} Segundo: {t2[0].lower() + t2[1:]}'),
                      ('carlao', 'Prancheta é bonito, mas jogo se ganha com vontade! Faltou sangue no olho!'),
                      ('helena', 'Carlão, vontade sem plano vira correria. O adversário tinha um plano.'),
                      ('toninho', 'Lá vem a Helena com a lousa de novo! Daqui a pouco ela escala o time!')]}


@pauta
def como_o_rival_vem(M, rnd):
    import redes_vivas
    pj = M.get('pj') or {}
    if not pj.get('data'):
        return None
    reg = redes_vivas._ia_reg(pj.get('adversario'), pj['data'])
    if not reg or not reg.get('tecnico'):
        return None
    j = redes_vivas._jeito(reg.get('plano'))
    if not j:
        return None
    adv = clube.nome_time(pj.get('adversario'))
    marc = next((i[len('Marcação ('):-1] for i in reg.get('instrucoes') or [] if i.startswith('Marcação (')), None)
    falas = [('rogerio', f'E o {adv}? O {reg["tecnico"]} deve {j}.'),
             ('helena', f'É o perfil do {reg["tecnico"]}. Contra o {_nos(M)}, ele sabe que precisa de um plano para competir.')]
    if marc:
        falas.append(('beto', f'Bastidor: o {adv} treinou marcação individual a semana toda. O alvo seria o {marc}.'))
        falas.append(('carlao', f'Marcar o {marc} homem a homem? Abre espaço para os outros! Tem que saber aproveitar!'))
    else:
        falas.append(('carlao', 'Contra time organizado, tem que ter paciência e não se desesperar!'))
    falas.append(('toninho', f'O {reg["tecnico"]} vai passar a semana inteira vendo vídeo do {_nos(M)}. Vai sonhar com a gente!'))
    return {'id': 'como_o_rival_vem', 'cat': 'proximo', 'peso': 6.5, 'titulo': f'Como o {adv} deve jogar', 'falas': falas}


import bola_na_mesa as _B  # noqa: E402
_B.POS_SO.update({'mesa_tatica_explica', 'duas_derrotas'})
_B.PRE_SO.update({'como_o_rival_vem'})
