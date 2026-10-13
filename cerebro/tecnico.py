# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Técnico IA: monta a escalação preferida dos times da IA dentro da formação que o time já usa.

- titulares: melhor jogador para cada vaga da formação (nota estimada na posição da vaga);
- banco: goleiro reserva primeiro, depois o melhor de cada setor (defesa, meio, ataque), depois o resto;
- só troca a escalação se o ganho for relevante (evita mexer por migalha).
Limite conhecido: não enxerga cansaço nem lesão (o jogo pode substituir na hora da partida).
"""
import encaixe
from dados import POS

DEF = {'CB', 'LB', 'RB'}
MID = {'DMF', 'CMF', 'LMF', 'RMF', 'AMF'}
ATT = {'LWF', 'RWF', 'SS', 'CF'}
MIN_GAIN = 4.0   # soma das notas do XI precisa melhorar pelo menos isso


def slot_rating(p, pos):
    return encaixe.rating(p, pos) if p else 0.0


def best_assignment(slots, cands):
    """Atribuição gulosa global + trocas 2 a 2 para melhorar a soma."""
    pairs = sorted(((slot_rating(p, pos), s, i) for s, pos in enumerate(slots) for i, p in enumerate(cands)),
                   reverse=True)
    chosen, used_s, used_p = {}, set(), set()
    for r, s, i in pairs:
        if s not in used_s and i not in used_p:
            chosen[s] = i
            used_s.add(s)
            used_p.add(i)
        if len(chosen) == len(slots):
            break
    improved = True
    while improved:
        improved = False
        for a in range(len(slots)):
            for b in range(a + 1, len(slots)):
                ia, ib = chosen[a], chosen[b]
                cur = slot_rating(cands[ia], slots[a]) + slot_rating(cands[ib], slots[b])
                alt = slot_rating(cands[ib], slots[a]) + slot_rating(cands[ia], slots[b])
                if alt > cur + 0.01:
                    chosen[a], chosen[b] = ib, ia
                    improved = True
            # troca titular por reserva
            for i in range(len(cands)):
                if i in chosen.values():
                    continue
                if slot_rating(cands[i], slots[a]) > slot_rating(cands[chosen[a]], slots[a]) + 0.01:
                    chosen[a] = i
                    improved = True
    return [chosen[s] for s in range(len(slots))]


def propose(save, players, idx):
    """Retorna (nova_ordem, ganho, trocas) para o time idx, ou None se não houver dados suficientes."""
    squad = save.squad(idx)
    cur = save.lineup(idx)
    if len(squad) < 11 or sorted(cur) != list(range(len(squad))):
        return None
    codes = save.formation(idx)
    if len(codes) != 11 or any(c >= len(POS) for c in codes):
        return None
    slots = [POS[c] for c in codes]
    cands = [players.get(k) for k in squad]
    if sum(1 for p in cands if p) < 14:
        return None
    xi = best_assignment(slots, cands)
    cur_xi = cur[:11]
    cur_sum = sum(slot_rating(cands[i], slots[s]) for s, i in enumerate(cur_xi))
    new_sum = sum(slot_rating(cands[i], slots[s]) for s, i in enumerate(xi))
    # banco: goleiro reserva, melhor de cada setor, depois por nota
    rest = [i for i in range(len(squad)) if i not in xi]
    best = lambda i: max((slot_rating(cands[i], pos) for pos in encaixe.KEYS
                          if cands[i] and (cands[i].pos == pos or cands[i][f'pp_{pos}'] == 2)), default=0)
    rest.sort(key=lambda i: -best(i))
    bench = []
    for group in ({'GK'}, DEF, MID, ATT):
        pick = next((i for i in rest if cands[i] and cands[i].pos in group), None)
        if pick is not None:
            bench.append(pick)
            rest.remove(pick)
    order = xi + bench + rest
    changes = []
    for s, (old_i, new_i) in enumerate(zip(cur_xi, xi)):
        if old_i != new_i:
            o, n = cands[old_i], cands[new_i]
            changes.append((slots[s], n.name if n else '?', round(slot_rating(n, slots[s])),
                            o.name if o else '?', round(slot_rating(o, slots[s]))))
    return order, round(new_sum - cur_sum, 1), changes


def apply_all(save, players, team_names, min_gain=MIN_GAIN):
    """Aplica o técnico IA nos times indicados. Retorna lista de (time, ganho, trocas)."""
    done = []
    for name in team_names:
        idx = save.find_team(name)
        if idx is None:
            continue
        res = propose(save, players, idx)
        if not res:
            continue
        order, gain, changes = res
        if gain >= min_gain and changes:
            save.set_lineup(idx, order)
            done.append((name, gain, changes))
    return done
