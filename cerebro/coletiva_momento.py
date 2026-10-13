# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""COLETIVAS — LOTE 3 (12/10/2026): o MOMENTO, não só o último jogo.

Pedido do usuário: "na vitória eu vi, mas na derrota eles não falam da quantidade de derrotas acumuladas — perdemos duas
seguidas, o rival encostou, precisamos nos recuperar na Champions e no campeonato, o clássico está chegando". Os
cenários daqui leem car['momento'] (momento.py: sequência, tabela agora x duas rodadas atrás, agenda) e a forma dos
jogadores nas últimas súmulas:
  a sequência   duas derrotas seguidas, série de derrotas, vitória que alivia, invencibilidade longa;
  a tabela      liderança perdida/conquistada, rival que encostou, rival que disparou, distância que caiu,
                desempenho contra os grandes, a força (ou a fraqueza) em casa;
  a agenda      semana decisiva (Champions + clássico), reagir na Champions, clássico sob pressão, maratona;
  as pessoas    craque em má fase, fase iluminada, substituição que irritou, duelo de artilheiros;
  as vozes      o técnico rival provocou, o comentarista do Bola na Mesa criticou, a leitura da Mesa Tática,
                "todo mundo se fecha contra vocês" (planos que a IA adversária usou).
"""
import json
import os

import clube
import coletiva_cenarios as CC
from coletiva_cenarios import E, G, cen, op, _seq
from coletiva_extra import _t, _pts, _q, _jog_por_nome

MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
NUM = {2: 'duas', 3: 'três', 4: 'quatro', 5: 'cinco', 6: 'seis', 7: 'sete', 8: 'oito'}


def _M(X):
    return X.get('momento') or {}


def _L(X):
    return _M(X).get('liga') or {}


def _rv(X):
    return _L(X).get('rival') or {}


def _fim(X):
    """Mês em que a liga termina (maio na Europa; dezembro nas ligas de ano civil)."""
    try:
        import temporada
        if temporada.ATUAL.get('ini') and temporada.anual(temporada.ATUAL['ini']):
            return 'dezembro'
    except Exception:  # noqa: BLE001
        pass
    return 'maio'


def _mes(X):
    return MESES[X['hoje'][1] - 1]


def _ult_advs(X, n):
    return [_t(g['adversario']) for g in X['ultimos'][-n:]]


def _grandes(X, dias=10):
    return [x for x in _M(X).get('proximos') or [] if x['tags'] and x['dias'] <= dias]


def _desc(x):
    import momento
    return momento.descreve_jogo(x)


def _quando(d):
    return 'hoje' if d == 0 else 'amanhã' if d == 1 else f'daqui a {d} dias'


def _pior(X):
    ls = [x for x in X['linhas'] if x['min'] >= 45 and x['nota']]
    return min(ls, key=lambda x: x['nota'], default=None)


def _forma_jog(X, j, n=3):
    """Notas e participações em gols de um jogador nos últimos n jogos em que atuou (súmulas da reunião)."""
    k = tuple(j['k'])
    notas, ga = [], 0
    for linhas in reversed(X.get('hist') or []):
        x = next((y for y in linhas if (y['reg'], y['pid']) == k and y.get('minutos', 0) >= 30), None)
        if x and x.get('nota'):
            notas.append(x['nota'])
            ga += x['gols'] + x['assist']
        if len(notas) >= n:
            break
    return notas, ga


# ================================================================ a sequência
@cen
def duas_derrotas_seguidas(X, rnd):
    s = _seq(X)
    if X['res'] != 'D' or s['d'] != 2 or len(X['ultimos']) < 2:
        return None
    a, b = _ult_advs(X, 2)
    raro = 'DD' not in ''.join(s['res'][:-2])
    formas = [f'{a} e {b}: duas derrotas seguidas. O que aconteceu com o time?',
              f'Duas derrotas em sequência, para o {a} e o {b}. É hora de acender o alerta?']
    if raro:
        formas.append('É a primeira vez na temporada que o time perde dois jogos seguidos. O que mudou de uma semana para cá?')
    return 9, 'crise', _q(rnd, *formas), [
        op('O alerta acendeu, e eu sou o primeiro a reconhecer. Mas este grupo já mostrou do que é capaz. Não vou rasgar o trabalho por duas derrotas.',
           [G(1, 'o técnico protegeu o trabalho depois de duas derrotas')], 'Técnico: "não vou rasgar o trabalho por duas derrotas"', 'Discurso de calma na primeira turbulência.'),
        op('Faltou intensidade nos dois jogos. Quem não estiver disposto a correr vai assistir ao próximo de fora.',
           [G(-2, 'o técnico ameaçou tirar quem não corresse', 2)], 'Técnico ameaça: "quem não correr vai assistir de fora"', 'Cobrança pública depois da sequência ruim.'),
        op(f'Contra o {a} e o {b} criamos para vencer. O resultado não veio, mas o caminho é esse.',
           [G(1, 'o técnico defendeu a atuação do time')], 'Técnico vê o time no caminho certo apesar das derrotas', 'Leitura que a torcida contesta.')]


@cen
def derrotas_em_serie(X, rnd):
    s = _seq(X)
    if X['res'] != 'D' or s['d'] < 3:
        return None
    n = NUM.get(s['d'], s['d'])
    return 9.6, 'pressao', _q(rnd, f'{str(n).capitalize()} derrotas seguidas. O vestiário ainda acredita em você?',
                             f'Já são {n} derrotas em sequência. Em que momento isso vira crise?',
                             f'{str(n).capitalize()} derrotas seguidas: o que você disse aos jogadores depois do jogo?'), [
        op('Acredita. Eu vejo nos treinos, vejo nos olhos deles. Uma sequência ruim não apaga o que construímos.',
           [G(2, 'o técnico garantiu que o grupo segue com ele')], 'Técnico garante: "o grupo acredita"', 'Respaldo em meio à crise.'),
        op('Vou mexer. Tem gente que perdeu a vaga hoje, e vai saber disso no treino de amanhã.',
           [G(-2, 'o técnico anunciou mudanças e cobrou o elenco', 2)], 'Técnico anuncia mudanças no time', 'Clima tenso no vestiário.'),
        op('Peço desculpas à torcida. A responsabilidade é minha, e a solução também vai ser.',
           [G(2, 'o técnico assumiu a culpa pela sequência')], 'Técnico pede desculpas e assume a culpa', 'Postura elogiada até pelos críticos.')]


@cen
def vitoria_que_alivia(X, rnd):
    s = _seq(X)
    res = s['res']
    if X['res'] != 'V' or len(res) < 3 or res[-2] != 'D' or res[-3] != 'D':
        return None
    gs = _grandes(X)
    seguinte = f' E agora vem {_desc(gs[0])}.' if gs else ''
    return 8, 'resultado', _q(rnd, f'Vitória depois de duas derrotas. Alívio ou só o começo?{seguinte}',
                             f'O time voltou a vencer. Foi a resposta que você queria?{seguinte}'), [
        op('Alívio não. Obrigação. Agora é emendar uma sequência e esquecer as duas derrotas.',
           [G(1, 'o técnico cobrou sequência depois da vitória')], 'Técnico: "vencer era obrigação"', 'Exigência mesmo na volta por cima.'),
        op('Foi a resposta de um grupo que ficou incomodado. Eu gosto de time incomodado.',
           [G(3, 'o técnico exaltou a reação do grupo')], '"Gosto de time incomodado": técnico exalta a reação', 'Moral em alta no vestiário.'),
        op('Ainda tem muito para corrigir. Não vou me iludir com uma vitória.',
           [G(0, 'o técnico manteve os pés no chão')], 'Técnico não se ilude com a vitória', 'Cautela no discurso.')]


@cen
def invicto_longo(X, rnd):
    s = _seq(X)
    if X['res'] == 'D' or s['inv'] < 10:
        return None
    return 6.5, 'sequencia', _q(rnd, f'{s["inv"]} jogos sem perder. Qual é o segredo?', f'O time está invicto há {s["inv"]} jogos. Dá para chegar ao fim da temporada assim?'), [
        op('Não tem segredo: treino, concentração e um grupo que se cobra.', [G(1, 'o técnico creditou a invencibilidade ao grupo')],
           'Técnico: "não tem segredo, tem trabalho"', 'Discurso pé no chão.'),
        op(f'Invencibilidade é consequência. Eu quero é título, e título não se ganha em {_mes(X)}.', [G(2, 'o técnico apontou a meta maior')],
           'Técnico mira o título, não a invencibilidade', 'Ambição declarada.'),
        op('Uma hora vamos perder. O importante é como a gente vai reagir quando acontecer.', [G(0, 'o técnico preparou o grupo para a derrota')],
           'Técnico prepara o grupo: "uma hora vamos perder"', 'Frase vira assunto nas redes.')]


# ================================================================ a tabela
@cen
def perdeu_lideranca(X, rnd):
    L, rv = _L(X), _rv(X)
    if L.get('lideranca') != 'perdeu' or not rv:
        return None
    gs = _grandes(X, 14)
    direto = next((x for x in gs if x['adv'].upper() == rv['nome'].upper()), None)
    fim = _fim(X)
    return 9.2, 'corrida', _q(rnd, f'O {rv["nome"]} tomou a liderança. Quanto pesa perder a ponta agora?',
                             f'A ponta ficou com o {rv["nome"]}, {_pts(rv["dif"])} à frente. Dá para retomar?',
                             f'O time saiu da liderança pela primeira vez em semanas. Preocupa?'), [
        op(f'Liderança em {MESES[X["hoje"][1] - 1]} não dá título. Dá título quem estiver na frente em {fim}.',
           [G(1, 'o técnico minimizou a perda da liderança')], f'Técnico: "liderança em {MESES[X["hoje"][1] - 1]} não dá título"', 'Calma diante da tabela.'),
        op('Doeu perder a ponta, e é bom que doa. O grupo precisa sentir isso para reagir.',
           [G(1, 'o técnico usou a perda da liderança para mexer com o grupo')], 'Técnico: "é bom que doa"', 'Ferida aberta no vestiário.'),
        op(f'O {rv["nome"]} vai ter que nos encarar' + (f' {_quando(direto["dias"])}. É no campo que a gente pega de volta.' if direto else '. É no campo que a gente pega de volta.'),
           [G(3, 'o técnico prometeu retomar a liderança em campo', 2)], f'Recado ao {rv["nome"]}: "vamos pegar de volta"', 'O confronto direto ganha temperatura.')]


@cen
def assumiu_lideranca(X, rnd):
    L, rv = _L(X), _rv(X)
    if L.get('lideranca') != 'assumiu':
        return None
    quem = f' do {rv["nome"]}' if rv else ''
    return 7.5, 'corrida', _q(rnd, f'O time assumiu a liderança{quem}. Muda alguma coisa?', 'Líder! Agora o time passa a ser caçado. Está preparado?'), [
        op('Muda que agora todo mundo quer ganhar da gente. Ótimo: é assim que time grande vive.', [G(2, 'o técnico abraçou o papel de líder')],
           'Técnico: "agora todo mundo quer ganhar da gente"', 'Confiança de líder.'),
        op('Não muda nada. Faltam muitas rodadas, e a tabela de hoje não vale troféu.', [G(1, 'o técnico pediu pés no chão')],
           'Técnico segura a euforia da liderança', 'Discurso prudente.'),
        op(f'Bom para a torcida dormir feliz. Mas eu só comemoro em {_fim(X)}.', [G(1, 'o técnico brincou com a liderança')],
           f'Técnico brinca: "só comemoro em {_fim(X)}"', 'Leveza no discurso.')]


@cen
def rival_encostou(X, rnd):
    L, rv = _L(X), _rv(X)
    if rv.get('movimento') != 'encostou' or L.get('lideranca') == 'perdeu':
        return None
    p = (f'Eram {_pts(rv["dif_antes"])} de vantagem, agora {"é só 1" if rv["dif"] == 1 else "são " + str(rv["dif"])}. O {rv["nome"]} está chegando?' if rv['dif'] > 0
         else f'O {rv["nome"]} alcançou o time na pontuação. A liderança está por um fio?')
    return 8.7, 'corrida', p, [
        op('Deixa chegar. Pressão de quem vem atrás é normal. A gente tem que olhar para o nosso jogo.',
           [G(1, 'o técnico tratou a aproximação do rival com calma')], f'Técnico sobre o {rv["nome"]}: "deixa chegar"', 'Frieza na corrida.'),
        op('Estamos dando espaço, e a culpa é nossa. Não dá para tropeçar de novo.',
           [G(1, 'o técnico admitiu que o time deu espaço ao rival')], 'Técnico admite: "estamos dando espaço"', 'Autocrítica na corrida pelo título.'),
        op(f'O {rv["nome"]} encostou, mas não passou. E não vai passar.',
           [G(2, 'o técnico garantiu a liderança')], f'"Não vai passar": técnico desafia o {rv["nome"]}', 'Frase vira provocação.')]


@cen
def rival_disparou(X, rnd):
    rv = _rv(X)
    if rv.get('movimento') != 'disparou':
        return None
    return 8, 'corrida', _q(rnd, f'O {rv["nome"]} abriu {_pts(rv["dif"])}. A liga escapou?',
                           f'Eram {_pts(rv["dif_antes"])} de distância, agora são {abs(rv["dif"])}. Ainda dá para alcançar o {rv["nome"]}?'), [
        op('Não escapou nada. Eles ainda vão tropeçar, e nós precisamos estar perto quando acontecer.',
           [G(2, 'o técnico manteve a fé na liga')], 'Técnico: "a liga não escapou"', 'Discurso de quem não desiste.'),
        op(f'O {rv["nome"]} está numa fase muito boa, é justo reconhecer. Nós precisamos fazer muito mais.',
           [G(0, 'o técnico reconheceu a superioridade do rival')], f'Técnico reconhece a fase do {rv["nome"]}', 'Realismo que esfria a torcida.'),
        op('Agora é jogo a jogo, sem calculadora. Quem faz conta antes da hora perde o foco.',
           [G(1, 'o técnico pediu foco jogo a jogo')], 'Técnico guarda a calculadora', 'Foco no próximo jogo.')]


@cen
def distancia_caiu(X, rnd):
    rv = _rv(X)
    mv = rv.get('movimento')
    if mv not in ('aproximamos', 'ficou_para_tras'):
        return None
    if mv == 'aproximamos':
        p = f'A distância para o {rv["nome"]} caiu de {abs(rv["dif_antes"])} para {abs(rv["dif"])}. O time está de volta à briga?'
    else:
        p = f'A vantagem sobre o {rv["nome"]} subiu para {_pts(rv["dif"])}. Já dá para respirar?'
    return 6.8, 'corrida', p, [
        op('O trabalho aparece quando a gente para de olhar a tabela e olha o próprio jogo.', [G(1, 'o técnico creditou a boa fase ao trabalho')],
           'Técnico: "o trabalho aparece"', 'Confiança em alta.'),
        op('Ninguém respira em campeonato longo. Uma semana ruim e tudo volta.', [G(1, 'o técnico pediu atenção mesmo na boa fase')],
           'Técnico: "ninguém respira"', 'Cautela na boa fase.'),
        op(f'Quem vai ter que respirar fundo é o {rv["nome"]}.', [G(2, 'o técnico provocou o rival na tabela')],
           f'Técnico provoca o {rv["nome"]}', 'O rival responde nas redes.')]


@cen
def contra_os_grandes(X, rnd):
    ct = _L(X).get('contra_topo') or {}
    n = sum(ct.values()) if ct else 0
    if n < 3:
        return None
    v, e, d = ct['v'], ct['e'], ct['d']
    if v <= 1 and e + d >= 2:
        return 7, 'estilo', _q(rnd, f'Contra os times de cima da tabela, foram {v} vitória{"s" if v != 1 else ""} em {n} jogos. Falta algo nos jogos grandes?',
                               f'O time sobra contra os pequenos e sofre contra os grandes ({v}V {e}E {d}D). Por quê?'), [
            op('Jogo grande se decide em detalhe, e nos detalhes temos falhado. Já estamos trabalhando nisso.', [G(1, 'o técnico reconheceu a falha nos jogos grandes')],
               'Técnico admite falhas nos jogos grandes', 'Autocrítica.'),
            op('Esse número vai mudar. Título se ganha contra todos, e este time sabe disso.', [G(2, 'o técnico prometeu virar a chave nos jogos grandes')],
               'Técnico promete mudar o retrospecto contra os grandes', 'Promessa registrada.'),
            op('Ponto contra pequeno vale o mesmo que contra grande. Prefiro assim do que o contrário.', [G(0, 'o técnico relativizou o retrospecto')],
               'Técnico relativiza o retrospecto nos jogos grandes', 'Argumento divide opiniões.')]
    if v >= 3 and d == 0:
        return 6, 'estilo', f'Contra os grandes da liga, {v} vitórias e nenhuma derrota em {n} jogos. Esse time cresce nos jogos grandes?', [
            op('Jogo grande é onde o jogador gosta de estar. O meu elenco gosta de holofote.', [G(2, 'o técnico exaltou o elenco nos jogos grandes')],
               'Técnico: "o elenco gosta de holofote"', 'Moral alta.'),
            op('Me preocupo mais com os jogos contra os pequenos. É ali que se perde campeonato.', [G(1, 'o técnico alertou para os jogos menores')],
               'Técnico alerta para os jogos "pequenos"', 'Leitura de quem conhece a liga.'),
            op('Números bonitos, mas não ganham nada sozinhos.', [], 'Técnico não se apega aos números', 'Discurso seco.')]
    return None


@cen
def fortaleza_em_casa(X, rnd):
    cs = _L(X).get('em_casa') or {}
    n = sum(cs.values()) if cs else 0
    est = clube.C.get('estadio') or 'o estádio'
    if n >= 4 and cs['d'] + cs['e'] >= 3 and X['casa']:
        return 7, 'resultado', _q(rnd, f'{est} deixou de ser fortaleza? Em casa foram {cs["v"]} vitórias em {n} jogos na liga.',
                                  f'Os visitantes estão perdendo o medo de jogar em {est}?'), [
            op('A torcida é o nosso 12º jogador. Quem tem que voltar a meter medo somos nós, em campo.', [G(1, 'o técnico chamou a responsabilidade em casa')],
               'Técnico: "temos que voltar a meter medo em casa"', 'Recado ao elenco.'),
            op('Em casa o adversário se fecha, e ainda não achamos a chave para isso. É trabalho de treino.', [G(0, 'o técnico explicou a dificuldade em casa')],
               'Técnico explica as dificuldades em casa', 'Leitura tática.'),
            op('Peço paciência à torcida. Vaia não ajuda quem está dentro de campo.', [G(-1, 'o técnico pediu que a torcida não vaiasse')],
               'Técnico pede paciência à torcida', 'Nem todo mundo gostou do pedido.')]
    if n >= 4 and cs['d'] == 0 and cs['v'] >= n - 1:
        return 5.5, 'resultado', f'Em casa, {cs["v"]} vitórias em {n} jogos na liga. {est} virou território proibido?', [
            op('Jogar aqui com essa torcida é covardia. Eles empurram o time do primeiro ao último minuto.', [G(2, 'o técnico dividiu a fortaleza com a torcida')],
               'Técnico exalta a torcida', 'Arquibancada orgulhosa.'),
            op('Em casa a obrigação é vencer. Não tem mérito extra nisso.', [G(0, 'o técnico tratou o retrospecto como obrigação')],
               'Técnico: "em casa é obrigação"', 'Exigência máxima.'),
            op('Quero o mesmo fora de casa. Time campeão ganha em qualquer lugar.', [G(1, 'o técnico cobrou desempenho fora')],
               'Técnico cobra o time fora de casa', 'Próximo desafio definido.')]
    return None


# ================================================================ a agenda
@cen
def semana_decisiva(X, rnd):
    gs = _grandes(X)
    if len(gs) < 2:
        return None
    a, b = gs[0], gs[1]
    gap = b['dias'] - a['dias']
    formas = [f'Pela frente, {_desc(a)} e, {gap} dias depois, {_desc(b)}. É a semana da temporada?']
    if 'continental' in a['tags'] and 'classico' in b['tags']:
        formas.append(f'Vai poupar alguém na {a["comp"].replace("UEFA ", "")} pensando no {b["classico"]}?')
    if _seq(X)['d'] >= 2:
        formas.append(f'Duas derrotas seguidas e agora {_desc(a)} e {_desc(b)}. O time chega pronto para essa semana?')
    return 9, 'semana', _q(rnd, *formas), [
        op('São duas finais. Vou com o que tenho de melhor nas duas, e o físico vai ter que aguentar.',
           [G(2, 'o técnico tratou a semana como duas finais', 2)], 'Técnico: "são duas finais"', 'Força máxima prometida.'),
        op(f'Vou administrar. Alguns começam no banco no primeiro jogo para chegar inteiros {_quando(b["dias"])}.',
           [G(1, 'o técnico anunciou rodízio na semana decisiva')], f'Técnico vai poupar pensando no {b["classico"] or b["adv"]}', 'Rodízio em semana decisiva divide opiniões.'),
        op(f'Não existe semana da temporada em {MESES[X["hoje"][1] - 1]}. Existe o próximo jogo, um de cada vez.',
           [G(0, 'o técnico tirou o peso da semana')], 'Técnico: "um jogo de cada vez"', 'Frase de manual que a torcida já conhece.')]


@cen
def reagir_na_champions(X, rnd):
    ps = _M(X).get('proximos') or []
    if X['res'] != 'D' or not ps or 'continental' not in ps[0]['tags'] or ps[0]['dias'] > 5:
        return None
    a = ps[0]
    comp = a['comp'].replace('UEFA ', '')
    pior = _pior(X)
    return 8.3, 'reacao', _q(rnd, f'Depois da derrota para o {_t(X["adv"])}, a {comp} chega {_quando(a["dias"])}. É o lugar para reagir?',
                            f'A {comp} contra o {a["adv"]} pode ser o remédio depois da derrota?'), [
        op(f'Noite de {comp} acorda qualquer jogador. Não preciso motivar ninguém para esse jogo.',
           [G(2, 'o técnico confiou na noite europeia para a reação')], f'Técnico aposta na {comp} para reagir', 'Clima de noite grande.'),
        op(f'A {comp} não pode virar fuga. O problema da liga se resolve na liga.',
           [G(0, 'o técnico separou os problemas')], f'Técnico: "a {comp} não é fuga"', 'Discurso racional.'),
        op('Vou dar chance a quem está com fome. Quem foi mal hoje sabe que vai ter de esperar.',
           [G(-1, 'o técnico avisou que vai mexer no time')] + ([E(pior['kc'], -3, 2, 'o técnico deu a entender que ele perde a vaga')] if pior else []),
           'Técnico promete mudanças para a Champions', 'Quem foi mal já sabe.')]


@cen
def classico_sob_pressao(X, rnd):
    ps = _M(X).get('proximos') or []
    c = next((x for x in ps if 'classico' in x['tags'] and x['dias'] <= 8), None)
    s = _seq(X)
    if not c or (X['res'] != 'D' and s['sv'] < 2):
        return None
    rv = _rv(X)
    vale = rv and rv['nome'].upper() == c['adv'].upper() and _L(X).get('pos', 9) <= 2
    queda = ('duas derrotas' if s['d'] == 2 else f'{NUM.get(s["d"], s["d"])} derrotas' if s['d'] > 2
             else f'{NUM.get(s["sv"], s["sv"])} jogos sem vencer' if s['sv'] >= 2 else 'uma derrota')
    p = (f'O {c["classico"]} contra o {c["adv"]} vale a liderança, e o time chega depois de {queda}. Como encarar?' if vale
         else f'Chegar ao {c["classico"]} depois de {queda}: o {c["adv"]} pega o time na pior hora?')
    return 9.5 if vale else 9.1, 'proximo', p, [
        op('Clássico apaga qualquer fase. Ninguém precisa me dizer o que esse jogo vale para o torcedor.',
           [G(3, 'o técnico usou o clássico para virar a chave', 2)], f'Técnico: "o {c["classico"]} apaga qualquer fase"', 'O clássico vira chance de redenção.'),
        op(f'O {c["adv"]} vai encontrar um time ferido. E time ferido é o mais perigoso que existe.',
           [G(2, 'o técnico prometeu um time mordido no clássico')], f'Recado ao {c["adv"]}: "time ferido é perigoso"', 'Provocação esquenta a semana.'),
        op('Se a gente não tiver humildade, o clássico vira castigo. É hora de trabalhar calado.',
           [G(1, 'o técnico pediu humildade antes do clássico')], 'Técnico pede humildade antes do clássico', 'Semana de treino fechado.')]


@cen
def maratona(X, rnd):
    m = _M(X).get('maratona')
    if not m:
        return None
    cans = [j for j in X['J'] if j.get('condicao') is not None and j['condicao'] < 80 and j['t_jogos'] >= 5]
    return 6.8, 'fisico', _q(rnd, f'Três jogos em {m["dias"]} dias. Como administrar o elenco?',
                            f'Maratona pela frente: três jogos em {m["dias"]} dias. Vai rodar o time?'), [
        op('Vou rodar. Tenho 25 jogadores e confio em todos. Esse é o momento de mostrar.', [G(2, 'o técnico prometeu oportunidades na maratona')],
           'Técnico promete rodízio na maratona', 'Reservas animados.'),
        op('Quem estiver melhor joga. Não escolho time pelo calendário.', [G(-1, 'o técnico ignorou o desgaste do calendário')]
           + [E(j['kc'], -1, 2, 'deve jogar cansado na maratona') for j in cans[:2]],
           'Técnico ignora o calendário', 'O departamento médico fica em alerta.'),
        op('A comissão de preparação física decide comigo, jogo a jogo, pelos números.', [G(1, 'o técnico confiou na ciência')],
           'Técnico vai decidir pelos números do físico', 'Gestão moderna.')]


# ================================================================ as pessoas
@cen
def queda_de_rendimento(X, rnd):
    H = X.get('hist') or []
    if len(H) < 6:
        return None
    med = lambda ls: [x['nota'] for x in ls if x.get('minutos', 0) >= 45 and x.get('nota')]
    rec = [n for ls in H[-3:] for n in med(ls)]
    ant = [n for ls in H[-8:-3] for n in med(ls)]
    if not rec or not ant:
        return None
    a, b = sum(rec) / len(rec), sum(ant) / len(ant)
    if b - a < 0.35 or a > 6.6:
        return None
    return 7, 'rendimento', _q(rnd, f'A média de notas do time caiu de {b:.1f} para {a:.1f} nos últimos três jogos. Cansaço ou acomodação?',
                              'O time parece ter perdido o ritmo das primeiras semanas. O que explica?'), [
        op('Cansaço. O calendário está pesado, e isso aparece nas pernas e na cabeça.', [G(1, 'o técnico atribuiu a queda ao calendário')],
           'Técnico culpa o calendário pela queda', 'Explicação física.'),
        op('Acomodação, sim. Tem jogador que achou que já tinha ganhado alguma coisa.', [G(-2, 'o técnico acusou o elenco de acomodação', 2)],
           'Técnico acusa: "tem jogador acomodado"', 'Frase pesada no vestiário.'),
        op('Os adversários nos estudaram. É hora de eu mexer, não de culpar ninguém.', [G(2, 'o técnico assumiu a responsabilidade de mudar')],
           'Técnico promete mudanças táticas', 'O técnico chama a responsabilidade.')]


@cen
def craque_em_ma_fase(X, rnd):
    les = (X.get('lesao') or {}).get('nome')
    tops = sorted((j for j in X['J'] if j['t_jogos'] >= 6 and j['nome'] != les), key=lambda j: -j['ovr'])[:6]
    for j in tops:
        notas, ga = _forma_jog(X, j)
        if len(notas) >= 3 and sum(notas) / 3 <= j['t_nota'] - 0.6 and ga == 0:
            m = sum(notas) / 3
            return 7.2, 'jogador', _q(rnd, f'O {j["nome"]} não é o mesmo das primeiras rodadas: média {m:.1f} nos últimos três jogos. O que acontece com ele?',
                                     f'A torcida já pergunta pelo {j["nome"]}. Ele está em má fase?'), [
                op(f'O {j["nome"]} tem crédito para o resto da vida. Fase ruim todo craque tem, e ele vai sair dessa.',
                   [E(j['kc'], 4, 3, 'o técnico o defendeu em público na má fase')], f'Técnico blinda {j["nome"]}', 'Proteção ao craque.'),
                op(f'Conversei com ele. Precisa voltar a fazer o simples. Está tentando resolver tudo sozinho.',
                   [E(j['kc'], 1, 2, 'o técnico explicou em público o que falta para ele')], f'Técnico revela conversa com {j["nome"]}', 'Diagnóstico público.'),
                op(f'Ninguém tem vaga cativa. Se o {j["nome"]} não render, quem está no banco vai jogar.',
                   [E(j['kc'], -4, 3, 'o técnico ameaçou tirá-lo do time'), G(1, 'os reservas ganharam esperança')],
                   f'{j["nome"]} ameaçado de perder a vaga', 'Recado direto ao craque.')]
    return None


@cen
def fase_iluminada(X, rnd):
    for j in sorted((j for j in X['J'] if j['t_jogos'] >= 4), key=lambda j: -j['t_gols'] - j['t_assist']):
        notas, ga = _forma_jog(X, j)
        if len(notas) >= 3 and sum(notas) / 3 >= 7.4 and ga >= 3:
            return 6.8, 'jogador', _q(rnd, f'{j["nome"]}: {ga} participações em gol nos últimos três jogos. É a melhor fase da carreira dele?',
                                     f'O {j["nome"]} está voando. Até onde ele pode chegar?'), [
                op(f'O {j["nome"]} está no nível dos melhores do mundo. E ainda pode mais.', [E(j['kc'], 4, 3, 'o técnico o colocou entre os melhores do mundo')],
                   f'Técnico: "{j["nome"]} está entre os melhores do mundo"', 'Elogio que vira manchete.'),
                op('Fase boa é fruto de trabalho. Ele chega antes e sai depois de todo mundo do treino.', [E(j['kc'], 3, 2, 'o técnico elogiou a dedicação dele'), G(1, 'o técnico deu o exemplo ao grupo')],
                   f'Técnico revela a rotina de {j["nome"]}', 'Exemplo para o elenco.'),
                op('Bom, mas não quero ninguém deslumbrado. Elogio demais atrapalha.', [E(j['kc'], -1, 2, 'o técnico freou os elogios a ele')],
                   f'Técnico freia a euforia com {j["nome"]}', 'Pés no chão.')]
    return None


@cen
def substituido_cedo(X, rnd):
    if X['res'] == 'V':
        return None
    tops = {j['nome'] for j in sorted(X['J'], key=lambda j: -j['ovr'])[:6]}
    x = next((x for x in X['linhas'] if x['nome'] in tops and x.get('titular') and 30 <= x['min'] <= 70), None)
    if not x:
        return None
    return 7.3, 'escalacao', _q(rnd, f'O {x["nome"]} saiu aos {x["min"]} minutos. Foi opção técnica ou ele sentiu alguma coisa?',
                               f'O {x["nome"]} deixou o campo com cara de poucos amigos. Ele não gostou de sair?'), [
        op('Opção técnica. O jogo pedia outra característica naquele momento, e eu fui atrás do resultado.',
           [E(x['kc'], -2, 2, 'saiu por opção técnica e o técnico disse isso em público')], f'Técnico explica a saída de {x["nome"]}', 'Decisão técnica.'),
        op('Ele sentiu um desconforto e eu preferi não arriscar. Não foi nada grave.',
           [E(x['kc'], 1, 1, 'o técnico o protegeu na coletiva')], f'{x["nome"]} saiu por precaução', 'O departamento médico tranquiliza.'),
        op(f'Saiu porque não estava bem. Aqui ninguém tem lugar cativo, nem o {x["nome"]}.',
           [E(x['kc'], -4, 3, 'o técnico o expôs em público pela substituição'), G(1, 'o grupo viu que ninguém tem lugar cativo')],
           f'"Nem o {x["nome"]} tem lugar cativo"', 'A relação com o craque vira assunto.')]


@cen
def duelo_de_artilheiros(X, rnd):
    p = X.get('prox')
    if not p:
        return None
    cl = (X.get('mundo') or {}).get('clubes') or {}
    deles = next((x for x in cl.get(p['adv']) or [] if x['jogos'] >= 3 and x['gols'] >= 5), None)
    les = (X.get('lesao') or {}).get('nome')
    nosso = max((j for j in X['J'] if j['nome'] != les), key=lambda j: j['t_gols'], default=None)
    if not deles or not nosso or nosso['t_gols'] < 5:
        return None
    adv = _t(p['adv'])
    return 6.5, 'duelo', _q(rnd, f'{nosso["nome"]} ({nosso["t_gols"]} gols) contra {deles["nome"]} ({deles["gols"]}). O duelo dos artilheiros decide o jogo com o {adv}?',
                           f'Como parar o {deles["nome"]}, artilheiro do {adv} com {deles["gols"]} gols?'), [
        op(f'Não se para um jogador como o {deles["nome"]} com um homem só. É o time inteiro defendendo.', [G(1, 'o técnico pediu marcação coletiva')],
           f'Técnico tem plano coletivo para o {deles["nome"]}', 'Respeito ao artilheiro rival.'),
        op(f'Eu prefiro me preocupar com o {nosso["nome"]}. Eles é que têm que se preocupar com ele.', [E(nosso['kc'], 3, 2, 'o técnico o colocou acima do artilheiro rival')],
           f'"Eles que se preocupem com o {nosso["nome"]}"', 'Confiança no artilheiro da casa.'),
        op('Jogo não é duelo de dois jogadores. Ganha quem jogar melhor coletivamente.', [], 'Técnico: "não é duelo de dois"', 'Resposta protocolar.')]


# ================================================================ as vozes de fora
def _frase_rival(X, rnd, adv, classico):
    X = dict(X, nos=clube.C.get('nome') or _t(X['nos']))
    s = _seq(X)
    L = _L(X)
    if s['d'] >= 2 or s['sv'] >= 3:
        return rnd.choice([f'"O {X["nos"]} está nervoso. Dá para sentir de longe."', f'"Pegamos o {X["nos"]} na hora certa. Eles estão em dúvida, nós não."'])
    if L.get('pos') == 1:
        return rnd.choice(['"A pressão é toda deles. Nós vamos lá para nos divertir."', '"Quem está na frente é que tem medo de perder. Nós não temos nada a perder."'])
    if classico:
        return rnd.choice(['"Clássico não tem favorito, e eles sabem disso."', f'"A cidade é nossa. Depois do jogo, o {X["nos"]} vai lembrar disso."'])
    return rnd.choice([f'"Respeito o {X["nos"]}, mas não temos medo de ninguém."', '"Vamos jogar de igual para igual, como sempre."'])


@cen
def tecnico_rival_provoca(X, rnd):
    p = X.get('prox')
    if not p:
        return None
    ps = _M(X).get('proximos') or []
    x0 = ps[0] if ps else {'tags': []}
    if not (x0['tags'] or p.get('classico')):
        return None
    tec = (X.get('ia_prox') or {}).get('tecnico')
    adv = _t(p['adv'])
    quem = f'O {tec}, técnico do {adv},' if tec else f'O técnico do {adv}'
    frase = _frase_rival(X, rnd, adv, p.get('classico'))
    return 7.6, 'rival', f'{quem} disse hoje: {frase} Quer responder?', [
        op('Não respondo técnico adversário. Eu respondo em campo.', [G(1, 'o técnico não entrou na provocação')],
           f'Técnico ignora provocação do {adv}', 'Elegância antes do jogo.'),
        op('Cada um cuida da própria casa. A dele tem bastante coisa para arrumar.', [G(2, 'o técnico devolveu a provocação')],
           f'Técnico rebate: "a casa dele tem muito para arrumar"', 'Guerra de declarações esquenta o jogo.'),
        op('Ele tem razão em uma coisa: o jogo vai ser decidido em campo. E lá a gente se encontra.', [G(1, 'o técnico respondeu com ironia')],
           'Técnico responde com ironia', 'O duelo de técnicos ganha um capítulo.')]


@cen
def comentarista_critica(X, rnd):
    M = _M(X)
    cl = M.get('clima')
    if cl in ('crise', 'alerta'):
        quem, frase = rnd.choice([('Carlão Pereira', 'perdeu a alma'), ('Carlão Pereira', 'está jogando com o freio de mão puxado'),
                                  ('Toninho Marrento', 'virou freguês de qualquer um'), ('Carlão Pereira', 'está sentindo o peso de ser favorito')])
        p = f'No Bola na Mesa, {quem} disse que o time "{frase}". Concorda?'
        return 6.8, 'imprensa', p, [
            op('Respeito a opinião, mas quem está no dia a dia vê outra coisa.', [G(1, 'o técnico defendeu o grupo da crítica da TV')],
               f'Técnico rebate {quem}', 'O programa promete responder.'),
            op('Tem um fundo de verdade. Eu mesmo já disse isso ao grupo, com outras palavras.', [G(-1, 'o técnico concordou com a crítica da TV')],
               f'Técnico concorda com {quem}', 'O vestiário assiste ao programa.'),
            op(f'O {quem.split()[0]} fala isso desde quando a gente ganhava. Não muda nada.', [G(1, 'o técnico ironizou o comentarista')],
               f'Técnico ironiza {quem}', 'Bancada do Bola na Mesa reage.')]
    if cl == 'embalado':
        p = 'No Bola na Mesa, a Helena Saraiva mostrou que este é o melhor momento do time na temporada, pelos números. Você sente isso?'
        return 5.8, 'imprensa', p, [
            op('Sinto no treino. A intensidade está lá em cima.', [G(2, 'o técnico confirmou o bom momento')], 'Técnico confirma o melhor momento', 'Confiança.'),
            op('Número é bom para televisão. Eu prefiro título.', [G(0, 'o técnico desdenhou dos números')], 'Técnico: "prefiro título a número"', 'Resposta seca.'),
            op('O melhor momento ainda não chegou. Esse time pode mais.', [G(2, 'o técnico disse que o time pode mais')], '"O melhor ainda não chegou"', 'Ambição.')]
    return None


@cen
def leitura_da_mesa_tatica(X, rnd):
    an = [a for a in X.get('analise') or [] if a['chave'] not in ('destaque', 'corrida', 'momento', 'algoz')]
    if not an or X['res'] == 'V' and an[0]['chave'] not in ('costas', 'marcacao_falhou'):
        return None
    t = an[0]['texto'].rstrip('.')
    return 7, 'tatica', _q(rnd, f'A Mesa Tática apontou: "{t}". Concorda com a leitura?', f'Os analistas disseram que "{t[0].lower() + t[1:]}". Foi isso mesmo?'), [
        op('Leitura correta. Vimos isso no intervalo e não conseguimos corrigir a tempo.', [G(1, 'o técnico concordou com a análise tática')],
           'Técnico concorda com a análise da Mesa Tática', 'Autocrítica tática.'),
        op('Quem analisa de fora vê uma parte. Tem coisa que só quem está no vestiário sabe.', [G(0, 'o técnico relativizou a análise')],
           'Técnico relativiza a análise tática', 'Os analistas rebatem no programa.'),
        op('Concordo, e já corrigimos no treino de hoje. Não vai se repetir.', [G(2, 'o técnico garantiu a correção tática')],
           'Técnico promete corrigir: "não vai se repetir"', 'A promessa fica registrada.')]


@cen
def todos_se_fecham(X, rnd):
    try:
        reg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico', 'ia_adversaria.json'),
                             encoding='utf-8')).get('registro') or []
    except (OSError, ValueError):
        return None
    ult = [x for x in reg if tuple(x.get('data') or (9999,)) <= tuple(X['hoje'])][-5:]
    baixos = [x for x in ult if (x.get('plano') or {}).get('linha_defensiva', 9) <= 4]
    if len(ult) < 4 or len(baixos) < 3:
        return None
    return 6.8, 'tatica', _q(rnd, f'{len(baixos)} dos últimos {len(ult)} adversários jogaram com a linha lá atrás. Todo mundo aprendeu a se fechar contra vocês?',
                            'Os adversários já entram em campo para não perder contra o seu time. Como furar isso?'), [
        op('É o preço de ser grande. Vamos treinar mais bola parada e chute de fora.', [G(1, 'o técnico tratou a retranca como elogio')],
           'Técnico: "retranca é o preço de ser grande"', 'Treino de bola parada à vista.'),
        op('Precisamos ser mais rápidos com a bola. Quando o time demora, eles se organizam.', [G(1, 'o técnico apontou a velocidade como solução')],
           'Técnico pede mais velocidade contra retrancas', 'Leitura tática.'),
        op('Vou mudar o jeito de atacar. Quem estudou o nosso time vai encontrar outro.', [G(2, 'o técnico prometeu novidades táticas')],
           'Técnico promete um time diferente', 'Mistério sobre as mudanças.')]


CC.SO_OFICIAL.update({'duas_derrotas_seguidas', 'derrotas_em_serie', 'vitoria_que_alivia', 'invicto_longo', 'perdeu_lideranca',
                      'assumiu_lideranca', 'rival_encostou', 'rival_disparou', 'distancia_caiu', 'contra_os_grandes',
                      'fortaleza_em_casa', 'semana_decisiva', 'reagir_na_champions', 'classico_sob_pressao', 'queda_de_rendimento',
                      'comentarista_critica', 'todos_se_fecham', 'leitura_da_mesa_tatica', 'substituido_cedo'})
CC.TABELA.update({'perdeu_lideranca', 'assumiu_lideranca', 'rival_encostou', 'rival_disparou', 'distancia_caiu'})
