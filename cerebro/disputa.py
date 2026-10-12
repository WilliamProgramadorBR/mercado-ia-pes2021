"""DIRETOR DE CAMPEONATO (12/10/2026): quem está "dando a vida" em cada liga.

Pedido do usuário: rivais em disputa (título, vagas, rebaixamento) devem jogar como quem decide cada ponto — sem
entregar resultado. Medição de 12/10/2026 no simulador: a forma (seta) quase não muda o placar (+0,08 gol por +1 na
média do XI, sem sinal confiável), mas a FORÇA de quem entra em campo muda muito (+0,13 gol por ponto de nota; poupar
3 titulares custa ~meio gol). Então a alavanca é a escalação (escalacao_ia.py):
  - pressão alta  -> força máxima toda rodada (nada de poupar), inclusive o goleiro titular;
  - sem objetivo  -> no fim da temporada roda o elenco (como na vida real), o que favorece quem disputa algo contra ele.

Pressão de um time numa disputa (0..1), sem regra fixa por liga:
  momento  = sobe de 0 (35% do campeonato) a 1 (75%); na rodada 2 é zero;
  distância = pontos até a linha da zona (alcançar ou não ser alcançado) comparados com os pontos ainda em jogo:
              perto da linha = pressão alta; impossível de alcançar ou já garantido = zero;
  liga concentrada: se o líder e o 2º (ou 3º) estão descolados do resto (8+ pontos), o duelo pelo título liga mais
              cedo (a partir de 20% do campeonato) — a LaLiga de Real x Barça; ligas emboladas como a Premier ganham
              pressão em várias zonas ao mesmo tempo.
Zonas por liga (código da competição): título, vagas continentais e rebaixamento.
"""
import collections

# (vagas da 1ª zona continental, até onde vai a 2ª zona, nº de rebaixados)
ZONAS = {17: (4, 6, 3), 19: (4, 6, 3), 18: (4, 6, 3), 20: (4, 6, 2), 50: (3, 5, 2), 21: (2, 4, 2), 22: (2, 4, 2),
         29: (6, 12, 4), 0xA3: (4, 4, 4), 30: (6, 12, 2), 52: (3, 3, 3), 79: (2, 6, 3), 80: (2, 6, 4), 81: (2, 3, 2),
         82: (2, 8, 3), 67: (4, 8, 2)}
NOMES_ZONA = {'titulo': 'título', 'vaga1': 'vaga principal (Champions/Libertadores/acesso)',
              'vaga2': 'vaga continental', 'rebaixamento': 'fuga do rebaixamento'}


def tabelas(jogos, hoje):
    """{comp: {'tabela': [(time, pts, j)], 'rodadas_total': n, 'rodadas_feitas': k}} das ligas com zonas conhecidas,
    calculadas pelos jogos da temporada de CADA liga (registros do pulso; início pela rodada 1 mais recente)."""
    import temporada
    out = {}
    por_comp = collections.defaultdict(list)
    inicio = {c: temporada.inicio(jogos, c, tuple(hoje)) for c in {j['comp'] for j in jogos if j['comp'] in ZONAS}}
    for j in jogos:
        if j['comp'] in ZONAS and tuple(j['data']) >= tuple(inicio[j['comp']]):
            por_comp[j['comp']].append(j)
    for comp, js in por_comp.items():
        pts, jog = collections.Counter(), collections.Counter()
        times = set()
        for j in js:
            times.update((j['time1'], j['time2']))
            if not j['jogado']:
                continue
            g1, g2 = j['gols1'], j['gols2']
            pts[j['time1']] += 3 if g1 > g2 else 1 if g1 == g2 else 0
            pts[j['time2']] += 3 if g2 > g1 else 1 if g1 == g2 else 0
            jog[j['time1']] += 1
            jog[j['time2']] += 1
        if len(times) < 10:
            continue
        total = 2 * (len(times) - 1)
        tab = sorted(((t, pts[t], jog[t]) for t in times), key=lambda x: (-x[1], x[2]))
        out[comp] = {'tabela': tab, 'rodadas_total': total, 'rodadas_feitas': max(jog.values(), default=0)}
    return out


def _momento(feitas, total, inicio=0.35):
    x = feitas / max(1, total)
    return max(0.0, min(1.0, (x - inicio) / (0.75 - inicio)))


def pressoes(info):
    """{time: (pressão 0..1, zona, texto)} para os times de uma liga (a disputa mais forte de cada um)."""
    tab, total, feitas = info['tabela'], info['rodadas_total'], info['rodadas_feitas']
    n = len(tab)
    z1, z2, reb = ZONAS.get(info.get('comp'), (4, 6, 3))
    pts = [p for _, p, _ in tab]
    restantes = {t: total - j for t, _, j in tab}
    # liga concentrada: os 2 (ou 3) primeiros descolados do resto liga o duelo pelo título mais cedo
    concentrada = n >= 4 and (pts[1] - pts[2] >= 8 or (n >= 5 and pts[2] - pts[3] >= 8))
    out = {}
    for pos, (t, p, j) in enumerate(tab, start=1):
        em_jogo = 3 * restantes[t]
        if em_jogo <= 0:
            out[t] = (0.0, None, 'temporada encerrada')
            continue
        disputas = []
        # (zona, linha: pontos de quem está na última vaga da zona / primeiro de fora)
        linhas = [('titulo', 1), ('vaga1', z1), ('vaga2', z2), ('rebaixamento', n - reb)]
        for zona, corte in linhas:
            if corte < 1 or corte >= n:
                continue
            dentro = pos <= corte
            # ameaça: quem está fora alcança? / alvo: quem está dentro escapa?
            ref = pts[corte] if dentro else pts[corte - 1]        # 1º de fora (se dentro) / último de dentro (se fora)
            dist = abs(p - ref)
            if dist > em_jogo:
                continue                                          # matematicamente decidido para esse time
            perto = max(0.0, 1 - dist / (min(12, em_jogo) + 1))
            inicio = 0.2 if (zona == 'titulo' and concentrada and pos <= 3) else 0.35
            pr = perto * _momento(feitas, total, inicio)
            if zona == 'rebaixamento':
                pr *= 1.0 if not dentro or pos > n - reb - 3 else 0.0  # só quem está no fundo da tabela
            disputas.append((round(pr, 2), zona, dist, dentro))
        if not disputas:
            out[t] = (0.0, None, 'sem objetivo')
            continue
        pr, zona, dist, dentro = max(disputas)
        texto = (f'{NOMES_ZONA[zona]}: ' + ('defende a posição' if dentro else 'persegue') + f' ({dist} pts)')
        out[t] = (pr, zona if pr > 0 else None, texto if pr > 0 else 'sem pressão ainda')
    return out


def do_save(todas, agenda, hoje):
    """mapa() a partir das súmulas e do calendário do save (reunião), em vez da memória."""
    jogos = [dict(p, jogado=True) for p in todas or []] + [dict(p, jogado=False, gols1=0, gols2=0) for p in agenda or []]
    return mapa(jogos, hoje)


def corrida(info_mapa, ti, nomes, jogos, hoje):
    """A disputa do time `ti` com os concorrentes da mesma zona (para a imprensa): None se não há pressão."""
    m = info_mapa.get(ti)
    if not m or not m['zona'] or m['pressao'] < 0.45:
        return None
    tab = tabelas(jogos, hoje).get(m['comp'])
    if not tab:
        return None
    pos = {t: i + 1 for i, (t, _, _) in enumerate(tab['tabela'])}
    pts = {t: p for t, p, _ in tab['tabela']}
    rivais = [t for t in pos if t != ti and info_mapa.get(t, {}).get('zona') == m['zona']
              and abs(pts[t] - pts[ti]) <= 9]
    rivais.sort(key=lambda t: abs(pts[t] - pts[ti]))
    return {'zona': m['zona'], 'nome_zona': NOMES_ZONA[m['zona']], 'pressao': m['pressao'], 'pos': pos[ti], 'pts': pts[ti],
            'restantes': tab['rodadas_total'] - tab['rodadas_feitas'],
            'rivais': [{'nome': nomes(t), 'pos': pos[t], 'pts': pts[t], 'dif': pts[t] - pts[ti]} for t in rivais[:3]]}


def mapa(jogos, hoje):
    """{time: {'pressao', 'zona', 'texto', 'comp', 'progresso', 'sem_objetivo'}} para todos os times de ligas."""
    out = {}
    for comp, info in tabelas(jogos, hoje).items():
        info['comp'] = comp
        prog = info['rodadas_feitas'] / max(1, info['rodadas_total'])
        for t, (pr, zona, texto) in pressoes(info).items():
            out[t] = {'pressao': pr, 'zona': zona, 'texto': texto, 'comp': comp, 'progresso': round(prog, 2),
                      'sem_objetivo': zona is None and prog >= 0.75}
    return out
