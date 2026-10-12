"""Vestiário dos clubes da IA (para o Mercado IA): quem está insatisfeito por falta de minutos em outro clube.

Fonte: súmulas da temporada (partidas_save) — minutos de cada jogador nos últimos jogos do PRÓPRIO clube —
comparadas com o papel que a qualidade dele "merece" no elenco (11 ideal por posição do próprio clube).
  - estrela do clube (3 melhores do 11 ideal) com menos de 50% dos minutos  -> insatisfeito
  - titular esperado (no 11 ideal) com menos de 40% dos minutos       -> insatisfeito
  (calibrado em 09/10/2026: com 65%/50% e 4 jogos davam 1341 insatisfeitos — rodízio normal virava crise)
  - jovem (<= 21) acima da média do elenco quase sem jogar (< 15%)    -> quer rodar
Precisa de pelo menos 6 jogos do clube na temporada (no começo da temporada não há dados: ninguém reclama).
Resultado: {(reg, id): {'u': 0..1, 'motivo': texto, 'time': idx}} — só u >= 0.3.
Uso no mercado: jogador insatisfeito fica mais barato, o clube aceita vendê-lo mais fácil e ele topa até ir
para um clube um pouco mais fraco.
"""
import collections
import statistics as st

import encaixe
import partidas_save as ps

JANELA = 8
MIN_JOGOS = 6
ESTRELA_MIN = 0.50   # estrela (3 melhores) insatisfeita abaixo disso
TITULAR_MIN = 0.40   # titular esperado (11 melhores) insatisfeito abaixo disso


def _inicio_temporada(data):
    y, m = data[0], data[1]
    return (y if m >= 7 else y - 1, 7, 1)


def insatisfeitos(d, teams, rating, user_idx=None, todas=None, excluir=frozenset()):
    """teams: objetos com .idx/.name e .players (fichas com .reg/.pid/.age/.name); rating(p) -> nota.
    excluir: nomes de times a ignorar (seleções: os minutos que importam são os do clube)."""
    todas = todas if todas is not None else ps.todas(d, *ps.FAIXA)
    if not todas:
        return {}
    hoje = max(p['data'] for p in todas)
    ini = _inicio_temporada(hoje)
    jogos_time = collections.defaultdict(list)
    for p in todas:
        if p['data'] < ini:
            continue
        for lado, t in (('linhas1', p['time1']), ('linhas2', p['time2'])):
            jogos_time[t].append((p['data'], p[lado]))
    out = {}
    for team in teams:
        if team.idx == user_idx or len(team.players) < 11 or team.name in excluir:
            continue
        jt = sorted(jogos_time.get(team.idx, []), key=lambda x: x[0])[-JANELA:]
        if len(jt) < MIN_JOGOS:
            continue
        minutos = collections.Counter()
        for _, linhas in jt:
            for x in linhas:
                minutos[(x['reg'], x['pid'])] += x['minutos']
        notas = {id(p): rating(p) for p in team.players}
        media = st.mean(notas.values())
        # titulares esperados = 11 ideal POR POSIÇÃO (encaixe.best_xi, o mesmo do mercado); estrelas = 3 melhores dele
        try:
            xi = [p for _, p, _ in encaixe.best_xi(team.players, encaixe.formation_slots(team))[0]]
        except Exception:  # noqa: BLE001
            xi = sorted(team.players, key=lambda p: -notas[id(p)])[:11]
        no_xi = {id(p) for p in xi}
        estrelas = {id(p) for p in sorted(xi, key=lambda p: -notas[id(p)])[:3]}
        total = 90 * len(jt)
        for p in team.players:
            nota = notas[id(p)]
            s = minutos[(p.reg, p.pid)] / total
            u, motivo = 0.0, ''
            if id(p) in estrelas and s < ESTRELA_MIN:
                u = min(1.0, 0.45 + (ESTRELA_MIN - s))
                motivo = f'estrela do clube jogando só {s:.0%} dos minutos'
            elif id(p) in no_xi and s < TITULAR_MIN:
                u = min(1.0, (TITULAR_MIN - s) / TITULAR_MIN * 0.9)
                motivo = f'deveria ser titular, joga só {s:.0%} dos minutos'
            elif p.age <= 21 and nota >= media and s < 0.15:
                u = 0.4
                motivo = f'jovem promissor quase sem jogar ({s:.0%})'
            if u >= 0.3:
                out[(p.reg, p.pid)] = {'u': round(u, 2), 'motivo': motivo, 'time': team.idx, 'nome': p.name,
                                       'nota': round(nota), 'idade': p.age, 'pos': p.pos}
    return out
