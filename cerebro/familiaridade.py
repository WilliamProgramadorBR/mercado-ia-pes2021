# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""FAMILIARIDADE TÁTICA do elenco do usuário (12/10/2026) — os números das telas "Tática ofensiva/defensiva".

O jogo guarda, só para os jogadores do time do usuário, 14 notas (0-99) aprendidas com o tempo: quanto cada um está
acostumado a cada opção do plano de jogo (o Rüdiger, há anos num time de posse: posse 91, contra-ataque 53). Ficam no
save fora dos blocos comprimidos (~0xC50000-0xC80000; em 2 cópias): u32 registro, u32 id e os 14 bytes na ordem
  contra, posse, longo, curto, ampla, centro, manter, flexível, pressão na frente, retranca, contenção centro,
  contenção ampla, agressiva, tradicional.
Daqui saem: o entrosamento de cada jogador com o plano ATUAL, o custo de trocar cada ajuste e quem destoa.
"""
import struct

import tatica_save as T

# ajuste do plano -> (posição do byte quando o valor é 0, quando é 1, nome do 0, nome do 1)
AJUSTES = {'estilo_ofensivo': (0, 1, 'contra-ataque', 'posse de bola'), 'saida_de_bola': (2, 3, 'passe longo', 'passe curto'),
           'area_ataque': (4, 5, 'ataque pelos lados', 'ataque pelo centro'), 'posicionamento': (6, 7, 'manter formação', 'flexível'),
           'estilo_defensivo': (8, 9, 'pressão na frente', 'retranca'), 'contencao': (10, 11, 'contenção no centro', 'contenção ampla'),
           'pressao': (12, 13, 'pressão agressiva', 'pressão tradicional')}
FAIXA = (0xB00000, 0xE00000)


def ler(d, chaves):
    """{(reg, id): [14 notas]} para os jogadores pedidos (primeira cópia válida)."""
    alvo = {struct.pack('<II', r, i): (r, i) for r, i in chaves}
    out = {}
    lo, hi = FAIXA
    for o in range(lo, min(hi, len(d) - 22), 4):
        k = d[o:o + 8]
        if k in alvo and alvo[k] not in out:
            v = list(d[o + 8:o + 22])
            if all(10 <= x <= 99 for x in v):
                out[alvo[k]] = v
    return out


def analisar(d, jogadores):
    """jogadores = lista da Central (nome, reg, pid, pos, minutos_recentes). Devolve o painel de entrosamento."""
    o = T.bloco_usuario(d)
    if o is None:
        return None
    pl = T.ler_em(d, o)
    notas = ler(d, [(j['reg'], j['pid']) for j in jogadores])
    if not notas:
        return None
    escolhido = {k: AJUSTES[k][pl[k]] for k in AJUSTES}            # posição do byte da opção em uso
    alternativa = {k: AJUSTES[k][1 - pl[k]] for k in AJUSTES}
    linhas = []
    for j in jogadores:
        v = notas.get((j['reg'], j['pid']))
        if not v:
            continue
        atual = round(sum(v[escolhido[k]] for k in AJUSTES) / len(AJUSTES))
        fracos = sorted(((v[escolhido[k]], AJUSTES[k][2 + pl[k]]) for k in AJUSTES))[:2]
        linhas.append({'nome': j['nome'], 'pos': j.get('pos'), 'entrosamento': atual,
                       'titular': (j.get('minutos_recentes') or 0) >= 0.4,
                       'fracos': [f'{n} {x}' for x, n in fracos if x < 75]})
    linhas.sort(key=lambda x: (not x['titular'], -x['entrosamento']))
    base = [x for x in linhas if x['titular']] or linhas
    tit = [notas[(j['reg'], j['pid'])] for j in jogadores if (j['reg'], j['pid']) in notas
           and ((j.get('minutos_recentes') or 0) >= 0.4 or not any(x['titular'] for x in linhas))]
    mudancas = []
    for k, (b0, b1, n0, n1) in AJUSTES.items():
        hoje = round(sum(v[escolhido[k]] for v in tit) / len(tit))
        troca = round(sum(v[alternativa[k]] for v in tit) / len(tit))
        mudancas.append({'ajuste': k, 'atual': (n0, n1)[pl[k]], 'alternativa': (n0, n1)[1 - pl[k]], 'hoje': hoje,
                         'se_trocar': troca, 'custo': hoje - troca})
    mudancas.sort(key=lambda x: -x['custo'])
    return {'time': round(sum(x['entrosamento'] for x in base) / len(base)), 'jogadores': linhas,
            'mudancas': mudancas, 'plano': {k: (AJUSTES[k][2], AJUSTES[k][3])[pl[k]] for k in AJUSTES}}
