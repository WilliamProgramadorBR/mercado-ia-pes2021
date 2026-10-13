# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Imprensa do MUNDO (11/10/2026): matérias que vão além do clube, com os números de destaques.py.

  premios     fim de temporada: a SELEÇÃO DA TEMPORADA votada por 30 jornalistas (4-3-3), artilheiro e garçom do
              mundo, a revelação do ano e a corrida da Bola de Ouro. Uma por temporada.
  revelacao   "Quem é ele?": o jogador que ninguém conhecia e que virou assunto (nota baixa, clube pequeno ou muito
              jovem, mas com números de craque; se foi chamado para a seleção, a matéria conta). Ex. real: Igor Thiago.
  olho_adv    "De olho no adversário": os números dos perigos do próximo rival (pré-jogo).
  retro       a temporada que acabou: o jogo apaga as súmulas na virada; as cópias do save da reunião (save_work)
              ainda têm a temporada completa, então a premiação sai mesmo depois da virada.
"""
import glob
import os

import imprensa_db as db

POS_TXT = {'GK': 'goleiro', 'CB': 'zagueiro', 'LB': 'lateral-esquerdo', 'RB': 'lateral-direito', 'DMF': 'volante',
           'CMF': 'meio-campista', 'AMF': 'meia-atacante', 'LMF': 'meia pela esquerda', 'RMF': 'meia pela direita',
           'LWF': 'ponta-esquerda', 'RWF': 'ponta-direita', 'SS': 'segundo atacante', 'CF': 'centroavante'}
SLOT_TXT = {'GK': 'Gol', 'RB': 'Lateral-direito', 'CB': 'Zaga', 'LB': 'Lateral-esquerdo', 'MEI': 'Meio-campo', 'ATA': 'Ataque'}


def _n(x):
    return f'{x:.1f}'.replace('.', ',') if x is not None else '—'


def _lista(xs):
    xs = list(xs)
    return ', '.join(xs[:-1]) + ' e ' + xs[-1] if len(xs) > 1 else (xs[0] if xs else '')


def _selecao_txt(x):
    s = (x.get('selecao') or '').strip()
    return s.title() if s else None


# ---------------------------------------------------------------- premiação do fim de temporada
def premios(ck, res, nos, hoje, rnd, autor='Redação · prêmios da temporada'):
    sel = (res or {}).get('selecao')
    if not sel or len(sel['time']) < 11:
        return None
    temp, J = res['temporada'], sel['jurados']
    chave = f'premios|{ck}|{temp}'
    t = sel['time']
    por = {}
    for x in t:
        por.setdefault(x['slot'], []).append(x)
    linha = lambda xs: _lista(f'{x["nome"]} ({x["time"]}, {x["votos"]} votos)' for x in xs)
    corpo = [f'Fim de temporada, hora do voto. {J} jornalistas de todo o mundo montaram, cada um, o seu time ideal da temporada '
             f'{temp} num 4-3-3. Somados os votos, esta é a Seleção da Temporada.']
    corpo.append(f'No gol, {linha(por["GK"])}. Na defesa, {linha(por["RB"] + por["CB"] + por["LB"])}.')
    corpo.append(f'No meio-campo, {linha(por["MEI"])}. No ataque, {linha(por["ATA"])}.')
    unan = [x['nome'] for x in t if x['votos'] == J]
    if unan:
        corpo.append(('Unanimidade: ' if len(unan) > 1 else 'Voto unânime: ') + _lista(unan)
                     + f' {"apareceram" if len(unan) > 1 else "apareceu"} em todas as {J} cédulas.')
    nossos = [x['nome'] for x in t if x['time'] == nos]
    if nossos:
        corpo.append(f'O {nos} emplacou {len(nossos)} jogador{"es" if len(nossos) > 1 else ""} na seleção: {_lista(nossos)}.'
                     + (' É o retrato de uma temporada dominante.' if len(nossos) >= 5 else ''))
    else:
        corpo.append(f'O {nos} não emplacou ninguém na seleção, um recado claro sobre a temporada.')
    perto = sorted(sel['mencoes'], key=lambda x: -x['votos'])[:3]
    if perto:
        corpo.append('Ficaram na porta: ' + _lista(f'{x["nome"]} ({x["time"]}, {x["votos"]} votos)' for x in perto) + '.')
    a = (res.get('artilheiros') or [None])[0]
    g = (res.get('garcons') or [None])[0]
    if a:
        corpo.append(f'Artilheiro do mundo na temporada: {a["nome"]}, do {a["time"]}, com {a["gols"]} gols em {a["jogos"]} jogos.'
                     + (f' O garçom foi {g["nome"]} ({g["time"]}), com {g["assist"]} assistências.' if g else ''))
    rv = (res.get('revelacoes') or [None])[0]
    if rv:
        corpo.append(f'Revelação da temporada: {rv["nome"]}, {POS_TXT.get(rv["pos"], rv["pos"])} de {rv["idade"]} anos do {rv["time"]}. '
                     f'Com nota {rv["ovr"]}, ninguém apostava nele, e ele respondeu com {rv["gols"]} gols e {rv["assist"]} assistências em {rv["jogos"]} jogos.')
    tc = res.get('tecnicos') or []
    if tc:
        t0 = tc[0]
        corpo.append(f'Técnico da temporada, para a imprensa: {t0["nome"]}' + ('' if t0['nosso'] else f' ({t0["time"]})')
                     + f', {t0["pos"]}º na {t0["liga"]} com {t0["aproveitamento"]}% de aproveitamento em {t0["jogos"]} jogos. Completam o top 5: '
                     + _lista(f'{x["nome"]}' + ('' if x['nosso'] else '') for x in tc[1:5]) + '.')
    bo = res.get('bola_de_ouro') or []
    if len(bo) >= 3:
        corpo.append('Para a Bola de Ouro, a imprensa aponta ' + _lista(f'{x["nome"]} ({x["time"]})' for x in bo[:3])
                     + ' como os favoritos. A eleição sai em dezembro.')
    return {'chave': chave, 'frente': 'premios', 'data': tuple(hoje), 'autor': autor,
            'titulo': rnd.choice([f'A Seleção da Temporada {temp}', f'Os 11 melhores do mundo em {temp}, segundo a imprensa']),
            'linha_fina': f'{J} jornalistas, um 4-3-3' + (f': {len(nossos)} do {nos} entre os 11' if nossos else '') + '.',
            'corpo': corpo,
            'dados': {'temporada': temp, 'selecao': sel, 'artilheiros': (res.get('artilheiros') or [])[:5],
                      'garcons': (res.get('garcons') or [])[:3], 'revelacoes': (res.get('revelacoes') or [])[:3],
                      'bola_de_ouro': bo[:3], 'tecnicos': res.get('tecnicos') or [], 'final': True}}


# ---------------------------------------------------------------- revelação ("quem é ele?")
def revelacao(ck, res, car, hoje, rnd):
    """A revelação mais forte que ainda não virou matéria (uma por reunião; ou a convocação de quem já virou)."""
    if not res:
        return None
    temp = res['temporada']
    tab = {t['time']: t for t in ((car.get('liga') or {}).get('classificacao') or [])}
    liga = (car.get('liga') or {}).get('competicao') or 'liga'
    for x in res.get('revelacoes') or []:
        if x['jogos'] < 8 or (x['gols'] + x['assist'] < 8 and not x['sel_jogos']):
            continue
        base = f'revel|{ck}|{temp}|{x["k"][0]}:{x["k"][1]}'
        conv = x['sel_jogos'] and db.existe(ck, base) and not db.existe(ck, base + '|selecao')
        if db.existe(ck, base) and not conv:
            continue
        pos = POS_TXT.get(x['pos'], x['pos'])
        sel = _selecao_txt(x)
        if conv:   # já virou matéria; agora veio a convocação
            return {'chave': base + '|selecao', 'frente': 'revelacao', 'data': tuple(hoje), 'autor': 'Redação · mundo',
                    'titulo': rnd.choice([f'{x["nome"]} chega à seleção', f'De desconhecido a convocado: {x["nome"]}']),
                    'linha_fina': f'{x["gols"]} gols na temporada pelo {x["time"]} e agora a camisa da seleção.',
                    'corpo': [f'A história de {x["nome"]} ganhou mais um capítulo. O {pos} do {x["time"]}, que ninguém conhecia no começo da temporada, '
                              f'já entrou em campo {x["sel_jogos"]} {"vez" if x["sel_jogos"] == 1 else "vezes"} pela seleção' + (f' ({sel})' if sel else '') + '.',
                              f'Pelo clube, são {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos.'
                              + (f' Pela seleção, já marcou {x["sel_gols"]}.' if x['sel_gols'] else ''),
                              'É o caminho que o futebol adora contar: o jogador que fura a fila pelos números, não pelo nome.'],
                    'dados': {'jogador': x}}
        estrela = next((a for a in (res.get('estrelas') or []) + (res.get('artilheiros') or [])
                        if (a['ovr'] or 0) >= (x['ovr'] or 0) + 10 and a['gols'] < x['gols'] and a['pos'] in ('CF', 'SS', 'LWF', 'RWF', 'AMF')
                        and a['k'] != x['k']), None)
        corpo = [rnd.choice([f'No começo da temporada, pouca gente fora do {x["time"]} sabia quem era {x["nome"]}. Hoje, o {pos} de {x["idade"]} anos é um dos nomes mais comentados do futebol: {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos.',
                             f'{x["nome"]} não estava em nenhuma lista de craques. O {pos} de {x["idade"]} anos do {x["time"]} entrou na temporada como coadjuvante e, {x["jogos"]} jogos depois, soma {x["gols"]} gols e {x["assist"]} assistências.'])]
        papel = f'No papel, nada indicava isso: a nota dele no game é {x["ovr"]}, longe da elite.'
        if estrela:
            papel += f' Mesmo assim, ele já tem mais gols que {estrela["nome"]}, do {estrela["time"]}, nota {estrela["ovr"]}, que soma {estrela["gols"]}.'
        corpo.append(papel)
        if x['idade'] <= 19:
            corpo.append(f'Com {x["idade"]} anos, a comparação com os fenômenos precoces é inevitável. A pergunta é quanto tempo o {x["time"]} consegue segurar.')
        if x['media']:
            corpo.append(f'A média de nota, {_n(x["media"])}, mostra que não é sorte de uma noite: é regularidade.' if x['media'] >= 6.2 else
                         f'A nota média ({_n(x["media"])}) ainda oscila, mas os números de gol e de passe falam por ele.')
        if x['sel_jogos']:
            corpo.append(f'E o prêmio já veio: chamado para a seleção' + (f' ({sel})' if sel else '') + f', entrou em campo {x["sel_jogos"]} '
                         f'{"vez" if x["sel_jogos"] == 1 else "vezes"}' + (f' e marcou {x["sel_gols"]}.' if x['sel_gols'] else '.'))
        else:
            corpo.append('A convocação para a seleção ainda não veio, mas a pressão da imprensa cresce a cada rodada.')
        t = tab.get(x['time'])
        if t:
            corpo.append(f'Na {liga}, o {x["time"]} é o {t["pos"]}º, com {t["pts"]} pontos.')
        elif (x['rank'] or 0) > 60:
            corpo.append(f'Detalhe que valoriza ainda mais: pelos números, o elenco do {x["time"]} é só o {x["rank"]}º mais forte do mundo.')
        corpo.append(rnd.choice(['Nos bastidores, a pergunta já não é se ele vai sair, e sim quando e para onde.',
                                 'Os olheiros dos grandes clubes já marcaram os próximos jogos dele na agenda.']))
        tit = rnd.choice([f'Quem é {x["nome"]}, o {pos} que ninguém conhecia',
                          f'{x["nome"]}: de desconhecido a sensação da temporada',
                          f'O fenômeno {x["nome"]}' if x['idade'] <= 19 else f'{x["nome"]} pede passagem'])
        return {'chave': base, 'frente': 'revelacao', 'data': tuple(hoje), 'autor': 'Redação · mundo', 'titulo': tit,
                'linha_fina': f'{x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos pelo {x["time"]}, com nota {x["ovr"]}.',
                'corpo': corpo, 'dados': {'jogador': x}}
    return None


# ---------------------------------------------------------------- pré-jogo
def olho_adversario(res, adv):
    js = ((res or {}).get('clubes') or {}).get(adv) or []
    js = [x for x in js if x['jogos'] >= 2][:3]
    if not js:
        return None, []
    partes = []
    for x in js:
        p = f'{x["nome"]} ({POS_TXT.get(x["pos"], x["pos"])}, {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos'
        partes.append(p + (f', média {_n(x["media"])})' if x['media'] else ')'))
    return f'De olho no {adv}: os números da temporada apontam os perigos. ' + '; '.join(partes) + '.', js


def paragrafos_temporada(res, nos):
    if not res:
        return []
    out = []
    a = (res.get('artilheiros') or [None])[0]
    if a and a['gols'] >= 3:
        out.append(f'No mundo, o artilheiro da temporada é {a["nome"]}, do {a["time"]}, com {a["gols"]} gols em {a["jogos"]} jogos.')
    bo = res.get('bola_de_ouro') or []
    if len(bo) >= 3:
        meu = next((x for x in bo if x['time'] == nos), None)
        out.append('Na corrida pela Bola de Ouro, a imprensa aponta ' + _lista(f'{x["nome"]} ({x["time"]})' for x in bo[:3])
                   + ('.' if not meu or meu in bo[:3] else f'; {meu["nome"]} corre por fora.'))
    rv = (res.get('revelacoes') or [None])[0]
    if rv and rv['gols'] + rv['assist'] >= 5:
        out.append(f'A sensação até aqui é {rv["nome"]}, {POS_TXT.get(rv["pos"], rv["pos"])} de {rv["idade"]} anos do {rv["time"]}: '
                   f'{rv["gols"]} gols e {rv["assist"]} assistências com nota {rv["ovr"]} no game.')
    return out


# ---------------------------------------------------------------- a temporada que acabou (depois da virada)
def retro(car, ck, snap, ti, nos, hoje, log=print):
    """Premiação da temporada anterior, quando a virada já apagou as súmulas: procura a cópia mais nova do save
    (save_work/vestiario_*) que ainda tem a temporada inteira. Uma vez por temporada."""
    import destaques
    import partidas_save as ps
    from save_ml import SaveML
    ini_atual = destaques.ini_temporada(hoje)
    import temporada
    ini = temporada.anterior(ini_atual)
    temp = destaques.temporada_txt(ini)
    marca = f'v2|{temp}'   # v2: a 1ª versão aceitava a cópia de depois da virada (só ligas de calendário anual)
    if db.existe(ck, f'premios|{ck}|{temp}') or (car.get('premios_retro') or {}).get(marca):
        return None
    car.setdefault('premios_retro', {})[marca] = True
    here = os.path.dirname(os.path.abspath(__file__))
    decs = sorted(glob.glob(os.path.join(here, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime, reverse=True)
    for f in decs[:30]:
        try:
            d = open(f, 'rb').read()
            todas = ps.todas(d)
        except Exception:  # noqa: BLE001
            continue
        datas = [tuple(p['data']) for p in todas if ini <= tuple(p['data']) < ini_atual]
        # a cópia tem de ter a temporada do PRÓPRIO clube (depois da virada só sobram as ligas de calendário anual,
        # Japão e Brasil, e a "seleção" virava a do Kashiwa Reysol)
        meus = [p for p in todas if ini <= tuple(p['data']) < ini_atual and ti in (p['time1'], p['time2'])
                and p['comp'] not in destaques.NAO_OFICIAL]
        import datetime as _dt
        if len(datas) < 1500 or len(meus) < 25 or (_dt.date(*ini_atual) - _dt.date(*max(datas))).days > 75:
            continue
        try:
            import dados
            s = SaveML.__new__(SaveML)
            s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
            P = dados.load_players(snap)
            res = destaques.calcular(todas, s, P, max(datas), ti, nos, ini=ini, fim=ini_atual, tecnico=car.get('_tecnico'))
        except Exception as e:  # noqa: BLE001
            log(f'aviso: premiação retroativa: {type(e).__name__}: {e}')
            return None
        if res:
            log(f'premiação {temp}: temporada completa achada em {os.path.basename(os.path.dirname(os.path.dirname(f)))}')
            return res
    log(f'premiação {temp}: nenhuma cópia do save com a temporada completa')
    return None
