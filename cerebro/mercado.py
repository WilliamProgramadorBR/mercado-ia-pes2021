"""Motor de decisão de transferências (v0).

Fluxo de uma janela:
  1. diagnóstico: carências de cada clube (encaixe, profundidade, idade, vaga mais fraca)
  2. alvos: jogadores de outros clubes (ou livres) que resolvem a carência no nível certo
  3. escolha: o candidato que mais melhora o índice do clube pelo menor custo
  4. rodadas: clubes fortes agem primeiro; quem perde jogador reage na rodada seguinte

Dinheiro: livro-caixa próprio (o valor em R$ do jogo não é lido). Valores em "milhões".
"""
import math
import random
import statistics as st
from dataclasses import dataclass, field

import encaixe
import encaixe_plano
import memoria_clubes

# 12/10/2026: elencos de tamanho real. O simulador do jogo escolhe o XI dos clubes da IA quase ao acaso; com elenco
# inchado (o Real chegou a 38) os melhores jogam menos (melhor do setor começa 62% com até 24, 53% com 33+).
MIN_SQUAD, MAX_SQUAD = 22, 28
SQUAD_TRIM_TO = 27       # acima de MAX_SQUAD o clube vende excedentes até ficar com 27
TRIM_MAX_SALES = 5       # no máximo 5 vendas de excedente por clube por janela (aos poucos, como na vida real)
TRIM_CLUBES = 60         # só os 60 clubes mais fortes (os que decidem ligas e Champions); 312 clubes passavam de 28
TRIM_MAX_TOTAL = 15      # por rodada do mercado, para sobrar espaço para as contratações normais
MAX_BUYS = 2          # contratações por clube por janela (preserva entrosamento)
MAX_SALES = 2         # vendas por clube por janela
MIN_GAIN = 1.5        # ganho mínimo no índice para valer a contratação
ACT_CHANCE = 0.55     # chance de um clube com carência agir numa rodada (mercado imperfeito)
ROUNDS = 4
# clubes de elite ("rivais"): força do XI a até RIVAL_GAP pontos do time do usuário
RIVAL_GAP = 4.0
RIVAL_MAX_BUYS = 3
RIVAL_ACT_CHANCE = 0.85
RIVAL_STAR_ROOM = 8      # rivais podem contratar até 8 pontos acima do próprio nível
RIVAL_BUDGET_MULT = 1.6
RIVAL_MAX_SQUAD = 28     # era 38: elenco inchado piora a escalação do simulador (ver MAX_SQUAD)
POACH_PREMIUM = 1.3      # pagar mais para tirar jogador de clube do mesmo nível
SPECIAL_TEAMS = {'WORLD SELECTION', 'THE OLD BOYS'}

NEED_ROLE = {
    'meio sem volante de contenção': ('DMF', lambda p: p.style in encaixe.SHIELDS or (p['def'] >= 80 and p['ball_win'] >= 80)),
    'sem armador/criador': ('CMF', lambda p: p.style in encaixe.CREATORS or 'Through Passing' in p.skills),
    'pivô sem ninguém que cruze': ('RWF', lambda p: p.style == 'Crossing Specialist' or 'Pinpoint Crossing' in p.skills),
    'artilheiro sem quem lance em profundidade': ('AMF', lambda p: 'Through Passing' in p.skills or p.style in encaixe.CREATORS),
    'zaga baixa (jogo aéreo)': ('CB', lambda p: p['height'] >= 187 or p['header'] >= 82),
    'zaga lenta': ('CB', lambda p: p['speed'] >= 78),
    'zaga sem saída de bola': ('CB', lambda p: p.style == 'Build Up' or p['lowpass'] >= 76),
    'dois laterais ofensivos sem proteção no meio': ('DMF', lambda p: p.style in encaixe.SHIELDS),
    'ataque lento': ('LWF', lambda p: p['speed'] >= 85),
}


def value(p, ovr):
    """Valor de mercado próprio (milhões): cresce exponencialmente com a nota, cai com a idade."""
    age_f = 1.25 if p.age <= 21 else 1.1 if p.age <= 24 else 1.0 if p.age <= 28 else 0.7 if p.age <= 31 else 0.35
    return round(0.4 * math.exp((ovr - 65) / 5.5) * age_f, 1)


@dataclass
class Club:
    team: object
    tier: float                 # força do XI no início da janela
    budget: float
    buys: int = 0
    sales: int = 0
    rival: bool = False
    profile: dict = field(default_factory=dict)
    log: list = field(default_factory=list)


@dataclass
class Move:
    rodada: int
    jogador: str
    idade: int
    pos: str
    estilo: str
    nota: float
    de: str
    para: str
    valor: float
    motivo: str
    reg: int = 0
    pid: int = 0
    src_idx: int = -1     # -1 = jogador sem clube
    dst_idx: int = -1
    perfil: str = ''


def is_national(team, membership):
    """Heurística extra: seleção = mais da metade do elenco também aparece em outro time (convocados)."""
    if not team.players:
        return False
    shared = sum(1 for p in team.players if len(membership.get(id(p), [])) > 1)
    return shared / len(team.players) >= 0.5


def best_rating(p):
    return max(encaixe.rating(p, pos) for pos in encaixe.KEYS if p.pos == pos or p[f'pp_{pos}'] == 2)


def role_for_formation(team, desired):
    """Traduz uma necessidade conceitual para uma posição existente na formação real."""
    slots = [slot for slot, _ in encaixe.formation_slots(team)]
    if desired in slots:
        return desired
    alternatives = {
        'DMF': ('CMF', 'LMF', 'RMF', 'AMF'),
        'CMF': ('AMF', 'DMF', 'LMF', 'RMF'),
        'AMF': ('CMF', 'SS', 'LWF', 'RWF'),
        'LWF': ('RWF', 'LMF', 'RMF', 'SS', 'CF'),
        'RWF': ('LWF', 'RMF', 'LMF', 'SS'),
    }
    return next((pos for pos in alternatives.get(desired, ()) if pos in slots), desired)


def needs_of(club):
    """Lista de carências: (posição, filtro, faixa de nota mínima, motivo)."""
    ev = encaixe.evaluate(club.team)
    if not ev:
        return [], None
    xi, bench = encaixe.best_xi(club.team.players, encaixe.formation_slots(club.team))
    forca = ev['forca']
    out = []
    for issue in ev['problemas']:
        if issue in NEED_ROLE:
            pos, flt = NEED_ROLE[issue]
            pos = role_for_formation(club.team, pos)
            out.append((pos, flt, forca - 2, issue))
    # vaga mais fraca do XI (se estiver 4+ pontos abaixo da média)
    slot, weakest, r = min(xi, key=lambda x: x[2])
    if r < forca - 4:
        out.append((slot, lambda p: True, r + 3, f'reforçar {slot} (titular fraco: {weakest.name})'))
    # titulares com 33+ precisam de sucessor
    for slot, p, r in xi:
        if p.age >= 33:
            out.append((slot, lambda q: q.age <= 27, r - 3, f'sucessor para {p.name} ({p.age} anos)'))
    # elenco curto
    if len(club.team.players) < MIN_SQUAD:
        out.append((slot, lambda p: True, forca - 6, 'completar elenco'))
    if club.rival:
        # rival quer ser campeão: depois de resolver o encaixe, troca o titular mais fraco por alguém claramente melhor
        up_slot, weakest, r = min(xi, key=lambda x: x[2])
        out.append((up_slot, lambda p: p.age <= 29, r + 3, f'upgrade {up_slot} (sai da titularidade: {weakest.name})'))
    return out, ev


def seller_ok(seller, p, relaxed=False):
    """O clube vendedor não pode ficar descoberto: o XI dele não pode cair mais de 1,5 ponto.
    relaxed (clube grande comprando de clube menor, pagando bem): aceita queda de até 3 pontos e 1 problema novo;
    o vendedor repõe nas rodadas seguintes."""
    team = seller.team
    if len(team.players) - 1 < MIN_SQUAD:
        return False
    before = encaixe.evaluate(team)
    rest = [q for q in team.players if q is not p]
    t2 = type(team)(team.idx, team.name, team.short, [], rest, list(getattr(team, 'formation', [])))
    after = encaixe.evaluate(t2)
    if not (after and before):
        return False
    # não vende se o XI cair demais nem se a venda criar um problema de encaixe novo
    new_issues = set(after['problemas']) - set(before['problemas'])
    willingness = seller.profile.get('propensao_venda', 0.5)
    if relaxed:
        return before['forca'] - after['forca'] <= 2.5 + willingness and len(new_issues) <= 1
    return before['forca'] - after['forca'] <= 1.2 + willingness * 0.8 and not new_issues


def gain(club, p, need_pos):
    """Quanto o índice do comprador melhora com o jogador (força + encaixe + profundidade)."""
    before = encaixe.evaluate(club.team)
    t2 = type(club.team)(club.team.idx, club.team.name, club.team.short, [], club.team.players + [p],
                         list(getattr(club.team, 'formation', [])))
    after = encaixe.evaluate(t2)
    return (after['forca'] - before['forca']) * 3 + (after['encaixe'] - before['encaixe']) * 0.4 \
        + (after['profundidade'] - before['profundidade']) * 0.1


def profile_fit(club, p, rating, price):
    """Preferência esportiva/econômica do clube; complementa, não substitui, a necessidade tática."""
    profile = club.profile
    youth = profile.get('juventude', 0.5)
    risk = profile.get('risco', 0.5)
    target_age = profile.get('idade_alvo', 29)
    age_score = max(-8.0, (target_age - p.age) * youth * 0.35)
    if profile.get('tipo') == 'elite':
        age_score += max(0.0, rating - club.tier) * 0.45
    elif profile.get('tipo') in ('formador', 'vendedor') and p.age <= 23:
        age_score += (24 - p.age) * (1.0 + youth)
    elif profile.get('tipo') == 'reconstrucao' and p.age <= 27:
        age_score += 2.5
    affordability = price / max(1.0, club.budget)
    cost_score = -affordability * (2.2 - risk)
    return age_score + cost_score


def run_window(players, teams, user_team, free_agents=(), seed_budget=1.0, seed=2033, national=frozenset(),
               buyers=None, max_total=None, protected=frozenset(), prior_buys=None, prior_sales=None,
               club_memory=None, year=2033, insatisfeitos=None, planos=None):
    """national: nomes das seleções (nunca compram nem recebem; aplicar inclui todo time a partir da ALBÂNIA);
    buyers: nomes dos clubes que podem comprar (None = todos); max_total: limite de negócios na janela;
    planos: {índice do time: plano de jogo} (encaixe_plano.planos) — o jogador que combina com o plano do comprador
      ganha até +2 na ORDEM dos candidatos (só entre os que já passaram em todas as regras; None = desligado).
    protected: (reg, pid) que não podem ser vendidos (capitão/cobradores etc.).
    insatisfeitos: {(reg, pid): {'u': 0..1, 'motivo': ...}} do vestiário dos clubes da IA (vestiario_ia):
      jogador insatisfeito fica até 25% mais barato, o clube aceita vendê-lo mais fácil, ele topa ir para um
      clube um pouco mais fraco e sobe na lista dos compradores."""
    insatisfeitos = insatisfeitos or {}
    rng = random.Random(seed)
    membership = {}
    for t in teams:
        for p in t.players:
            membership.setdefault(id(p), []).append(t.name)
    user = next((t for t in teams if t.name == user_team), None)
    user_ev = encaixe.evaluate(user) if user else None
    user_tier = user_ev['forca'] if user_ev else 99
    clubs = {}
    for t in teams:
        if (t.name == user_team or t.name in SPECIAL_TEAMS or t.name in national or len(t.players) < 11
                or is_national(t, membership)):
            continue
        ev = encaixe.evaluate(t)
        if ev:
            rival = ev['forca'] >= user_tier - RIVAL_GAP
            memory_state = club_memory if club_memory is not None else {'clubes': {}}
            profile, budget = memoria_clubes.prepare(memory_state, t, ev, year, rival, seed_budget)
            clubs[t.name] = Club(t, ev['forca'], budget=budget, rival=rival, profile=profile,
                                 buys=(prior_buys or {}).get(t.name, 0), sales=(prior_sales or {}).get(t.name, 0))
    owner = {}
    for c in clubs.values():
        for p in c.team.players:
            owner[id(p)] = c
    # trava: jogador que aparece em 2+ clubes (dado inconsistente) nunca é negociado
    in_clubs = {}
    for c in clubs.values():
        for p in c.team.players:
            in_clubs[id(p)] = in_clubs.get(id(p), 0) + 1
    protected = set(protected) | {(p.reg, p.pid) for c in clubs.values() for p in c.team.players if in_clubs[id(p)] > 1}
    pool = [p for c in clubs.values() for p in c.team.players] + list(free_agents)
    ratings = {id(p): best_rating(p) for p in pool}
    moved, moves = set(), []
    # 0) elenco inchado: vende os excedentes antes de comprar (quem está acima do limite não compra)
    moves += trim_squads(clubs, ratings, owner, moved, rng, max_total, protected, buyers)

    for rnd in range(1, ROUNDS + 1):
        order = sorted(clubs.values(), key=lambda c: (not c.rival, -c.tier))
        for club in order:
            if max_total is not None and len(moves) >= max_total:
                break
            if buyers is not None and club.team.name not in buyers:
                continue
            max_buys = RIVAL_MAX_BUYS if club.rival else MAX_BUYS
            chance = RIVAL_ACT_CHANCE if club.rival else ACT_CHANCE
            chance = min(0.98, chance * (0.82 + 0.36 * club.profile.get('risco', 0.5)))
            squad_cap = RIVAL_MAX_SQUAD if club.rival else MAX_SQUAD
            if club.buys >= max_buys or len(club.team.players) >= squad_cap or rng.random() > chance:
                continue
            needs, ev = needs_of(club)
            if not needs:
                continue
            pos, flt, min_r, why = needs[0]
            max_r = club.tier + (RIVAL_STAR_ROOM if club.rival else 5)  # só rivais podem buscar craques
            cands = []
            for p in pool:
                if id(p) in moved or owner.get(id(p)) is club or (p.reg, p.pid) in protected:
                    continue
                r = ratings[id(p)]
                if not (min_r <= r <= max_r):
                    continue
                if not (p.pos == pos or p[f'pp_{pos}'] == 2) or not flt(p):
                    continue
                # Perfis conservadores não lotam o elenco de veteranos; a elite ainda aceita solução imediata.
                if p.age > club.profile.get('idade_alvo', 29) + 3 and club.profile.get('tipo') != 'elite':
                    continue
                seller = owner.get(id(p))
                ins = insatisfeitos.get((p.reg, p.pid))
                u = ins['u'] if ins else 0.0
                # fluxo realista: não tira jogador de clube mais forte (rival pode disputar com clube do mesmo nível);
                # insatisfeito aceita descer um pouco de nível para jogar
                limit = (3.0 if club.rival else 1.5) + 2.5 * u
                if seller and (seller.tier > club.tier + limit or seller.sales >= MAX_SALES):
                    continue
                price = round(value(p, r) * (1 - 0.25 * u), 1)
                if seller and seller.tier >= club.tier - 1.5:
                    price = round(price * POACH_PREMIUM, 1)  # tirar de um concorrente custa mais
                if price > club.budget:
                    continue
                natural = 3 if p.pos == pos else 0
                # idade inteligente: trintões só compensam como solução imediata
                age_pen = max(0, p.age - 29) * (2.0 if club.rival else 1.2)
                identity = profile_fit(club, p, r, price)
                plano_b, plano_txt = encaixe_plano.fit((planos or {}).get(club.team.idx), p, pos) if planos else (0.0, '')
                cands.append((r + natural - age_pen - price * 0.03 + identity + 3 * u + plano_b, p, r, price, seller,
                              plano_b, plano_txt))
            cands.sort(key=lambda x: -x[0])
            best = None
            for _, p, r, price, seller, plano_b, plano_txt in cands[:15]:
                relaxed = club.rival and seller is not None and not seller.rival and seller.tier < club.tier - 1.5
                insat = insatisfeitos.get((p.reg, p.pid), {}).get('u', 0) >= 0.5
                if seller and not seller_ok(seller, p, relaxed or insat):
                    continue
                if relaxed:
                    price = round(price * POACH_PREMIUM, 1)  # tirar o titular de um clube menor custa caro
                g = gain(club, p, pos) + (1.0 if p.pos == pos else 0)
                decision = g + profile_fit(club, p, r, price) * 0.25 + plano_b * 0.5
                if g > MIN_GAIN and (best is None or decision > best[0]):   # o encaixe nunca substitui o ganho mínimo
                    best = (decision, p, r, price, seller, plano_txt)
            if not best:
                continue
            decision, p, r, price, seller, plano_txt = best
            if plano_txt:
                why = f'{why}; encaixa no plano ({plano_txt})'
            if seller:
                seller.team.players.remove(p)
                seller.budget += price
                seller.sales += 1
            club.team.players.append(p)
            club.budget -= price
            club.buys += 1
            owner[id(p)] = club
            moved.add(id(p))
            ins = insatisfeitos.get((p.reg, p.pid))
            if ins:
                why = f'{why}; {ins["motivo"]} (pediu para sair)'
            moves.append(Move(rnd, p.name, p.age, p.pos, p.style, round(r, 1),
                              seller.team.name if seller else 'sem clube', club.team.name, price, why,
                              p.reg, p.pid, seller.team.idx if seller else -1, club.team.idx,
                              club.profile.get('tipo', 'equilibrado')))
    left = None if max_total is None else max(0, max_total - len(moves))
    moves += place_bets(clubs, pool, ratings, owner, moved, rng, buyers, left, protected)
    return moves, clubs


GRUPO_POS = {'GK': 'GK', 'CB': 'CB', 'LB': 'LAT', 'RB': 'LAT', 'DMF': 'MEIO', 'CMF': 'MEIO', 'AMF': 'MEIO',
             'LMF': 'PONTA', 'RMF': 'PONTA', 'LWF': 'PONTA', 'RWF': 'PONTA', 'SS': 'ATA', 'CF': 'ATA'}


def trim_squads(clubs, ratings, owner, moved, rng, limit=None, protected=frozenset(), buyers=None):
    """12/10/2026: clubes acima de MAX_SQUAD vendem excedentes até SQUAD_TRIM_TO (no máximo TRIM_MAX_SALES).
    Excedente = fora do melhor XI e dos 7 primeiros reservas, maior de 21 anos, não protegido; do mais fraco para o
    mais forte. Destino: clube com vaga (abaixo de MAX_SQUAD - 1) onde ele seja útil (nota a até 2 pontos abaixo do
    nível do clube ou acima), que pague 70% do valor; prefere o clube mais carente naquele setor."""
    out = []
    limit = TRIM_MAX_TOTAL if limit is None else min(limit, TRIM_MAX_TOTAL)
    for club in sorted(clubs.values(), key=lambda c: -c.tier)[:TRIM_CLUBES]:
        if len(club.team.players) <= MAX_SQUAD:
            continue
        xi, bench = encaixe.best_xi(club.team.players, encaixe.formation_slots(club.team))
        fica = {id(p) for _, p, _ in xi} | {id(p) for p in sorted(bench, key=lambda q: -ratings.get(id(q), 0))[:7]}
        sobra = [p for p in club.team.players if id(p) not in fica and p.age > 21 and (p.reg, p.pid) not in protected
                 and id(p) not in moved and id(p) in ratings]
        sobra.sort(key=lambda p: (ratings[id(p)], -p.age))
        vendas = 0
        for p in sobra:
            if (len(club.team.players) <= SQUAD_TRIM_TO or vendas >= TRIM_MAX_SALES
                    or (limit is not None and len(out) >= limit)):
                break
            r = ratings[id(p)]
            price = round(value(p, r) * 0.7, 1)
            grupo = GRUPO_POS.get(p.pos)
            dest = [c for c in clubs.values() if c is not club and len(c.team.players) < MAX_SQUAD - 1
                    and r >= c.tier - 2 and r <= c.tier + 4 and c.budget >= price
                    and (buyers is None or c.team.name in buyers)]
            if not dest:
                continue
            carencia = lambda c: sum(GRUPO_POS.get(q.pos) == grupo for q in c.team.players)
            dest.sort(key=lambda c: (carencia(c), abs(r - c.tier), rng.random()))
            novo = dest[0]
            club.team.players.remove(p)
            club.budget += price
            club.sales += 1
            novo.team.players.append(p)
            novo.budget -= price
            novo.buys += 1
            owner[id(p)] = novo
            moved.add(id(p))
            vendas += 1
            out.append(Move(0, p.name, p.age, p.pos, p.style, round(r, 1), club.team.name, novo.team.name, price,
                            f'excedente: {club.team.name.title()} enxugou o elenco ({len(club.team.players) + 1} jogadores)',
                            p.reg, p.pid, club.team.idx, novo.team.idx, novo.profile.get('tipo', 'equilibrado')))
    return out


BET_CHANCE = 0.25     # fração de clubes que faz uma aposta na janela
BET_MAX_AGE = 21


def place_bets(clubs, pool, ratings, owner, moved, rng, buyers=None, limit=None, protected=frozenset()):
    """Apostas em promessas: no máximo 1 por clube, só quem não é titular no clube de origem."""
    import potencial
    starters = {}
    for c in clubs.values():
        xi, _ = encaixe.best_xi(c.team.players, encaixe.formation_slots(c.team))
        for _, p, _ in xi:
            starters[id(p)] = True
    bets = []
    for club in sorted(clubs.values(), key=lambda c: -c.tier):
        if limit is not None and len(bets) >= limit:
            break
        if buyers is not None and club.team.name not in buyers:
            continue
        cap = RIVAL_MAX_BUYS if club.rival else MAX_BUYS
        bet_chance = BET_CHANCE * (0.45 + club.profile.get('juventude', 0.5) * 1.35)
        if rng.random() > bet_chance or len(club.team.players) >= MAX_SQUAD or club.buys >= cap:
            continue
        xi, _ = encaixe.best_xi(club.team.players, encaixe.formation_slots(club.team))
        # posição que vai precisar de reposição: titular mais velho (29+) ou o mais fraco
        old = [(slot, p) for slot, p, r in xi if p.age >= 29]
        slot = max(old, key=lambda x: x[1].age)[0] if old else min(xi, key=lambda x: x[2])[0]
        cands = []
        for p in pool:
            if (id(p) in moved or p.age > BET_MAX_AGE or starters.get(id(p)) or owner.get(id(p)) is club
                    or (p.reg, p.pid) in protected):
                continue
            if not (p.pos == slot or p[f'pp_{slot}'] == 2):
                continue
            r = ratings[id(p)]
            proj = potencial.projection(p, r)
            if r < club.tier - 12 or proj < club.tier + 2:
                continue
            seller = owner.get(id(p))
            if seller and (seller.sales >= MAX_SALES or len(seller.team.players) - 1 < MIN_SQUAD):
                continue
            price = round(value(p, r) * (1.6 if p.origem != 'normal' else 1.2), 1)  # promessa custa um pouco mais
            if price > club.budget:
                continue
            # nível atual pesa: quem já rende é aposta mais segura
            score = proj * 0.5 + r * 0.5 - price * 0.1
            cands.append((score, p, r, proj, price, seller))
        if not cands:
            continue
        # imprevisível: sorteio ponderado entre os 6 melhores (não é sempre o "óbvio")
        cands.sort(key=lambda x: -x[0])
        top = cands[:6]
        weights = [max(0.1, c[0] - top[-1][0] + 1) for c in top]
        best = rng.choices(top, weights=weights, k=1)[0]
        _, p, r, proj, price, seller = best
        if seller:
            seller.team.players.remove(p)
            seller.budget += price
            seller.sales += 1
        club.team.players.append(p)
        club.budget -= price
        club.buys += 1
        owner[id(p)] = club
        moved.add(id(p))
        tag = {'regen': 'regen', 'gerado': 'cria da base'}.get(p.origem, 'promessa')
        bets.append(Move(5, p.name, p.age, p.pos, p.style, round(r, 1), seller.team.name if seller else 'sem clube',
                         club.team.name, price, f'aposta: {tag}, {p.age} anos, projeção ~{proj:.0f} ({slot})',
                         p.reg, p.pid, seller.team.idx if seller else -1, club.team.idx,
                         club.profile.get('tipo', 'equilibrado')))
    return bets
