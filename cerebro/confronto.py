# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""JOGO DA RODADA: 4 x 4 (11/10/2026). Os 4 destaques de cada time frente a frente, como no pré-jogo da TV.

Dados do próprio jogo: atributos da foto da memória (dados.load_players), elencos do save, números da temporada nas
súmulas (gols, assistências, nota média, jogos), média de gols feitos/sofridos por time.
Gera: 4 jogadores por lado (sempre com pelo menos 1 atacante e 1 defensor), o duelo-chave (melhor atacante de um x
melhor defensor do outro) e uma análise curta ("quem ataca mais", "como lidar"). O redator com IA pode reescrever a
análise (redator.py, campo 'analise').
"""
ATA = ('CF', 'SS', 'LWF', 'RWF')
MEI = ('AMF', 'CMF', 'LMF', 'RMF', 'DMF')
DEF = ('CB', 'LB', 'RB', 'DMF')


def _numeros(todas, k, ini, time=None):
    """Números da temporada pelo CLUBE `time` (11/10/2026: sem o filtro, jogos da seleção entravam na conta)."""
    jogos = gols = assist = 0
    notas = []
    for p in sorted(todas, key=lambda p: p['data']):
        if tuple(p['data']) < ini or (time is not None and time not in (p['time1'], p['time2'])):
            continue
        for x in p['linhas1'] + p['linhas2']:
            if (x['reg'], x['pid']) == k and x['minutos'] > 0:
                jogos += 1
                gols += x['gols']
                assist += x['assist']
                if x['nota']:
                    notas.append(x['nota'])
    media = round(sum(notas) / len(notas), 1) if notas else None
    rec = round(sum(notas[-4:]) / len(notas[-4:]), 1) if len(notas) >= 4 else None
    tend = None if rec is None or media is None else 'alta' if rec >= media + 0.3 else 'baixa' if rec <= media - 0.3 else 'estável'
    return {'jogos': jogos, 'gols': gols, 'assist': assist, 'media': media, 'recente': rec, 'tendencia': tend}


def _ponto_forte(f):
    a = f.attrs
    cands = [('finalização', a['finish']), ('drible', a['drib']), ('velocidade', max(a['speed'], a['accel'])),
             ('passe', max(a['lowpass'], a['loftpass'])), ('desarme', a['ball_win']), ('marcação', a['def']),
             ('jogo aéreo', max(a['header'], a['jump'])), ('força', a['phys_cont'])]
    if f.pos == 'GK':
        cands = [('reflexos', a['reflex']), ('alcance', a['gk_reach']), ('pegada', a['catching'])]
    return max(cands, key=lambda c: c[1])


def _quatro(s, idx, P, todas, ini):
    import encaixe
    js = []
    for k in s.squad(idx):
        f = P.get(k) if P else None
        if not f:
            continue
        try:
            nota = encaixe.rating(f, f.pos)
        except Exception:  # noqa: BLE001
            continue
        n = _numeros(todas, k, ini, idx)
        js.append({'k': k, 'f': f, 'nome': f.name.strip(), 'pos': f.pos, 'idade': f.age, 'nota': round(nota),
                   'peso': nota + n['gols'] * 1.2 + n['assist'] * 0.8 + (n['media'] or 6) - 6, **n})
    js.sort(key=lambda j: -j['peso'])
    escolha = []
    for grupo in (ATA, DEF):
        j = next((j for j in js if j['pos'] in grupo and j not in escolha), None)
        if j:
            escolha.append(j)
    for j in js:
        if len(escolha) >= 4:
            break
        if j not in escolha and j['pos'] != 'GK':
            escolha.append(j)
    ordem = {p: i for i, p in enumerate(ATA + ('AMF', 'CMF', 'LMF', 'RMF') + DEF + ('GK',))}
    escolha.sort(key=lambda j: ordem.get(j['pos'], 99))
    return escolha


def _gols_medios(todas, t, ini):
    gp = gc = n = 0
    for p in todas:
        if tuple(p['data']) < ini or t not in (p['time1'], p['time2']):
            continue
        n += 1
        a, b = (p['gols1'], p['gols2']) if p['time1'] == t else (p['gols2'], p['gols1'])
        gp += a
        gc += b
    return (round(gp / n, 1), round(gc / n, 1), n) if n else (None, None, 0)


def gerar(s, casa, fora, P, todas, hoje):
    ini = (hoje[0] if hoje[1] >= 7 else hoje[0] - 1, 7, 1)
    if not any(tuple(p['data']) >= ini for p in todas):
        ini = (hoje[0], 1, 1)
    na, nb = s.name(casa).strip(), s.name(fora).strip()
    qa, qb = _quatro(s, casa, P, todas, ini), _quatro(s, fora, P, todas, ini)
    if len(qa) < 2 or len(qb) < 2:
        return None
    ga, gb = _gols_medios(todas, casa, ini), _gols_medios(todas, fora, ini)

    def cartao(j):
        pf = _ponto_forte(j['f'])
        return {'nome': j['nome'], 'pid': j['k'][1], 'pos': j['pos'], 'idade': j['idade'], 'nota': j['nota'],
                'jogos': j['jogos'], 'gols': j['gols'], 'assist': j['assist'], 'media': j['media'],
                'recente': j['recente'], 'tendencia': j['tendencia'], 'forte': f'{pf[0]} {pf[1]}'}
    analise = []
    if ga[0] is not None and gb[0] is not None:
        mais = na if ga[0] > gb[0] else nb if gb[0] > ga[0] else None
        v = lambda x: str(x).replace('.', ',')
        analise.append(f'Na temporada, o {na} marca {v(ga[0])} e sofre {v(ga[1])} gols por jogo; o {nb} marca {v(gb[0])} e sofre {v(gb[1])}.'
                       + (f' Quem ataca mais é o {mais}.' if mais else ' Os dois ataques têm números parecidos.'))
    atk_a = next((j for j in qa if j['pos'] in ATA), qa[0])
    atk_b = next((j for j in qb if j['pos'] in ATA), qb[0])
    def_a = max((j for j in qa if j['pos'] in DEF), key=lambda j: j['f'].attrs['def'], default=None)
    def_b = max((j for j in qb if j['pos'] in DEF), key=lambda j: j['f'].attrs['def'], default=None)
    duelos = []
    if def_b:
        duelos.append({'ataque': atk_a['nome'], 'time_ataque': na, 'defesa': def_b['nome'], 'time_defesa': nb,
                       'a': atk_a['f'].attrs['finish'], 'd': def_b['f'].attrs['def']})
    if def_a:
        duelos.append({'ataque': atk_b['nome'], 'time_ataque': nb, 'defesa': def_a['nome'], 'time_defesa': na,
                       'a': atk_b['f'].attrs['finish'], 'd': def_a['f'].attrs['def']})
    for du in duelos:
        lado = 'leva vantagem' if du['a'] > du['d'] + 3 else 'tem a missão de parar' if du['d'] > du['a'] + 3 else 'equilíbrio total'
        analise.append(f'Duelo-chave: {du["ataque"]} (finalização {du["a"]}) contra {du["defesa"]} (marcação {du["d"]}) — '
                       + (f'{du["ataque"]} {lado}.' if lado == 'leva vantagem' else f'{du["defesa"]} {lado} {du["ataque"]}.' if lado.startswith('tem') else 'equilíbrio total.'))
    rapido = max(qb, key=lambda j: max(j['f'].attrs['speed'], j['f'].attrs['accel']))
    vel = max(rapido['f'].attrs['speed'], rapido['f'].attrs['accel'])
    if vel >= 85:
        analise.append(f'Como lidar: atenção à velocidade de {rapido["nome"]} ({vel}); vale proteger as costas da defesa '
                       f'e não dar campo nas transições.')
    for j in qa + qb:
        if j['tendencia'] == 'alta':
            analise.append(f'Em alta: {j["nome"]} tem média {j["recente"]} nos últimos jogos (temporada: {j["media"]}).')
            break
    for j in qa + qb:
        if j['tendencia'] == 'baixa':
            analise.append(f'Em baixa: {j["nome"]} caiu para {j["recente"]} nos últimos jogos (temporada: {j["media"]}).')
            break
    artilheiro = max(qa + qb, key=lambda j: j['gols'])
    if artilheiro['gols'] >= 3:
        analise.append(f'Em alta: {artilheiro["nome"]} soma {artilheiro["gols"]} gols na temporada.')
    return {'casa': na, 'fora': nb, 'jogadores': {'casa': [cartao(j) for j in qa], 'fora': [cartao(j) for j in qb]},
            'medias': {'casa': {'gp': ga[0], 'gc': ga[1], 'jogos': ga[2]}, 'fora': {'gp': gb[0], 'gc': gb[1], 'jogos': gb[2]}},
            'duelos': duelos, 'analise': analise}
