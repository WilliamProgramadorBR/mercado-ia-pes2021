"""DUELO ESTATÍSTICA x REDE NEURAL (12/10/2026).

Pedido do usuário: "a rede neural entra como apoio ou competidor: quantos resultados (ou próximo deles) a estatística
acertou x a rede. Quem acertar mais dentro de 100 jogos passa à frente para decidir" — sem tirar a estatística, que
"fez um efeito absurdo no jogo". Duas arenas, cada uma com o seu placar (escolha do usuário):

  simulados  jogos entre clubes da IA. Antes de cada jogo os dois modelos dão um palpite de placar. Quem lidera decide
             quantos titulares cada clube da IA poupa (escalacao_ia): o rodízio só fica se o líder achar que custa
             pouco (o placar de 100 jogos enche em poucos dias de jogo).
  usuario    os jogos do usuário. Os dois dão palpite antes do jogo; quem lidera escolhe o plano tático do adversário
             entre os candidatos da IA adversária (a estatística = amostragem de Thompson que já existe; a rede = o
             plano em que ela prevê o melhor saldo para o adversário). ~100 jogos = 1,5 temporada.

Bolão: placar exato 3, saldo certo 2, vencedor/empate certo 1. Começa com a estatística no comando; depois de 100
jogos pontuados numa arena, quem somar mais nos últimos 100 assume (a liderança só troca se o outro passar à frente).
Os modelos:
  estatística  simulados: gols esperados = média da liga ± 0,065 por ponto de diferença de nota dos XI (medição de
               12/10: +0,13 de saldo por ponto; sem vantagem de mando no simulador); usuário: saldo esperado da
               prévia (força + mando + forma) + o que a IA adversária aprendeu sobre o plano escolhido.
  rede         rede.Rede (Python puro): lê notas dos XI, forma, competição (e, contra o usuário, as características do
               plano do adversário), prevê os gols de cada lado e aprende a cada jogo pontuado.
"""
import collections
import datetime as dt
import json
import os
import random
import threading

import rede as R

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(HERE, 'historico', 'duelo.json')
ARQ_REDE = {'simulados': os.path.join(HERE, 'historico', 'rede_simulados.json'),
            'usuario': os.path.join(HERE, 'historico', 'rede_usuario.json')}
ARQ_BUF = {'simulados': os.path.join(HERE, 'historico', 'rede_simulados_dados.json'),
           'usuario': os.path.join(HERE, 'historico', 'rede_usuario_dados.json')}
JANELA = 100
COPAS = {23, 24, 25, 26, 27, 28, 31, 53, 54, 55, 59, 68, 123, 124, 125, 142}
GRANDES = {3, 4, 8, 9, 10, 1, 15, 16}
NAO_OFICIAL = set(range(100, 111)) | set(range(34, 47)) | {56}
TAGS = ['bloco_baixo', 'bloco_medio', 'linha_alta', 'contra_ataque', 'posse', 'pressao_na_frente', 'compacto',
        'ataque_pelos_lados', 'fecha_o_meio', 'inst_14', 'inst_13', 'inst_12']
COEF = 0.065          # gols por ponto de diferença de nota (metade do +0,13 de saldo medido)
TRAVA = threading.Lock()
_REDES = {}


# ---------------------------------------------------------------- estado
def estado():
    try:
        with open(ARQ, encoding='utf-8') as f:
            e = json.load(f)
    except (OSError, ValueError):
        e = {}
    e.setdefault('arenas', {})
    for a in ('simulados', 'usuario'):
        e['arenas'].setdefault(a, {'lider': 'estatistica', 'pend': {}, 'hist': [], 'trocas': []})
    e.setdefault('base_gols', 1.3)
    e.setdefault('total_usuario', 3.0)
    return e


def gravar(e):
    for a in e['arenas'].values():
        a['hist'] = a['hist'][-600:]
    tmp = ARQ + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(e, f, ensure_ascii=False)
    os.replace(tmp, ARQ)


def rede(arena):
    if arena not in _REDES:
        _REDES[arena] = R.Rede.carregar(ARQ_REDE[arena]) or R.Rede(N_IN[arena], 10, 2, semente=7)
    return _REDES[arena]


# ---------------------------------------------------------------- o que os modelos enxergam
def xi_info(notas_gk):
    """notas_gk = [(nota, é_goleiro)] do XI -> (média, média dos 3 melhores, goleiro)."""
    ns = sorted((n for n, _ in notas_gk), reverse=True) or [70]
    gk = next((n for n, g in notas_gk if g), min(ns))
    return sum(ns) / len(ns), sum(ns[:3]) / min(3, len(ns)), gk


def tipo_comp(comp):
    return (1.0 if comp in GRANDES else 0.0, 1.0 if comp in COPAS else 0.0)


def feat_sim(xa, xb, fa, fb, comp):
    """xa/xb = xi_info; fa/fb = forma (pontos por jogo, gols pró, gols contra nos últimos 5)."""
    cont, copa = tipo_comp(comp)
    return [(xa[0] - 75) / 10, (xb[0] - 75) / 10, (xa[0] - xb[0]) / 5, (xa[1] - 80) / 10, (xb[1] - 80) / 10,
            (xa[2] - 75) / 10, (xb[2] - 75) / 10, fa[0] / 3, fb[0] / 3, fa[1] / 2, fa[2] / 2, fb[1] / 2, fb[2] / 2,
            cont, copa]


def feat_usr(fu, fa, casa_user, forma_u, forma_a, grande, tags):
    return ([(fu - 75) / 10, (fa - 75) / 10, (fu - fa) / 5, 1.0 if casa_user else 0.0, forma_u / 3, forma_a / 3,
             1.0 if grande else 0.0] + [1.0 if t in tags else 0.0 for t in TAGS])


N_IN = {'simulados': 15, 'usuario': 7 + len(TAGS)}


def forma_str(s):
    """'VVDEV' -> pontos por jogo."""
    s = [c for c in (s or '') if c in 'VED'][-5:]
    return sum(3 if c == 'V' else 1 if c == 'E' else 0 for c in s) / len(s) if s else 1.4


class Formas:
    """Forma de cada time antes de uma data, a partir de uma lista de jogos (ordem cronológica)."""
    def __init__(self, jogos):
        self.por_time = collections.defaultdict(list)
        for j in sorted((j for j in jogos if j.get('jogado', True)), key=lambda j: tuple(j['data'])):
            for t, gp, gc in ((j['time1'], j['gols1'], j['gols2']), (j['time2'], j['gols2'], j['gols1'])):
                self.por_time[t].append((tuple(j['data']), gp, gc))

    def antes(self, t, data):
        xs = [x for x in self.por_time.get(t, []) if x[0] < tuple(data)][-5:]
        if not xs:
            return (1.4, 1.3, 1.3)
        pts = sum(3 if gp > gc else 1 if gp == gc else 0 for _, gp, gc in xs) / len(xs)
        return (pts, sum(gp for _, gp, _ in xs) / len(xs), sum(gc for _, _, gc in xs) / len(xs))


# ---------------------------------------------------------------- os dois modelos
def est_sim(e, xa, xb):
    d = xa[0] - xb[0]
    b = e.get('base_gols', 1.3)
    return [max(0.15, b + COEF * d), max(0.15, b - COEF * d)]


def est_usr(e, esperado_adv, extra_ia=0.0):
    """Gols esperados [usuário, adversário] pela estatística: saldo esperado do adversário (prévia) + o que a IA
    adversária aprendeu sobre o plano escolhido."""
    t = e.get('total_usuario', 3.0)
    s = (esperado_adv or 0.0) + (extra_ia or 0.0)
    return [max(0.2, t / 2 - s / 2), max(0.2, t / 2 + s / 2)]


# ---------------------------------------------------------------- previsões, pontuação, liderança
def chave(data, t1, t2):
    return f'{data[0]:04d}-{data[1]:02d}-{data[2]:02d}|{t1}|{t2}'


def resultados_de(jogos):
    """{chave: [gols casa, gols fora]} dos jogos já disputados (registros do pulso ou súmulas)."""
    return {chave(j['data'], j['time1'], j['time2']): [j['gols1'], j['gols2']] for j in jogos if j.get('jogado', True)}


def ciclo(jogos, hoje=None, log=print):
    """Pontua as duas arenas com os resultados novos e faz a rede estudar esses jogos. Devolve as trocas de líder."""
    res = resultados_de(jogos)
    with TRAVA:
        e = estado()
        antes = {a: e['arenas'][a]['lider'] for a in e['arenas']}
        novos = {a: pontuar(e, a, res, hoje) for a in e['arenas']}
        gravar(e)
    for a, ams in novos.items():
        if ams:
            treinar(a, ams)
            pl = placar(e['arenas'][a])
            log(f'duelo ({a}): {len(ams)} jogo(s) pontuado(s) — últimos {pl["jogos"]}: estatística {pl["estatistica"]} x rede {pl["rede"]} pts')
    return [(a, e['arenas'][a]['lider']) for a in e['arenas'] if e['arenas'][a]['lider'] != antes[a]]


def resumo():
    """Para a Central: placar de cada arena, quem manda e os últimos palpites nos jogos do usuário."""
    e = estado()
    out = {}
    for a, A in e['arenas'].items():
        pl = placar(A)
        out[a] = {'lider': A['lider'], 'placar': pl, 'total': len(A['hist']), 'pendentes': len(A['pend']),
                  'trocas': A['trocas'][-3:], 'rede_estudou': getattr(rede(a), 'vistos', 0)}
    out['usuario']['ultimos'] = [{k: h.get(k) for k in ('data', 'adv', 'est', 'rede', 'real', 'p_est', 'p_rede', 'decidiu', 'plano')}
                                 for h in e['arenas']['usuario']['hist'][-6:]][::-1]
    out['usuario']['proximo'] = next(({k: p.get(k) for k in ('data', 'adv', 'est', 'rede', 'decidiu', 'plano')}
                                      for p in e['arenas']['usuario']['pend'].values()), None)
    out['pretreino'] = e.get('pretreino')
    return out


def prever(e, arena, chave, data, x, lam_est, info=None):
    """Guarda os palpites dos dois modelos para um jogo (uma vez por jogo)."""
    A = e['arenas'][arena]
    if chave in A['pend'] or any(h['chave'] == chave for h in A['hist'][-300:]):
        return A['pend'].get(chave)
    lam_r = rede(arena).prever(x)
    p = {'chave': chave, 'data': list(data), 'x': [round(v, 4) for v in x],
         'est': R.palpite(*lam_est), 'rede': R.palpite(*lam_r),
         'lam_est': [round(v, 2) for v in lam_est], 'lam_rede': [round(v, 2) for v in lam_r], **(info or {})}
    A['pend'][chave] = p
    return p


def pontuar(e, arena, resultados, hoje=None):
    """resultados = {chave: [gols A, gols B]} -> pontua os pendentes e devolve as amostras para o treino.
    Palpite de jogo que passou há mais de 20 dias sem resultado (adiado, outra carreira) é descartado."""
    A = e['arenas'][arena]
    amostras = []
    for chave, p in list(A['pend'].items()):
        real = resultados.get(chave)
        if real is not None and p.get('inverter'):
            real = [real[1], real[0]]      # arena do usuário: [usuário, adversário]
        if real is None:
            if hoje and (dt.date(*tuple(hoje)[:3]) - dt.date(*p['data'][:3])).days > 20:
                A['pend'].pop(chave)
            continue
        h = dict(p, real=list(real), p_est=R.pontos(p['est'], real), p_rede=R.pontos(p['rede'], real))
        h.pop('x', None)
        A['hist'].append(h)
        A['pend'].pop(chave)
        amostras.append((p['x'], [float(real[0]), float(real[1])]))
    if amostras:
        _liderança(A, arena)
    return amostras


def placar(A, n=JANELA):
    ult = A['hist'][-n:]
    soma = lambda k: sum(h[k] for h in ult)
    conta = lambda k, v: sum(1 for h in ult if h[k] == v)
    return {'jogos': len(ult), 'estatistica': soma('p_est'), 'rede': soma('p_rede'),
            'exatos': {'estatistica': conta('p_est', 3), 'rede': conta('p_rede', 3)},
            'vencedor': {'estatistica': sum(1 for h in ult if h['p_est'] >= 1), 'rede': sum(1 for h in ult if h['p_rede'] >= 1)}}


def _liderança(A, arena):
    pl = placar(A)
    if pl['jogos'] < JANELA:
        return
    atual = A['lider']
    outro = 'rede' if atual == 'estatistica' else 'estatistica'
    if pl[outro] > pl[atual]:
        A['lider'] = outro
        A['trocas'].append({'data': A['hist'][-1]['data'], 'lider': outro, 'placar': [pl['estatistica'], pl['rede']]})


def lider(arena):
    return estado()['arenas'][arena]['lider']


def treinar(arena, amostras, epocas=3):
    """Aprendizado contínuo: os jogos novos + uma amostra do que já viu (para não esquecer)."""
    if not amostras:
        return
    try:
        with open(ARQ_BUF[arena], encoding='utf-8') as f:
            buf = json.load(f)
    except (OSError, ValueError):
        buf = []
    rnd = random.Random(len(buf))
    lote = list(amostras) + rnd.sample(buf, min(len(buf), 6 * len(amostras)))
    r = rede(arena)
    r.treinar(lote, epocas=epocas, lr=0.004)
    buf = (buf + [list(a) for a in amostras])[-4000:]
    with open(ARQ_BUF[arena] + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(buf, f)
    os.replace(ARQ_BUF[arena] + '.tmp', ARQ_BUF[arena])
    r.salvar(ARQ_REDE[arena])


def saldo(arena, modelo, x, lam_est):
    """Saldo previsto (A - B) pelo modelo indicado."""
    la, lb = (rede(arena).prever(x) if modelo == 'rede' else lam_est)
    return la - lb


# ---------------------------------------------------------------- pré-treino com o histórico do save
def amostras_historicas(r, P, s, d=None):
    """Amostras das duas arenas a partir das súmulas do save (vestiario.analisar): os 11 de cada lado, notas pela foto
    da memória, forma antes do jogo, competição; contra o usuário, as características do plano original do clube."""
    import encaixe
    n_clubes = s.find_team('ALBÂNIA') or 625
    todas = sorted(r.get('todas_partidas') or [], key=lambda p: tuple(p['data']))
    F = Formas(todas)
    ti = r['ti']

    def xi(linhas):
        xs = sorted((x for x in linhas if x['minutos'] > 0 and (x['reg'], x['pid']) in P), key=lambda x: -x['minutos'])[:11]
        return [(encaixe.rating(P[(x['reg'], x['pid'])], P[(x['reg'], x['pid'])].pos), P[(x['reg'], x['pid'])].pos == 'GK') for x in xs]
    sim, usr, gols = [], [], []
    tags_clube = {}
    for p in todas:
        if p['comp'] in NAO_OFICIAL or p['time1'] >= n_clubes or p['time2'] >= n_clubes:
            continue
        a, b = xi(p['linhas1']), xi(p['linhas2'])
        if len(a) < 9 or len(b) < 9:
            continue
        xa, xb = xi_info(a), xi_info(b)
        fa, fb = F.antes(p['time1'], p['data']), F.antes(p['time2'], p['data'])
        if ti not in (p['time1'], p['time2']):
            sim.append((feat_sim(xa, xb, fa, fb, p['comp']), [float(p['gols1']), float(p['gols2'])], tuple(p['data'])))
            gols += [p['gols1'], p['gols2']]
        elif d is not None:
            casa = p['time1'] == ti
            adv = p['time2'] if casa else p['time1']
            if adv not in tags_clube:
                tags_clube[adv] = _tags_originais(d, adv)
            xu, xa_ = (xa, xb) if casa else (xb, xa)
            fu, fa_ = (fa, fb) if casa else (fb, fa)
            y = [float(p['gols1']), float(p['gols2'])] if casa else [float(p['gols2']), float(p['gols1'])]
            grande = p['comp'] in GRANDES
            usr.append((feat_usr(xu[0], xa_[0], casa, fu[0], fa_[0], grande, tags_clube[adv]), y, tuple(p['data'])))
    return sim, usr, (sum(gols) / len(gols) if gols else 1.3)


def _tags_originais(d, ti):
    import ia_adversaria as IA
    import tatica_save as T
    e = IA._ler_estado()
    pl = (e.get('originais') or {}).get(str(ti)) or T.ler(d, ti)
    try:
        instr = [(c, a) for c, _, a in T.instrucoes(d, ti)]
    except Exception:  # noqa: BLE001
        instr = []
    return IA.tags(pl, instr) if pl else []
