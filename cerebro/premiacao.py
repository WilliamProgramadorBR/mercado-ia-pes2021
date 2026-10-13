# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""PREMIAÇÃO (13/10/2026): a noite da Bola de Ouro vira o assunto do mundo do futebol.

Pedido do usuário: "o meu boneco ganhou a Bola de Ouro agora, o PES tem um sistema para anunciar o ganhador. Consegue
adaptar isso nos noticiários, rede e tudo mais? É a época mais agitada do futebol. Os fãs amam!"

De onde vem: o próprio jogo grava o resultado oficial no save ("Prêmio de melhor jogador do mundo", e os continentais),
com o pódio e os votos (premios_save.ler — o mesmo que já alimenta o Hall da Central e o Bola na Mesa). Aqui, quando
aparece uma EDIÇÃO NOVA de um prêmio (o ano subiu), a reunião monta a "cerimônia" uma única vez e espalha:
  capas         fato 'premio_mundo' (manchete por tom de jornal, texto de abertura e a fala do premiado);
  matérias      três vozes (Mesa Tática, Plantão do Esporte, Resenha Raiz): a apuração em números, a noite da
                cerimônia e a resenha — o redator de IA reescreve no estilo de cada uma;
  vestiário     moral do premiado, do grupo que festeja e de quem ficou no pódio (o vaidoso que perdeu para o
                companheiro sente);
  celular       o premiado manda mensagem ao técnico (e o vice vaidoso também, se for o caso);
  redes         modelos de posts, conta oficial, post do jogador e "Em alta" (redes_vivas usa redes_*);
  coletiva      cenários do prêmio (coletiva_extra usa car['premiacao_ultima']).
Os continentais só viram notícia se tiver alguém do clube no pódio. Na 1ª vez que roda numa carreira, só a edição do
melhor do mundo que saiu há pouco (até 40 dias) é tratada como nova; as antigas ficam como já vistas.
"""
import datetime as dt

from clube import C as CL

NOME_PREMIO = {'mundo': 'Bola de Ouro', 'europa': 'Melhor jogador da Europa',
               'america_sul': 'Melhor jogador da América do Sul', 'asia': 'Melhor jogador da Ásia'}
# com artigo, para frases como "conquista a Bola de Ouro"
FRASE = {'mundo': 'a Bola de Ouro', 'europa': 'o prêmio de melhor jogador da Europa',
         'america_sul': 'o prêmio de melhor jogador da América do Sul', 'asia': 'o prêmio de melhor jogador da Ásia'}
DIA_MUNDO = (12, 2)          # o jogo entrega o melhor do mundo em 2 de dezembro (legado.premio_recente)
JANELA_REDES = 12            # dias em que o prêmio domina o feed
JANELA_COLETIVA = 10
VEZES = {1: '', 2: 'bicampeão', 3: 'tricampeão', 4: 'tetracampeão', 5: 'pentacampeão', 6: 'hexacampeão',
         7: 'heptacampeão', 8: 'octacampeão'}
POS_TXT = {'GK': 'goleiro', 'CB': 'zagueiro', 'LB': 'lateral', 'RB': 'lateral', 'DMF': 'volante', 'CMF': 'meia',
           'AMF': 'meia', 'LMF': 'meia', 'RMF': 'meia', 'LWF': 'ponta', 'RWF': 'ponta', 'SS': 'atacante', 'CF': 'centroavante'}


def _kc(k):
    return f'{k[0]}:{k[1]}'


def _d(a, b):
    return (dt.date(*tuple(a)[:3]) - dt.date(*tuple(b)[:3])).days


def vezes_txt(n):
    """2 -> 'bicampeão'; 1 -> ''; 9 -> '9 vezes campeão'."""
    return VEZES.get(n, f'{n} vezes campeão')


# ---------------------------------------------------------------- a cerimônia
def _edicoes(d, s, P, J, ti):
    import clube
    import premios_save as ps
    porK = {tuple(j['k']): j for j in J}
    out = {}
    for cat, v in ps.ler(d).items():
        top = []
        for pos, x in enumerate(v['top'], 1):
            k = (x['reg'], x['pid'])
            j = porK.get(k)
            f = P.get(k) if P else None
            top.append({'pos': pos, 'k': list(k), 'nome': (j or {}).get('nome') or (f.name.strip() if f else '?'),
                        'clube': clube.nome_time(s.name(x['clube']).strip()), 'votos': x['votos'],
                        'nosso': x['clube'] == ti, 'posicao': (j or {}).get('pos') or (f.pos if f else '')})
        if top:
            out[cat] = {'cat': cat, 'ano': v['ano'], 'top': top}
    return out


def _novas(car, eds, hoje):
    vista = car.get('premiacao_vista')
    primeira = vista is None
    vista = dict(vista or {})
    novas = []
    for cat, e in eds.items():
        ja = vista.get(cat)
        if primeira:
            recente = cat == 'mundo' and 0 <= _d(hoje, (e['ano'],) + DIA_MUNDO) <= 40
            if recente:
                novas.append(e)
        elif ja is None or e['ano'] > ja:
            novas.append(e)
        vista[cat] = e['ano']
    car['premiacao_vista'] = vista
    return novas


def montar(e, car, J, hoje):
    """Cerimônia completa de uma edição: pódio, diferença, títulos do premiado, números da temporada, lendas."""
    import legado
    a = e['top'][0]
    j = next((x for x in J if list(x['k']) == a['k']), None)
    ck = car.get('ck')
    p = None
    try:
        p = legado.perfil(ck, tuple(a['k']), a['nome'])
    except Exception:  # noqa: BLE001
        p = None
    bolas = sorted(set((p or {}).get('bolas') or []) | ({e['ano']} if e['cat'] == 'mundo' else set()))
    seg = 1
    while e['cat'] == 'mundo' and len(bolas) > seg and bolas[-1 - seg] == e['ano'] - seg:
        seg += 1
    comp = []
    if e['cat'] == 'mundo' and p is not None:
        try:
            comp = [(t, x[0], x[2]) for t, x in legado.comparacoes(dict(p, bolas=bolas))]
        except Exception:  # noqa: BLE001
            comp = []
    b = e['top'][1] if len(e['top']) > 1 else None
    nossos = [x for x in e['top'] if x['nosso']]
    cer = {'cat': e['cat'], 'premio': NOME_PREMIO.get(e['cat'], 'Prêmio'), 'frase': FRASE.get(e['cat'], 'o prêmio'), 'ano': e['ano'], 'top': e['top'],
           'vencedor': a, 'nosso_venceu': a['nosso'], 'nossos': nossos, 'podio_nosso': len(nossos) == len(e['top']) >= 3,
           'dif': a['votos'] - b['votos'] if b else None, 'pct': round(100 * a['votos'] / max(1, sum(x['votos'] for x in e['top']))),
           'n': len(bolas) if e['cat'] == 'mundo' else None, 'anos': bolas if e['cat'] == 'mundo' else [],
           'seguidas': seg if e['cat'] == 'mundo' else 0, 'lendas': comp, 'data': list(hoje)}
    if j:
        cer['numeros'] = {'jogos': j.get('t_jogos', 0), 'gols': j.get('t_gols', 0), 'assist': j.get('t_assist', 0),
                          'nota': round(j.get('t_nota') or 0, 2), 'idade': j.get('idade'), 'pos': j.get('pos'),
                          'anos_clube': j.get('anos'), 'status': j.get('status'),
                          'tracos': ((j.get('perfil') or {}).get('tracos')) or []}
    return cer


def cerimonia(car, r, d, s, P, hoje, log=print):
    """Chamada na reunião. Devolve (matérias, fatos para as capas, notícias, casos do celular) e aplica a moral."""
    J = r['J']
    novas = _novas(car, _edicoes(d, s, P, J, r['ti']), hoje)
    mats, fatos, noticias, casos = [], [], [], []
    for e in sorted(novas, key=lambda e: e['cat'] != 'mundo'):
        if e['cat'] != 'mundo' and not any(x['nosso'] for x in e['top']):
            continue
        cer = montar(e, car, J, hoje)
        if e['cat'] == 'mundo':
            car['premiacao_ultima'] = cer
        car.setdefault('premiacao_hist', []).append({k: cer[k] for k in ('cat', 'ano', 'vencedor', 'nosso_venceu', 'n', 'data')})
        car['premiacao_hist'] = car['premiacao_hist'][-30:]
        a = cer['vencedor']
        log(f'premiação: {cer["premio"]} {cer["ano"]} — {a["nome"]} ({a["clube"]}, {a["votos"]} votos)')
        noticias.append(f'PRÊMIO: {a["nome"]} ({a["clube"]}) conquista {cer["frase"]} {cer["ano"]} com {a["votos"]} votos'
                        + (f' — {vezes_txt(cer["n"])}' if (cer.get('n') or 0) >= 2 else '') + '.')
        fatos.append({'tipo': 'premio_mundo', 'sub': f'{cer["cat"]}|{cer["ano"]}', 'cer': cer,
                      'peso': (16 if cer['nosso_venceu'] else 7 if cer['nossos'] else 3.5) * (1 if cer['cat'] == 'mundo' else 0.6)})
        mats += materias(cer, car.get('ck'), hoje)
        _moral(car, cer, J, hoje)
        casos += celular(cer, r, car, hoje)
    return mats, fatos, noticias, casos


def _moral(car, cer, J, hoje):
    import compromissos
    efs = []
    a = cer['vencedor']
    if cer['nosso_venceu']:
        efs.append({'k': _kc(a['k']), 'delta': 8 if cer['cat'] == 'mundo' else 5, 'rodadas': 5,
                    'motivo': f'conquistou {cer["frase"]} {cer["ano"]}'})
        efs.append({'k': '*', 'delta': 2, 'rodadas': 2, 'motivo': f'o vestiário festejou o prêmio de {a["nome"]}'})
    for x in cer['top'][1:]:
        if not x['nosso']:
            continue
        j = next((j for j in J if list(j['k']) == x['k']), None)
        vaidoso = 'vaidoso' in (((j or {}).get('perfil') or {}).get('tracos') or [])
        if cer['nosso_venceu'] and vaidoso:
            efs.append({'k': _kc(x['k']), 'delta': -3, 'rodadas': 2,
                        'motivo': f'terminou atrás do companheiro {a["nome"]} na votação ({x["votos"]} votos)'})
        else:
            efs.append({'k': _kc(x['k']), 'delta': 3, 'rodadas': 3, 'motivo': f'{x["pos"]}º lugar na votação d{cer["frase"][0]} {cer["frase"][2:]} {cer["ano"]}'})
    if efs:
        compromissos.historias(car, efs, [_kc(j['k']) for j in J], hoje, f'Premio|{cer["cat"]}|{cer["ano"]}')


# ---------------------------------------------------------------- capas (jornal_extra delega para cá)
def manchete(f, tom, rnd):
    c = f['cer']
    a, n, pr = c['vencedor'], c.get('n') or 1, c['premio']
    nome, up = a['nome'], a['nome'].upper()
    vz = vezes_txt(n)
    podio = ', '.join(f'{x["nome"]} ({x["votos"]})' for x in c['top'])
    if c['cat'] != 'mundo':
        return {'sensacionalista': (f'{up} É O {pr.upper()}!', f'{a["votos"]} votos. Pódio: {podio}.'),
                'analítico': (f'{pr} {c["ano"]}: {nome}', f'{a["votos"]} votos, {c["pct"]}% do pódio. Pódio: {podio}.'),
                'torcedor': (f'{nome}, {pr}!', 'Mais um troféu para a nossa galeria.')}[tom]
    if c['nosso_venceu']:
        sens = [f'{up} É O MELHOR DO MUNDO!', f'O MUNDO É DE {up}!'] + ([f'{vz.upper()}! {up} FAZ HISTÓRIA'] if vz else [])
        fina_s = (f'{a["votos"]} votos e {c["dif"]} de vantagem para {c["top"][1]["nome"]}.' if c.get('dif') else f'{a["votos"]} votos.') \
            + (' PÓDIO 100% ' + (CL.get('apelido') or CL.get('curto') or 'NOSSO').upper() + '!' if c['podio_nosso'] else '')
        return {'sensacionalista': (rnd.choice(sens), fina_s),
                'analítico': (f'Bola de Ouro {c["ano"]}: {nome}' + (f', {vz}' if vz else ''),
                              f'{a["votos"]} votos ({c["pct"]}% do pódio). ' + (f'{n} prêmios, {c["seguidas"]} seguidos.' if n >= 2 else 'Primeiro prêmio da carreira.')),
                'torcedor': (f'É NOSSO! {nome}, o melhor do mundo!' if n < 2 else f'{nome} {vz} do mundo!',
                             'Pódio todinho de casa. Que temporada!' if c['podio_nosso'] else 'A torcida já sabia. Agora é oficial.')}[tom]
    if c['nossos']:
        x = c['nossos'][0]
        return {'sensacionalista': (f'INJUSTIÇA? {x["nome"].upper()} FICA EM {x["pos"]}º NA BOLA DE OURO', f'{nome} ({a["clube"]}) leva o prêmio com {a["votos"]} votos.'),
                'analítico': (f'Bola de Ouro {c["ano"]}: {nome}; {x["nome"]} é {x["pos"]}º', f'Pódio: {podio}.'),
                'torcedor': (f'{x["nome"]} no pódio do mundo!', f'O prêmio foi para {nome}, mas o nosso está entre os melhores.')}[tom]
    return {'sensacionalista': (f'{up} É O MELHOR DO MUNDO', f'O craque do {a["clube"]} leva a Bola de Ouro {c["ano"]}.'),
            'analítico': (f'Bola de Ouro {c["ano"]}: {nome}', f'Pódio: {podio}.'),
            'torcedor': (f'Bola de Ouro para {nome}', 'Nenhum dos nossos no pódio desta vez.')}[tom]


def texto(f):
    c = f['cer']
    a, nu = c['vencedor'], c.get('numeros') or {}
    partes = [f'{a["nome"]}, do {a["clube"]}, conquista {c["frase"]} {c["ano"]}, com {a["votos"]} votos'
              + (f' — {c["dif"]} a mais que {c["top"][1]["nome"]} ({c["top"][1]["clube"]})' if c.get('dif') else '') + '.']
    if c['cat'] == 'mundo' and (c.get('n') or 0) >= 2:
        partes.append(f'É a {c["n"]}ª Bola de Ouro da carreira ({", ".join(map(str, c["anos"]))})'
                      + (f', {c["seguidas"]} seguidas' if c['seguidas'] >= 2 else '') + '.')
    if nu.get('jogos'):
        partes.append(f'Na temporada: {nu["gols"]} gols e {nu["assist"]} assistências em {nu["jogos"]} jogos, nota média {str(nu["nota"]).replace(".", ",")}.')
    if c['podio_nosso']:
        partes.append(f'O pódio é todo do {CL.get("curto") or "clube"}: ' + ', '.join(f'{x["nome"]} ({x["votos"]})' for x in c['top']) + '.')
    for tipo, nome, frase in c.get('lendas') or []:
        if tipo == 'igual':
            partes.append(f'Com isso, iguala {nome}, que tem {frase}.')
        elif tipo == 'alvo':
            partes.append(f'O próximo degrau é {nome}: {frase}.')
    return ' '.join(partes)


def aspas(f, rnd):
    c = f['cer']
    a = c['vencedor']
    if not c['nosso_venceu']:
        x = (c['nossos'] or [None])[0]
        if not x:
            return None
        return {'quem': x['nome'], 'papel': f'{x["pos"]}º na votação', 'texto': rnd.choice(
            ['Estar entre os três melhores do mundo já é uma honra. Ano que vem tem mais.',
             'Parabéns ao vencedor. Eu vou continuar trabalhando para estar lá em cima.'])}
    tr = set((c.get('numeros') or {}).get('tracos') or [])
    n = c.get('n') or 1
    if 'vaidoso' in tr:
        fr = ['Eu sempre soube que esse dia ia chegar. Trabalhei a vida inteira para isso.' if n < 2 else
              f'{n} vezes o melhor do mundo. E eu ainda quero mais: quero passar todo mundo da história.',
              'Quem duvidou agora vai ter que engolir. Melhor do mundo!' if n < 2 else 'Podem continuar duvidando. Eu continuo ganhando.']
    elif 'líder' in tr:
        fr = ['Esse prêmio é do grupo. Sem os meus companheiros, nada disso existe.',
              'Levanto esse troféu, mas quem ganhou foi o vestiário inteiro.']
    else:
        fr = ['Obrigado a Deus, à minha família, aos companheiros e à torcida. Esse prêmio é de todos nós.',
              'Ainda estou sem palavras. Agora quero ganhar títulos coletivos, que é o que importa.']
        if n >= 2:
            fr.append(f'Ganhar uma vez é um sonho. Ser {vezes_txt(n)} é uma responsabilidade.')
    return {'quem': a['nome'], 'papel': f'{c["premio"]} {c["ano"]}', 'texto': rnd.choice(fr)}


# ---------------------------------------------------------------- matérias (três vozes)
VOZES = {
    'mesa_tatica': ('Mesa Tática', 'programa de análise de canal de esportes (estilo ESPN): frio, técnico, números da '
                    'votação e da temporada, comparação com a história; nada de torcida'),
    'plantao': ('Plantão do Esporte', 'noticiário esportivo de TV aberta (estilo SporTV): a noite da cerimônia, emoção '
                'contida, contexto do clube e da temporada, frases de efeito moderadas'),
    'resenha': ('Resenha Raiz', 'canal jovem de futebol na internet (estilo CazéTV): linguagem solta, gírias leves, humor e '
                'zoeira com os rivais, emojis com moderação, mas com os números certos'),
}


def materias(cer, ck, hoje):
    import clube
    a, nu, n = cer['vencedor'], cer.get('numeros') or {}, cer.get('n') or 1
    vz = vezes_txt(n)
    podio = '; '.join(f'{x["pos"]}º {x["nome"]} ({x["clube"]}), {x["votos"]} votos' for x in cer['top'])
    hist = (f'{n}ª Bola de Ouro ({", ".join(map(str, cer["anos"]))})' + (f', {cer["seguidas"]} seguidas' if cer['seguidas'] >= 2 else '')) \
        if cer['cat'] == 'mundo' and n >= 2 else 'primeiro prêmio do tipo na carreira'
    lendas = ' '.join((f'Iguala {nm}, dono de {fr}.' if t == 'igual' else f'Mira {nm}: {fr}.' if t == 'alvo' else f'Já supera {nm}, que tem {fr}.')
                      for t, nm, fr in cer.get('lendas') or [])
    num = (f'{nu["gols"]} gols e {nu["assist"]} assistências em {nu["jogos"]} jogos, nota média {str(nu["nota"]).replace(".", ",")}'
           if nu.get('jogos') else None)
    corpos = {
        'mesa_tatica': ([f'{a["nome"]} ({a["clube"]}) venceu {cer["frase"]} {cer["ano"]} com {a["votos"]} votos, '
                         f'{cer["pct"]}% dos votos do pódio' + (f' e {cer["dif"]} de vantagem sobre o segundo.' if cer.get('dif') else '.'),
                         f'Pódio: {podio}.', f'Na história: {hist}. {lendas}'.strip()]
                        + ([f'Os números da temporada que sustentam o voto: {num}.'] if num else [])
                        + ([f'Dado raro: os três primeiros jogam no {clube.C.get("curto") or a["clube"]}.'] if cer['podio_nosso'] else [])),
        'plantao': ([f'Na noite de gala do futebol mundial, {a["nome"]} subiu ao palco para receber {cer["frase"]} {cer["ano"]}.',
                     (f'Agora é {vz}: {hist}.' if vz else 'É o primeiro prêmio do tipo na carreira.')
                     + (f' Aos {nu["idade"]} anos, o {POS_TXT.get(nu.get("pos"), "jogador")} vive o auge.' if nu.get('idade') else ''),
                     f'O pódio: {podio}.']
                    + ([f'Para a torcida, uma noite histórica: o pódio inteiro veste a camisa do {clube.C.get("curto") or a["clube"]}.']
                       if cer['podio_nosso'] else [])
                    + ([f'A temporada justifica: {num}.'] if num else [])),
        'resenha': ([f'Pode parar tudo: {a["nome"].upper()} É O MELHOR DO MUNDO' + (f' DE NOVO, {vz.upper()}' if vz else '') + '! 🏆',
                     f'Foram {a["votos"]} votos' + (f', {cer["dif"]} a mais que o {cer["top"][1]["nome"]}' if cer.get('dif') else '')
                     + '. Não teve conversa.']
                    + (['Pódio 100% da casa. Os rivais assistindo a cerimônia de casa, de pijama. 😂'] if cer['podio_nosso'] else [])
                    + ([f'E o cara ainda tem {num} só nesta temporada. Que fase!'] if num else [])
                    + ([lendas] if lendas else [])),
    }
    titulos = {
        'mesa_tatica': (f'{cer["premio"]} {cer["ano"]}: a apuração de {a["nome"]} em números', f'{a["votos"]} votos · {cer["pct"]}% do pódio'),
        'plantao': (f'{a["nome"]} conquista {cer["frase"]} {cer["ano"]}' + (f' e vira {vz}' if vz else ''), 'A noite da cerimônia e o caminho até o prêmio'),
        'resenha': (f'{a["nome"]} {vz or "melhor do mundo"}! 🏆' if cer['nosso_venceu'] else f'Deu {a["nome"]} na Bola de Ouro', 'A resenha da noite mais esperada do ano'),
    }
    out = []
    for v, (nome_v, estilo) in VOZES.items():
        t, fina = titulos[v]
        out.append({'chave': f'premio|{ck}|{cer["cat"]}|{cer["ano"]}|{v}', 'frente': 'pos_jogo', 'data': tuple(hoje),
                    'titulo': clube.concordar(t), 'linha_fina': clube.concordar(fina), 'autor': nome_v, 'estilo': estilo,
                    'corpo': clube.concordar_tudo([x for x in corpos[v] if x]), 'dados': {'premio': cer['cat'], 'ano': cer['ano'], 'veiculo': v}})
    return out


# ---------------------------------------------------------------- celular
def celular(cer, r, car, hoje):
    import celular as CEL
    if cer['cat'] != 'mundo' or not cer['nossos']:
        return []
    tec = r.get('tecnico') or 'professor'
    a, n = cer['vencedor'], cer.get('n') or 1
    out = []
    if cer['nosso_venceu']:
        k = _kc(a['k'])
        out.append(CEL._caso(f'cel|premio|{cer["ano"]}|{k}', hoje, a['nome'], f'jogador|{a["nome"]}', '🏆',
                             [f'{tec}!!! Acabei de descer do palco. {cer["premio"]} {cer["ano"]}' + (f', {vezes_txt(n)}!' if n >= 2 else '!'),
                              'Queria te agradecer primeiro. Você confiou em mim e me deu liberdade em campo.',
                              'Esse troféu também é seu. 🙏'],
                             f'{a["nome"]} agradece pel{cer["frase"]}', [k], [a['nome']], [
            {'texto': 'Você mereceu cada voto. Agora é transformar isso em títulos com o grupo.',
             'efeitos': [CEL.E(k, 3, 2, 'o técnico o parabenizou e já falou em títulos')],
             'eco': (f'{a["nome"]} revela mensagem do técnico: "agora é título"', 'O premiado mostrou a conversa aos amigos.')},
            {'texto': 'Parabéns, craque! Comemora hoje, porque amanhã tem treino. Pés no chão.',
             'efeitos': [CEL.E(k, -1 if 'vaidoso' in ((cer.get('numeros') or {}).get('tracos') or []) else 1, 2, 'o técnico pediu pés no chão no dia do prêmio')],
             'eco': ('Técnico pede "pés no chão" ao melhor do mundo', 'Cobrança até na noite de gala.')},
            {'texto': 'O prêmio é seu, mas a homenagem é do grupo. Dedica a eles no próximo treino.',
             'efeitos': [CEL.E(k, 0, 1, 'o técnico pediu que dividisse o prêmio com o grupo'), CEL.E('*', 2, 2, 'o melhor do mundo dedicou o prêmio ao grupo')],
             'eco': (f'{a["nome"]} dedica o prêmio ao elenco', 'Gesto que fortalece o vestiário.')},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [CEL.E(k, -3, 2, 'o técnico nem respondeu no dia do prêmio')], 'eco': None}]))
    for x in cer['top'][1:]:
        j = next((j for j in r['J'] if list(j['k']) == x['k']), None) if x['nosso'] else None
        if not j or not cer['nosso_venceu'] or 'vaidoso' not in (((j.get('perfil') or {}).get('tracos')) or []):
            continue
        k = _kc(x['k'])
        out.append(CEL._caso(f'cel|premio|{cer["ano"]}|{k}', hoje, x['nome'], f'jogador|{x["nome"]}', '😤',
                             [f'{tec}, parabéns ao {a["nome"]}, de verdade.',
                              f'Mas {x["votos"]} votos e {x["pos"]}º lugar... eu fiz uma temporada de melhor do mundo também.',
                              'Às vezes acho que aqui ninguém me vê.'],
                             f'{x["nome"]} se sente esquecido na Bola de Ouro', [k], [x['nome']], [
            {'texto': 'Eu vejo. Você foi gigante e o pódio prova isso. Ano que vem é a sua vez.',
             'efeitos': [CEL.E(k, 4, 2, 'o técnico disse que o próximo prêmio é dele')], 'eco': None},
            {'texto': 'Prêmio individual é consequência. Foca no time que o resto vem.',
             'efeitos': [CEL.E(k, -1, 2, 'o técnico minimizou a frustração dele')], 'eco': None},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [CEL.E(k, -4, 2, 'o técnico ignorou a frustração dele')],
             'eco': (f'{x["nome"]} incomodado com o segundo plano', 'Bastidores agitados depois da premiação.')}]))
        break
    return out


# ---------------------------------------------------------------- redes (redes_vivas chama)
MODELOS_REDES = [
    ('premio_nosso', '{torc}', '{premiado_up} MELHOR DO MUNDO!!! 🏆🏆🏆 NÃO TEM DISCUSSÃO!', 'pos'),
    ('premio_nosso', '{torc}', 'Chorei vendo o {premiado} subir no palco. Que orgulho desse cara! 😭❤️', 'pos'),
    ('premio_nosso', '@numerosdabola', '{premio} {premio_ano}: {premiado} com {votos1} votos ({pct}% do pódio). {dif} votos a mais que o {segundo}. 📊', 'num'),
    ('premio_nosso', '@antigoat_fc', 'Bola de Ouro do {premiado}? Comprada. Votação marcada. Pronto, falei. 🙄', 'hate'),
    ('premio_nosso', '@secadorprofissional', 'O {premiado} ganha tudo e eu sigo sem entender o que ele joga 😤', 'hate'),
    ('premio_nosso', '@memesdabola', 'O {premiado} chegando no treino amanhã com a Bola de Ouro debaixo do braço: 🚶‍♂️🏆', 'meme'),
    ('premio_nosso', '@tiozao_do_futebol', 'No meu tempo melhor do mundo tinha que ganhar Copa. Mas esse {premiado} joga muita bola, tenho que admitir.', 'neu'),
    ('premio_nosso', '@futebol_raiz', 'Prêmio individual coroando um coletivo forte. O {nos} merece parte desse troféu.', 'pos'),
    ('premio_nosso', '@zoeira_fc', 'Torcedor rival assistindo a cerimônia da Bola de Ouro hoje: 😐📺', 'meme'),
    ('premio_nosso', '@resenhaFC_', 'Quem foi o melhor do mundo pra você: {premiado}, {segundo} ou {terceiro}? 👇', 'neu'),
    ('premio_bi', '{torc}', '{vezes_up}!!! O {premiado} é {vezes} do mundo e ainda tem gente que duvida 🏆x{n_bolas}', 'pos'),
    ('premio_bi', '@numerosdabola', '{premiado} chega a {n_bolas} Bolas de Ouro ({anos_bolas}). {lenda_txt} 📈', 'num'),
    ('premio_bi', '@antigoat_fc', '{n_bolas} Bolas de Ouro e zero Copa do Mundo. Só lembrando. 🤷', 'hate'),
    ('premio_bi', '@memesdabola', 'A estante da casa do {premiado} depois da {n_bolas}ª Bola de Ouro: 🏆🏆📚😅', 'meme'),
    ('podio_nosso', '{torc}', 'PÓDIO TODO NOSSO: {premiado}, {segundo} e {terceiro}. Os outros clubes que lutem 😂🔴', 'pos'),
    ('podio_nosso', '@numerosdabola', 'Pódio da Bola de Ouro {premio_ano} 100% {nos}: {premiado} ({votos1}), {segundo} ({votos2}) e {terceiro} ({votos3}).', 'num'),
    ('podio_nosso', '@{rival_premio_slug}_raiz', 'Pódio todo do {nos} kkkk acabou a graça do prêmio. Muda o nome pra Taça {nos} 🙄', 'riv'),
    ('podio_nosso', '@zoeira_fc', 'Os outros 600 clubes do mundo na cerimônia da Bola de Ouro: 👏👏 (só aplaudindo)', 'meme'),
    ('premio_vice', '{torc}', '{vice_nosso} merecia mais. {vice_votos} votos é muito pouco pro que ele jogou. Injustiça! 😤', 'neg'),
    ('premio_vice', '@secadorprofissional', '{vice_nosso} em {vice_pos}º kkkk nem com o time todo jogando pra ele 😂', 'hate'),
    ('premio_vice', '@futebol_raiz', 'Ficar no pódio do mundo jogando no {nos} já diz muito sobre o {vice_nosso}.', 'pos'),
    ('premio_outro', '{torc}', 'Bola de Ouro pro {premiado}? Tá. Mas a gente sabe quem jogou mais 😒', 'neg'),
    ('premio_outro', '@numerosdabola', '{premio} {premio_ano}: {premiado} ({premiado_clube}), {votos1} votos. 📊', 'num'),
]
PESO_REDES = {'premio_nosso': 6.0, 'premio_bi': 5.2, 'podio_nosso': 4.8, 'premio_vice': 3.6, 'premio_outro': 2.6}
RESP_REDES = {'premio_nosso': ['MELHOR DO MUNDO 🏆', 'Merecido demais', 'Que orgulho ❤️', 'Chora, hater 😂', 'Respeita o melhor do mundo!',
                               'Ano que vem tem mais'],
              'premio_bi': ['Lenda viva', 'Já é o maior da história do clube?', 'Ninguém segura', 'Vai buscar o Messi 👀'],
              'podio_nosso': ['Monopólio 😂', 'Timaço', 'O mundo é nosso', 'Isso nunca aconteceu, guarda o print 📸']}


def redes_contexto(M, c, cats):
    """Campos e categorias do feed (redes_vivas.contexto). M['premiacao'] = car['premiacao_ultima']."""
    cer = M.get('premiacao') or {}
    if not cer or cer.get('cat') != 'mundo' or not 0 <= _d(M['hoje'], cer['data']) <= JANELA_REDES:
        return
    import redes_vivas as RV
    a, top = cer['vencedor'], cer['top']
    c.update(premiado=a['nome'], premiado_up=a['nome'].upper(), premiado_clube=a['clube'], premio=cer['premio'],
             premio_ano=cer['ano'], votos1=a['votos'], pct=cer['pct'], premiado_slug=RV._slug(a['nome']))
    if len(top) >= 2:
        c.update(segundo=top[1]['nome'], votos2=top[1]['votos'], dif=cer.get('dif') or 0)
    if len(top) >= 3:
        c.update(terceiro=top[2]['nome'], votos3=top[2]['votos'])
    if cer['nosso_venceu']:
        cats.add('premio_nosso')
        n = cer.get('n') or 1
        if n >= 2:
            lenda = next((f'Igualou {nm}.' if t == 'igual' else f'Próximo alvo: {nm}.' for t, nm, _ in cer.get('lendas') or []
                          if t in ('igual', 'alvo')), '')
            c.update(n_bolas=n, vezes=vezes_txt(n), vezes_up=vezes_txt(n).upper(), anos_bolas=', '.join(map(str, cer['anos'])), lenda_txt=lenda)
            cats.add('premio_bi')
        if cer['podio_nosso'] and len(top) >= 3:
            cats.add('podio_nosso')
            # o "rival" que reclama: o clube mais votado entre os de fora (se não houver, um perfil genérico)
            c['rival_premio_slug'] = 'futebolrival'
    else:
        cats.add('premio_outro')
    vice = next((x for x in top[1:] if x['nosso']), None)
    if vice and not cer['podio_nosso']:
        c.update(vice_nosso=vice['nome'], vice_votos=vice['votos'], vice_pos=vice['pos'])
        cats.add('premio_vice')


def redes_especiais(M, c, cats, rnd):
    """Conta oficial, o post do premiado e o abraço do companheiro de pódio (redes_vivas.especiais)."""
    cer = M.get('premiacao') or {}
    if 'premio_nosso' not in cats or not cer or _d(M['hoje'], cer['data']) > 4:
        return []
    import redes_vivas as RV
    of = f'@{c["sigla"]}_oficial'
    a, n = cer['vencedor'], cer.get('n') or 1
    out = [{'autor': of, 'verificado': True, 'tipo': 'oficial', 'pauta': 'redes|premio', 'tom': 'pos',
            'texto': f'🏆 O MELHOR DO MUNDO É NOSSO! {a["nome"]} conquista {cer["frase"]} {cer["ano"]}'
                     + (f' — {vezes_txt(n)}!' if n >= 2 else '!') + (' E o pódio é todo da casa. ❤️' if cer['podio_nosso'] else ' ❤️')},
           {'autor': RV._handle(a['nome']), 'nome_exibicao': a['nome'], 'verificado': True, 'tipo': 'jogador', 'pauta': 'redes|premio', 'tom': 'pos',
            'texto': rnd.choice(['Obrigado, meu Deus! 🙏🏆 Esse prêmio é de cada companheiro, de cada torcedor. Isso é só o começo.',
                                 'Sem palavras. Obrigado a todos que sonharam comigo. ❤️🏆',
                                 f'{vezes_txt(n).capitalize() + "!" if n >= 2 else "Melhor do mundo!"} Mas o que eu quero mesmo é levantar taça com vocês. 🏆⚽'])}]
    for x in cer['top'][1:]:
        if x['nosso']:
            out.append({'autor': RV._handle(x['nome']), 'nome_exibicao': x['nome'], 'verificado': True, 'tipo': 'jogador',
                        'pauta': 'redes|premio', 'tom': 'pos', 'texto': rnd.choice(
                            [f'Parabéns, irmão! Merecido demais 🏆👏 Orgulho de dividir o vestiário com o melhor do mundo.',
                             f'Pódio em família ❤️ Parabéns, {a["nome"]}! Ano que vem a gente briga de novo 😂🏆'])})
            break
    return out


def redes_em_alta(M, c, cats):
    """Hashtags do prêmio para o 'Em alta' (peso alto nos primeiros dias)."""
    if 'premio_nosso' in cats or 'premio_outro' in cats:
        nome = ''.join(w.capitalize() for w in c.get('premiado', '').split())
        out = [(f'#{nome}MelhorDoMundo', 4.0 if 'premio_nosso' in cats else 1.8), ('#BolaDeOuro', 3.4)]
        if 'premio_bi' in cats:
            out.append((f'#{c["vezes"].capitalize()}', 2.6))
        if 'podio_nosso' in cats:
            out.append(('#PódioÉNosso', 2.2))
        return out
    return []
