# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""SAÍDAS E CHEGADAS do elenco (11/10/2026): a imprensa, a torcida e os rivais reagem às movimentações do clube.

Fonte: tabela de TRANSFERÊNCIAS da carreira no save (~0x1291xxx no save de 2035), registros de 0xF0 bytes, achada pela
rescisão do KAIO (01/07/2035, R$ 182,7 mi, até 2039):
  -16 data em que vale (u16 ano, u8 mês, u8 dia) | +0 u32 registro, u32 id | +8 u32 valor (x430 = R$) | +12 u32 salário (x430)
  +16 fim do contrato novo | +24 u32 código do clube de DESTINO (& 0x3FFF = índice do time)
Transferência combinada aparece ANTES de valer (data futura = "pendente": o jogador ainda está no elenco).

Histórias (casos reais do futebol, para a imprensa comparar):
  sombra   — craque que vivia à sombra de uma lenda do elenco (Neymar deixando Messi pelo PSG, 2017)
  rival    — vai para um rival direto (Figo, do Barcelona para o Real Madrid, 2000)
  idolo    — ídolo antigo vai embora (Casillas deixando o Real Madrid, 2015)
  dinheiro — troca a elite por uma liga menor (Oscar, do Chelsea para a China, 2017)
  jovem / veterano / venda — demais casos
"""
import struct

REC = 0xF0
REAIS = {
    'sombra': 'o Neymar deixou o Barcelona e a sombra do Messi para ser o protagonista no PSG, em 2017, numa transferência recorde de 222 milhões de euros',
    'rival': 'o Figo trocou o Barcelona pelo rival Real Madrid em 2000 e nunca foi perdoado pela torcida',
    'idolo': 'o Casillas deixou o Real Madrid em 2015, depois de uma vida inteira no clube',
    'dinheiro': 'o Oscar trocou o Chelsea pela China em 2017, no auge da carreira',
}


# 12/10/2026: a história depende da POSIÇÃO. Zagueiro não disputa vaga com atacante: a "sombra" só vale dentro do setor,
# e cada setor tem as suas comparações reais (todas de fatos conhecidos).
SETOR = {'GK': 'gol', 'CB': 'zaga', 'LB': 'lateral', 'RB': 'lateral', 'DMF': 'meio', 'CMF': 'meio', 'AMF': 'meio', 'LMF': 'meio',
         'RMF': 'meio', 'LWF': 'ataque', 'RWF': 'ataque', 'SS': 'ataque', 'CF': 'ataque'}
SETOR_TXT = {'gol': 'o gol', 'zaga': 'a zaga', 'lateral': 'a lateral', 'meio': 'o meio-campo', 'ataque': 'o ataque'}
REAIS_POS = {
    ('sombra', 'gol'): 'o Alisson deixou a Roma pelo Liverpool em 2018 para ser o dono absoluto da camisa 1',
    ('sem_espaco', 'gol'): 'o Alisson deixou a Roma pelo Liverpool em 2018 para ser o dono absoluto da camisa 1',
    ('idolo', 'gol'): 'o Buffon deixou a Juventus em 2018, depois de 17 temporadas como dono do gol',
    ('venda', 'gol'): 'o Alisson trocou a Roma pelo Liverpool em 2018 e virou peça de time campeão',
    ('sombra', 'zaga'): 'o Virgil van Dijk deixou o Southampton pelo Liverpool em 2018 para liderar uma defesa de time grande',
    ('sem_espaco', 'zaga'): 'o Harry Maguire foi do Leicester ao Manchester United em 2019 para ser o líder da defesa',
    ('idolo', 'zaga'): 'o Sergio Ramos deixou o Real Madrid em 2021, depois de 16 temporadas e quatro Champions',
    ('venda', 'zaga'): 'o Thiago Silva saiu do Milan para o PSG em 2012 e mudou o patamar do novo clube',
    ('sombra', 'lateral'): 'o Daniel Alves trocou o Sevilla pelo Barcelona em 2008 e virou referência na posição',
    ('sem_espaco', 'lateral'): 'o Achraf Hakimi deixou a Inter pelo PSG em 2021 atrás de protagonismo',
    ('idolo', 'lateral'): 'o Marcelo deixou o Real Madrid em 2022, depois de 15 anos e 25 títulos',
    ('venda', 'lateral'): 'o Achraf Hakimi deixou a Inter pelo PSG em 2021, logo depois de ser campeão italiano',
    ('sombra', 'meio'): 'o Kevin De Bruyne saiu do Chelsea sem espaço em 2014 e virou estrela no Wolfsburg',
    ('sem_espaco', 'meio'): 'o Kevin De Bruyne saiu do Chelsea sem espaço em 2014 e virou estrela no Wolfsburg',
    ('idolo', 'meio'): 'o Xavi deixou o Barcelona em 2015, depois de 17 temporadas no time principal',
    ('venda', 'meio'): 'o Frenkie de Jong deixou o Ajax pelo Barcelona em 2019, depois de uma temporada mágica',
    ('sombra', 'ataque'): 'o Neymar deixou o Barcelona e a sombra do Messi para ser o protagonista no PSG, em 2017, numa transferência recorde de 222 milhões de euros',
    ('idolo', 'ataque'): 'o Thierry Henry deixou o Arsenal em 2007 como maior artilheiro da história do clube',
    ('venda', 'ataque'): 'o Cristiano Ronaldo deixou o Manchester United pelo Real Madrid em 2009, por 94 milhões de euros',
}


def setor(pos):
    return SETOR.get(pos or '', 'meio')


def _registro(d, o, chaves):
    if o < 16 or o + 32 > len(d):
        return None
    reg, pid = struct.unpack_from('<II', d, o)
    if (reg, pid) not in chaves:
        return None
    y, m, dd = struct.unpack_from('<HBB', d, o - 16)
    cy, cm, cd = struct.unpack_from('<HBB', d, o + 16)
    t = struct.unpack_from('<I', d, o + 24)[0] & 0x3FFF
    if not (2015 <= y <= 2060 and 1 <= m <= 12 and 1 <= dd <= 31 and 2015 <= cy <= 2070 and t < 730):
        return None
    valor, sal = struct.unpack_from('<II', d, o + 8)
    return {'k': (reg, pid), 'data': (y, m, dd), 'valor': valor * 430, 'salario': sal * 430, 'contrato': (cy, cm, cd),
            'destino': t, 'pos': o}


def tabela(d, chaves, ini=0x1100000, fim=0x1500000):
    """Todos os registros de transferência da região (os blocos são separados — um por clube?; 11/10/2026 a busca
    por âncora achava só um deles). Varre de 4 em 4 bytes; o par (registro, id) de jogador conhecido + datas e clube
    válidos confirmam o registro."""
    out, vistos = [], set()
    fim = min(fim, len(d) - 32)
    for o in range(max(ini, 16), fim, 4):
        if struct.unpack_from('<II', d, o) not in chaves:
            continue
        x = _registro(d, o, chaves)
        if x:
            chave = (x['k'], x['data'], x['destino'])
            if chave not in vistos:
                vistos.add(chave)
                out.append(x)
    return out


def movimentos(d, ti, P, hoje, J=None, dias=40):
    """Saídas e chegadas do clube t perto de hoje: [{'tipo', 'k', 'nome', 'data', 'valor', 'clube', 'pendente', ...}]."""
    import datetime as dt
    elenco = {j['k'] for j in J} if J else set()
    out = []
    for x in tabela(d, set(P)):
        dif = (dt.date(*x['data']) - dt.date(*hoje)).days
        if not -dias <= dif <= 60:
            continue
        f = P.get(x['k'])
        if not f:
            continue
        if x['destino'] != ti:   # a tabela é a do NOSSO clube: outro destino = saída (pendente ou já efetivada)
            tipo = 'saida'
            # 12/10/2026: data já passada e o jogador CONTINUA no elenco = negociação que não aconteceu (o William
            # apareceu "vendido à Real Sociedad por R$ 440 mi" estando no time). Saída efetivada vem de executadas()
            if dif <= 0 and elenco and x['k'] in elenco:
                continue
        elif x['destino'] == ti:
            tipo = 'chegada'
        else:
            continue
        try:
            import encaixe
            ovr = round(encaixe.rating(f, f.pos))
        except Exception:  # noqa: BLE001
            ovr = 0
        out.append({**x, 'tipo': tipo, 'nome': f.name.strip(), 'pos_campo': f.pos, 'idade': f.age, 'pendente': dif > 0, 'ovr': ovr,
                    'no_elenco': x['k'] in elenco})
    return out


def retrato(J):
    """Retrato do elenco guardado a cada reunião (car['elenco_snap']): a próxima reunião descobre quem saiu/chegou."""
    return {f'{j["k"][0]}:{j["k"][1]}': {'nome': j['nome'], 'pos': j['pos'], 'idade': j['idade'], 'ovr': j['ovr'],
                                          'status': j['status'], 'anos': round(j['anos'], 1), 'moral': j['moral'],
                                          'motivos': j.get('motivos', [])[:3], 't_gols': j['t_gols']} for j in J}


def executadas(car, r, d, hoje, dias=21):
    """Saídas/chegadas EFETIVADAS: elenco da reunião anterior x atual (o save apaga a transferência pendente quando
    ela vale — 11/10/2026: o KAIO apareceu como 'pendente para a Roma' e foi efetivado na Juventus).
    Guarda em car['mov_executadas'] (cobertas por `dias` dias) e devolve as recentes."""
    import datetime as dt
    from save_ml import SaveML
    prev = car.get('elenco_snap') or {}
    atual = {f'{j["k"][0]}:{j["k"][1]}': j for j in r['J']}
    hist = car.setdefault('mov_executadas', [])
    if prev:
        s = SaveML.__new__(SaveML)
        s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
        n_clubes = __import__('selecoes').primeira(s, 625)
        pend = {f'{m["k"][0]}:{m["k"][1]}': m for m in car.get('mov_pendentes') or []}
        for kc, info in prev.items():
            if kc in atual or any(h['kc'] == kc and h['tipo'] == 'saida' for h in hist):
                continue
            k = tuple(int(x) for x in kc.split(':'))
            dest = next((i for i in range(n_clubes) if k in s.squad(i)), None)
            p = pend.get(kc) or {}
            hist.append({'kc': kc, 'k': list(k), 'tipo': 'saida', 'nome': info['nome'], 'data': list(hoje), 'pendente': False,
                         'destino': dest, 'clube': s.name(dest).strip() if dest is not None else 'clube desconhecido',
                         'valor': p.get('valor', 0) if p.get('destino') == dest else 0, 'contrato': p.get('contrato') or [hoje[0] + 3, 6, 30],
                         'idade': info['idade'], 'pos_campo': info['pos'], 'ovr': info['ovr'], 'no_elenco': False,
                         'prev': {**info, 'k': k}})
        for kc, j in atual.items():
            if kc not in prev and not any(h['kc'] == kc and h['tipo'] == 'chegada' for h in hist):
                hist.append({'kc': kc, 'k': list(j['k']), 'tipo': 'chegada', 'nome': j['nome'], 'data': list(hoje), 'pendente': False,
                             'destino': r['ti'], 'clube': r['time'], 'valor': 0, 'contrato': list(j['contrato'] or (hoje[0] + 3, 6, 30)),
                             'idade': j['idade'], 'pos_campo': j['pos'], 'ovr': j['ovr'], 'no_elenco': True})
    car['mov_executadas'] = [h for h in hist if (dt.date(*hoje) - dt.date(*h['data'])).days <= 60]
    # pendentes da tabela (para saber valor/destino quando efetivar) e o retrato para a próxima reunião
    car['mov_pendentes'] = [{'k': list(m['k']), 'valor': m['valor'], 'destino': m['destino'], 'contrato': list(m['contrato'])}
                            for m in r.get('movimentos') or [] if m['tipo'] == 'saida']
    car['elenco_snap'] = retrato(r['J'])
    return [dict(h, k=tuple(h['k'])) for h in car['mov_executadas'] if (dt.date(*hoje) - dt.date(*h['data'])).days <= dias]


PESO_HISTORIA = {'sombra': 5, 'rival': 5, 'idolo': 4, 'dinheiro': 3, 'jovem': 2, 'sem_espaco': 2, 'veterano': 2, 'venda': 1,
                 'chegada': 2, 'renovacao': 0}


def principal(movs, J, ck, nos, top4=(), tipos=('saida', 'chegada')):
    """A movimentação mais importante: pela história (sombra/rival/ídolo antes) e pela nota — não pelo valor (a saída
    efetivada não traz o valor; 11/10/2026 o programa escolhia o Kauê em vez do KAIO)."""
    melhor = None
    for m in movs or []:
        if m['tipo'] not in tipos:
            continue
        n = narrativa(m, J, ck, nos, top4)
        chave = (PESO_HISTORIA.get(n['tipo'], 1), m.get('ovr', 0), m.get('valor', 0))
        if melhor is None or chave > melhor[0]:
            melhor = (chave, m, n)
    return (melhor[1], melhor[2]) if melhor else (None, None)


def _mi(v):
    return f'{v / 1e6:.1f}'.replace('.', ',')


def narrativa(m, J, ck, nos, liga_times=()):
    """Texto da movimentação para todos os canais: {'tipo', 'titulo', 'lead', 'analogia', 'torcida', 'rival', 'resumo'}."""
    import classicos
    if m.get('prev') and not any(j['k'] == tuple(m['k']) for j in J):   # já saiu do elenco: usa o retrato anterior
        J = list(J) + [dict(m['prev'], k=tuple(m['k']), anos=m['prev'].get('anos', 0))]
    perfis = {}
    try:
        import legado
        for j in J:
            perfis[j['k']] = legado.perfil(ck, j['k'], j['nome'])
        res = legado.resumo(perfis.get(m['k']) or {'bolas': [], 'n_titulos': 0, 'artilharias': [], 'continentais': []}, curto=True) \
            if perfis.get(m['k']) else ''
    except Exception:  # noqa: BLE001
        res = ''
    nome, dest = m['nome'], m['clube']
    quando = 'vai deixar' if m['pendente'] else 'deixou'
    valor = f' R$ {_mi(m["valor"])} milhões' if m['valor'] >= 1e6 else ''
    o_d = f'{art(dest)} {dest}'   # 'a Roma', 'o Chelsea'
    if m['tipo'] == 'chegada':
        return {'tipo': 'chegada', 'titulo': f'{nome} é do {nos}!', 'resumo': res,
                'lead': f'Reforço confirmado: {nome} ({m["pos_campo"]}, {m["idade"]} anos) chega ao {nos}' + (f' por{valor}' if valor else '') + f', com contrato até {m["contrato"][0]}.',
                'analogia': '', 'torcida': [f'Bem-vindo, {nome}! Chega para fazer história! 🔥', f'Que contratação! {nome} é dos nossos! 🙌'], 'rival': []}
    if m['tipo'] == 'renovacao':
        return {'tipo': 'renovacao', 'titulo': f'{nome} renova até {m["contrato"][0]}', 'resumo': res,
                'lead': f'{nome} renovou com o {nos} até {m["contrato"][0]}. Um recado de confiança dos dois lados.',
                'analogia': '', 'torcida': [f'{nome} fica! Contrato até {m["contrato"][0]} 💪'], 'rival': []}
    rival = classicos.nome(nos, dest) or (dest in liga_times)
    tipo, sombra = historia(m, J, perfis, nos, dest, classico=classicos.nome(nos, dest), liga_rival=dest in liga_times)
    st = setor(m.get('pos_campo'))
    pf = perfis.get(m['k']) or {}
    vice = f' Foi vice da Bola de Ouro em {", ".join(map(str, pf["podios"]))}.' if pf.get('podios') else ''
    sombra_tit = {'gol': f'Cansado de esperar atrás de {sombra}, {nome} vai ser titular {"na" if art(dest) == "a" else "no"} {dest}',
                  'zaga': f'{nome} deixa a reserva da zaga e vai liderar a defesa {"da" if art(dest) == "a" else "do"} {dest}',
                  'lateral': f'Sem vaga na lateral, {nome} vai ser titular {"na" if art(dest) == "a" else "no"} {dest}',
                  'meio': f'{nome} sai da sombra de {sombra} no meio-campo e vai para {o_d}',
                  'ataque': f'{nome} sai da sombra de {sombra} e vai para {o_d}'}.get(st)
    titulo = {'sombra': sombra_tit,
              'rival': f'Traição? {nome} troca o {nos} pelo rival {dest}', 'idolo': f'Fim de uma era: {nome} {quando} o {nos}',
              'dinheiro': f'{nome} troca a elite por {o_d}', 'jovem': f'Joia vendida: {nome} {quando} o clube',
              'sem_espaco': f'Sem espaço, {nome} vai buscar minutos {"na" if art(dest) == "a" else "no"} {dest}',
              'veterano': f'Fim de ciclo: {nome} {quando} o {nos}', 'venda': f'{nome} {quando} o {nos} rumo {"à" if art(dest) == "a" else "ao"} {dest}'}[tipo]
    lead = f'{nome} {quando} o {nos}: {o_d} pagou{valor} e terá o jogador até {m["contrato"][0]}.' + \
        (f' Na bagagem, {res}.' if res else '') + vice
    sombra_extra = {'gol': f' Goleiro reserva vive de esperar: com {sombra} dono da camisa 1, ele preferiu jogar.',
                    'zaga': f' Na zaga, quem não joga não ganha confiança. Atrás de {sombra}, ele quer ser o líder da defesa.',
                    'lateral': f' A lateral tinha dono, {sombra}; ele vai atrás de minutos e de seleção.',
                    'meio': f' No meio-campo, o time girava em torno de {sombra}; agora ele quer ser o cérebro do time.',
                    'ataque': f' Por anos ele foi coadjuvante de {sombra}; agora quer ser a estrela principal.'}.get(st, '')
    venda_extra = {'gol': f' Sem ele, {SETOR_TXT[st]} precisa de um novo dono da camisa 1.',
                   'zaga': ' A dupla de zaga vai precisar ser remontada, e isso leva tempo de entrosamento.',
                   'lateral': ' A lateral fica aberta: o técnico terá de improvisar ou buscar reposição.',
                   'meio': ' O meio-campo perde uma engrenagem; a circulação de bola vai sentir.',
                   'ataque': ' O ataque perde gols; alguém vai ter de assumir a responsabilidade.'}.get(st, '')
    extra = {'sombra': sombra_extra,
             'rival': ' Para a torcida, a escolha do destino dói mais do que a saída.',
             'idolo': ' Sai um ídolo; fica um vazio no vestiário e na arquibancada.',
             'dinheiro': ' A dúvida que fica: projeto esportivo ou contracheque?',
             'jovem': ' O torcedor teme ver a promessa explodir longe de casa.',
             'sem_espaco': ' Sem minutos no elenco campeão, preferiu ser titular em outro lugar.',
             'veterano': ' Sai pela porta da frente, com o agradecimento da torcida.', 'venda': venda_extra}[tipo]
    if tipo == 'idolo':
        extra += {'gol': ' O gol perde mais que um goleiro: perde a voz que organizava a defesa.',
                  'zaga': ' A defesa perde o seu xerife.', 'lateral': ' O corredor perde o seu dono.',
                  'meio': ' O meio-campo perde a sua bússola.', 'ataque': ' O ataque perde a sua referência.'}.get(st, '')
    if tipo == 'sem_espaco':
        extra = f' Sem minutos {"no" if st in ("gol", "meio", "ataque") else "na"} {SETOR_TXT[st].split(" ", 1)[1]}, preferiu ser titular em outro lugar.'
    torcida = {'sombra': ([f'Obrigado por tudo, {nome}. Mas trocar o {nos} para não ser coadjuvante? 💔',
                           f'O {nome} quer ser o protagonista. Boa sorte, mas aqui o rei é {sombra} 👑'] if st in ('ataque', 'meio') else
                          [f'Faz sentido, {nome}: atrás de {sombra} não ia ter vaga. Boa sorte! 🙏',
                           f'Vai ser titular lá e a gente vai torcer daqui. Obrigado, {nome}! 👏']),
               'rival': [f'TRAIDOR! {nome} morreu para nós 😡', f'Logo para o {dest}, {nome}? Não precisava disso.'],
               'idolo': [f'Obrigado por tudo, {nome}. Ídolo eterno 🙏', 'Chorei vendo a despedida. Fim de uma era 💔'],
               'dinheiro': [f'{nome} escolheu o dinheiro. Respeito, mas não entendo 💸'],
               'jovem': [f'Venderam a nossa joia, {nome}! Vai brilhar longe daqui 😞'],
               'sem_espaco': [f'Faz sentido, {nome} precisava jogar. Boa sorte! 🙏', f'Mais um que não teve chance aqui. Pena 😕'],
               'veterano': [f'Obrigado, {nome}! Saiu pela porta da frente 👏'],
               'venda': [f'Boa sorte {"na" if art(dest) == "a" else "no"} {dest}, {nome}!']}[tipo]
    return {'tipo': tipo, 'sombra': sombra, 'titulo': titulo, 'lead': lead + extra, 'resumo': res, 'rival_destino': bool(rival),
            'analogia': REAIS_POS.get((tipo, st)) or REAIS.get(tipo, ''), 'torcida': torcida, 'setor': st,
            'rival': [f'Bem-vindo, {nome}! Agora você vai ser o dono do time! 🔥'] if tipo in ('sombra', 'rival', 'dinheiro') else []}


def historia(m, J, perfis, nos, destino_nome, rank_destino=None, classico=None, liga_rival=False):
    """Classifica a saída numa história. 11/10/2026: 'estrela' é pela nota/status/pódio (a fama soma títulos coletivos e
    deixava todo mundo 'na sombra'); 'rival' só clássico ou time do topo da tabela."""
    j = next((j for j in J if j['k'] == m['k']), {})
    pf = (perfis or {}).get(m['k']) or {}
    # já fora do elenco (transferência efetivada): nota pela ficha (m['ovr']) e sem exigir o status do vestiário
    craque = (max(j.get('ovr', 0), m.get('ovr', 0)) >= 88 or pf.get('podios') or pf.get('bolas')) and         (not j or j.get('status') in ('Lenda', 'Ídolo', 'Superastro', 'Craque'))
    st = setor(m.get('pos_campo') or j.get('pos'))
    outros = [(((perfis or {}).get(o['k']) or {}).get('fama', 0), o['nome']) for o in J
              if o['k'] != m['k'] and setor(o.get('pos')) == st]   # só quem disputa o mesmo setor
    lenda, sombra = max(outros) if outros else (0, None)
    # goleiro: a sombra é o titular (nota maior), mesmo sem Bola de Ouro
    if st == 'gol' and not classico and not liga_rival:
        tit = max((o for o in J if o['k'] != m['k'] and setor(o.get('pos')) == 'gol'), key=lambda o: o.get('ovr', 0), default=None)
        if tit and tit.get('ovr', 0) > max(j.get('ovr', 0), m.get('ovr', 0)):
            return 'sombra', tit['nome']
    if classico or liga_rival:
        return 'rival', None
    if craque and len(((perfis or {}).get(next((o['k'] for o in J if o['nome'] == sombra), None)) or {}).get('bolas', [])) >= 1 \
            and lenda > pf.get('fama', 0) + 60:
        return 'sombra', sombra
    if j.get('moral', 60) < 50 and any('joga pouco' in x for x in j.get('motivos', [])):
        return 'sem_espaco', None
    if j.get('status') in ('Lenda', 'Ídolo') and j.get('anos', 0) >= 5:
        return 'idolo', None
    if rank_destino and rank_destino > 60 and craque:
        return 'dinheiro', None
    if m['idade'] <= 21:
        return 'jovem', None
    if m['idade'] >= 32:
        return 'veterano', None
    return 'venda', None


from clube import FEMININOS  # noqa: E402  (12/10/2026: a lista mora em clube.py)


def art(clube):
    """'a Roma', 'a Juventus'... 'o Chelsea'."""
    return 'a' if clube.strip().upper() in FEMININOS else 'o'
