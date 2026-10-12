"""TIME DO MÊS OFICIAL do jogo x a seleção da imprensa (12/10/2026).

O save guarda o Time do mês da liga do usuário (premios_save.time_do_mes): 11 jogadores com a nota média do mês, mas
SEM o mês. Descobrimos o mês comparando essas notas com as médias de cada jogador nas súmulas, mês a mês: o mês em que
mais notas batem é o certo (maio de 2035 bateu com o print do usuário).

Quando o jogo troca o time (mês novo), sai a reportagem: o time oficial, quem a imprensa também escolheu, quem o jogo
escolheu e a imprensa não (e vice-versa), quantos do nosso clube. Vai para o redator com IA como as outras matérias.
"""
import collections
import hashlib

import imprensa_db as db
import rodada_mes as rm

MESES = rm.MESES
SLOT_POS = {'GK': 'GK', 'CB': 'CB', 'LB': 'LB', 'RB': 'RB', 'DMF': 'MEI', 'CMF': 'MEI', 'AMF': 'MEI', 'LMF': 'MEI', 'RMF': 'MEI',
            'LWF': 'ATA', 'RWF': 'ATA', 'SS': 'ATA', 'CF': 'ATA'}


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def _medias_mes(todas, y, m, so_comp=None):
    E = collections.defaultdict(list)
    for p in todas:
        if p['data'][0] != y or p['data'][1] != m or p['comp'] in rm.NAO_OFICIAL or (so_comp is not None and p['comp'] != so_comp):
            continue
        for _, x, _ in rm._linhas(p):
            if x['nota']:
                E[(x['reg'], x['pid'])].append(x['nota'])
    return {k: sum(v) / len(v) for k, v in E.items()}


def detectar_mes(tdm, todas):
    """(ano, mês) em que as notas do Time do mês batem com as súmulas, ou None."""
    melhor, ms = None, set()
    for p in todas:
        if p['comp'] == tdm['comp']:
            ms.add((p['data'][0], p['data'][1]))
    for y, m in ms:
        for so in (tdm['comp'], None):   # só a liga ou todas as competições oficiais
            med = _medias_mes(todas, y, m, so)
            ok = sum(1 for j in tdm['jogadores'] if (j['reg'], j['pid']) in med and abs(round(med[(j['reg'], j['pid'])] * 10) - j['valor']) <= 1)
            if not melhor or ok > melhor[0]:
                melhor = (ok, y, m)
    return (melhor[1], melhor[2]) if melhor and melhor[0] >= 7 else None


def _nossa(todas, ti, P, nome_time, y, m, liga):
    """A seleção da imprensa no mesmo mês (mesma regra de rodada_mes: média + gols + assistências, mínimo 2 jogos)."""
    clubes = {t for p in todas if p['comp'] == liga for t in (p['time1'], p['time2'])}
    E = collections.defaultdict(lambda: {'jogos': 0, 'gols': 0, 'assist': 0, 'notas': [], 't': None})
    for p in todas:
        if p['data'][0] != y or p['data'][1] != m or p['comp'] in rm.NAO_OFICIAL:
            continue
        for t, x, _ in rm._linhas(p):
            if t in clubes:
                e = E[(x['reg'], x['pid'])]
                e['jogos'] += 1
                e['gols'] += x['gols']
                e['assist'] += x['assist']
                e['t'] = t
                if x['nota']:
                    e['notas'].append(x['nota'])
    cands = []
    for k, e in E.items():
        f = P.get(k)
        if f and e['jogos'] >= 2 and e['notas']:
            med = sum(e['notas']) / len(e['notas'])
            cands.append({'id': k, 'k': list(k), 'nome': f.name.strip(), 'pos': f.pos, 'time': nome_time(e['t']), 'nosso': e['t'] == ti,
                          'media': round(med, 2), 'gols': e['gols'], 'assist': e['assist'], 'jogos': e['jogos'],
                          'sc': round(med + 0.35 * e['gols'] + 0.25 * e['assist'] + 0.05 * e['jogos'], 2)})
    xi = rm._onze(cands) or []
    for x in xi:
        x.pop('id', None)
        x['nota'] = x['media']
    return xi, {tuple(c['k']): c for c in cands}


def da_reuniao(car, r, d, snap, log=print):
    """(matérias, fatos). Só quando o jogo publica um Time do mês novo (o bloco do save mudou)."""
    import imprensa
    import premios_save as ps
    ck = car.get('ck')
    ctx = imprensa._contexto(car, r, d, snap)
    P = ctx['P']
    tdm = ps.time_do_mes(d, set(P))
    if not tdm:
        return [], []
    assinatura = hashlib.sha1(repr([(j['reg'], j['pid'], j['valor']) for j in tdm['jogadores']]).encode()).hexdigest()[:16]
    if car.get('tdm_assinatura') == assinatura:
        return [], []
    todas = r.get('todas_partidas') or []
    ym = detectar_mes(tdm, todas)
    car['tdm_assinatura'] = assinatura
    if not ym:
        log('time do mês: o jogo trocou o time, mas o mês não bateu com as súmulas')
        return [], []
    y, m = ym
    chave = f'tdm|{ck}|{y}-{m:02d}|{tdm["comp"]}'
    if db.existe(ck, chave):
        return [], []
    nome_time = lambda i: ctx['s'].name(i).strip()
    from proximo_jogo import nome_comp
    liga = nome_comp(tdm['comp'])
    nossa, stats = _nossa(todas, r['ti'], P, nome_time, y, m, tdm['comp'])
    of = []
    for j in tdm['jogadores']:
        f = P.get((j['reg'], j['pid']))
        st = stats.get((j['reg'], j['pid'])) or {}
        of.append({'k': [j['reg'], j['pid']], 'nome': f.name.strip() if f else '?', 'pos': f.pos if f else 'CMF',
                   'slot': SLOT_POS.get(f.pos if f else 'CMF', 'MEI'), 'time': nome_time(j['clube']), 'nosso': j['clube'] == r['ti'],
                   'nota': j['valor'] / 10, 'gols': st.get('gols', 0), 'assist': st.get('assist', 0), 'jogos': st.get('jogos')})
    ko = {tuple(x['k']) for x in of}
    kn = {tuple(x['k']) for x in nossa}
    ambos = [x for x in of if tuple(x['k']) in kn]
    so_jogo = [x for x in of if tuple(x['k']) not in kn]
    so_nos = [x for x in nossa if tuple(x['k']) not in ko]
    nossos = [x['nome'] for x in of if x['nosso']]
    mes = MESES[m - 1]
    top = max(of, key=lambda x: (x['nota'], x['gols']))
    lin = lambda xs: ', '.join(f'{x["nome"]} ({x["time"]})' for x in xs)
    corpo = [f'Saiu o Time do mês de {mes} da {liga}, escolhido pela organização: {lin(of)}.',
             f'A maior nota do time é de {top["nome"]}, do {top["time"]}: média {_n(top["nota"])} no mês'
             + (f', com {top["gols"]} gol' + ('s' if top['gols'] > 1 else '') if top['gols'] else '') + '.',
             (f'O {r["time"]} emplacou {len(nossos)}: {", ".join(nossos)}.' if nossos else f'Nenhum jogador do {r["time"]} entrou no time de {mes}.')]
    if nossa:
        corpo.append(f'A redação tinha a própria seleção de {mes} e acertou {len(ambos)} dos 11: {", ".join(x["nome"] for x in ambos) or "nenhum"}.')
        if so_jogo:
            corpo.append('O time oficial lembrou de ' + lin(so_jogo[:4]) + ', que ficaram fora da lista da imprensa.')
        if so_nos:
            corpo.append('Já a imprensa preferia ' + ', '.join(f'{x["nome"]} ({x["time"]}, média {_n(x["media"])}'
                                                              + (f', {x["gols"]} gols' if x['gols'] else '') + ')' for x in so_nos[:4])
                         + '. Ficaram de fora do time oficial.')
    m_ = {'chave': chave, 'frente': 'rodada', 'data': tuple(r['hoje']), 'autor': 'Redação · time do mês',
          'titulo': f'Time do mês de {mes}: {len(nossos)} do {r["time"]}' if nossos else f'Time do mês de {mes} na {liga}',
          'linha_fina': f'{liga} · a escolha oficial e a da imprensa: {len(ambos)} nomes em comum.',
          'corpo': corpo,
          'dados': {'tipo': 'tdm', 'mes': mes, 'ano': y, 'competicao': liga,
                    'selecao': {'time': of, 'mencoes': [], 'jurados': None},
                    'imprensa': {'time': nossa, 'mencoes': [], 'jurados': None} if nossa else None,
                    'ambos': [x['nome'] for x in ambos], 'so_jogo': [x['nome'] for x in so_jogo], 'so_imprensa': [x['nome'] for x in so_nos]}}
    fato = {'tipo': 'rodada', 'modo': 'tdm', 'sub': chave, 'peso': 2.2 + 0.4 * len(nossos), 'mes': mes, 'liga': liga,
            'top': top, 'nossos': nossos, 'ambos': len(ambos)}
    car.setdefault('rodada_destaque', {})['tdm'] = {k: v for k, v in fato.items() if k != 'peso'} | {'data': list(r['hoje'])}
    log(f'time do mês oficial: {mes}/{y} ({liga}), {len(nossos)} do clube, {len(ambos)} em comum com a imprensa')
    return [m_], [fato]
