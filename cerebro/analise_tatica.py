# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Relatório da COMISSÃO TÉCNICA para o próximo jogo (11/10/2026): foco tático, com dados do próprio jogo.

Adversário: formação real do clube no save (SaveML.formation), melhor escalação nela (encaixe.best_xi), estilos de jogo
e atributos (foto da memória). Diz como ele ataca (lados x meio, jogo aéreo, transição, quem cria), onde é fraco
(encaixe.fit_issues + piores titulares) e o que fazer.
Nosso time: titulares reais (lista do bloco do usuário no save) com o momento de cada um (seta de condição, condição
física, moral): elos fortes e elos fracos, e os confrontos de lado (nosso lateral x ponta deles).
"""
import encaixe

POS = encaixe.POS_CODES
LADO = {'LB': 'esquerdo', 'LMF': 'esquerdo', 'LWF': 'esquerdo', 'RB': 'direito', 'RMF': 'direito', 'RWF': 'direito'}
OPOSTO = {'LB': ('RWF', 'RMF'), 'RB': ('LWF', 'LMF')}


def _formacao(codes):
    p = [POS[c] for c in codes]
    d = sum(1 for x in p if x in ('CB', 'LB', 'RB'))
    a = sum(1 for x in p if x in ('CF', 'SS', 'LWF', 'RWF'))
    m = 10 - d - a
    return f'{d}-{m}-{a}'


def _vel(f):
    return max(f.attrs['speed'], f.attrs['accel'])


def gerar(s, d, ti, adv, P, J):
    import carreira
    pl = [P[k] for k in s.squad(adv) if P.get(k)]
    if len(pl) < 11:
        return None
    try:
        codes = s.formation(adv)
        slots = [(POS[c], encaixe.ACCEPTED[POS[c]]) for c in codes] if len(codes) == 11 and POS[codes[0]] == 'GK' else encaixe.SLOTS
        form = _formacao(codes) if len(codes) == 11 else '4-3-3'
    except Exception:  # noqa: BLE001
        slots, form = encaixe.SLOTS, '4-3-3'
    xi, _ = encaixe.best_xi(pl, slots)
    _nota, problemas = encaixe.fit_issues(xi)
    nome_adv = s.name(adv).strip()
    por_slot = [(sl, f, round(r)) for sl, f, r in xi]
    lados = [f for sl, f, _ in por_slot if sl in ('LWF', 'RWF', 'LMF', 'RMF')]
    centro = [f for sl, f, _ in por_slot if sl in ('CF', 'SS', 'AMF')]
    frente = [f for sl, f, _ in por_slot if sl in ('CF', 'SS', 'LWF', 'RWF')]
    ataque = [f'Formação provável: {form}.']
    if lados and centro:
        pl_l = sum(_vel(f) + f.attrs['drib'] for f in lados) / len(lados)
        pl_c = sum(f.attrs['finish'] + max(f.attrs['lowpass'], f.attrs['drib']) for f in centro) / len(centro)
        destaque = max(lados, key=lambda f: _vel(f) + f.attrs['drib']) if pl_l >= pl_c else max(centro, key=lambda f: f.attrs['finish'])
        ataque.append(('Ataca mais pelos lados' if pl_l >= pl_c else 'Ataca mais por dentro') +
                      f': a principal arma é {destaque.name.strip()} ({destaque.pos}).')
    cf = next((f for sl, f, _ in por_slot if sl == 'CF'), None)
    cruz = [f for _, f, _ in por_slot if f.style == 'Crossing Specialist' or 'Pinpoint Crossing' in f.skills]
    if cf and (cf.attrs['header'] >= 80 or cf.attrs['height'] >= 188) and cruz:
        ataque.append(f'Jogo aéreo: {cf.name.strip()} (cabeceio {cf.attrs["header"]}) recebe cruzamentos de {cruz[0].name.strip()}.')
    if frente and sum(_vel(f) for f in frente) / len(frente) >= 85:
        ataque.append(f'Transição rápida: o ataque tem velocidade média {round(sum(_vel(f) for f in frente) / len(frente))}.')
    criador = next((f for _, f, _ in por_slot if f.style in encaixe.CREATORS), None)
    if criador:
        ataque.append(f'Quem pensa o jogo: {criador.name.strip()} ({criador.style}).')
    fracos_deles = [f'{f.name.strip()} ({sl}, nota {r})' for sl, f, r in sorted(por_slot, key=lambda x: x[2])[:2] if sl != 'GK']
    fracos_deles += [p for p in problemas][:3]
    # nosso time: titulares reais (lista do bloco do usuário) e o momento de cada um
    sq = s.squad(ti)
    u = carreira.BLOCO_USUARIO
    idx = [i for i in d[u:u + 11] if i < len(sq)]
    porK = {j['k']: j for j in J}
    meus = [porK[sq[i]] for i in idx if sq[i] in porK]
    fortes, fracos = [], []
    for j in sorted(meus, key=lambda j: -j['ovr']):
        bom = (j.get('seta') or 2) >= 3 and j['moral'] >= 65 and (j.get('condicao') or 100) >= 85
        ruim = (j.get('seta') or 2) <= 1 or j['moral'] < 45 or (j.get('condicao') or 100) < 72
        if bom and len(fortes) < 3:
            fortes.append(f'{j["nome"]} ({j["pos"]}, nota {j["ovr"]}): em boa fase e inteiro fisicamente.')
        if ruim and len(fracos) < 3:
            motivo = ('seta em baixa' if (j.get('seta') or 2) <= 1 else 'moral baixa' if j['moral'] < 45 else
                      f'condição {j.get("condicao")}')
            fracos.append(f'{j["nome"]} ({j["pos"]}): {motivo}.')
    recomenda = []
    fichas = {j['k']: P.get(j['k']) for j in meus}
    for j in meus:
        f = fichas.get(j['k'])
        if not f or j['pos'] not in OPOSTO:
            continue
        ponta = next((g for sl, g, _ in por_slot if sl in OPOSTO[j['pos']]), None)
        if ponta and _vel(ponta) - _vel(f) >= 8:
            fracos.append(f'Lado {LADO[j["pos"]]}: {j["nome"]} (velocidade {_vel(f)}) contra {ponta.name.strip()} (velocidade {_vel(ponta)}).')
            recomenda.append(f'Dobrar a marcação no lado {LADO[j["pos"]]} ou recuar {j["nome"]} para não ficar no mano a mano.')
    if 'zaga lenta' in problemas:
        recomenda.append(f'A zaga do {nome_adv} é lenta: bolas nas costas e atacantes rápidos em profundidade.')
    if 'zaga baixa (jogo aéreo)' in problemas:
        recomenda.append(f'O {nome_adv} sofre no jogo aéreo: cruzamentos e bolas paradas são caminho.')
    if 'meio sem volante de contenção' in problemas:
        recomenda.append('Eles não têm volante de contenção: infiltrar pelo meio e chutar de fora.')
    if any(a.startswith('Transição rápida') for a in ataque):
        recomenda.append('Cuidado ao perder a bola: manter a linha de trás compacta contra a transição deles.')
    if not recomenda:
        recomenda.append('Jogo equilibrado no papel: manter o plano e decidir nos detalhes, como bola parada e transição.')
    return {'adversario': nome_adv, 'formacao': form, 'ataque': ataque, 'fracos_deles': fracos_deles,
            'nossos_fortes': fortes, 'nossos_fracos': fracos, 'recomendacoes': recomenda[:4]}
