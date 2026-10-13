# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""IA ADVERSÁRIA (12/10/2026): o técnico do computador estuda o usuário, prepara o jogo e aprende com o resultado.

O usuário joga no Lenda e quer a IA mais agressiva e inteligente, sem "roubo": nenhum atributo é tocado (o bônus
oculto do jogo continua zerado pelo Dynamic_Difficulty). A alavanca é o PLANO DE JOGO do adversário (tatica_save):
estilo, saída, pressão, linha, compactação e as INSTRUÇÕES AVANÇADAS (pressão ofensiva, marcação no craque do
usuário, defesa recuada, pivô de contra-ataque...).

Como decide, antes de cada jogo contra o usuário:
  1. CONTEXTO: força dos elencos, mando, jogo grande (Champions/Libertadores, final, clássico) -> postura base;
  2. OLHEIRO (olheiro.py): o plano do usuário, quem faz os gols, velocidade e jogo aéreo do ataque, forma recente
     -> ajustes (linha baixa contra ataque rápido, pressão contra time de posse, marcação no artilheiro...);
  3. CANDIDATOS: o plano do especialista (1+2) e variações (mais pressão, bloco mais baixo, com/sem marcação);
  4. APRENDIZADO: cada jogo contra o usuário vira dado. A recompensa é o saldo do adversário MENOS o esperado pela
     prévia (perder de 1 para quem devia perder de 3 conta como acerto). Cada característica da tática (linha alta,
     bloco baixo, pressão na frente, gegenpress, marcação...) acumula a média de recompensa por faixa de força
     (mais fraco / equilibrado / mais forte), com recuo para a média geral quando há pouco dado. A escolha entre os
     candidatos usa amostragem de Thompson: o que funcionou contra ESTE usuário ganha mais chance, e de vez em quando
     uma variação é testada — a IA não fica previsível e muda se o usuário aprender a furar o plano.
Escreve na MEMÓRIA do jogo (sem recarregar; o próprio jogo grava no save depois), só os bytes dos 3 planos
(+219..+584: ajustes, barras e vagas de instrução), conferindo antes e depois. Os 3 planos originais do clube voltam,
byte a byte, depois do jogo contra o usuário (os jogos entre clubes da IA não são afetados).
Registro por partida e aprendizado em historico/ia_adversaria.json. Desliga com "ia_adversaria": false no automacao.json.
"""
import json
import math
import os
import random
import struct
import time

import tatica_save as T

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(HERE, 'historico', 'ia_adversaria.json')
GRANDES = {'UEFA Champions League', 'Copa Libertadores', 'Libertadores', 'Mundial de Clubes'}
OFFS = [p + T.CAMPOS[k] for p in T.PLANOS for k in T.CAMPOS]
LO, HI = min(OFFS), max(OFFS) + 1   # trecho contínuo dos 3 planos: +219 .. +584
VAGA_REL = 108                      # vagas de instrução = plano + 108 (+228 no plano A)
FRENTE = {'CF', 'SS', 'LWF', 'RWF'}
# nota de um candidato = bônus do técnico + média das amostras das suas características (em gols de saldo).
# Sem dado nenhum, o plano do técnico vence ~3 em 4 vezes; com o aprendizado, a média de cada característica decide.
PRIOR_N, BONUS_ESPECIALISTA, SIGMA = 3.0, 0.3, 1.0
CURIOSIDADE = 0.10   # chance de testar outro candidato mesmo quando um já se provou
ESQUECIMENTO = 0.97  # a cada jogo novo, o peso do que foi aprendido antes cai 3% (o usuário também aprende)


# ---------------------------------------------------------------- estado
def _ler_estado():
    try:
        with open(ARQ, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'originais': {}, 'ativo': None, 'registro': [], 'base_memoria': None}


def _gravar_estado(e):
    tmp = ARQ + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ARQ)


# ---------------------------------------------------------------- decisão
def faixa(ctx):
    dif = (ctx.get('forca_adv') or 75) - (ctx.get('forca_nos') or 75)
    return 'mais_fraco' if dif <= -3 else 'equilibrado' if dif < 3 else 'mais_forte'


def _faixa(v, lo, hi):
    return max(lo, min(hi, v))


def postura(base, ctx):
    """1. Contexto, RESPEITANDO A IDENTIDADE do clube (12/10/2026: antes quase todo mundo virava contra-ataque com
    compactação 8). O plano original é a base; o contexto mexe só na INTENSIDADE numa faixa em torno do original:
    linha -3..+2, compactação -1..+3, pressão. O estilo (posse/contra-ataque) só muda em caso extremo (muito mais
    fraco e fora de casa). Devolve (plano, motivo)."""
    p = dict(base)
    lin0, cmp0 = base['linha_defensiva'], base['compactacao']
    faixa_lin, faixa_cmp = (max(1, lin0 - 3), min(10, lin0 + 2)), (max(1, cmp0 - 1), min(10, cmp0 + 3))
    lin = lambda v: _faixa(v, *faixa_lin)
    cmp_ = lambda v: _faixa(v, *faixa_cmp)
    dif = (ctx.get('forca_adv') or 75) - (ctx.get('forca_nos') or 75)
    casa = ctx.get('adv_em_casa')
    estilo = 'jogo de posse' if base['estilo_ofensivo'] else 'contra-ataque'
    if dif <= -8 and not casa:
        p.update(estilo_ofensivo=0, linha_defensiva=lin(lin0 - 3), compactacao=cmp_(cmp0 + 3))
        motivo = 'muito mais fraco e fora de casa: recua as linhas e sai no contra-ataque (sobrevivência)'
    elif dif <= -3:
        p.update(linha_defensiva=lin(lin0 - 2), compactacao=cmp_(cmp0 + 2))
        motivo = f'mais fraco: mantém o {estilo}, mas mais compacto e com a linha mais baixa'
    elif dif < 3:
        p.update(pressao=0, linha_defensiva=lin(lin0), compactacao=cmp_(cmp0 + 1))
        motivo = f'jogo equilibrado: o {estilo} de sempre, com pressão agressiva'
    else:
        p.update(pressao=0, estilo_defensivo=0, linha_defensiva=lin(lin0 + 2), compactacao=cmp_(cmp0))
        motivo = f'mais forte: impõe o {estilo}, linha adiantada e pressão na frente'
    if ctx.get('grande'):
        p['pressao'] = 0
        p['compactacao'] = cmp_(p['compactacao'] + 1)
        motivo += ' | jogo grande: mais concentrado e agressivo'
    p['_lin'], p['_cmp'] = faixa_lin, faixa_cmp
    return p, motivo


def personalidade(base, base_instr, rec, semente):
    """Cada técnico explora as fraquezas do usuário do SEU jeito (estável por clube): quem já usa marcação individual
    (ou é defensivo) gosta dela; quem ataca pelo centro prefere sufocar o armador; quem ataca pelos lados ou tem pontas
    rápidos prefere o lateral fraco."""
    import random
    rnd = random.Random(f'tecnico|{semente}')
    usa_marcacao = any(c == 14 for c, _, _ in base_instr)
    gosta_marcacao = usa_marcacao or (base['estilo_defensivo'] == 1 and rnd.random() < 0.5) or rnd.random() < 0.2
    tem_lados = (rec or {}).get('pontas', 0) >= 1 or (rec or {}).get('laterais_of', 0) >= 1
    chance_lados = (0.6 if base['area_ataque'] == 0 else 0.25) if tem_lados else 0.0
    foco = 'lados' if rnd.random() < chance_lados else 'meio'
    return {'gosta_marcacao': gosta_marcacao, 'foco': foco}


def contra_olheiro(p, olho, rec=None, pers=None):
    """2. Explora as vulnerabilidades do usuário com o que o clube TEM (rec = recursos do elenco titular do clube).
    Devolve (plano, [motivos])."""
    p, mot = dict(p), []
    if not olho:
        return p, mot
    lin = lambda v: _faixa(v, *p.get('_lin', (1, 10)))
    rec = rec or {}
    vel = olho.get('velocidade_ataque') or 0
    if vel >= 88 and p['linha_defensiva'] > 5:
        p['linha_defensiva'] = lin(5)
        mot.append(f'ataque muito rápido (velocidade {vel}): sem espaço nas costas, linha até 5')
    vul = {v['tipo']: v for v in olho.get('vulnerabilidades') or []}
    foco = (pers or {}).get('foco', 'lados')
    if foco != 'lados':
        vul.pop('lateral_fraco', None)
    if foco != 'meio':
        vul.pop('armador', None)
    if 'lateral_fraco' in vul and (rec.get('pontas') or rec.get('laterais_of')):
        p['area_ataque'] = 0
        v = vul['lateral_fraco']
        mot.append(f'ataca pelos lados: o lado {v["lado"]} do adversário é o ponto fraco ({v["nome"]})')
    if 'armador' in vul:
        p['contencao'] = 0
        p['estilo_defensivo'] = 0
        mot.append(f'fecha o meio e pressiona quem cria: {vul["armador"]["nome"]} não pode pensar o jogo')
    if 'laterais_sobem' in vul and p['estilo_ofensivo'] == 0:
        p['area_ataque'] = 0
        mot.append('contra-ataque nas costas dos laterais que sobem')
    ent = olho.get('entrosamento')
    if ent is not None and ent < 85:
        p.update(estilo_defensivo=0, pressao=0)
        mot.append(f'o adversário ainda não se acostumou ao plano novo (entrosamento {ent}): pressão para forçar o erro')
    return p, mot


def instrucoes_para(p, base_instr, olho, atacante_rapido, rec=None, alvo_marcacao='auto', pers=None):
    """Até 2 instruções de ataque e 2 de defesa: [(código, alvo)], na ordem das vagas, e os motivos.
    Ataque: as do próprio clube (identidade) + exploração de flanco se o adversário tem lateral fraco.
    Defesa: por prioridade, com a marcação individual no alvo CERTO (o armador que comanda, ou o artilheiro)."""
    mot, rec, olho = [], rec or {}, olho or {}
    vul = {v['tipo']: v for v in olho.get('vulnerabilidades') or []}
    pers = pers or {'gosta_marcacao': True, 'foco': 'lados'}
    if pers['foco'] != 'lados':
        vul.pop('lateral_fraco', None)
    if not pers['gosta_marcacao']:
        alvo_marcacao = None
    ofs = [(c, a) for c, _, a in base_instr if c in T.OFENSIVAS and not (c == 6 and p['estilo_ofensivo'] == 0)]
    if 'lateral_fraco' in vul and len(ofs) < 2:
        if rec.get('laterais_of') and all(c != 4 for c, _ in ofs):
            ofs.append((4, 0))
            mot.append('lateral ofensivo: os laterais do clube atacam o lado fraco')
        elif rec.get('pontas') and all(c != 1 for c, _ in ofs):
            ofs.append((1, 0))
            mot.append(f'preso às laterais: pontas abertos para explorar o lado {vul["lateral_fraco"]["lado"]}')
    defs = []
    amea = olho.get('ameacas') or []
    a0 = amea[0] if amea else None
    if alvo_marcacao == 'auto':
        if 'armador' in vul:
            defs.append((14, vul['armador']['idx']))
            mot.append(f'marcação individual no armador {vul["armador"]["nome"]}')
        elif a0 and a0['titular'] and (a0['parte_gols'] >= 0.3 or a0['peso'] >= 0.9):
            defs.append((14, a0['idx']))
            mot.append(f'marcação individual no {a0["nome"]} ({a0["gols"]} gols, {a0["assist"]} assistências)')
    pl = olho.get('plano') or {}
    if p['estilo_defensivo'] == 0 and p['pressao'] == 0 and p['linha_defensiva'] >= 6 and pl.get('saida_de_bola', 1):
        defs.append((13, 0))
        mot.append('pressão ofensiva: o adversário sai jogando curto')
    if p['linha_defensiva'] <= 4 or (olho.get('velocidade_ataque') or 0) >= 88:
        defs.append((12, 0))
        mot.append('defesa recuada: sem espaço nas costas')
    if p['linha_defensiva'] <= 4 and (olho.get('aereo') or 0) >= 85:
        defs.append((11, 0))
        mot.append('invadir a área: centroavante forte no alto')
    if atacante_rapido is not None and (p['estilo_ofensivo'] == 0 or 'zaga_lenta' in vul):
        defs.append((15, atacante_rapido[0]))
        mot.append(f'pivô de contra-ataque: {atacante_rapido[1]} fica na frente'
                   + (' contra a zaga lenta do adversário' if 'zaga_lenta' in vul else ''))
    defs += [(c, a) for c, _, a in base_instr if c in T.DEFENSIVAS]
    vistos, d2 = set(), []
    for c, a in defs:
        if c not in vistos:
            vistos.add(c)
            d2.append((c, a))
    return (ofs[:2] + [(0, 0)] * 2)[:2] + (d2[:2] + [(0, 0)] * 2)[:2], mot


def tags(p, instr):
    t = ['bloco_baixo' if p['linha_defensiva'] <= 4 else 'bloco_medio' if p['linha_defensiva'] <= 6 else 'linha_alta',
         'contra_ataque' if p['estilo_ofensivo'] == 0 else 'posse']
    if p['estilo_defensivo'] == 0 and p['pressao'] == 0:
        t.append('pressao_na_frente')
    if p['compactacao'] >= 8:
        t.append('compacto')
    if p['area_ataque'] == 0:
        t.append('ataque_pelos_lados')
    if p['contencao'] == 0:
        t.append('fecha_o_meio')
    t += [f'inst_{c}' for c, _ in instr if c]
    return t


def _limpo(p):
    return {k: v for k, v in p.items() if not k.startswith('_')}


def candidatos(base, base_instr, ctx, olho, atacante_rapido, rec=None, semente=0):
    """3. O plano do técnico (identidade + contexto + vulnerabilidades, do jeito DELE) e variações dentro da identidade."""
    pers = personalidade(base, base_instr, rec, semente)
    p0, motivo = postura(base, ctx)
    p0, m_olho = contra_olheiro(p0, olho, rec, pers)
    i0, m_inst = instrucoes_para(p0, base_instr, olho, atacante_rapido, rec, pers=pers)
    lin = lambda v: _faixa(v, *p0['_lin'])
    cmp_ = lambda v: _faixa(v, *p0['_cmp'])
    cands = [{'plano': p0, 'instr': i0, 'nome': 'plano do técnico', 'especialista': True,
              'motivos': [motivo] + m_olho + m_inst}]
    pr = dict(p0, estilo_defensivo=0, pressao=0, linha_defensiva=lin(p0['linha_defensiva'] + 2))
    cands.append({'plano': pr, 'nome': 'variação: mais pressão', 'especialista': False,
                  'instr': instrucoes_para(pr, base_instr, olho, atacante_rapido, rec, pers=pers)[0], 'motivos': ['variação testada: mais pressão']})
    bl = dict(p0, linha_defensiva=lin(p0['linha_defensiva'] - 2), compactacao=cmp_(p0['compactacao'] + 2))
    cands.append({'plano': bl, 'nome': 'variação: mais fechado', 'especialista': False,
                  'instr': instrucoes_para(bl, base_instr, olho, atacante_rapido, rec, pers=pers)[0], 'motivos': ['variação testada: mais fechado']})
    if any(c == 14 for c, _ in i0):   # sem a marcação individual (a marcação pode desmontar o time)
        cands.append({'plano': p0, 'nome': 'variação: sem marcação individual', 'especialista': False,
                      'instr': instrucoes_para(p0, base_instr, olho, atacante_rapido, rec, alvo_marcacao=None, pers=pers)[0],
                      'motivos': ['variação testada: sem marcação individual']})
    for c in cands:
        c['plano'] = _limpo(c['plano'])
        c['tags'] = tags(c['plano'], c['instr'])
    return cands


def recursos(d, s, ti, P):
    """O que o clube TEM no time titular para executar um plano: pontas abertos, laterais ofensivos."""
    if not P:
        return {}
    sq = s.squad(ti)
    tit = [P.get(tuple(sq[i])) for i in T.titulares(d, ti) if i < len(sq)]
    tit = [f for f in tit if f]
    pontas = [f for f in tit if f.pos in ('LWF', 'RWF', 'LMF', 'RMF') and (f['speed'] >= 80 or f.style in ('Prolific Winger', 'Roaming Flank', 'Crossing Specialist'))]
    lats = [f for f in tit if f.pos in ('LB', 'RB') and f.style in ('Offensive Fullback', 'Fullback Finisher')]
    return {'pontas': len(pontas), 'laterais_of': len(lats)}


def _media(apr, tag, fx):
    g = apr.get(tag) or {'n': 0, 's': 0.0}
    b = apr.get(f'{tag}|{fx}') or {'n': 0, 's': 0.0}
    mg = g['s'] / (g['n'] + PRIOR_N)                                  # média geral encolhida para 0
    return (b['s'] + PRIOR_N * mg) / (b['n'] + PRIOR_N), b['n'] + g['n']


def escolher(cands, e, ctx, rnd=None):
    """4. Amostragem de Thompson sobre as características de cada candidato."""
    rnd = rnd or random.Random()
    apr = e.get('aprendizado') or {}
    fx = faixa(ctx)
    melhor = None
    for c in cands:
        amostras = []
        for t in c['tags']:
            m, n = _media(apr, t, fx)
            amostras.append(rnd.gauss(m, SIGMA / math.sqrt(n + PRIOR_N)))
        nota = (BONUS_ESPECIALISTA if c['especialista'] else 0.0) + sum(amostras) / max(1, len(amostras))
        c['nota'] = round(nota, 2)
        if melhor is None or nota > melhor['nota']:
            melhor = c
    outros = [c for c in cands if c is not melhor]
    if outros and rnd.random() < CURIOSIDADE:   # nunca 100% previsível
        return rnd.choice(outros)
    return melhor


def aprender(e, resultados):
    """Fecha os jogos já disputados do registro: recompensa = saldo do adversário - esperado."""
    feitos = []
    apr = e.setdefault('aprendizado', {})
    for r in e.get('registro') or []:
        if 'recompensa' in r or not r.get('tags'):
            continue
        j = next((x for x in resultados or [] if list(x.get('data') or []) == list(r.get('data') or [])
                  and (x.get('adversario') or '').upper() == r['adversario'].upper()), None)
        if not j:
            continue
        saldo = j['contra'] - j['pro']
        rec = round(saldo - (r.get('esperado') or 0), 2)
        r['resultado'] = f'{j["pro"]} x {j["contra"]}'
        r['recompensa'] = rec
        for a in apr.values():   # o que foi aprendido antes pesa um pouco menos
            a['n'] = round(a['n'] * ESQUECIMENTO, 3)
            a['s'] = round(a['s'] * ESQUECIMENTO, 3)
        for t in r['tags']:
            for chave in (t, f'{t}|{r.get("faixa")}'):
                a = apr.setdefault(chave, {'n': 0, 's': 0.0})
                a['n'] += 1
                a['s'] = round(a['s'] + rec, 3)
        feitos.append(r)
    return feitos


def limpar_registro(e):
    """Remove preparações repetidas do mesmo jogo (fica a última) e refaz o aprendizado do zero, em ordem."""
    vistos, limpo = set(), []
    for x in reversed(e.get('registro') or []):
        k = (tuple(x.get('data') or ()), (x.get('adversario') or '').upper())
        if k in vistos:
            continue
        vistos.add(k)
        limpo.append(x)
    limpo.reverse()
    e['registro'] = limpo
    apr = {}
    for r in limpo:
        if 'recompensa' not in r or not r.get('tags'):
            continue
        for a in apr.values():
            a['n'] = round(a['n'] * ESQUECIMENTO, 3)
            a['s'] = round(a['s'] * ESQUECIMENTO, 3)
        for t in r['tags']:
            for chave in (t, f'{t}|{r.get("faixa")}'):
                a = apr.setdefault(chave, {'n': 0, 's': 0.0})
                a['n'] += 1
                a['s'] = round(a['s'] + r['recompensa'], 3)
    e['aprendizado'] = apr
    e['resumo'] = resumo_aprendizado(e)
    return e


def resumo_aprendizado(e, n=4):
    """O que mais funcionou e o que menos funcionou contra o usuário (só características com 2+ jogos)."""
    apr = e.get('aprendizado') or {}
    gerais = [(k, v['s'] / v['n'], v['n']) for k, v in apr.items() if '|' not in k and v['n'] >= 2]
    gerais.sort(key=lambda x: -x[1])
    nome = lambda k: T.INSTRUCOES.get(int(k[5:]), k) if k.startswith('inst_') else k.replace('_', ' ')
    return {'jogos': sum(1 for r in e.get('registro') or [] if 'recompensa' in r),
            'melhores': [(nome(k), round(m, 2), q) for k, m, q in gerais[:n] if m > 0],
            'piores': [(nome(k), round(m, 2), q) for k, m, q in gerais[::-1][:n] if m < 0]}


# ---------------------------------------------------------------- memória
def _base_memoria(h, d, e, log):
    """Endereço do bloco 0 na memória (os 731 blocos são contíguos, como no save). Usa o guardado se ainda bater;
    senão procura pela assinatura de um bloco (índice do time + nome do técnico) — ~1 min na 1ª vez."""
    import memoria as M
    o_ref = T.BASE + 200 * T.TAM
    assin = d[o_ref + 56:o_ref + 96]
    b0 = e.get('base_memoria')
    if b0 and M.ler(h, b0 + 200 * T.TAM + 56, 40) == assin:
        return b0
    for base, size in M.regioes(h):
        if size > 256 * 1024 * 1024:
            continue
        x = M.ler(h, base, size)
        i = x.find(assin) if x else -1
        if i >= 0:
            b0 = base + i - 56 - 200 * T.TAM
            e['base_memoria'] = b0
            log(f'IA adversária: blocos de tática achados na memória em {b0:#x}')
            return b0
    raise RuntimeError('blocos de tática não encontrados na memória (o jogo está numa carreira?)')


def _escrever_plano(h, addr_bloco, plano, escrever_de_verdade, cru=None, instr=None):
    """Escreve os 3 planos (ajustes, barras e, se `instr`, as 4 vagas de instrução) com conferência; devolve o plano
    que estava na memória. cru = bytes originais do trecho +219..+584 (devolução exata)."""
    import ao_vivo as A
    import memoria as M
    atual = M.ler(h, addr_bloco, T.TAM)
    antes = {k: atual[T.PLANOS[0] + off] for k, off in T.CAMPOS.items()}
    novo = bytearray(atual)
    if cru is not None:
        novo[LO:HI] = cru
    else:
        for p in T.PLANOS:
            for k, off in T.CAMPOS.items():
                novo[p + off] = int(plano[k])
            if instr is not None:
                for i, (c, a) in enumerate(instr):
                    struct.pack_into('<II', novo, p + VAGA_REL + 8 * i, c, a if c else 0)
    if escrever_de_verdade and bytes(novo) != atual:
        A.escrever(h, addr_bloco + LO, bytes(novo[LO:HI]), atual[LO:HI])
    return antes


def _atacante_rapido(d, s, ti, P):
    """(posição no elenco, nome) do atacante mais rápido entre os titulares gravados do clube."""
    if not P:
        return None
    sq = s.squad(ti)
    melhor = None
    for i in T.titulares(d, ti):
        if i < len(sq):
            f = P.get(tuple(sq[i]))
            if f and f.pos in FRENTE and (melhor is None or f['speed'] > melhor[2]):
                melhor = (i, f.name, f['speed'])
    return melhor[:2] if melhor else None


def preparar(d, ti_adv, nome_adv, ctx, olho=None, P=None, resultados=None, escrever_de_verdade=False, log=print,
             rnd=None):
    """Fecha o aprendizado do jogo anterior, devolve o adversário anterior ao original e prepara este."""
    import ao_vivo as A
    import memoria as M
    from save_ml import SaveML
    e = _ler_estado()
    for r in aprender(e, resultados):
        log(f'IA adversária aprendeu: {r["adversario"]} {r["resultado"]} (recompensa {r["recompensa"]:+.2f}) — {", ".join(r["tags"])}')
    h = A.abrir(escrita=escrever_de_verdade)
    b0 = _base_memoria(h, d, e, log)

    def addr(ti):
        o = T.bloco(d, ti)
        a = b0 + (o - T.BASE)
        if M.ler(h, a + 56, 2) != d[o + 56:o + 58]:
            raise RuntimeError(f'bloco do time {ti} não confere na memória')
        return a

    ativo = e.get('ativo')
    if ativo and ativo['ti'] != ti_adv:         # o jogo anterior já foi: o clube volta aos planos dele (A, B e C)
        ka = str(ativo['ti'])
        cru = bytes.fromhex(e['originais_cru'][ka]) if ka in e.get('originais_cru', {}) else None
        _escrever_plano(h, addr(ativo['ti']), e['originais'][ka], escrever_de_verdade, cru=cru)
        log(f'IA adversária: {ativo["nome"]} voltou ao plano original')
        e['ativo'] = None
    k = str(ti_adv)
    o = T.bloco(d, ti_adv)
    if k not in e['originais']:   # 1ª vez contra esse clube: guarda o original (o save é de antes de mexermos nele)
        e['originais'][k] = T.ler(d, ti_adv)
        e.setdefault('originais_cru', {})[k] = d[o + LO:o + HI].hex()
    cru = bytes.fromhex(e['originais_cru'][k])
    base_instr = [(c, T.INSTRUCOES.get(c, '?'), a) for c, a in
                  (struct.unpack_from('<II', cru, T.VAGAS[0] - LO + 8 * i) for i in range(4)) if c]
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    cands = candidatos(e['originais'][k], base_instr, ctx, olho, _atacante_rapido(d, s, ti_adv, P), recursos(d, s, ti_adv, P),
                       semente=ti_adv)
    decidiu = 'estatistica'
    try:   # 12/10/2026: duelo estatística x rede — quem lidera a arena "usuario" escolhe o plano
        import duelo
        if duelo.lider('usuario') == 'rede':
            esc, decidiu = _escolher_pela_rede(cands, ctx, rnd), 'rede'
        else:
            esc = escolher(cands, e, ctx, rnd)
    except Exception as ex:  # noqa: BLE001
        log(f'duelo: {ex}')
        esc = escolher(cands, e, ctx, rnd)
    antes = _escrever_plano(h, addr(ti_adv), esc['plano'], escrever_de_verdade, instr=esc['instr'])
    mud = {c: (antes[c], esc['plano'][c]) for c in esc['plano'] if antes[c] != esc['plano'][c]}
    nomes_alvo = {}
    for c, a in esc['instr']:
        if c == 14:
            nomes_alvo[c] = next((x['nome'] for x in (olho or {}).get('ameacas') or [] if x['idx'] == a), None)
    instr_txt = [T.INSTRUCOES[c] + (f' ({nomes_alvo[c]})' if nomes_alvo.get(c) else '') for c, _ in esc['instr'] if c]
    log(f'IA adversária: {nome_adv} ({T.tecnico(d, ti_adv)}) — {esc["nome"]}: {" | ".join(esc["motivos"])}; '
        f'instruções {instr_txt}; mudanças {mud or "nenhuma"}' + ('' if escrever_de_verdade else ' [ensaio]'))
    if escrever_de_verdade:
        try:   # palpites dos dois modelos para este jogo (placar do duelo, arena "usuario")
            _palpite_usuario(d, ti_adv, nome_adv, ctx, esc, e, decidiu)
        except Exception as ex:  # noqa: BLE001
            log(f'duelo (palpite): {ex}')
        e['ativo'] = {'ti': ti_adv, 'nome': nome_adv, 'data': ctx.get('data')}
        # 12/10/2026: o mesmo jogo preparado de novo (Central reiniciada) substitui o registro em vez de duplicar —
        # duplicado, o resultado contava várias vezes no aprendizado (o Ipswich entrou 8 vezes)
        e['registro'] = [x for x in (e.get('registro') or [])[-120:]
                         if not (list(x.get('data') or []) == list(ctx.get('data') or []) and (x.get('adversario') or '').upper() == nome_adv.upper()
                                 and 'recompensa' not in x)]
        e['registro'] = e['registro'] + [{
            'quando': time.strftime('%Y-%m-%d %H:%M'), 'data': ctx.get('data'), 'adversario': nome_adv,
            'tecnico': T.tecnico(d, ti_adv), 'competicao': ctx.get('competicao'), 'faixa': faixa(ctx),
            'esperado': ctx.get('esperado'), 'escolha': esc['nome'], 'motivo': ' | '.join(esc['motivos']),
            'olheiro': (olho or {}).get('frases') or [], 'instrucoes': instr_txt, 'tags': esc['tags'], 'decidiu': decidiu,
            'candidatos': [(c['nome'], c['nota']) for c in cands], 'original': e['originais'][k], 'plano': esc['plano']}]
        e['resumo'] = resumo_aprendizado(e)
    _gravar_estado(e)
    return esc


def _x_usuario(ctx, tags_):
    import duelo
    return duelo.feat_usr(ctx.get('forca_nos') or 75, ctx.get('forca_adv') or 75, not ctx.get('adv_em_casa'),
                          duelo.forma_str(ctx.get('forma_nos')), duelo.forma_str(ctx.get('forma_adv')), ctx.get('grande'), tags_)


def _escolher_pela_rede(cands, ctx, rnd=None):
    """A rede prevê os gols de cada lado com cada plano candidato e fica com o melhor saldo para o adversário."""
    import duelo
    rnd = rnd or random.Random()
    r = duelo.rede('usuario')
    melhor = None
    for c in cands:
        lu, la = r.prever(_x_usuario(ctx, c['tags']))
        c['nota'] = round(la - lu, 2)
        if melhor is None or c['nota'] > melhor['nota']:
            melhor = c
    outros = [c for c in cands if c is not melhor]
    if outros and rnd.random() < CURIOSIDADE:
        return rnd.choice(outros)
    return melhor


def _palpite_usuario(d, ti_adv, nome_adv, ctx, esc, e, decidiu):
    import carreira
    import duelo
    if not ctx.get('data'):
        return
    user_ti, _ = carreira.time_do_usuario(d)
    casa = ti_adv if ctx.get('adv_em_casa') else user_ti
    fora = user_ti if ctx.get('adv_em_casa') else ti_adv
    apr, fx = e.get('aprendizado') or {}, faixa(ctx)
    extra = sum(_media(apr, t, fx)[0] for t in esc['tags']) / max(1, len(esc['tags']))   # o que a IA aprendeu do plano
    with duelo.TRAVA:
        ed = duelo.estado()
        duelo.prever(ed, 'usuario', duelo.chave(ctx['data'], casa, fora), ctx['data'], _x_usuario(ctx, esc['tags']),
                     duelo.est_usr(ed, ctx.get('esperado'), extra),
                     {'adv': clube_nome(nome_adv), 'inverter': bool(ctx.get('adv_em_casa')), 'decidiu': decidiu, 'plano': esc['nome']})
        duelo.gravar(ed)


def clube_nome(n):
    import clube
    return clube.nome_time(n)


def contexto(dados, pr):
    """Contexto do próximo jogo (pr = próximo do pulso) a partir da prévia da reunião (força, competição, chances)."""
    px = next((x for x in dados.get('proximos') or [] if x.get('data') == pr.get('data') and x.get('casa') == pr.get('casa')
               and x.get('fora') == pr.get('fora')), None) or dados.get('proximo_jogo') or {}
    eu_casa = px.get('eu_casa', pr.get('casa') == (dados.get('time') or '').upper())
    f = px.get('forca') or {}
    comp = px.get('competicao') or ''
    pb = px.get('prob') or {}
    p_adv, p_nos = (pb.get('fora'), pb.get('casa')) if eu_casa else (pb.get('casa'), pb.get('fora'))
    esperado = round(((p_adv or 0) - (p_nos or 0)) / 100 * 1.6, 2) if pb else 0.0   # saldo esperado do adversário
    fm = px.get('forma') or {}
    return {'data': pr.get('data'), 'competicao': comp, 'adv_em_casa': not eu_casa, 'esperado': esperado,
            'forma_nos': fm.get('casa') if eu_casa else fm.get('fora'), 'forma_adv': fm.get('fora') if eu_casa else fm.get('casa'),
            'forca_adv': f.get('fora') if eu_casa else f.get('casa'), 'forca_nos': f.get('casa') if eu_casa else f.get('fora'),
            'grande': comp in GRANDES or bool(px.get('final')) or bool(px.get('classico'))}
