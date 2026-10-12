"""Cobertura da LIGA INTEIRA pela mídia (10/10/2026).

O jornal não fala só do clube do usuário: pega as competições que o usuário disputa na temporada (a liga e a copa
continental, ex. Premier League + Champions, Brasileirão + Libertadores) e cobre todos os times delas, com as
súmulas do próprio jogo (partidas_save; o save guarda os jogos do mundo todo):
  - resultados recentes, goleadas, zebras (pela tabela), líder e lanterna, artilharia, sequências de times.
Produz FATOS para as capas/programa (midia.py, tipo 'liga') e o painel "Rodada" da Central.
"""
import collections

from proximo_jogo import nome_comp  # noqa: E402  (nomes das competições num lugar só)


def CL_nome():
    from clube import C
    return (C.get('curto') or 'CLUBE').upper()


ANUAIS = {0x1D, 0xA3, 0x1F, 0x0A}   # Brasileirão A/B, Copa do Brasil, Libertadores: temporada de janeiro a dezembro
CANON = {4: 3, 6: 5, 16: 15, 10: 9}   # fase de grupos + mata-mata = uma competição só (Champions, Europa League, AFC, Libertadores)
NAO_LIGA = set(range(100, 111)) | {56}   # amistosos/torneios de pré-temporada (103..108 vistos) e seleções   # Champions: fase de grupos = 3, mata-mata = 4 (marcador 0x40) -> uma competição só na Central


def _temporada_ini(hoje, liga):
    """Início da temporada: janeiro para as ligas de calendário anual (Brasil), julho para o resto.
    11/10/2026: antes adivinhava pelos meses dos jogos; a temporada europeia (set..mai) parecia anual e o painel
    contava a temporada a partir de 1º de janeiro (sumia a fase de grupos da Champions; artilharia da liga errada)."""
    import temporada
    if temporada.ATUAL['ini'] and temporada.ATUAL['liga'] == liga:
        return temporada.ini_de(hoje)
    if liga in ANUAIS:
        return (hoje[0], 1, 1)
    return (hoje[0] if hoje[1] >= 7 else hoje[0] - 1, 7, 1)


def liga_valida(L):
    """Painel de liga utilizável (não um amistoso gravado por engano na pré-temporada)."""
    n = (L or {}).get('competicao') or ''
    return bool(L) and n != 'Amistoso' and 'pré-temporada' not in n and not n.startswith('Competição 10')


def cobertura(r, car, hoje, snap):
    import dados
    from save_ml import SaveML  # noqa: F401  (nomes dos times vêm de r['ultimos']/tabela; aqui usamos o save)
    todas = [dict(p, comp=CANON.get(p['comp'], p['comp']), comp_orig=p['comp']) for p in r.get('todas_partidas') or []]
    ti = r['ti']
    meus = [p for p in todas if ti in (p['time1'], p['time2'])]
    if not meus:
        return None, []
    ini_ano = (hoje[0], 1, 1)
    # 11/10/2026: amistosos de pré-temporada e jogos de seleção não são a liga ("Campeão da Amistoso!")
    oficiais = [p for p in meus if p['comp'] not in NAO_LIGA]
    if not oficiais:   # pré-temporada: o jogo apaga as súmulas na virada; sem jogo oficial não há liga a cobrir
        return None, []
    import temporada   # 12/10/2026: a liga de verdade (mais times e jogos), não a copa mais jogada do clube
    liga0 = temporada.ATUAL['liga'] if temporada.ATUAL['liga'] is not None else collections.Counter(p['comp'] for p in oficiais[-60:]).most_common(1)[0][0]
    ini = _temporada_ini(hoje, liga0)
    comps = collections.Counter(p['comp'] for p in meus if tuple(p['data']) >= ini and p['comp'] not in NAO_LIGA)
    if liga0 in comps:   # a liga é a da temporada; na pré-temporada, a da temporada que acabou
        comps[liga0] += 10 ** 6
    if not comps:
        comps = collections.Counter(p['comp'] for p in meus[-10:])
    # 12/10/2026: a liga é a do clube (liga0) mesmo antes da 1ª rodada; antes, com só Supercopa e Community Shield
    # jogadas, a "liga" virava a Community Shield e herdava a tabela final da temporada passada
    liga = liga0
    outras = [c for c, n in comps.items() if c != liga]
    nomes_time = r['_nomes_time']
    try:
        P = dados.load_players(snap)
    except Exception:  # noqa: BLE001
        P = {}

    def nm_j(reg, pid):
        p = P.get((reg, pid)) if P else None
        return p.name.strip() if p else None

    def jogos_comp(c):
        return sorted((p for p in todas if p['comp'] == c and tuple(p['data']) >= ini), key=lambda p: (p['data'], p['rodada']))

    lj = jogos_comp(liga)
    # artilharia da liga
    gols = collections.Counter()
    time_de = {}
    for p in lj:
        for lado, t in (('linhas1', p['time1']), ('linhas2', p['time2'])):
            for x in p[lado]:
                if x['gols']:
                    gols[(x['reg'], x['pid'])] += x['gols']
                    time_de[(x['reg'], x['pid'])] = t
    artilheiros = []
    for k, g in gols.most_common(12):
        n = nm_j(*k)
        if n:
            artilheiros.append({'nome': n, 'time': nomes_time(time_de[k]), 'gols': g})
        if len(artilheiros) == 8:
            break
    tab = (car.get('diretoria') or {}).get('tabela') or []
    if not lj:   # a liga ainda não começou nesta temporada: a tabela que existir é a da temporada passada
        tab = []
    pos_de = {t['time']: t['pos'] for t in tab}
    ultima_data = lj[-1]['data'] if lj else None
    recentes = [p for p in lj if ultima_data and (tuple(ultima_data) >= tuple(p['data']))][-10:]
    res = [{'data': list(p['data']), 'casa': nomes_time(p['time1']), 'fora': nomes_time(p['time2']),
            'g1': p['gols1'], 'g2': p['gols2'], 'meu': ti in (p['time1'], p['time2'])} for p in recentes]
    outras_res, fatos_copas = [], []
    agenda = r.get('agenda') or []
    for c in outras:
        todos_c = jogos_comp(c)
        oj = todos_c[-6:]
        # grupo do usuário: adversários (jogados ou agendados) na FASE DE GRUPOS e os jogos entre eles
        fase = [p for p in todos_c if p.get('comp_orig', c) == c]
        rivais = {t for p in fase + [a for a in agenda if a['comp'] == c]
                  for t in (p['time1'], p['time2']) if ti in (p['time1'], p['time2'])}
        grupo = []
        if 3 <= len(rivais) <= 6:
            tg = {t: {'time': nomes_time(t), 'j': 0, 'pts': 0, 'gp': 0, 'gc': 0, 'eu': t == ti} for t in rivais}
            for p in fase:
                if p['time1'] in rivais and p['time2'] in rivais:
                    for t, gp, gc in ((p['time1'], p['gols1'], p['gols2']), (p['time2'], p['gols2'], p['gols1'])):
                        x = tg[t]
                        x['j'] += 1; x['gp'] += gp; x['gc'] += gc
                        x['pts'] += 3 if gp > gc else 1 if gp == gc else 0
            grupo = sorted(tg.values(), key=lambda x: (-x['pts'], -(x['gp'] - x['gc']), -x['gp']))
            for i, x in enumerate(grupo):
                x['pos'] = i + 1
        gols_c = collections.Counter()
        tdc = {}
        for p in todos_c:
            for lado, t in (('linhas1', p['time1']), ('linhas2', p['time2'])):
                for x in p[lado]:
                    if x['gols']:
                        gols_c[(x['reg'], x['pid'])] += x['gols']
                        tdc[(x['reg'], x['pid'])] = t
        art_c = [{'nome': nm_j(*k), 'time': nomes_time(tdc[k]), 'gols': g} for k, g in gols_c.most_common(8) if nm_j(*k)][:5]
        outras_res.append({'competicao': nome_comp(c), 'grupo': grupo, 'artilheiros': art_c, 'resultados': [
            {'data': list(p['data']), 'casa': nomes_time(p['time1']), 'fora': nomes_time(p['time2']),
             'g1': p['gols1'], 'g2': p['gols2'], 'meu': ti in (p['time1'], p['time2'])} for p in oj]})
        # fatos da copa (desde a última cobertura)
        nc = nome_comp(c)
        vistos_c = tuple((car.get('midia_liga') or {}).get(f'ate|{c}') or (0, 0, 0))
        novos_c = [p for p in todos_c if tuple(p['data']) > vistos_c and ti not in (p['time1'], p['time2'])]
        for p in novos_c:
            a, b = nomes_time(p['time1']), nomes_time(p['time2'])
            dif = p['gols1'] - p['gols2']
            if abs(dif) >= 3:
                venc, perd = (a, b) if dif > 0 else (b, a)
                placar = f'{a} {p["gols1"]} x {p["gols2"]} {b}'
                fatos_copas.append({'tipo': 'liga', 'peso': 2.0 + abs(dif) * 0.2, 'txt': {
                    'sensacionalista': (f'{nc.upper()}: {venc.upper()} ATROPELA', placar + '.'),
                    'analítico': (f'{nc}: goleada do {venc}', placar + '.'),
                    'torcedor': (f'{venc} sobra na {nc}', placar + '.')}})
        if grupo and novos_c:
            eu = next(x for x in grupo if x['eu'])
            lider = grupo[0]
            fatos_copas.append({'tipo': 'liga', 'peso': 2.4, 'txt': {
                'sensacionalista': (f'{nc.upper()}: {CL_nome()} É {eu["pos"]}º DO GRUPO' if not eu is lider else f'{nc.upper()}: {CL_nome()} LIDERA O GRUPO!',
                                    f'{eu["pts"]} pontos em {eu["j"]} jogos.'),
                'analítico': (f'{nc}: a situação no grupo', f'{lider["time"]} lidera com {lider["pts"]}; o clube tem {eu["pts"]} em {eu["j"]} jogos.'),
                'torcedor': (f'Rumo ao mata-mata da {nc}', f'{eu["pos"]}º no grupo, {eu["pts"]} pontos.')}})
        if art_c and novos_c:
            a = art_c[0]
            fatos_copas.append({'tipo': 'liga', 'peso': 1.4, 'txt': {
                'sensacionalista': (f'{a["nome"].upper()} É O ARTILHEIRO DA {nc.upper()}', f'{a["gols"]} gols pelo {a["time"]}.'),
                'analítico': (f'Artilharia da {nc}', f'{a["nome"]} ({a["time"]}) lidera com {a["gols"]} gols.'),
                'torcedor': (f'{a["nome"]} brilha na {nc}', f'{a["gols"]} gols.')}})
        if todos_c:
            car.setdefault('midia_liga', {})[f'ate|{c}'] = list(todos_c[-1]['data'])
    painel = {'competicao': nome_comp(liga), 'pre_temporada': not lj, 'resultados': res, 'artilheiros': artilheiros,
              'classificacao': tab, 'outras': outras_res}

    # ---------------- fatos novos (desde a última cobertura) para as capas
    visto = tuple((car.get('midia_liga') or {}).get('ate') or (0, 0, 0))
    novos = [p for p in lj if tuple(p['data']) > visto and ti not in (p['time1'], p['time2'])]
    fatos = []
    for p in novos:
        a, b = nomes_time(p['time1']), nomes_time(p['time2'])
        dif = p['gols1'] - p['gols2']
        venc, perd = (a, b) if dif > 0 else (b, a)
        if abs(dif) >= 3:
            placar = f'{a} {p["gols1"]} x {p["gols2"]} {b}'
            fatos.append({'tipo': 'liga', 'peso': 1.6 + abs(dif) * 0.2, 'txt': {
                'sensacionalista': (f'MASSACRE! {venc.upper()} ATROPELA O {perd.upper()}', placar + '.'),
                'analítico': (f'Goleada do {venc}', f'{placar} pela {nome_comp(liga)}.'),
                'torcedor': (f'{venc} passa por cima do {perd}', placar + '.')}})
        if dif and pos_de.get(venc) and pos_de.get(perd) and pos_de[venc] - pos_de[perd] >= 8:
            placar = f'{a} {p["gols1"]} x {p["gols2"]} {b}'
            fatos.append({'tipo': 'liga', 'peso': 2.2, 'txt': {
                'sensacionalista': (f'ZEBRA! {venc.upper()} DERRUBA O {perd.upper()}', f'{placar}. Ninguém esperava.'),
                'analítico': (f'Surpresa na rodada: {venc} vence o {perd}', f'{placar}; {pos_de[venc]}º bateu o {pos_de[perd]}º.'),
                'torcedor': (f'Zebra: {venc} surpreende o {perd}', placar + '.')}})
    if tab and novos:
        lider = tab[0]
        if not lider.get('eu'):
            fatos.append({'tipo': 'liga', 'peso': 1.4, 'txt': {
                'sensacionalista': (f'{lider["time"].upper()} SEGUE NO TOPO', f'{lider["pts"]} pontos em {lider["j"]} jogos.'),
                'analítico': (f'{lider["time"]} lidera a {nome_comp(liga)}', f'{lider["pts"]} pontos, saldo {lider["gp"] - lider["gc"]:+d}.'),
                'torcedor': (f'{lider["time"]} lidera', f'{lider["pts"]} pontos.')}})
        lant = tab[-1]
        if not lant.get('eu') and lant.get('j', 0) >= 5:
            fatos.append({'tipo': 'liga', 'peso': 1.0, 'txt': {
                'sensacionalista': (f'{lant["time"].upper()} AFUNDA NA LANTERNA', f'Só {lant["pts"]} pontos.'),
                'analítico': (f'{lant["time"]} na lanterna', f'{lant["pts"]} pontos em {lant["j"]} jogos.'),
                'torcedor': (f'Crise no {lant["time"]}', 'Lanterna da competição.')}})
    if artilheiros and novos:
        a = artilheiros[0]
        fatos.append({'tipo': 'liga', 'peso': 1.2, 'txt': {
            'sensacionalista': (f'{a["nome"].upper()} NÃO PARA!', f'{a["gols"]} gols e a artilharia da {nome_comp(liga)}.'),
            'analítico': (f'Artilharia: {a["nome"]} ({a["time"]})', f'{a["gols"]} gols na competição.'),
            'torcedor': (f'{a["nome"]} lidera a artilharia', f'{a["gols"]} gols pelo {a["time"]}.')}})
    # sequências de times (sem o usuário): 5+ vitórias ou 5+ sem vencer
    seq = collections.defaultdict(list)
    for p in lj:
        for t, gp, gc in ((p['time1'], p['gols1'], p['gols2']), (p['time2'], p['gols2'], p['gols1'])):
            seq[t].append('V' if gp > gc else 'E' if gp == gc else 'D')
    for t, rs in seq.items():
        if t == ti or len(rs) < 5:
            continue
        nome = nomes_time(t)
        if rs[-5:] == ['V'] * 5 and (car.get('midia_liga') or {}).get(f'seqV|{t}') != len(rs):
            fatos.append({'tipo': 'liga', 'peso': 1.3, 'txt': {
                'sensacionalista': (f'{nome.upper()} EMBALADO', '5 vitórias seguidas.'),
                'analítico': (f'{nome}: 5 vitórias seguidas', 'Melhor momento na competição.'),
                'torcedor': (f'{nome} não para de vencer', '5 seguidas.')}})
            car.setdefault('midia_liga', {})[f'seqV|{t}'] = len(rs)
        if 'V' not in rs[-6:] and (car.get('midia_liga') or {}).get(f'seqD|{t}') != len(rs):
            fatos.append({'tipo': 'liga', 'peso': 1.1, 'txt': {
                'sensacionalista': (f'CRISE NO {nome.upper()}', '6 jogos sem vencer.'),
                'analítico': (f'{nome} sem vencer há 6 jogos', 'O técnico balança.'),
                'torcedor': (f'{nome} em queda livre', '6 jogos sem vitória.')}})
            car.setdefault('midia_liga', {})[f'seqD|{t}'] = len(rs)
    car.setdefault('midia_liga', {})['ate'] = list(lj[-1]['data']) if lj else list(hoje)
    fatos += fatos_copas
    fatos.sort(key=lambda f: -f['peso'])
    return painel, fatos[:6]
