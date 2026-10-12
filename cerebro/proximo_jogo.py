"""Próximo jogo + ENQUETE DA RODADA (10/10/2026), com números do próprio jogo.

Fontes: calendário (partidas_save.agenda: jogos agendados de todas as competições), súmulas (forma, gols, confronto
direto), tabela da liga, força dos elencos (média das 14 melhores notas pela foto da memória).
Calcula probabilidades simples (força + mando + forma), palpite de placar, enquete da torcida e o palpite de cada
comentarista do "Bola na Mesa".
"""
import math
import random

# copas nacionais identificadas pelos finalistas de 2034/35 (11/10/2026): Pisa x Cagliari, Barcelona x Granada, Dortmund x
# Frankfurt, PSV x Twente, Tondela x Moreirense, Lille x Lorient, Krasnodar x Zenit, St. Gallen x Basel, Beşiktaş x Kasımpaşa
NOMES_COMP = {3: 'UEFA Champions League', 4: 'UEFA Champions League', 23: 'FA Cup', 24: 'Coppa Italia', 25: 'Copa del Rey',
              26: 'DFB-Pokal', 27: 'Copa da Holanda', 28: 'Taça de Portugal', 53: 'Coupe de France', 123: 'Copa da Rússia',
              124: 'Copa da Suíça', 125: 'Copa da Turquia', 142: 'Copa da Dinamarca', 108: 'Amistoso', 107: 'Torneio de pré-temporada', 0x11: 'Premier League', 0x1D: 'Brasileirão Série A', 0xA3: 'Brasileirão Série B', 0x1F: 'Copa do Brasil',
              0x0A: 'Libertadores', 0x67: 'Amistoso', 86: 'FA Community Shield', 7: 'Supercopa da UEFA', 1: 'Mundial de Clubes',
              105: 'Torneio de pré-temporada',
              # 12/10/2026 (simulação em 5 carreiras): conferidos pelos clubes que disputam cada competição
              2: 'Eliminatórias europeias', 5: 'UEFA Europa League', 6: 'UEFA Europa League', 8: 'Copa Libertadores', 9: 'Copa Libertadores',
              15: 'AFC Champions League', 16: 'AFC Champions League', 18: 'Serie A', 19: 'LaLiga', 20: 'Ligue 1', 21: 'Eredivisie',
              22: 'Liga Portugal', 30: 'Liga Profesional Argentina', 50: 'Bundesliga', 52: 'J1 League', 54: 'Copa do Uruguai',
              55: 'Copa do Imperador', 59: 'Copa Argentina', 67: 'Campeonato Chileno', 68: 'Copa Chile', 79: 'EFL Championship',
              80: 'LaLiga 2', 81: 'Ligue 2', 82: 'Serie B italiana', 87: 'Supercopa da Espanha', 88: 'Trophée des Champions',
              89: 'Supercoppa Italiana', 90: 'Supercopa da Holanda', 92: 'Supercopa Argentina', 97: 'Supercopa do Japão',
              34: 'Copa do Mundo', 35: 'Copa do Mundo', 36: 'Eliminatórias da Eurocopa', 38: 'Eliminatórias sul-americanas',
              41: 'Eurocopa', 42: 'Eurocopa', 43: 'Copa América', 44: 'Copa da Ásia', 46: 'Copa Africana de Nações'}   # 86 = Community Shield (confirmado pelo usuário em 11/10/2026: 16/08, campeão da liga x da FA Cup)


def nome_comp(c):
    return NOMES_COMP.get(c, f'Competição {c}')


_FORCA = {}


def _forca(s, idx, P):
    # 12/10/2026: a força dos elencos era recalculada para os 625 clubes várias vezes por reunião
    chave = (id(s), id(P), idx)
    if chave in _FORCA:
        return _FORCA[chave]
    if len(_FORCA) > 5000:
        _FORCA.clear()
    _FORCA[chave] = v = _forca_calc(s, idx, P)
    return v


def _forca_calc(s, idx, P):
    import encaixe
    notas = []
    for k in s.squad(idx):
        f = P.get(k) if P else None
        if f:
            try:
                notas.append(encaixe.rating(f, f.pos))
            except Exception:  # noqa: BLE001
                pass
    notas.sort(reverse=True)
    return sum(notas[:14]) / len(notas[:14]) if notas else None


def _forma(todas, t, ate):
    rs = []
    for p in sorted((p for p in todas if t in (p['time1'], p['time2']) and tuple(p['data']) <= tuple(ate)),
                    key=lambda p: p['data'])[-5:]:
        gp, gc = (p['gols1'], p['gols2']) if p['time1'] == t else (p['gols2'], p['gols1'])
        rs.append({'r': 'V' if gp > gc else 'E' if gp == gc else 'D', 'gp': gp, 'gc': gc})
    return rs


def proximos(d, r, car, hoje, snap, n=3):
    """Prévias dos próximos `n` jogos do calendário (11/10/2026): quem simula rápido já encontra a prévia do jogo
    seguinte pronta na Central (o pulso diz qual é o próximo; a reunião só chega depois do save)."""
    import dados
    import partidas_save as ps
    ti = r['ti']
    jogos = [p for p in ps.agenda(d) if ti in (p['time1'], p['time2']) and tuple(p['data']) >= tuple(hoje)][:n]
    try:
        P = dados.load_players(snap)
    except Exception:  # noqa: BLE001
        P = {}
    out = []
    for p in jogos:
        try:
            g = gerar(d, r, car, hoje, snap, prox=p, P=P)
        except Exception as e:  # noqa: BLE001
            print('aviso: prévia não gerada:', e)
            g = None
        if g:
            out.append(g)
    return out


def gerar(d, r, car, hoje, snap, prox=None, P=None):
    import dados
    import partidas_save as ps
    from save_ml import SaveML
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    ti = r['ti']
    prox = prox or next((p for p in ps.agenda(d) if ti in (p['time1'], p['time2']) and tuple(p['data']) >= tuple(hoje)), None)
    if not prox:
        return None
    if P is None:
        try:
            P = dados.load_players(snap)
        except Exception:  # noqa: BLE001
            P = {}
    casa, fora = prox['time1'], prox['time2']
    todas = r.get('todas_partidas') or []
    fa, fb = _forca(s, casa, P), _forca(s, fora, P)
    forma_a, forma_b = _forma(todas, casa, hoje), _forma(todas, fora, hoje)
    pts = lambda f: sum(3 if x['r'] == 'V' else 1 if x['r'] == 'E' else 0 for x in f) / max(1, len(f))
    tab = (car.get('diretoria') or {}).get('tabela') or []
    pos = {t['time']: t for t in tab}
    na, nb = s.name(casa).strip(), s.name(fora).strip()
    # índice: força (1 ponto de nota ~ 0,25), mando (+0,35), forma (pontos por jogo nos últimos 5)
    x = ((fa or 75) - (fb or 75)) * 0.25 + 0.35 + (pts(forma_a) - pts(forma_b)) * 0.35
    p_casa = 1 / (1 + math.exp(-x))
    p_emp = 0.28 * math.exp(-abs(x) / 2.2)
    p_casa, p_fora = p_casa * (1 - p_emp), (1 - p_casa) * (1 - p_emp)
    gm = lambda f: sum(y['gp'] for y in f) / max(1, len(f)) if f else 1.3
    gs = lambda f: sum(y['gc'] for y in f) / max(1, len(f)) if f else 1.3
    xg_a = max(0.2, (gm(forma_a) + gs(forma_b)) / 2 + x * 0.25)
    xg_b = max(0.2, (gm(forma_b) + gs(forma_a)) / 2 - x * 0.25)
    placar = (round(xg_a), round(xg_b))
    h2h = [p for p in todas if {p['time1'], p['time2']} == {casa, fora}][-3:]
    eu_casa = casa == ti
    p_vit = p_casa if eu_casa else p_fora
    rnd = random.Random(f'enquete|{prox["data"]}|{casa}|{fora}')
    moral = sum(j['moral'] for j in r['J']) / max(1, len(r['J']))
    torcida_sim = round(max(5, min(95, p_vit * 100 + (moral - 60) * 0.4 + 12 + rnd.uniform(-5, 5))))
    adv = nb if eu_casa else na

    def palpite(vies):
        g_a, g_b = placar
        if vies > 0:
            g_a, g_b = (g_a + 1, g_b) if eu_casa else (g_a, g_b + 1)
        elif vies < 0:
            g_a, g_b = (g_a, g_b + 1) if eu_casa else (g_a + 1, g_b)
        return f'{na} {g_a} x {g_b} {nb}'
    favorito = na if p_casa > p_fora + 0.08 else nb if p_fora > p_casa + 0.08 else None
    try:   # jogo da rodada: 4 x 4 com atributos e números da temporada
        import confronto
        duelo = confronto.gerar(s, casa, fora, P, todas, hoje)
    except Exception as e:  # noqa: BLE001
        print('aviso: 4 x 4 não gerado:', e)
        duelo = None
    try:   # relatório tático da comissão técnica
        import analise_tatica
        tatica = analise_tatica.gerar(s, d, ti, fora if casa == ti else casa, P, r['J'])
    except Exception as e:  # noqa: BLE001
        print('aviso: análise tática não gerada:', e)
        tatica = None
    import classicos
    try:   # é FINAL? (último jogo da copa, jogo único — marcos.py)
        import marcos
        liga = (car.get('liga') or {}).get('competicao')
        liga_c = next((c for c, n in NOMES_COMP.items() if n == liga), None)
        final = marcos.eh_final(dict(prox, flag=prox.get('flag')), todas + ps.agenda(d), liga=liga_c)
    except Exception:  # noqa: BLE001
        final = False
    return {
        'duelo': duelo, 'tatica': tatica, 'classico': classicos.nome(na, nb), 'final': bool(final),
        'data': list(prox['data']), 'competicao': nome_comp(prox['comp']), 'rodada': prox['rodada'],
        'casa': na, 'fora': nb, 'eu_casa': eu_casa, 'adversario': adv,
        'forca': {'casa': round(fa, 1) if fa else None, 'fora': round(fb, 1) if fb else None},
        'forma': {'casa': ''.join(y['r'] for y in forma_a), 'fora': ''.join(y['r'] for y in forma_b)},
        'tabela': {'casa': pos.get(na), 'fora': pos.get(nb)},
        'prob': {'casa': round(p_casa * 100), 'empate': round(p_emp * 100), 'fora': round(p_fora * 100)},
        'placar_provavel': f'{na} {placar[0]} x {placar[1]} {nb}',
        'confrontos': [f'{s.name(p["time1"]).strip()} {p["gols1"]} x {p["gols2"]} {s.name(p["time2"]).strip()}' for p in h2h],
        'enquete': {'pergunta': f'Seu time vence o {adv}?', 'sim': torcida_sim},
        'palpites': [
            {'quem': 'Carlão Pereira', 'texto': palpite(+1), 'fala': 'Time grande joga para ganhar. Vai dar a gente!' if p_vit > 0.4 else 'Vai ser pedreira, mas no peito e na raça dá.'},
            {'quem': 'Helena Saraiva', 'texto': f'{na} {placar[0]} x {placar[1]} {nb}',
             'fala': f'Pelos números: {round(p_casa * 100)}% / {round(p_emp * 100)}% / {round(p_fora * 100)}%. '
                     + (f'O {favorito} chega como favorito.' if favorito else 'Jogo muito equilibrado.')},
            {'quem': 'Beto Rocha', 'texto': palpite(0 if moral >= 60 else -1),
             'fala': 'O clima no CT está bom, o grupo está fechado.' if moral >= 60 else 'O vestiário anda pesado. Isso pesa em campo.'},
        ],
    }
