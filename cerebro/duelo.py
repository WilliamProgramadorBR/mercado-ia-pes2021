# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
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

ARENA DO USUÁRIO v2 (13/10/2026, pedido do usuário: "vamos dar mais dados... cansaço, espírito de equipe, condições
físicas"). A análise dos jogos mostrou duas coisas: o cansaço é o sinal mais forte de 2035/36 e o jogo mudou de
patamar (2034/35 tinha 1 x 0 em metade dos jogos; 2035/36 ~4 gols por jogo) — os modelos tinham ficado no "mundo do
1 x 0". Agora os dois enxergam a FICHA DO JOGO (ficha_jogo.py: XI real/provável, condição, carga de 14 dias,
descanso, desfalques, espírito de equipe, moral) e o usuário como "fora da curva":
  estatística  regressão linear do saldo (ridge) que PARTE de valores medidos/combinados (PRIOR) e se ajusta aos
               jogos do usuário, com peso maior para os recentes (RECENCIA); a média de gols por jogo acompanha os
               jogos recentes (ALFA_TOTAL). O que nunca foi visto (condição, desfalques...) fica no valor de partida.
  rede         as mesmas entradas + notas dos XI + características do plano do adversário (28 entradas); as entradas
               que os jogos antigos não têm começam com peso zero e crescem com os dados novos.
  você         `const` da regressão = quanto o usuário costuma superar a força dos elencos; `voce` = o momento dele
               (média rápida - média lenta do quanto superou o esperado).
  por quê      porque_est / porque_rede: quanto cada grupo (força, mando, forma, cansaço, desfalques, vestiário,
               você, plano do rival) mexe no saldo previsto — o Painel mostra.
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
# 13/10/2026: a rede do usuário mudou de entradas (v2) — arquivos novos; os antigos ficam como estavam
ARQ_REDE = {'simulados': os.path.join(HERE, 'historico', 'rede_simulados.json'),
            'usuario': os.path.join(HERE, 'historico', 'rede_usuario_v2.json')}
ARQ_BUF = {'simulados': os.path.join(HERE, 'historico', 'rede_simulados_dados.json'),
           'usuario': os.path.join(HERE, 'historico', 'rede_usuario_v2_dados.json')}
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
    """A rede da arena: a desta carreira (historico) ou, na 1ª vez, o modelo inicial que vem no pacote (só para os
    jogos da IA, que não têm nada pessoal), ou uma rede nova que aprende do zero."""
    if arena not in _REDES:
        r = R.Rede.carregar(ARQ_REDE[arena]) or R.Rede.carregar(os.path.join(HERE, 'modelos', f'rede_{arena}.json'))
        _REDES[arena] = r if r is not None and r.n_in == N_IN[arena] else rede_nova(arena)
    return _REDES[arena]


def rede_nova(arena):
    """Rede do zero. Na arena do usuário, as entradas que os jogos antigos não têm (condição, desfalques, vestiário)
    começam com peso ZERO: sem isso o peso sorteado ficaria sem treino e viraria ruído quando o dado chegasse."""
    r = R.Rede(N_IN[arena], 10, 2, semente=7)
    if arena == 'usuario':
        for i in [EST_NOMES.index(k) for k in SO_NOVOS] + [len(EST_NOMES) + 3]:
            for row in r.W1:
                row[i] = 0.0
    return r


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


# ---------------------------------------------------------------- arena do usuário v2 (13/10/2026)
EST_NOMES = ['forca', 'casa', 'forma', 'carga', 'pesados', 'descanso', 'condicao', 'baixos', 'desfalques',
             'espirito', 'moral', 'voce']
# quanto cada coisa vale, em gols de saldo para o usuário, ANTES de haver dado (a estatística parte daqui):
# força 0,13 gol por ponto de nota (medição de 12/10); cansaço pela análise de 13/10 (com 8 titulares no limite o
# United sofria ~1,2 gol a mais); o resto é estimativa conservadora até os jogos mostrarem.
PRIOR = {'const': 1.0, 'forca': 0.65, 'casa': 0.15, 'forma': 0.3, 'carga': 0.3, 'pesados': 0.8, 'descanso': 0.3,
         'condicao': 0.5, 'baixos': 1.0, 'desfalques': 0.3, 'espirito': 0.3, 'moral': 0.2, 'voce': 0.6}
SO_NOVOS = ('condicao', 'baixos', 'desfalques', 'espirito', 'moral')   # os jogos antigos não têm (o save não guarda)
GRUPOS = {'força dos XI': ('forca',), 'mando': ('casa',), 'forma': ('forma',),
          'cansaço': ('carga', 'pesados', 'descanso', 'condicao', 'baixos'), 'desfalques': ('desfalques',),
          'vestiário': ('espirito', 'moral'), 'seu momento': ('voce',)}
RIDGE = 25.0         # quanto a regressão "segura" cada peso perto do valor de partida (validado em 13/10: 4, 10 e 25 -> 25)
RECENCIA = 0.97      # peso de um jogo cai 3% a cada jogo mais novo (o jogo muda, o usuário muda)
ALFA_TOTAL = 0.12    # média de gols por jogo acompanha os recentes
ALFA_RAPIDO, ALFA_LENTO = 0.25, 0.04
GOL_POR_PONTO = 0.13


def xe_de(ficha, casa_user, forma_u, forma_a, voce=0.0, f_nos=None, f_adv=None):
    """Entradas da estatística (todas viradas para o usuário: positivo = bom para ele)."""
    n, a = (ficha or {}).get('nos') or {}, (ficha or {}).get('adv') or {}
    xn, xa = n.get('xi') or f_nos or 75, a.get('xi') or f_adv or 75
    desc = lambda v: min(v, 7) if v is not None else 7
    tem = lambda k: n.get(k) is not None and a.get(k) is not None
    esp, mor = (ficha or {}).get('espirito'), (ficha or {}).get('moral')
    return {'forca': (xn - xa) / 5, 'casa': 1.0 if casa_user else -1.0, 'forma': (forma_u - forma_a) / 3,
            'carga': ((a.get('carga') or 0) - (n.get('carga') or 0)) / 90,
            'pesados': ((a.get('pesados') or 0) - (n.get('pesados') or 0)) / 11,
            'descanso': (desc(n.get('descanso')) - desc(a.get('descanso'))) / 7,
            'condicao': (n['cond'] - a['cond']) / 10 if tem('cond') else 0.0,
            'baixos': (a['baixos'] - n['baixos']) / 11 if tem('baixos') else 0.0,
            'desfalques': (a['desfalques'] - n['desfalques']) / 3 if tem('desfalques') else 0.0,
            'espirito': (esp - 75) / 25 if esp is not None else 0.0,
            'moral': (mor - 60) / 40 if mor is not None else 0.0,
            'voce': voce or 0.0}


def x_rede(xe, xi_nos, xi_adv, grande, tags, ficha_nova):
    return ([round(xe[k], 4) for k in EST_NOMES]
            + [(xi_nos - 80) / 10, (xi_adv - 80) / 10, 1.0 if grande else 0.0, 1.0 if ficha_nova else 0.0]
            + [1.0 if t in tags else 0.0 for t in TAGS])


N_IN = {'simulados': 15, 'usuario': len(EST_NOMES) + 4 + len(TAGS)}


def entradas_usr(ctx, tags, e=None):
    """(entradas da rede, entradas da estatística) de um jogo do usuário. ctx = ia_adversaria.contexto + 'ficha'."""
    e = e or estado()
    fi = ctx.get('ficha') or {}
    xe = xe_de(fi, not ctx.get('adv_em_casa'), forma_str(ctx.get('forma_nos')), forma_str(ctx.get('forma_adv')),
               momento(e), ctx.get('forca_nos'), ctx.get('forca_adv'))
    xn = (fi.get('nos') or {}).get('xi') or ctx.get('forca_nos') or 75
    xa = (fi.get('adv') or {}).get('xi') or ctx.get('forca_adv') or 75
    return x_rede(xe, xn, xa, ctx.get('grande'), tags, (fi.get('nos') or {}).get('cond') is not None), xe


def momento(e):
    v = e.get('voce') or {}
    return round((v.get('rapido') or 0.0) - (v.get('lento') or 0.0), 3)


def coefs(e):
    c = dict(PRIOR)
    c.update(e.get('coef_usr') or {})
    return c


def saldo_est(e, xe, extra=0.0):
    c = coefs(e)
    return c['const'] + sum(c[k] * xe.get(k, 0.0) for k in EST_NOMES) - (extra or 0.0)


def est_usr(e, xe, extra=0.0):
    """Gols esperados [usuário, adversário] pela estatística: saldo da regressão (ficha + você) menos o que a IA
    adversária aprendeu sobre o plano escolhido (extra = saldo a mais para o adversário); total = média recente."""
    t = e.get('total_usuario', 3.0)
    s = saldo_est(e, xe, extra)
    return [max(0.2, t / 2 + s / 2), max(0.2, t / 2 - s / 2)]


def porque_est(e, xe, extra=0.0):
    """[(fator, gols de saldo para o usuário)] da estatística, do que mais pesa para o que menos pesa."""
    c = coefs(e)
    out = [('você (média)', c['const'])] + [(g, sum(c[k] * xe.get(k, 0.0) for k in ks)) for g, ks in GRUPOS.items()]
    if extra:
        out.append(('plano do rival', -extra))
    return sorted(((g, round(v, 2)) for g, v in out if abs(v) >= 0.05), key=lambda t: -abs(t[1]))


def porque_rede(x):
    """Mesma pergunta para a rede: quanto o saldo previsto muda se aquele grupo de dados ficar neutro."""
    r = rede('usuario')
    sd = lambda y: (lambda la, lb: la - lb)(*r.prever(y))
    cheio, n, out = sd(x), len(EST_NOMES), []
    for g, ks in GRUPOS.items():
        y = list(x)
        for k in ks:
            y[EST_NOMES.index(k)] = 0.0
        if g == 'força dos XI':
            y[n] = y[n + 1] = (y[n] + y[n + 1]) / 2
        out.append((g, cheio - sd(y)))
    y = list(x[:n + 4]) + [0.0] * (len(x) - n - 4)
    out.append(('plano do rival', cheio - sd(y)))
    return sorted(((g, round(v, 2)) for g, v in out if abs(v) >= 0.05), key=lambda t: -abs(t[1]))


def _resolver(A, b):
    """Sistema linear pequeno (eliminação de Gauss com pivô)."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda i: abs(M[i][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            continue
        for i in range(n):
            if i != c:
                f = M[i][c] / M[c][c]
                M[i] = [vi - f * vc for vi, vc in zip(M[i], M[c])]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def ajustar_est(amostras):
    """Regressão ridge do saldo do usuário puxada para o PRIOR, com peso maior nos jogos recentes.
    amostras = [{'xe': {...}, 'saldo': gols usuário - adversário, 'extra': plano}] em ordem cronológica."""
    nomes = ['const'] + EST_NOMES
    k = len(nomes)
    A = [[0.0] * k for _ in range(k)]
    b = [0.0] * k
    n = len(amostras)
    for i, a in enumerate(amostras):
        w = RECENCIA ** (n - 1 - i)
        x = [1.0] + [a['xe'].get(nm, 0.0) for nm in EST_NOMES]
        y = max(-4.0, min(4.0, a['saldo'] + (a.get('extra') or 0.0)))   # goleada fora da curva não puxa tudo
        for p in range(k):
            b[p] += w * x[p] * y
            for q in range(k):
                A[p][q] += w * x[p] * x[q]
    for p, nm in enumerate(nomes):
        lam = 0.05 if nm == 'const' else RIDGE
        A[p][p] += lam
        b[p] += lam * PRIOR[nm]
    return {nm: round(v, 3) for nm, v in zip(nomes, _resolver(A, b))}


def registrar_jogo_usr(e, xe, real, extra=0.0, data=None):
    """Depois de um jogo do usuário: guarda a amostra, atualiza a média de gols e o momento, reajusta a estatística."""
    saldo = real[0] - real[1]
    e['total_usuario'] = round((1 - ALFA_TOTAL) * e.get('total_usuario', 3.0) + ALFA_TOTAL * (real[0] + real[1]), 3)
    resid = saldo - GOL_POR_PONTO * 5 * xe.get('forca', 0.0)
    v = e.setdefault('voce', {})
    v['rapido'] = round((1 - ALFA_RAPIDO) * v.get('rapido', resid) + ALFA_RAPIDO * resid, 3)
    v['lento'] = round((1 - ALFA_LENTO) * v.get('lento', resid) + ALFA_LENTO * resid, 3)
    am = e.setdefault('amostras_est', [])
    am.append({'xe': {k: round(x, 4) for k, x in xe.items()}, 'saldo': saldo, 'extra': extra or 0.0, 'data': data})
    e['amostras_est'] = am[-400:]
    e['coef_usr'] = ajustar_est(e['amostras_est'])


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
    campos = ('data', 'adv', 'est', 'rede', 'decidiu', 'plano', 'porque', 'ficha_txt', 'fisico')
    out['usuario']['ultimos'] = [{k: h.get(k) for k in campos + ('real', 'p_est', 'p_rede')}
                                 for h in e['arenas']['usuario']['hist'][-6:]][::-1]
    out['usuario']['proximo'] = next(({k: p.get(k) for k in campos}
                                      for p in sorted(e['arenas']['usuario']['pend'].values(), key=lambda p: p['data'])), None)
    out['usuario']['voce'] = {'media': coefs(e)['const'], 'momento': momento(e), 'gols_por_jogo': e.get('total_usuario')}
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
    amostras, pontuados = [], 0
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
        pontuados += 1
        if arena == 'usuario' and p.get('xe'):   # 13/10/2026: a estatística v2 se reajusta a cada jogo do usuário
            registrar_jogo_usr(e, p['xe'], real, p.get('extra') or 0.0, p.get('data'))
        if len(p.get('x') or []) == N_IN[arena]:   # palpites de antes da v2 não servem de treino para a rede nova
            amostras.append((p['x'], [float(real[0]), float(real[1])]))
    if pontuados:
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
    perda = r.treinar(lote, epocas=epocas, lr=0.004)
    # histórico do aprendizado (o Painel mostra a curva): perda média e quantos jogos novos em cada treino
    ex = getattr(r, 'extra', None) or {}
    ex['perdas'] = (ex.get('perdas') or [])[-299:] + [[amostras and len(amostras), round(perda, 4)]]
    r.extra = ex
    buf = (buf + [list(a) for a in amostras])[-4000:]
    with open(ARQ_BUF[arena] + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(buf, f)
    os.replace(ARQ_BUF[arena] + '.tmp', ARQ_BUF[arena])
    r.salvar(ARQ_REDE[arena], extra=r.extra)


def saldo(arena, modelo, x, lam_est):
    """Saldo previsto (A - B) pelo modelo indicado."""
    la, lb = (rede(arena).prever(x) if modelo == 'rede' else lam_est)
    return la - lb


# ---------------------------------------------------------------- pré-treino com o histórico do save
def amostras_historicas(r, P, s, d=None):
    """Amostras das duas arenas a partir das súmulas do save (vestiario.analisar): os 11 de cada lado, notas pela foto
    da memória, forma antes do jogo, competição; contra o usuário, as características do plano original do clube."""
    import encaixe
    import ficha_jogo
    n_clubes = __import__('selecoes').primeira(s, 625)
    todas = sorted(r.get('todas_partidas') or [], key=lambda p: tuple(p['data']))
    F = Formas(todas)
    cargas = ficha_jogo.Cargas(todas)
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
            fu, fa_ = (fa, fb) if casa else (fb, fa)
            y = [float(p['gols1']), float(p['gols2'])] if casa else [float(p['gols2']), float(p['gols1'])]
            ln_u, ln_a = (p['linhas1'], p['linhas2']) if casa else (p['linhas2'], p['linhas1'])
            ficha = {'nos': ficha_jogo.lado_sumula(cargas, ti, ln_u, p['data'], P),
                     'adv': ficha_jogo.lado_sumula(cargas, adv, ln_a, p['data'], P)}
            # 13/10/2026: v2 — amostra "crua"; o momento do usuário (voce) é encadeado depois, em ordem (encadear_usr)
            usr.append({'ficha': ficha, 'casa': casa, 'forma': (fu[0], fa_[0]), 'grande': p['comp'] in GRANDES,
                        'tags': tags_clube[adv], 'y': y, 'data': tuple(p['data'])})
    return sim, usr, (sum(gols) / len(gols) if gols else 1.3)


def encadear_usr(amostras):
    """Amostras do usuário em ordem de data -> [(x, y, data, xe)] com o momento (voce) de ANTES de cada jogo, e o
    estado final (total de gols e momento) para o duelo seguir dali."""
    e = {'total_usuario': None, 'voce': {}}
    out = []
    for a in sorted(amostras, key=lambda a: a['data']):
        xe = xe_de(a['ficha'], a['casa'], a['forma'][0], a['forma'][1], momento(e))
        x = x_rede(xe, a['ficha']['nos'].get('xi') or 75, a['ficha']['adv'].get('xi') or 75, a['grande'], a['tags'], False)
        out.append((x, a['y'], a['data'], xe))
        if e['total_usuario'] is None:
            e['total_usuario'] = a['y'][0] + a['y'][1]
        saldo = a['y'][0] - a['y'][1]
        e['total_usuario'] = (1 - ALFA_TOTAL) * e['total_usuario'] + ALFA_TOTAL * (a['y'][0] + a['y'][1])
        resid = saldo - GOL_POR_PONTO * 5 * xe['forca']
        v = e['voce']
        v['rapido'] = (1 - ALFA_RAPIDO) * v.get('rapido', resid) + ALFA_RAPIDO * resid
        v['lento'] = (1 - ALFA_LENTO) * v.get('lento', resid) + ALFA_LENTO * resid
    return out, {'total_usuario': round(e['total_usuario'] or 3.0, 3),
                 'voce': {k: round(v, 3) for k, v in e['voce'].items()}}


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
