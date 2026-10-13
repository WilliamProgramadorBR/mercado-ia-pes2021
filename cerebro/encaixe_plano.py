# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ENCAIXE NO PLANO DE JOGO para o mercado da IA (12/10/2026).

Cada clube da IA tem plano de jogo e instruções avançadas no save (tatica_save). O jogador que combina com o jeito do
clube jogar ganha um bônus de até +2 pontos na lista de alvos. CUIDADO (pedido do usuário): o bônus só ORDENA
candidatos que já passaram por todas as regras do mercado (nota mínima e máxima, posição natural, preço, idade,
vendedor) — nunca faz o clube pagar mais nem contratar fora de posição.

Análise de 12/10/2026: nos jogos SIMULADOS entre clubes da IA só a força pesa; o encaixe vale nos jogos jogados no
motor de verdade (contra o usuário) e deixa os elencos com a cara do técnico.
"""
import tatica_save as T

POSSE = {'Orchestrator', 'Creative Playmaker', 'Build Up', 'Hole Player', 'Classic No. 10'}
CONTRA = {'Goal Poacher', 'Prolific Winger', 'Roaming Flank', 'Dummy Runner', 'Fox in the Box'}
CRIA_9 = {'Classic No. 10', 'Creative Playmaker', 'Hole Player'}
MEIO = {'DMF', 'CMF', 'AMF', 'LMF', 'RMF'}
FRENTE = {'CF', 'SS', 'LWF', 'RWF'}
LATERAL = {'LB', 'RB'}
TETO = 2.0


def planos(d, teams):
    """{índice do time: {'plano': {...}, 'instr': {códigos}}} lidos do save."""
    out = {}
    for t in teams:
        try:
            pl = T.ler(d, t.idx)
        except Exception:  # noqa: BLE001
            pl = None
        if pl:
            out[t.idx] = {'plano': pl, 'instr': {c for c, _, _ in T.instrucoes(d, t.idx)}}
    return out


def fit(info, p, pos):
    """(bônus 0..2, motivo curto) do jogador `p` para a vaga `pos` no plano do clube."""
    if not info:
        return 0.0, ''
    pl, inst = info['plano'], info['instr']
    b, por = 0.0, []

    def soma(v, txt):
        nonlocal b
        b += v
        por.append(txt)
    if pl['estilo_ofensivo'] == 1 and pos in MEIO and p.style in POSSE:
        soma(1.0, f'{p.style} no time de posse')
    if pl['estilo_ofensivo'] == 0 and pos in FRENTE and p.style in CONTRA:
        soma(1.0, f'{p.style} no time de contra-ataque')
    if pl['estilo_ofensivo'] == 0 and pos in FRENTE and p['speed'] >= 85:
        soma(0.5, 'velocidade para o contra-ataque')
    if pl['saida_de_bola'] == 1 and pos not in FRENTE and p['lowpass'] >= 80:
        soma(0.3, 'passe curto para a saída curta')
    if pl['saida_de_bola'] == 0 and pos not in FRENTE and p['loftpass'] >= 80:
        soma(0.3, 'passe longo para a bola longa')
    if pl['estilo_defensivo'] == 0 and pl['pressao'] == 0 and pos != 'CB' and p['stamina'] >= 80:
        soma(0.5, 'fôlego para pressionar')
    if pl['linha_defensiva'] >= 7 and pos == 'CB' and p['speed'] >= 78:
        soma(0.7, 'zagueiro rápido para a linha alta')
    if 7 in inst and pos == 'CF' and p.style == 'Target Man':
        soma(1.5, 'pivô para o alvo de cruzamento')
    if 7 in inst and pos in {'LWF', 'RWF', 'LMF', 'RMF'} and p.style == 'Crossing Specialist':
        soma(1.0, 'cruzador para o alvo de cruzamento')
    if 2 in inst and pos == 'CF' and p.style in CRIA_9:
        soma(1.5, 'centroavante criador para o falso 9')
    if 4 in inst and pos in LATERAL and p.style == 'Offensive Fullback':
        soma(1.2, 'lateral ofensivo para a instrução do técnico')
    if 10 in inst and pos == 'DMF' and p.style == 'Anchor Man':
        soma(1.5, 'volante fixo para a ancoragem')
    if 6 in inst and 'One-touch Pass' in p.skills:
        soma(0.5, 'toque de primeira para o tiki-taka')
    if 13 in inst and pos != 'CB' and p['stamina'] >= 82:
        soma(0.5, 'fôlego para a pressão ofensiva')
    return min(TETO, round(b, 2)), (por[0] if por else '')
