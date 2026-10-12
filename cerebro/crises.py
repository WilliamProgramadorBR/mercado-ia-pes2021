"""Banco de CRISES do vestiário + IMAGEM do clube + ameaça do PATROCINADOR (11/10/2026).

Cada cenário tem uma CONDIÇÃO (momento real do clube: resultados, moral, status, tempo do técnico, súmula do último
jogo, contrato, patrocínio...) e um peso. A frequência sobe com a dificuldade (dificuldade.M['m']): técnico novo e
espírito de equipe baixo = mais crises. As opções mexem em moral (histórias), orçamento (custo/multa, ao vivo),
compromissos cobrados pela súmula e na IMAGEM do clube (0-100, car['patrocinio']['imagem']).
Imagem baixa + contrato de patrocínio = o patrocinador ameaça romper; resposta ruim = rescisão (o aporte anual sai da
verba de salários, ao vivo no jogo).
"""
from vestiario import dias

ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')
SALARIO_X = 430


def chave(k):
    return f'{k[0]}:{k[1]}'


def _mi(v):
    return f'R$ {abs(v) / 1e6:.1f} mi'.replace('.', ',')


def _todos(d, rod, motivo):
    return [{'k': '*', 'delta': d, 'rodadas': rod, 'motivo': motivo}]


def _afasta(k, nome, jogos=1):
    return {'k': k, 'nome': nome, 'tipo': 'afastamento', 'jogos': jogos,
            'ok': {'efeitos': _todos(1, 1, 'o técnico manteve a palavra'), 'noticia': f'{nome} cumpriu o afastamento.'},
            'quebra': {'efeitos': _todos(-3, 3, 'dois pesos, duas medidas: o afastado jogou'),
                       'noticia': f'{nome} estava afastado e jogou. O vestiário não perdoou.'}}


def _caso(hoje, sub, envolvidos, nomes, titulo, relato, opcoes, gravidade='média'):
    return {'id': f'crise|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}|{sub}|{envolvidos[0] if envolvidos else "clube"}',
            'tipo': 'crise', 'sub': sub, 'data': list(hoje), 'gravidade': gravidade, 'envolvidos': envolvidos,
            'nomes': nomes, 'titulo': titulo, 'relato': relato,
            'opcoes': [{'id': str(i + 1), **o} for i, o in enumerate(opcoes)]}


# ------------------------------------------------------------------ cenários
def _audio(ctx, rnd):
    js = [j for j in ctx['J'] if j['moral'] < 48 and j['status'] in ALTO]
    if not js:
        return None
    j = rnd.choice(js)
    k, n = chave(j['k']), j['nome']
    multa = round(j['salario'] * SALARIO_X / 12 * 0.3 / 1000) * 1000
    return 5 + (2 if ctx['novo'] else 0), lambda: _caso(ctx['hoje'], 'audio', [k], [n], f'Áudio vazado: {n} detona o técnico',
        rnd.choice([f'Um áudio de {n} num grupo de mensagens vazou: "esse treinador não sabe o que faz, a gente joga apesar dele". '
                    'O conteúdo já circula nas redes.',
                    f'Um programa de TV divulgou um áudio em que {n} reclama da comissão técnica e das escolhas do treinador.']), [
            {'texto': f'Multa pesada (30% do salário: {_mi(multa)}) e pedido de desculpas ao grupo',
             'efeitos': [{'k': k, 'delta': -8, 'rodadas': 3, 'motivo': 'foi multado pelo áudio vazado'}] + _todos(1, 1, 'o técnico impôs autoridade'),
             'multa': {k: multa}, 'imagem': 3, 'eco': (f'{n} multado pelo áudio vazado', 'O técnico cortou o assunto pela raiz.')},
            {'texto': 'Conversa a portas fechadas, sem punição pública',
             'efeitos': [{'k': k, 'delta': 3, 'rodadas': 2, 'motivo': 'o técnico preferiu conversar'}] + _todos(-2 if ctx['novo'] else -1, 2, 'o grupo achou o técnico fraco diante do áudio'),
             'imagem': -3, 'eco': ('Técnico abafa o caso do áudio', 'Para parte do elenco, faltou pulso.')},
            {'texto': 'Afastar por 2 jogos', 'compromisso_lista': [_afasta(k, n, 2)],
             'efeitos': [{'k': k, 'delta': -10, 'rodadas': 4, 'motivo': 'foi afastado pelo áudio vazado'}] + _todos(2, 1, 'o técnico mostrou quem manda'),
             'imagem': 4, 'eco': (f'{n} afastado', 'Medida dura após o áudio vazado.')},
            {'texto': 'Fingir que não ouviu',
             'efeitos': _todos(-4, 3, 'o técnico se omitiu no caso do áudio'), 'imagem': -8,
             'eco': ('Silêncio do técnico após áudio vazado', 'A omissão virou piada nas redes.')},
        ], 'grave')


def _motim(ctx, rnd):
    vets = [j for j in ctx['J'] if j['idade'] >= 30 and j['status'] in ALTO]
    if not ctx['novo'] or len(vets) < 2:
        return None
    vs = rnd.sample(vets, min(3, len(vets)))
    ks, ns = [chave(j['k']) for j in vs], [j['nome'] for j in vs]
    lista = ', '.join(ns)
    return 4, lambda: _caso(ctx['hoje'], 'motim', ks, ns, 'Veteranos pedem reunião com a diretoria',
        f'{lista} procuraram a diretoria para reclamar dos métodos do novo técnico: "treino pesado demais, pouca conversa". '
        'O presidente quer saber como você vai lidar com isso.', [
            {'texto': 'Ceder: semana de treinos leves e conversa individual com cada veterano',
             'efeitos': [{'k': k, 'delta': 4, 'rodadas': 3, 'motivo': 'o técnico ouviu os veteranos'} for k in ks] + _todos(-1, 1, 'os mais jovens viram privilégio aos veteranos'),
             'carreira': {k: {'cond_delta': 8} for k in ks}, 'imagem': 0,
             'eco': ('Técnico recua e ouve os veteranos', 'Gesto de diálogo ou sinal de fraqueza?')},
            {'texto': 'Bater o pé: "aqui quem decide sou eu"',
             'efeitos': [{'k': k, 'delta': -6, 'rodadas': 4, 'motivo': 'o técnico enfrentou os veteranos'} for k in ks] + _todos(2 if ctx['espirito'] >= 70 else -2, 2, 'o grupo reagiu à queda de braço com os veteranos'),
             'imagem': -2, 'eco': ('Queda de braço no vestiário', 'O técnico peitou os medalhões.')},
            {'texto': 'Meio-termo: ajustar a carga, mas manter o método',
             'efeitos': [{'k': k, 'delta': 1, 'rodadas': 2, 'motivo': 'o técnico ajustou parte do método'} for k in ks],
             'eco': ('Técnico ajusta treinos', 'Solução intermediária acalma, por ora.')},
        ])


def _protesto(ctx, rnd):
    if ctx['derrotas'] < 2:
        return None
    custo = 800_000
    return 3 + ctx['derrotas'], lambda: _caso(ctx['hoje'], 'protesto', [], [], 'Torcida organizada protesta no CT',
        rnd.choice(['Cerca de 300 torcedores foram ao CT com faixas e cobraram o elenco na saída do treino.',
                    'Torcedores picharam o muro do CT e exigem uma conversa com o técnico e os líderes do elenco.']), [
            {'texto': 'Receber uma comissão da torcida com o capitão',
             'efeitos': _todos(1, 1, 'o técnico enfrentou a crise de frente com a torcida'), 'imagem': 4,
             'eco': ('Técnico recebe a torcida', 'Conversa franca no CT baixa a temperatura.')},
            {'texto': f'Reforçar a segurança e fechar os treinos (custo {_mi(custo)})',
             'efeitos': _todos(1, 1, 'o elenco se sentiu protegido'), 'orcamento': -custo, 'imagem': -2,
             'eco': ('CT vira bunker', 'Clube fecha os portões e reforça a segurança.')},
            {'texto': 'Declarar que pressão de torcida não muda nada',
             'efeitos': _todos(2, 1, 'o técnico blindou o grupo'), 'imagem': -6,
             'eco': ('"Pressão não muda nada"', 'Frase do técnico irrita ainda mais a arquibancada.')},
        ], 'leve')


def _empresario(ctx, rnd):
    js = [j for j in ctx['J'] if j['status'] in ALTO and (j['moral'] < 55 or (j.get('contrato') and
          (j['contrato'][0] * 12 + j['contrato'][1]) - (ctx['hoje'][0] * 12 + ctx['hoje'][1]) <= 12))]
    if not js:
        return None
    j = rnd.choice(js)
    k, n = chave(j['k']), j['nome']
    rival = rnd.choice(ctx['rivais']) if ctx['rivais'] else 'um clube rival'
    return 3, lambda: _caso(ctx['hoje'], 'empresario', [k], [n], f'Empresário de {n} abre conversa com o {rival}',
        f'O empresário de {n} confirmou à imprensa que ouviu uma proposta do {rival}. "Meu cliente quer ser valorizado."', [
            {'texto': 'Ligar para o jogador e reforçar que ele é peça-chave do projeto',
             'efeitos': [{'k': k, 'delta': 6, 'rodadas': 3, 'motivo': 'o técnico o tratou como peça-chave'}],
             'eco': (f'Técnico segura {n}', 'Telefonema acalmou o jogador.')},
            {'texto': '"Ele tem contrato. Quem quiser sair, que se apresente à diretoria."',
             'efeitos': [{'k': k, 'delta': -6, 'rodadas': 3, 'motivo': 'o técnico o desafiou publicamente'}] + _todos(1, 1, 'o grupo viu firmeza'),
             'imagem': -1, 'eco': (f'Técnico desafia {n}', 'Resposta dura ao empresário.')},
            {'texto': 'Deixar a diretoria resolver',
             'efeitos': [{'k': k, 'delta': -2, 'rodadas': 2, 'motivo': 'o técnico lavou as mãos'}],
             'eco': (f'Futuro de {n} nas mãos da diretoria', 'O técnico preferiu não se envolver.')},
        ], 'leve')


def _festa(ctx, rnd):
    if ctx['ultimo'] != 'D':
        return None
    js = [j for j in ctx['J'] if j['idade'] <= 27]
    if not js:
        return None
    j = rnd.choice(js)
    k, n = chave(j['k']), j['nome']
    multa = round(j['salario'] * SALARIO_X / 12 * 0.2 / 1000) * 1000
    return 4, lambda: _caso(ctx['hoje'], 'festa', [k], [n], f'{n} vai a festa após derrota',
        f'Horas depois da derrota, {n} apareceu em vídeos numa festa. A torcida ficou revoltada.', [
            {'texto': f'Multa de 20% do salário ({_mi(multa)})', 'multa': {k: multa}, 'imagem': 3,
             'efeitos': [{'k': k, 'delta': -5, 'rodadas': 2, 'motivo': 'foi multado pela festa após a derrota'}] + _todos(1, 1, 'o grupo aprovou a punição'),
             'eco': (f'{n} multado', 'Festa após derrota sai caro.')},
            {'texto': 'Afastar por 1 jogo', 'compromisso_lista': [_afasta(k, n, 1)], 'imagem': 4,
             'efeitos': [{'k': k, 'delta': -7, 'rodadas': 3, 'motivo': 'foi afastado pela festa após a derrota'}],
             'eco': (f'{n} afastado', 'Técnico não perdoa a festa.')},
            {'texto': 'Ele é jovem, merece outra chance',
             'efeitos': [{'k': k, 'delta': 3, 'rodadas': 2, 'motivo': 'o técnico o perdoou'}] + _todos(-2, 2, 'o grupo viu leniência'),
             'imagem': -6, 'eco': ('Técnico passa a mão', f'{n} sai impune da festa após a derrota.')},
        ])


def _substituicao(ctx, rnd):
    p = ctx['ultimo_jogo']
    if not p:
        return None
    linhas = p['linhas1'] if p['time1'] == ctx['ti'] else p['linhas2']
    porK = {j['k']: j for j in ctx['J']}
    sai = [porK[(x['reg'], x['pid'])] for x in linhas if x['titular'] and 40 <= x['minutos'] <= 75
           and (x['reg'], x['pid']) in porK and porK[(x['reg'], x['pid'])]['status'] in ALTO]
    if not sai:
        return None
    j = rnd.choice(sai)
    k, n = chave(j['k']), j['nome']
    return 5, lambda: _caso(ctx['hoje'], 'substituicao', [k], [n], f'{n} sai irritado ao ser substituído',
        rnd.choice([f'No último jogo, {n} foi substituído, chutou uma garrafa e passou direto pelo técnico sem cumprimentá-lo.',
                    f'Ao deixar o campo no último jogo, {n} gesticulou para o banco e reclamou da substituição.']), [
            {'texto': 'Explicar publicamente que foi decisão tática',
             'efeitos': [{'k': k, 'delta': 2, 'rodadas': 2, 'motivo': 'o técnico explicou a substituição'}],
             'eco': ('"Foi decisão tática"', 'Técnico minimiza o gesto.')},
            {'texto': 'Cobrar respeito na frente do grupo',
             'efeitos': [{'k': k, 'delta': -5, 'rodadas': 3, 'motivo': 'foi cobrado na frente do grupo'}] + _todos(1, 1, 'o técnico impôs respeito'),
             'imagem': 1, 'eco': (f'Técnico enquadra {n}', 'Cobrança diante do elenco.')},
            {'texto': 'Ignorar',
             'efeitos': _todos(-1, 1, 'o grupo viu o gesto ficar sem resposta'), 'imagem': -2,
             'eco': (f'Gesto de {n} fica sem resposta', 'O técnico preferiu não comentar.')},
        ], 'leve')


def _adiantamento(ctx, rnd):
    js = [j for j in ctx['J'] if j['idade'] <= 26 and j['status'] not in ALTO]
    if not js:
        return None
    j = rnd.choice(js)
    k, n = chave(j['k']), j['nome']
    valor = max(300_000, round(j['salario'] * SALARIO_X / 12 * 2 / 100_000) * 100_000)
    return 2, lambda: _caso(ctx['hoje'], 'adiantamento', [k], [n], f'{n} pede adiantamento salarial',
        f'{n} procurou o clube: precisa de dois salários adiantados ({_mi(valor)}) para resolver um problema da família.', [
            {'texto': f'Liberar o adiantamento ({_mi(valor)} do orçamento)', 'orcamento': -valor,
             'efeitos': [{'k': k, 'delta': 6, 'rodadas': 4, 'motivo': 'o clube o ajudou com o adiantamento'}],
             'eco': ('Clube ajuda jogador', f'{n} recebe adiantamento.')},
            {'texto': 'Negar: política do clube',
             'efeitos': [{'k': k, 'delta': -4, 'rodadas': 3, 'motivo': 'o clube negou o adiantamento'}],
             'eco': ('Pedido negado', f'O clube não abriu exceção para {n}.')},
        ], 'leve')


def _vazamento(ctx, rnd):
    pj = ctx['proximo']
    if not pj or pj.get('parcial') or pj['competicao'] not in ('UEFA Champions League', 'Libertadores'):
        return None
    custo = 300_000
    return 3, lambda: _caso(ctx['hoje'], 'vazamento', [], [], f'Escalação vaza antes do jogo contra o {pj["adversario"]}',
        'A provável escalação para o jogo grande apareceu num site antes da coletiva. Alguém de dentro passou a informação.', [
            {'texto': 'Caçar o informante e punir quem vazou',
             'efeitos': _todos(-3, 2, 'o clima de desconfiança tomou o vestiário'), 'imagem': 2,
             'eco': ('Caça ao "X9"', 'Técnico promete descobrir quem vazou.')},
            {'texto': f'Fechar todos os treinos até o jogo (custo {_mi(custo)})', 'orcamento': -custo,
             'efeitos': _todos(1, 1, 'o elenco se fechou para o jogo grande'),
             'eco': ('Treinos fechados', 'Ninguém entra no CT até o jogo.')},
            {'texto': 'Ignorar e mudar a escalação na última hora',
             'efeitos': _todos(-1, 1, 'mudanças de última hora confundiram o grupo'),
             'eco': ('Mistério na escalação', 'O técnico deve surpreender.')},
        ], 'leve')


def _rede_patrocinador(ctx, rnd):
    if not ctx['contrato']:
        return None
    j = rnd.choice(ctx['J'])
    k, n = chave(j['k']), j['nome']
    marca = ctx['contrato']['marca']
    return 2, lambda: _caso(ctx['hoje'], 'patrocinador_rival', [k], [n], f'{n} faz propaganda da concorrente da {marca}',
        f'{n} publicou um vídeo patrocinado por uma concorrente direta da {marca}, patrocinadora master do clube.', [
            {'texto': 'Exigir que ele apague e multar', 'multa': {k: 200_000}, 'imagem': 4,
             'efeitos': [{'k': k, 'delta': -4, 'rodadas': 2, 'motivo': 'foi multado pela propaganda da concorrente'}],
             'eco': ('Clube enquadra jogador', f'A {marca} agradeceu a resposta rápida.')},
            {'texto': 'Pedir que apague, sem multa', 'imagem': 1,
             'efeitos': [{'k': k, 'delta': -1, 'rodadas': 1, 'motivo': 'teve de apagar a propaganda'}],
             'eco': ('Vídeo apagado', 'Caso encerrado sem punição.')},
            {'texto': 'É a vida pessoal dele', 'imagem': -9,
             'efeitos': [{'k': k, 'delta': 2, 'rodadas': 1, 'motivo': 'o técnico o defendeu'}],
             'eco': (f'A {marca} reclama do clube', 'A patrocinadora não gostou da omissão.')},
        ], 'leve')


CENARIOS = [_audio, _motim, _protesto, _empresario, _festa, _substituicao, _adiantamento, _vazamento, _rede_patrocinador]


# ------------------------------------------------------------------ imagem e patrocinador
def imagem(car):
    pat = car.setdefault('patrocinio', {})
    pat.setdefault('imagem', 60)
    return pat['imagem']


def mexer_imagem(car, delta, motivo, hoje):
    pat = car.setdefault('patrocinio', {})
    pat['imagem'] = max(0, min(100, imagem(car) + delta))
    pat.setdefault('imagem_hist', []).append({'data': list(hoje), 'delta': delta, 'motivo': motivo, 'valor': pat['imagem']})
    pat['imagem_hist'] = pat['imagem_hist'][-20:]


def ameaca_patrocinador(car, hoje):
    """Imagem < 30 com contrato ativo: o patrocinador ameaça romper (1 vez por temporada)."""
    pat = car.get('patrocinio') or {}
    c = pat.get('contrato')
    if not c or imagem(car) >= 30 or pat.get('ameaca_temporada') == c['temporada']:
        return None
    if any(x['tipo'] == 'crise' and x['sub'] == 'ameaca_patrocinador' for x in car.get('casos', [])):
        return None
    pat['ameaca_temporada'] = c['temporada']
    marca = c['marca']
    return _caso(hoje, 'ameaca_patrocinador', [], [], f'A {marca} ameaça romper o patrocínio',
        f'Depois da sequência de polêmicas, a {marca} enviou uma notificação: a imagem do clube (hoje {imagem(car)}/100) '
        f'está prejudicando a marca. Ou o clube reage, ou o contrato de {_mi(c["anual"])} por temporada será rescindido.', [
            {'texto': 'Campanha pública e pedido de desculpas (custo R$ 1,5 mi)', 'orcamento': -1_500_000, 'imagem': 18,
             'efeitos': _todos(-1, 1, 'o grupo foi exposto na campanha de desculpas'),
             'eco': ('Clube pede desculpas publicamente', f'A {marca} aceitou e manteve o contrato.')},
            {'texto': 'Prometer punir os envolvidos nas próximas polêmicas', 'imagem': 10,
             'efeitos': _todos(-2, 2, 'o elenco ficou sob vigilância'),
             'eco': ('Tolerância zero', f'Clube promete à {marca} punições exemplares.')},
            {'texto': 'O clube não aceita chantagem de patrocinador', 'rescindir': True, 'imagem': -5,
             'efeitos': _todos(1, 1, 'o técnico defendeu o grupo contra o patrocinador'),
             'eco': (f'A {marca} rompe com o clube', 'O dinheiro do patrocínio sai da verba de salários.')},
        ], 'grave')


# ------------------------------------------------------------------ geração da rodada
def gerar(r, car, hoje, rnd):
    import dificuldade
    m = dificuldade.M['m']
    pendentes = {k for c in car.get('casos', []) for k in c['envolvidos']}
    hist = car.setdefault('crises_hist', {})
    J = [j for j in r['J'] if chave(j['k']) not in pendentes]
    ult = r.get('ultimos') or []
    tab = (car.get('diretoria') or {}).get('tabela') or []
    meus = [p for p in r.get('jogos') or []]
    ctx = {'J': J, 'hoje': hoje, 'ti': r['ti'], 'novo': (car.get('dificuldade') or {}).get('dias_clube', 999) < 240,
           'espirito': (car.get('dificuldade') or {}).get('espirito', 70),
           'derrotas': sum(1 for g in ult[-4:] if g['pro'] < g['contra']),
           'ultimo': ('V' if ult[-1]['pro'] > ult[-1]['contra'] else 'E' if ult[-1]['pro'] == ult[-1]['contra'] else 'D') if ult else None,
           'ultimo_jogo': meus[-1] if meus else None, 'proximo': car.get('proximo_jogo'),
           'contrato': (car.get('patrocinio') or {}).get('contrato'),
           'rivais': [t['time'] for t in tab[:6] if not t.get('eu')]}
    novos = []
    am = ameaca_patrocinador(car, hoje)
    if am:
        novos.append(am)
    cands = []
    for f in CENARIOS:
        u = hist.get(f.__name__)
        if u and dias(tuple(hoje), tuple(u)) < 60:       # o mesmo tipo de crise só depois de 2 meses
            continue
        x = f(ctx, rnd)
        if x:
            cands.append((x[0], f.__name__, x[1]))
    n_max = 2 if m >= 1.6 else 1
    while cands and len(novos) < n_max + (1 if am else 0) and rnd.random() < dificuldade.chance(0.3, 0.85):
        tot = sum(c[0] for c in cands)
        x = rnd.random() * tot
        for c in cands:
            x -= c[0]
            if x <= 0:
                break
        cands.remove(c)
        caso = c[2]()
        if any(k in pendentes for k in caso['envolvidos']):
            continue
        pendentes |= set(caso['envolvidos'])
        hist[c[1]] = list(hoje)
        novos.append(caso)
    return novos
