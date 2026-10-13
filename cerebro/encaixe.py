# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Índice de encaixe de elencos (v0).

Não é a fórmula oficial do PES. Mede quatro coisas, de 0 a 100:
  forca        - nota média estimada do melhor XI (4-3-3)
  encaixe      - complementaridade de estilos/habilidades (regras de futebol, lista de problemas)
  profundidade - quantas vagas do XI têm reserva natural à altura (até 6 pontos abaixo; 1 reserva por vaga)
  ciclo        - idade do XI (ideal 24-29, pouca gente 32+)
"""
import statistics as st

# atributos-chave por posição (média -> nota estimada; calibrado com telas do jogo)
KEYS = {
    'GK': ['gk', 'catching', 'clearing', 'reflex', 'gk_reach'],
    'CB': ['def', 'ball_win', 'header', 'jump', 'phys_cont', 'aggres', 'speed'],
    'LB': ['def', 'ball_win', 'speed', 'stamina', 'lowpass', 'accel', 'drib'],
    'RB': ['def', 'ball_win', 'speed', 'stamina', 'lowpass', 'accel', 'drib'],
    'DMF': ['def', 'ball_win', 'lowpass', 'loftpass', 'stamina', 'phys_cont', 'aggres'],
    'CMF': ['lowpass', 'loftpass', 'ball_ctrl', 'stamina', 'drib', 'ball_win', 'atk'],
    'LMF': ['lowpass', 'drib', 'speed', 'stamina', 'ball_ctrl', 'accel', 'loftpass'],
    'RMF': ['lowpass', 'drib', 'speed', 'stamina', 'ball_ctrl', 'accel', 'loftpass'],
    'AMF': ['atk', 'ball_ctrl', 'drib', 'lowpass', 'finish', 'tight_pos', 'balance'],
    'LWF': ['atk', 'drib', 'speed', 'accel', 'finish', 'ball_ctrl', 'tight_pos'],
    'RWF': ['atk', 'drib', 'speed', 'accel', 'finish', 'ball_ctrl', 'tight_pos'],
    'SS': ['atk', 'finish', 'ball_ctrl', 'drib', 'tight_pos', 'accel', 'lowpass'],
    'CF': ['atk', 'finish', 'header', 'phys_cont', 'ball_ctrl', 'kick_pwr', 'speed'],
}
# calibração 30/09/2026 com 16 notas reais (julho/2033): erro médio ~1,2
CAL_A, CAL_B = -15.5, 1.208
POS_OFFSET = {'GK': -7.0, 'LB': 4.0, 'RB': 4.0}  # goleiros saíam altos e laterais baixos
APT_PENALTY = {2: 2, 1: 6, 0: 14}  # posição SECUNDÁRIA: 2 = aptidão A, 1 = B, 0 = sem aptidão
# (na posição registrada não há penalidade; ajuste por posição só vale para quem é da posição)

# Formação de segurança para exportações antigas. No save real, evaluate() usa
# as 11 posições do plano tático que o clube efetivamente está usando.
SLOTS = [
    ('GK', ['GK']), ('CB', ['CB']), ('CB', ['CB']), ('LB', ['LB', 'RB']), ('RB', ['RB', 'LB']),
    ('DMF', ['DMF', 'CMF']), ('CMF', ['CMF', 'DMF', 'AMF']), ('CMF', ['CMF', 'AMF', 'DMF']),
    ('LWF', ['LWF', 'LMF', 'SS']), ('RWF', ['RWF', 'RMF', 'SS']), ('CF', ['CF', 'SS']),
]
POS_CODES = ['GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
ACCEPTED = {
    'GK': ['GK'],
    'CB': ['CB'],
    'LB': ['LB', 'RB'],
    'RB': ['RB', 'LB'],
    'DMF': ['DMF', 'CMF'],
    'CMF': ['CMF', 'DMF', 'AMF'],
    'LMF': ['LMF', 'LWF', 'LB', 'CMF'],
    'RMF': ['RMF', 'RWF', 'RB', 'CMF'],
    'AMF': ['AMF', 'CMF', 'SS'],
    'LWF': ['LWF', 'LMF', 'SS'],
    'RWF': ['RWF', 'RMF', 'SS'],
    'SS': ['SS', 'AMF', 'CF', 'LWF', 'RWF'],
    'CF': ['CF', 'SS'],
}
CREATORS = {'Orchestrator', 'Creative Playmaker', 'Classic No. 10', 'Hole Player'}
SHIELDS = {'Anchor Man', 'The Destroyer'}


_RATING_CACHE = {}


def rating(p, pos):
    key = (id(p), pos)
    r = _RATING_CACHE.get(key)
    if r is None:
        base = CAL_A + CAL_B * sum(p[k] for k in KEYS[pos]) / len(KEYS[pos])
        if p.pos == pos:
            r = base + POS_OFFSET.get(pos, 0)
        else:
            r = base - APT_PENALTY.get(p[f'pp_{pos}'], 14)
        _RATING_CACHE[key] = r
    return r


def formation_slots(team):
    """Converte a formação real do save em vagas avaliáveis; recua para 4-3-3 se necessário."""
    codes = getattr(team, 'formation', None) or []
    if len(codes) != 11 or any(not isinstance(c, int) or c < 0 or c >= len(POS_CODES) for c in codes):
        return SLOTS
    positions = [POS_CODES[c] for c in codes]
    # Formação inválida/corrompida não deve contaminar decisões de mercado.
    if positions.count('GK') != 1:
        return SLOTS
    return [(pos, ACCEPTED[pos]) for pos in positions]


def best_xi(players, slots=None):
    """Escalação gulosa nas vagas recebidas (por padrão, o 4-3-3 de segurança)."""
    free = list(players)
    xi = []
    for slot, accepted in (slots or SLOTS):
        best = None
        for p in free:
            for pos in accepted:
                r = rating(p, pos) - (0 if pos == slot else 2)
                if best is None or r > best[0]:
                    best = (r, p, pos)
        if best:
            xi.append((slot, best[1], best[0]))
            free.remove(best[1])
    return xi, free


def fit_issues(xi):
    """Regras de complementaridade. Retorna (nota 0-100, lista de problemas)."""
    by = {}
    for slot, p, r in xi:
        by.setdefault(slot, []).append(p)
    mids = (by.get('DMF', []) + by.get('CMF', []) + by.get('LMF', []) +
            by.get('RMF', []) + by.get('AMF', []))
    cbs = by.get('CB', [])
    fbs = by.get('LB', []) + by.get('RB', [])
    front = by.get('LWF', []) + by.get('RWF', []) + by.get('SS', []) + by.get('CF', [])
    cf = by.get('CF', [None])[0]
    issues, score = [], 100

    def has_skill(ps, s):
        return any(s in p.skills for p in ps)

    shield = [p for p in mids if p.style in SHIELDS or (p['def'] >= 80 and p['ball_win'] >= 80)]
    creator = [p for p in mids + front if p.style in CREATORS or
               ('Through Passing' in p.skills and p['lowpass'] >= 82)]
    if not shield:
        score -= 15; issues.append('meio sem volante de contenção')
    if not creator:
        score -= 15; issues.append('sem armador/criador')
    if cf:
        if cf.style == 'Target Man':
            crossers = [p for p in front + fbs + mids if p.style == 'Crossing Specialist' or 'Pinpoint Crossing' in p.skills]
            if not crossers:
                score -= 10; issues.append('pivô sem ninguém que cruze')
        if cf.style in ('Goal Poacher', 'Fox in the Box', 'Dummy Runner') and not creator                 and not has_skill(mids + front, 'Through Passing'):
            score -= 10; issues.append('artilheiro sem quem lance em profundidade')
    if cbs:
        if not any(p['height'] >= 185 or p['header'] >= 80 for p in cbs):
            score -= 10; issues.append('zaga baixa (jogo aéreo)')
        if not any(p['speed'] >= 75 for p in cbs):
            score -= 8; issues.append('zaga lenta')
        if sum(1 for p in cbs if p.style == 'Extra Frontman') >= 2:
            score -= 6; issues.append('dois zagueiros que avançam')
        if not any(p.style == 'Build Up' or p['lowpass'] >= 75 for p in cbs):
            score -= 5; issues.append('zaga sem saída de bola')
    attacking_fbs = [p for p in fbs if p.style in ('Offensive Fullback', 'Fullback Finisher')]
    if len(attacking_fbs) == 2 and not shield:
        score -= 10; issues.append('dois laterais ofensivos sem proteção no meio')
    if front and st.mean(p['speed'] for p in front) < 78:
        score -= 8; issues.append('ataque lento')
    return max(score, 0), issues


def evaluate(team):
    players = team.players
    if len(players) < 11:
        return None
    slots = formation_slots(team)
    xi, bench = best_xi(players, slots)
    forca = st.mean(r for _, _, r in xi)
    enc, issues = fit_issues(xi)
    # cada reserva cobre uma vaga só; precisa ser natural na posição e no máximo 6 pontos pior
    covered, spare = 0, list(bench)
    for slot, starter, r in xi:
        cands = [(rating(p, slot), p) for p in spare if p.pos == slot or p[f'pp_{slot}'] == 2]
        if cands:
            br, bp = max(cands, key=lambda x: x[0])
            if br >= r - 6:
                covered += 1
                spare.remove(bp)
    prof = 100 * covered / len(xi)
    ages = [p.age for _, p, _ in xi]
    age_avg = st.mean(ages)
    ciclo = max(0, 100 - 8 * max(0, abs(age_avg - 26.5) - 2.5) - 6 * sum(1 for a in ages if a >= 32))
    return {
        'time': team.name, 'jogadores': len(players), 'forca': round(forca, 1), 'encaixe': enc,
        'profundidade': round(prof), 'idade_xi': round(age_avg, 1), 'ciclo': round(ciclo),
        'problemas': issues, 'formacao': '-'.join(slot for slot, _ in slots),
        'xi': [(slot, p.name, round(r)) for slot, p, r in xi],
    }
