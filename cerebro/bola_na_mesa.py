# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""BOLA NA MESA (11/10/2026): mesa-redonda esportiva + rede social + enquetes, gerados a cada reunião.

Banco de 54 PAUTAS. Cada pauta só entra se os dados do save sustentam o assunto (coerência): Bola de Ouro só com
jogadores de elite (nota >= 86, clube entre os 40 mais fortes do mundo, >= 6 jogos pelo clube na temporada);
"zona de rebaixamento" só se o time estiver lá; zoeira de jejum só com atacante que realmente não marca etc.
O programa escolhe 7 pautas (variedade de categorias, sem repetir assunto por 21 dias, exceto o último jogo).

Bancada: Rogério Lemos (apresentador), Carlão Pereira (ex-zagueiro, cobrador), Helena Saraiva (analista, números),
Beto Rocha (setorista, bastidores) e Toninho Marrento (ex-meia, polêmico e zoeiro: puxa sarro de quem vai mal).
As pautas também geram posts da rede social e enquetes. Textos-modelo com condições; o redator com IA reescreve
falas e posts numa chamada só (números que não estavam no texto derrubam a troca).
"""
import collections
import math
import random
import struct

PESSOAS = {
    'rogerio': ('Rogério Lemos', 'apresentador'),
    'carlao': ('Carlão Pereira', 'ex-zagueiro, sem papas na língua'),
    'helena': ('Helena Saraiva', 'analista tática'),
    'beto': ('Beto Rocha', 'setorista do clube'),
    'toninho': ('Toninho Marrento', 'ex-meia, polêmico e zoeiro'),
}
ESTILO_PESSOA = {
    'rogerio': 'apresentador: conduz, provoca o debate, passa a palavra',
    'carlao': 'ex-zagueiro bravo e cobrador, "no meu tempo", exige raça e atitude',
    'helena': 'analista tática calma, fala de números e sistema, rebate exageros',
    'beto': 'setorista que vive no CT, traz bastidores ("apurei", "fontes do clube")',
    'toninho': 'ex-meia polêmico e zoeiro, bordões, puxa sarro de quem vai mal (sem ofensa pessoal), adora uma provocação',
}
ATA = ('CF', 'SS', 'LWF', 'RWF')
DEF = ('CB', 'LB', 'RB')
MEI = ('DMF', 'CMF', 'AMF', 'LMF', 'RMF')
MAX_PAUTAS = 7
COOLDOWN = 21


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def _dias(a, b):
    import datetime as dt
    return (dt.date(*a) - dt.date(*b)).days


def _lista(xs):
    xs = list(xs)
    return ', '.join(xs[:-1]) + ' e ' + xs[-1] if len(xs) > 1 else (xs[0] if xs else '')


def _slug(t):
    import unicodedata
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in t if c.isalnum())[:20]


# ---------------------------------------------------------------- o mundo visto pela mesa
def mundo(car, r, d, snap, ctx=None):
    import imprensa
    ctx = ctx or imprensa._contexto(car, r, d, snap)
    s, P = ctx['s'], ctx['P']
    hoje = tuple(r['hoje'])
    import destaques
    ini = destaques.ini_temporada(hoje)
    todas = r.get('todas_partidas') or []
    n_clubes = s.find_team('ALBÂNIA') or 625   # depois disso vêm as seleções
    clube_de = {}
    for i in range(n_clubes):
        for k in s.squad(i):
            clube_de.setdefault(k, i)
    est = collections.defaultdict(lambda: {'jogos': 0, 'gols': 0, 'assist': 0, 'notas': []})
    selecao = collections.defaultdict(list)   # k -> datas de jogos que não são pelo clube (seleção)
    nacao = collections.defaultdict(collections.Counter)   # k -> seleção por que joga (nacionalidade)
    for p in todas:
        if tuple(p['data']) < ini:
            continue
        for t, linhas in ((p['time1'], p['linhas1']), (p['time2'], p['linhas2'])):
            for x in linhas:
                if x['minutos'] <= 0:
                    continue
                k = (x['reg'], x['pid'])
                if clube_de.get(k) == t:
                    e = est[k]
                    e['jogos'] += 1
                    e['gols'] += x['gols']
                    e['assist'] += x['assist']
                    if x['nota']:
                        e['notas'].append(x['nota'])
                elif t >= n_clubes:
                    selecao[k].append(tuple(p['data']))
                    nacao[k][t] += 1
    import proximo_jogo
    forca = {}
    for i in range(n_clubes):
        try:
            f = proximo_jogo._forca(s, i, P)
        except Exception:  # noqa: BLE001
            f = None
        if f:
            forca[i] = f
    rank = {i: n + 1 for n, i in enumerate(sorted(forca, key=lambda i: -forca[i]))}
    ti, nos = r['ti'], r['time']
    jogos = r.get('jogos') or []
    L = car.get('liga') or {}
    tab = L.get('classificacao') or []
    if tab and all(t['j'] >= 2 * (len(tab) - 1) for t in tab):   # liga encerrada: na pré-temporada a tabela sai de pauta
        oficiais = [tuple(p['data']) for p in (r.get('jogos') or []) if not (100 <= p['comp'] <= 110 or p['comp'] == 56)]
        if not oficiais or _dias(hoje, max(oficiais)) > 10:
            tab = []
    try:
        import imprensa_db as db
        with db.conectar() as c:
            negocios = [dict(x) for x in c.execute('SELECT * FROM negocios WHERE carreira = ? ORDER BY valor DESC', (car.get('ck'),))]
        negocios = [n for n in negocios if n.get('data') and _dias(hoje, tuple(int(v) for v in n['data'].split('-'))) <= 45]
    except Exception:  # noqa: BLE001
        negocios = []
    try:
        socios = struct.unpack_from('<I', d, 0xB629A4)[0]
        socios = socios if 1000 <= socios <= 50_000_000 else None
    except Exception:  # noqa: BLE001
        socios = None
    ult = None
    if jogos:
        p = jogos[-1]
        casa = p['time1'] == ti

        def js(linhas):
            out = []
            for x in linhas:
                f = P.get((x['reg'], x['pid']))
                if f and x['minutos'] > 0:
                    out.append({'k': (x['reg'], x['pid']), 'nome': f.name.strip(), 'pos': f.pos, 'nota': x['nota'],
                                'gols': x['gols'], 'assist': x['assist'], 'min': x['minutos']})
            return out
        a, b = (p['linhas1'], p['linhas2']) if casa else (p['linhas2'], p['linhas1'])
        ult = {'p': p, 'casa': casa, 'adv': s.name(p['time2'] if casa else p['time1']).strip(),
               'gp': p['gols1'] if casa else p['gols2'], 'gc': p['gols2'] if casa else p['gols1'],
               'nos': js(a), 'eles': js(b), 'recente': _dias(hoje, tuple(p['data'])) <= 8}
        from proximo_jogo import nome_comp
        ult['comp'] = nome_comp(p['comp'])
    try:
        esc = imprensa._escalacao(ctx, ti, usuario=True)
    except Exception:  # noqa: BLE001
        esc = None
    perfis, hall, recente, trave = {}, {}, None, []
    try:   # a carreira de cada um (legado.py): Bolas de Ouro, títulos, artilharias
        import legado
        ck = car.get('ck')
        for j in r['J']:
            perfis[j['k']] = legado.perfil(ck, j['k'], j['nome'])
        hall = legado.hall(ck)
        recente = legado.premio_recente(ck, hoje)
        trave = legado.podio_sem_vitoria(ck, 1)
    except Exception as e:  # noqa: BLE001
        print('aviso: legado indisponível para o Bola na Mesa:', e)
    try:
        import apelidos as _ap
        cat_ap = _ap.catalogo()
    except Exception:  # noqa: BLE001
        cat_ap = {}
    selecao_de = {k: s.name(c.most_common(1)[0][0]).strip() for k, c in nacao.items() if c}
    return {'s': s, 'P': P, 'car': car, 'r': r, 'hoje': hoje, 'ini': ini, 'ti': ti, 'nos': nos, 'J': r['J'],
            'jogos': jogos, 'ult': ult, 'tab': tab, 'eu': next((t for t in tab if t.get('eu')), None),
            'liga': L.get('competicao') or 'liga', 'art': L.get('artilheiros') or [], 'res_liga': L.get('resultados') or [],
            'outras': L.get('outras') or [], 'pj': car.get('proximo_jogo') or {}, 'dir': car.get('diretoria') or {},
            'dif': car.get('dificuldade') or {}, 'casos': car.get('casos') or [], 'disc': car.get('disciplina_hist') or [],
            'pat': car.get('patrocinio') or {}, 'socios': socios, 'negocios': negocios, 'est': est, 'selecao': selecao,
            'clube_de': clube_de, 'forca': forca, 'rank': rank, 'n_clubes': n_clubes, 'todas': todas,
            'conflitos': r.get('conflitos') or [], 'lideres': r.get('lideres') or [], 'esc': esc, 'sigla': _slug(nos),
            'perfis': perfis, 'hall': hall, 'premio_recente': recente, 'trave': trave, 'apelido': cat_ap,
            'selecao_de': selecao_de, 'dest': car.get('mundo') or {}, 'hist': car.get('historia') or {}, 'rd': car.get('rodada_destaque') or {}, 'fifa': car.get('data_fifa'), 'rumores': [x for x in car.get('rumores') or [] if x.get('ativo')], 'vit': car.get('vitoriosos') or {}, 'lesao': car.get('lesao_ultima'), 'lesao_volta': car.get('lesao_volta'),
            'momento': car.get('momento'), 'analise': car.get('analise_porques') or [], 'analise_data': car.get('analise_data')}


def _media(e):
    return sum(e['notas']) / len(e['notas']) if e['notas'] else None


def _seq(jogos, ti):
    import imprensa
    return imprensa._sequencia(jogos, ti)


def _res(p, t):
    gp, gc = (p['gols1'], p['gols2']) if p['time1'] == t else (p['gols2'], p['gols1'])
    return 'V' if gp > gc else 'E' if gp == gc else 'D', gp, gc


def _enquete(pergunta, opcoes, rnd):
    """opcoes = [(texto, peso)] -> porcentagens que somam 100, com ruído."""
    pesos = [max(0.05, w * rnd.uniform(0.8, 1.25)) for _, w in opcoes]
    tot = sum(pesos)
    pct = [round(100 * w / tot) for w in pesos]
    pct[pct.index(max(pct))] += 100 - sum(pct)
    return {'pergunta': pergunta, 'opcoes': [{'texto': t, 'pct': x} for (t, _), x in zip(opcoes, pct)]}


# ---------------------------------------------------------------- as pautas
# cada pauta: f(M, rnd) -> None | {'id','cat','peso','titulo','falas':[(quem, texto)], 'enquete', 'posts':[(autor, texto)]}
PAUTAS = []


def pauta(fn):
    PAUTAS.append(fn)
    return fn


def _torc(M):
    return f'@{M["sigla"]}_raiz'


# ----- o último jogo
@pauta
def resultado(M, rnd):
    u = M['ult']
    if not u or u['p']['comp'] in CONTINENTAIS:   # jogo continental: pauta própria (noite_europeia)
        return None
    res = 'V' if u['gp'] > u['gc'] else 'E' if u['gp'] == u['gc'] else 'D'
    pl = f'{u["gp"]} a {u["gc"]}' if u['gp'] >= u['gc'] else f'{u["gc"]} a {u["gp"]}'
    top = max(u['nos'], key=lambda j: (j['nota'] or 5) + 0.6 * j['gols'], default=None)
    if not top:
        return None
    tit = f'{M["nos"]} {u["gp"]} x {u["gc"]} {u["adv"]}'
    import classicos
    c = classicos.nome(M['nos'], u['adv'])
    if c:
        tit = f'{c}: {tit}'
    if res == 'V':
        f = [('rogerio', f'Vamos começar pelo jogo: o {M["nos"]} venceu o {u["adv"]} por {pl}, pela {u["comp"]}. Carlão, convenceu?'),
             ('carlao', rnd.choice([f'Convenceu! Time que joga com vontade assim eu assino embaixo. O {top["nome"]} jogou de terno.',
                                    'Ganhou, mas eu quero ver isso contra time grande. Vitória é obrigação de time desse tamanho.'])),
             ('helena', f'O destaque nos números é o {top["nome"]}, nota {_n(top["nota"])}' + (f', com {top["gols"]} gols' if top['gols'] > 1 else ', com 1 gol' if top['gols'] else '')
              + '. O time controlou os espaços e não deu chance.'),
             ('toninho', rnd.choice([f'Do jeito que tá, o {u["adv"]} pediu música no Fantástico e ainda saiu no lucro!',
                                     f'O {u["adv"]} veio para o passeio. Só faltou pedir foto com o {top["nome"]} no fim.']))]
    elif res == 'E':
        f = [('rogerio', f'Empate entre {M["nos"]} e {u["adv"]}: {u["gp"]} a {u["gc"]}. Resultado justo?'),
             ('helena', 'Pelo volume, o empate reflete um jogo travado. Faltou profundidade no último terço.'),
             ('carlao', 'Empate desse jeito tem cheiro de derrota. Time grande tem que sair para ganhar!'),
             ('beto', 'No vestiário, o técnico cobrou intensidade no intervalo. Ninguém saiu satisfeito.')]
    else:
        f = [('rogerio', f'Derrota do {M["nos"]}: o {u["adv"]} venceu por {pl}. O que aconteceu?'),
             ('carlao', rnd.choice(['Faltou sangue! No meu tempo, depois de um jogo desse, ninguém dormia.',
                                    'Isso é falta de cobrança. Tem jogador achando que já ganhou alguma coisa.'])),
             ('helena', 'Calma, Carlão. O problema foi a recomposição: o time perdia a bola e ficava exposto.'),
             ('toninho', 'Olha, esse time hoje não ganhava nem par ou ímpar. Tem que pedir desculpa para a torcida!')]
    if c:   # clássico: a resenha esquenta
        f.append(('toninho', f'E é {c}, hein! A cidade inteira vai {"tirar sarro" if res == "V" else "ouvir"} durante a semana!'
                  if res != 'E' else f'Empate em {c} é igual beijo de irmã: ninguém fica satisfeito!'))
    return {'id': 'resultado', 'cat': 'jogo', 'peso': (12 if c else 10) if u['recente'] else 3, 'titulo': tit, 'falas': f,
            'posts': [(_torc(M), f'{tit}! {top["nome"]} demais 🔥' if res == 'V' else f'{tit}... que jogo ruim, hein. Bora reagir.'),
                      ('@resenha_fc', f'{tit}: {top["nome"]} foi o nome do jogo (nota {_n(top["nota"])}).')]}


@pauta
def craque_do_jogo(M, rnd):
    u = M['ult']
    if not u or not u['recente'] or len(u['nos']) < 3:
        return None
    tops = sorted(u['nos'], key=lambda j: -((j['nota'] or 5) + 0.6 * j['gols'] + 0.3 * j['assist']))[:3]
    return {'id': 'craque_do_jogo', 'cat': 'jogo', 'peso': 6, 'titulo': 'Quem foi o craque do jogo?',
            'falas': [('rogerio', f'Votação da semana: quem foi o craque contra o {u["adv"]}? {_lista(j["nome"] for j in tops)}.'),
                      ('helena', f'Eu vou de {tops[0]["nome"]}: nota {_n(tops[0]["nota"])}, a maior entre os nossos.'),
                      ('toninho', f'Eu voto no {tops[1]["nome"]} só para ver a Helena brava!')],
            'enquete': _enquete(f'Craque do jogo contra o {u["adv"]}', [(j['nome'], (j['nota'] or 5) ** 3 + 30 * j['gols']) for j in tops], rnd)}


@pauta
def decepcao(M, rnd):
    u = M['ult']
    if not u or not u['recente']:
        return None
    cands = [j for j in u['nos'] if j['min'] >= 45 and j['nota']]
    if len(cands) < 5:
        return None
    med = sum(j['nota'] for j in cands) / len(cands)
    pior = min(cands, key=lambda j: j['nota'] + 0.6 * j['gols'])
    if pior['nota'] > med - 0.5:
        return None
    return {'id': 'decepcao', 'cat': 'jogo', 'peso': 6, 'titulo': f'{pior["nome"]} na berlinda',
            'extra': _cobranca_lenda(M, pior['k'], pior['nome'], rnd),
            'falas': [('rogerio', f'Agora a parte que ninguém gosta: {pior["nome"]} teve a pior nota do time, {_n(pior["nota"])}.'),
                      ('toninho', rnd.choice([f'O {pior["nome"]} entrou em campo ou mandou o primo? Porque eu não vi!',
                                              f'O {pior["nome"]} hoje não acertava nem o chão com a bola parada!'])),
                      ('carlao', f'Tem que cobrar, sim. Mas cobra no vestiário, olho no olho. O {pior["nome"]} tem crédito.'),
                      ('helena', f'Foi uma atuação abaixo da média do time ({_n(med)}). Um jogo não define ninguém.')],
            'posts': [('@zoeira_fc', f'{pior["nome"]} hoje: 👻 alguém viu? Nota {_n(pior["nota"])}'),
                      (_torc(M), f'Pega leve com o {pior["nome"]}, um jogo ruim todo mundo tem.')]}


@pauta
def goleada_nossa(M, rnd):
    u = M['ult']
    if not u or not u['recente'] or u['gp'] - u['gc'] < 3:
        return None
    return {'id': 'goleada_nossa', 'cat': 'jogo', 'peso': 7, 'titulo': f'Atropelo: {u["gp"]} a {u["gc"]} no {u["adv"]}',
            'falas': [('rogerio', f'Goleada! {u["gp"]} a {u["gc"]} no {u["adv"]}. Toninho, já preparou a piada?'),
                      ('toninho', f'O ônibus do {u["adv"]} voltou mais rápido do que veio. Saiu de fininho!'),
                      ('helena', f'Goleada mostra eficiência: o time transformou volume em gols. Isso é treino.'),
                      ('beto', 'No vestiário teve pagode até tarde. O técnico liberou, mas avisou: semana que vem tem mais.')],
            'posts': [(_torc(M), f'{u["gp"]} a {u["gc"]}!!! Que time é esse, meu Deus 😍'),
                      (f'@{_slug(u["adv"])}_sofredor', 'Prefiro nem comentar. Próximo jogo.')]}


@pauta
def derrota_dura(M, rnd):
    u = M['ult']
    if not u or not u['recente'] or u['gp'] >= u['gc']:
        return None
    return {'id': 'derrota_dura', 'cat': 'jogo', 'peso': 9, 'titulo': 'A derrota e a cobrança',
            'falas': [('rogerio', f'Derrota para o {u["adv"]}. Quem tem culpa: técnico ou jogadores?'),
                      ('carlao', 'A culpa é de todo mundo! Mas o técnico é o primeiro a ter que responder.'),
                      ('helena', 'O sistema não funcionou: o time ficou longe entre as linhas. Isso é ajuste de treino.'),
                      ('beto', 'Apurei que a diretoria vai conversar com o técnico ainda nesta semana.'),
                      ('toninho', 'Esse time tá precisando de um psicólogo e de um despertador!')],
            'enquete': _enquete('Quem tem mais culpa pela derrota?', [('O técnico', 1.1), ('Os jogadores', 1.0), ('A diretoria', 0.4)], rnd),
            'posts': [(_torc(M), 'Inadmissível perder assim. Cadê a raça?? 😡'), ('@resenha_fc', f'{u["adv"]} {u["gc"]} x {u["gp"]} {M["nos"]}. Zebra?')]}


@pauta
def goleiro(M, rnd):
    u = M['ult']
    if not u or not u['recente']:
        return None
    gk = next((j for j in u['nos'] if j['pos'] == 'GK'), None)
    if not gk:
        return None
    if u['gc'] == 0:
        return {'id': 'goleiro', 'cat': 'jogo', 'peso': 4, 'titulo': f'{gk["nome"]}, o paredão',
                'falas': [('rogerio', f'{gk["nome"]} não foi vazado. Mérito dele ou da defesa?'),
                          ('carlao', 'Goleiro bom é aquele que ninguém lembra que existe. Sinal de defesa organizada.'),
                          ('toninho', f'O {gk["nome"]} hoje podia ter levado uma cadeira de praia para o gol!')]}
    if u['gc'] >= 3 or (gk['nota'] and gk['nota'] <= 5.0):
        return {'id': 'goleiro', 'cat': 'jogo', 'peso': 6, 'titulo': f'{gk["nome"]} sob pressão',
                'falas': [('rogerio', f'{u["gc"]} gols sofridos. O goleiro {gk["nome"]} teve culpa?'),
                          ('toninho', f'O {gk["nome"]} tá com as mãos ensaboadas! Bola que vinha devagarinho, entrava!'),
                          ('helena', 'Goleiro sofre com o que acontece na frente dele. A linha de trás ficou muito exposta.'),
                          ('carlao', 'Goleiro tem que gritar, organizar! Não pode ficar só olhando.')]}
    return None


# ----- momento
@pauta
def sequencia_vitorias(M, rnd):
    tipo, n = _seq(M['jogos'], M['ti'])
    if tipo != 'vitórias' or n < 4:
        return None
    return {'id': 'sequencia_vitorias', 'cat': 'momento', 'peso': 6 + min(3, n / 5), 'titulo': f'{n} vitórias seguidas',
            'falas': [('rogerio', f'São {n} vitórias seguidas. Até onde vai esse embalo?'),
                      ('helena', 'Sequência longa não é sorte: o time repete padrão de jogo. É isso que dá regularidade.'),
                      ('carlao', 'Fase boa é hora de apertar, não de relaxar. Uma derrota boba e começa tudo de novo.'),
                      ('toninho', f'Do jeito que tá, o {M["nos"]} ganha até jogando de chinelo!')],
            'posts': [(_torc(M), f'{n} SEGUIDAS! ninguém para esse time 🚀')]}


@pauta
def jejum_vitorias(M, rnd):
    tipo, n = _seq(M['jogos'], M['ti'])
    if tipo not in ('sem vencer', 'derrotas') or n < 3:
        return None
    return {'id': 'jejum_vitorias', 'cat': 'momento', 'peso': 8, 'titulo': f'{n} jogos sem vencer',
            'falas': [('rogerio', f'Já são {n} jogos sem vencer. Crise ou fase?'),
                      ('carlao', 'Crise! Se fosse no meu tempo, o vestiário já tinha virado de cabeça para baixo.'),
                      ('beto', 'O clima no CT está pesado. Tem jogador evitando a imprensa na saída do treino.'),
                      ('toninho', f'O torcedor do {M["nos"]} já esqueceu como se comemora gol. Tá precisando de tutorial!')],
            'enquete': _enquete('O técnico deve continuar?', [('Sim, é fase', 1.0), ('Não, tem que trocar', 0.6 + n * 0.1)], rnd),
            'posts': [(_torc(M), f'{n} jogos sem vencer. Tá difícil ser torcedor. 😔'), ('@zoeira_fc', f'Alguém avisa o {M["nos"]} que a temporada já começou?')]}


@pauta
def invencibilidade(M, rnd):
    tipo, n = _seq(M['jogos'], M['ti'])
    if tipo != 'invicto' or n < 8:
        return None
    return {'id': 'invencibilidade', 'cat': 'momento', 'peso': 6, 'titulo': f'{n} jogos de invencibilidade',
            'falas': [('rogerio', f'{n} jogos sem perder. Qual o segredo?'),
                      ('helena', 'Equilíbrio: o time pode até não vencer sempre, mas raramente se expõe.'),
                      ('carlao', 'Time chato de enfrentar é time vencedor. Gosto disso.')]}


@pauta
def defesa_solida(M, rnd):
    ult5 = M['jogos'][-5:]
    zeros = sum(1 for p in ult5 if _res(p, M['ti'])[2] == 0)
    if len(ult5) < 5 or zeros < 3:
        return None
    return {'id': 'defesa_solida', 'cat': 'momento', 'peso': 5, 'titulo': 'A muralha',
            'falas': [('rogerio', f'Em {zeros} dos últimos 5 jogos, o {M["nos"]} não sofreu gol. É a melhor defesa?'),
                      ('carlao', 'Isso é coisa de zagueiro! Campeonato se ganha com defesa, ataque só vende ingresso.'),
                      ('helena', 'A pressão pós-perda está funcionando: o adversário quase não finaliza.')]}


@pauta
def defesa_vazada(M, rnd):
    ult5 = M['jogos'][-5:]
    vaz = sum(1 for p in ult5 if _res(p, M['ti'])[2] >= 2)
    if vaz < 3:
        return None
    return {'id': 'defesa_vazada', 'cat': 'momento', 'peso': 7, 'titulo': 'Defesa em pane',
            'falas': [('rogerio', f'Sofreu 2 gols ou mais em {vaz} dos últimos 5 jogos. A defesa preocupa?'),
                      ('carlao', 'Preocupa e muito! Zagueiro hoje quer sair jogando de calcanhar e esquece de marcar.'),
                      ('toninho', 'A defesa do time tá igual porta de shopping: abre sozinha!'),
                      ('helena', 'O problema começa no meio: falta proteção na frente da área.')],
            'posts': [('@zoeira_fc', f'Defesa do {M["nos"]} patrocinada por peneira 🕳️')]}


@pauta
def historico(M, rnd):
    tipo, n = _seq(M['jogos'], M['ti'])
    if tipo != 'vitórias' or n < 10:
        return None
    return {'id': 'historico', 'cat': 'momento', 'peso': 7, 'titulo': 'O melhor time da história?',
            'falas': [('rogerio', f'Com {n} vitórias seguidas, já dá para falar em melhor time da história do clube?'),
                      ('carlao', 'Calma! Melhor da história se mede com título na mão. Por enquanto é um timaço.'),
                      ('toninho', 'Melhor da história? Esse time ganharia até do videogame no modo difícil!'),
                      ('helena', 'Os números já colocam essa sequência entre as maiores. Falta o troféu para fechar a conta.')],
            'enquete': _enquete('É o melhor time da história do clube?', [('Sim!', 1.2), ('Ainda não, falta título', 1.0)], rnd)}


# ----- próximo jogo
@pauta
def previa(M, rnd):
    pj = M['pj']
    if not pj.get('casa') or pj.get('parcial') or not pj.get('prob') or pj.get('final'):   # final: pauta própria
        return None
    adv = pj['adversario']
    return {'id': 'previa', 'cat': 'proximo', 'peso': 8, 'titulo': f'Próximo: {pj["casa"]} x {pj["fora"]}',
            'falas': [('rogerio', f'O próximo desafio é o {adv}, pela {pj["competicao"]}. Palpites na mesa!')] +
                     [(q, f'{x["texto"]}. {x["fala"]}') for q, x in zip(('carlao', 'helena', 'beto'), pj.get('palpites') or [])] +
                     [('toninho', rnd.choice([f'Eu digo que o {adv} já tá procurando desculpa para a derrota.',
                                              f'Esse jogo contra o {adv} é casca de banana. Quem escorregar, chora.']))],
            'enquete': _enquete(f'{M["nos"]} vence o {adv}?', [('Sim', pj['enquete']['sim']), ('Não', 100 - pj['enquete']['sim'])], random.Random(0))}


@pauta
def jogo_grande(M, rnd):
    pj = M['pj']
    if not pj.get('casa') or pj.get('parcial'):
        return None
    adv = pj['adversario']
    if pj.get('final'):
        return None
    tb = (pj.get('tabela') or {}).get('fora' if pj.get('eu_casa') else 'casa') or {}
    grande = 'Champions' in (pj.get('competicao') or '') or 'Libertadores' in (pj.get('competicao') or '') or (tb.get('pos') or 99) <= 4
    if not grande:
        return None
    return {'id': 'jogo_grande', 'cat': 'proximo', 'peso': 8, 'titulo': f'Jogão contra o {adv}',
            'falas': [('rogerio', f'Semana de jogo grande: {pj["casa"]} x {pj["fora"]}. É o jogo da temporada?'),
                      ('beto', 'O técnico fechou os treinos. Tem novidade tática sendo preparada, pode apostar.'),
                      ('carlao', 'Jogo grande se ganha antes de entrar em campo, no olho. Quero ver atitude!'),
                      ('helena', f'Números: {pj["prob"]["casa"]}% para o {pj["casa"]}, {pj["prob"]["empate"]}% de empate e {pj["prob"]["fora"]}% para o {pj["fora"]}.')]}


@pauta
def classico(M, rnd):
    """Semana de clássico (classicos.py): o programa vira um esquenta."""
    pj = M['pj']
    c = pj.get('classico')
    if not c or pj.get('parcial'):
        return None
    adv = pj['adversario']
    h2h = pj.get('confrontos') or []
    return {'id': 'classico', 'cat': 'proximo', 'peso': 11, 'titulo': f'Semana de {c}',
            'falas': [('rogerio', f'Atenção, torcedor: é semana de {c}! {pj["casa"]} x {pj["fora"]}, pela {pj["competicao"]}.'
                       + (' Últimos encontros: ' + '; '.join(h2h) + '.' if h2h else '')),
                      ('carlao', rnd.choice(['Clássico não se joga, se ganha! Eu joguei vários e te digo: quem treme, perde.',
                                             'Em clássico, tabela não entra em campo. Entra a camisa e o coração.'])),
                      ('helena', f'Taticamente, o jogo deve ser decidido no meio. Nos números: {pj["prob"]["casa"]}% para o {pj["casa"]}, '
                                 f'{pj["prob"]["empate"]}% de empate e {pj["prob"]["fora"]}% para o {pj["fora"]}.' if pj.get('prob') else
                                 'Taticamente, o jogo deve ser decidido no meio-campo.'),
                      ('beto', f'No CT, o clima mudou. Os jogadores sabem o que significa o {c} para a torcida.'),
                      ('toninho', rnd.choice([f'O torcedor do {adv} já tá rezando desde segunda-feira!',
                                              f'Semana de {c} é semana de zoeira. Quem perder não sai de casa até o próximo!']))],
            'enquete': _enquete(f'Quem vence o {c}?', [(M['nos'], 1.2), ('Empate', 0.5), (adv, 0.8)], rnd),
            'posts': [(_torc(M), f'SEMANA DE {c.upper()}!!! A cidade vai parar 🔥🔥'),
                      (f'@{_slug(adv)}_raiz', f'Podem vir! O {c} é nosso, sempre foi 😤'),
                      ('@resenha_fc', f'{c}: {pj["casa"]} x {pj["fora"]}. Palpites? ⚔️')]}


@pauta
def reforco_adversario(M, rnd):
    pj = M['pj']
    adv = pj.get('adversario')
    novos = [n for n in M['negocios'] if n['para'] == adv]
    if not adv or not novos:
        return None
    n = novos[0]
    return {'id': 'reforco_adversario', 'cat': 'proximo', 'peso': 5, 'titulo': f'O {adv} se reforçou',
            'falas': [('rogerio', f'O próximo adversário, {adv}, acabou de contratar {n["jogador"]} ({n["pos"]}). Muda alguma coisa?'),
                      ('helena', f'Depende do encaixe. O {adv} buscou o jogador para {n["motivo"].split(";")[0]}.'),
                      ('toninho', f'Contratou o {n["jogador"]}? Vai estrear já tomando um baile!')]}


# ----- tabela
@pauta
def lideranca(M, rnd):
    eu, tab = M['eu'], M['tab']
    if not eu or eu['pos'] != 1 or len(tab) < 2 or eu['pts'] - tab[1]['pts'] < 6:
        return None
    dif = eu['pts'] - tab[1]['pts']
    return {'id': 'lideranca', 'cat': 'tabela', 'peso': 6, 'titulo': f'{dif} pontos de vantagem',
            'falas': [('rogerio', f'Líder com {dif} pontos sobre o {tab[1]["time"]}. Dá para dizer que o título está encaminhado?'),
                      ('carlao', 'Nunca! Campeonato só acaba quando o juiz apita a última rodada.'),
                      ('toninho', f'O {tab[1]["time"]} tá olhando a tabela com binóculo!'),
                      ('helena', f'{eu["v"]} vitórias em {eu["j"]} jogos. Matematicamente ainda não, mas a tendência é clara.')],
            'enquete': _enquete('O título está garantido?', [('Já é!', 1.0 + dif / 10), ('Ainda não', 1.0)], rnd)}


@pauta
def briga_titulo(M, rnd):
    eu, tab = M['eu'], M['tab']
    if not eu or len(tab) < 2:
        return None
    if eu['pos'] == 1:
        rival, dif = tab[1], eu['pts'] - tab[1]['pts']
    else:
        rival, dif = tab[0], tab[0]['pts'] - eu['pts']
    if dif > 3 or eu['pos'] > 3:
        return None
    return {'id': 'briga_titulo', 'cat': 'tabela', 'peso': 8, 'titulo': f'Briga pelo título com o {rival["time"]}',
            'falas': [('rogerio', f'Só {dif} ponto(s) separam o {M["nos"]} do {rival["time"]}. Quem leva?'),
                      ('helena', f'O {rival["time"]} tem {rival["gp"]} gols marcados; o {M["nos"]}, {eu["gp"]}. É detalhe.'),
                      ('carlao', 'Quem tiver mais estômago leva. Reta final é cabeça.'),
                      ('toninho', f'Eu já vi o {rival["time"]} amarelar antes. É só esperar!')],
            'enquete': _enquete('Quem leva o título?', [(M['nos'], 1.1), (rival['time'], 0.9)], rnd)}


@pauta
def zona_rebaixamento(M, rnd):
    eu, tab = M['eu'], M['tab']
    if not eu or len(tab) < 8:
        return None
    corte = tab[-4]
    if eu['pos'] < len(tab) - 5 and eu['pts'] - corte['pts'] > 3:
        return None
    na_zona = eu['pos'] > len(tab) - 4
    return {'id': 'zona_rebaixamento', 'cat': 'tabela', 'peso': 9, 'titulo': 'Fantasma do rebaixamento',
            'falas': [('rogerio', f'O {M["nos"]} é o {eu["pos"]}º, ' + ('dentro da zona.' if na_zona else 'perigosamente perto da zona.') + ' Dá para escapar?'),
                      ('carlao', 'Agora é briga de faca! Quem não tiver coragem, que peça para sair.'),
                      ('helena', f'Faltam jogos, mas o time precisa somar fora de casa. Só {eu["v"]} vitórias até aqui.'),
                      ('toninho', 'O torcedor já tá pesquisando o calendário da divisão de baixo!')],
            'enquete': _enquete('O time escapa?', [('Escapa', 1.0), ('Cai', 0.7 + (0.4 if na_zona else 0))], rnd)}


@pauta
def vaga_continental(M, rnd):
    eu, tab = M['eu'], M['tab']
    if not eu or len(tab) < 10 or not 3 <= eu['pos'] <= 7:
        return None
    return {'id': 'vaga_continental', 'cat': 'tabela', 'peso': 6, 'titulo': 'De olho na vaga continental',
            'falas': [('rogerio', f'Em {eu["pos"]}º, o {M["nos"]} está na briga pela vaga continental. O elenco aguenta?'),
                      ('helena', 'A diferença entre o 3º e o 7º costuma ser decidida nos confrontos diretos.'),
                      ('beto', 'A diretoria considera a vaga obrigação. O orçamento do ano que vem depende dela.')]}


@pauta
def meta_diretoria(M, rnd):
    conf = M['dir'].get('confianca')
    metas = M['dir'].get('metas') or {}
    if conf is None:
        return None
    if conf < 40:
        return {'id': 'meta_diretoria', 'cat': 'clube', 'peso': 9, 'titulo': 'O técnico balança?',
                'falas': [('rogerio', f'A confiança da diretoria no técnico está em {conf}. O cargo está em risco?'),
                          ('beto', 'Apurei que o presidente já conversa com nomes no mercado. Não é boato.'),
                          ('carlao', 'Técnico vive de resultado. Sem resultado, a mala fica pronta na porta.'),
                          ('toninho', 'O técnico já pode ir deixando o currículo atualizado!')],
                'enquete': _enquete('O técnico deve ser demitido?', [('Sim', 1.0 + (40 - conf) / 30), ('Não', 1.0)], rnd)}
    if metas.get('liga_texto') and M['eu']:
        ok = M['eu']['pos'] <= (metas.get('liga_alvo') or 1)
        return {'id': 'meta_diretoria', 'cat': 'clube', 'peso': 3, 'titulo': 'A meta da diretoria',
                'falas': [('rogerio', f'A meta é "{metas["liga_texto"]}". ' + ('Está sendo cumprida.' if ok else 'Hoje não está.') + ' Como avalia?'),
                          ('helena', f'Confiança da diretoria em {conf}. ' + ('Trabalho respaldado.' if conf >= 60 else 'Respaldo frágil.'))]}
    return None


@pauta
def lanterna(M, rnd):
    tab = M['tab']
    if len(tab) < 8 or tab[-1].get('eu'):
        return None
    l = tab[-1]
    return {'id': 'lanterna', 'cat': 'tabela', 'peso': 3, 'titulo': f'A situação do {l["time"]}',
            'falas': [('rogerio', f'O lanterna é o {l["time"]}, com {l["pts"]} pontos. Tem salvação?'),
                      ('toninho', f'O {l["time"]} tá tão mal que até o mascote pediu transferência!'),
                      ('helena', f'{l["gc"]} gols sofridos em {l["j"]} jogos. O problema começa atrás.')]}


@pauta
def ataque_defesa(M, rnd):
    tab = M['tab']
    if len(tab) < 8 or min(t['j'] for t in tab) < 5:
        return None
    a = max(tab, key=lambda t: t['gp'])
    d = min(tab, key=lambda t: t['gc'])
    return {'id': 'ataque_defesa', 'cat': 'tabela', 'peso': 3, 'titulo': 'Melhor ataque x melhor defesa',
            'falas': [('rogerio', f'Melhor ataque: {a["time"]}, {a["gp"]} gols. Melhor defesa: {d["time"]}, {d["gc"]} sofridos. O que ganha campeonato?'),
                      ('carlao', 'Defesa! Sempre defesa. Ataque vende camisa, defesa levanta taça.'),
                      ('toninho', 'Carlão é zagueiro, né? Óbvio que ia dizer isso!')]}


# ----- a liga
def _recentes_liga(M, dias=9):
    return [g for g in M['res_liga'] if not g.get('meu') and _dias(M['hoje'], tuple(g['data'])) <= dias]


@pauta
def zebra(M, rnd):
    pos = {t['time']: t['pos'] for t in M['tab']}
    for g in _recentes_liga(M):
        pa, pb = pos.get(g['casa']), pos.get(g['fora'])
        if not pa or not pb:
            continue
        venc, perd = (g['casa'], g['fora']) if g['g1'] > g['g2'] else (g['fora'], g['casa']) if g['g2'] > g['g1'] else (None, None)
        if venc and pos[venc] - pos[perd] >= 8:
            return {'id': 'zebra', 'cat': 'liga', 'peso': 5, 'titulo': f'Zebra: {venc} derruba o {perd}',
                    'falas': [('rogerio', f'Zebra na rodada: {g["casa"]} {g["g1"]} x {g["g2"]} {g["fora"]}.'),
                              ('toninho', f'O {perd} entrou de salto alto e saiu de chinelo!'),
                              ('helena', f'O {venc} é o {pos[venc]}º e o {perd}, o {pos[perd]}º. Futebol não é planilha.')],
                    'posts': [('@resenha_fc', f'ZEBRA! {g["casa"]} {g["g1"]} x {g["g2"]} {g["fora"]} 🦓')]}
    return None


@pauta
def goleada_rodada(M, rnd):
    gs = [g for g in _recentes_liga(M) if abs(g['g1'] - g['g2']) >= 3]
    if not gs:
        return None
    g = max(gs, key=lambda g: abs(g['g1'] - g['g2']))
    venc = g['casa'] if g['g1'] > g['g2'] else g['fora']
    perd = g['fora'] if venc == g['casa'] else g['casa']
    return {'id': 'goleada_rodada', 'cat': 'liga', 'peso': 4, 'titulo': f'Goleada do {venc}',
            'falas': [('rogerio', f'Na rodada, goleada: {g["casa"]} {g["g1"]} x {g["g2"]} {g["fora"]}.'),
                      ('toninho', f'O goleiro do {perd} vai precisar de fisioterapia no pescoço de tanto olhar para trás!'),
                      ('carlao', f'Isso é falta de vergonha do {perd}. Perder faz parte, ser humilhado não.')]}


@pauta
def rival_crise(M, rnd):
    top = [t for t in M['tab'][:6] if not t.get('eu')]
    s = M['s']
    for t in top:
        i = s.find_team(t['time'])
        if i is None:
            continue
        js = sorted((p for p in M['todas'] if i in (p['time1'], p['time2'])), key=lambda p: p['data'])
        tipo, n = _seq(js, i)
        if tipo in ('sem vencer', 'derrotas') and n >= 3:
            return {'id': 'rival_crise', 'cat': 'liga', 'peso': 5, 'titulo': f'Crise no {t["time"]}',
                    'falas': [('rogerio', f'O {t["time"]} está há {n} jogos sem vencer. O que está acontecendo lá?'),
                              ('beto', f'Colegas que cobrem o {t["time"]} falam em racha no vestiário.'),
                              ('toninho', f'O {t["time"]} tá numa fase que nem no videogame ganharia!')]}
    return None


@pauta
def artilharia(M, rnd):
    art = M['art']
    if len(art) < 3 or art[0]['gols'] < 5:
        return None
    meu = next((a for a in art if a['time'] == M['nos']), None)
    f = [('rogerio', f'Na artilharia da {M["liga"]}: {art[0]["nome"]} ({art[0]["time"]}) lidera com {art[0]["gols"]} gols. '
                     f'Atrás, {art[1]["nome"]} com {art[1]["gols"]}.')]
    if meu and meu is not art[0]:
        f.append(('carlao', f'O {meu["nome"]} tem {meu["gols"]}. Dá para buscar, mas tem que ser mais fominha!'))
    elif meu:
        f.append(('toninho', f'O {meu["nome"]} tá fazendo gol até sem querer. Bate na canela e entra!'))
    f.append(('helena', 'A artilharia costuma ser decidida pela regularidade: quem marca em sequência, sem jejum longo.'))
    return {'id': 'artilharia', 'cat': 'liga', 'peso': 5, 'titulo': 'Corrida da artilharia', 'falas': f,
            'enquete': _enquete(f'Quem termina artilheiro da {M["liga"]}?', [(f'{a["nome"]} ({a["time"]})', a['gols'] ** 2) for a in art[:3]], rnd)}


def _time_ideal(M):
    idx = [M['s'].find_team(t['time']) for t in M['tab']]
    idx = {i for i in idx if i is not None}
    if len(idx) < 8:
        return None
    cands = collections.defaultdict(list)
    for k, e in M['est'].items():
        if M['clube_de'].get(k) not in idx or e['jogos'] < 5:
            continue
        f = M['P'].get(k)
        if not f:
            continue
        g = 'GK' if f.pos == 'GK' else 'DEF' if f.pos in DEF else 'ATA' if f.pos in ATA else 'MEI'
        cands[g].append((_media(e) + 0.15 * e['gols'] + 0.1 * e['assist'], f.name.strip(), M['s'].name(M['clube_de'][k]).strip()))
    out = []
    for g, n in (('GK', 1), ('DEF', 4), ('MEI', 3), ('ATA', 3)):
        out += [(g, x[1], x[2]) for x in sorted(cands[g], reverse=True)[:n]]
    return out if len(out) == 11 else None


@pauta
def time_ideal(M, rnd):
    if M['eu'] and M['eu']['j'] < 8:
        return None
    ti = _time_ideal(M)
    if not ti:
        return None
    nossos = [n for _, n, t in ti if t == M['nos']]
    return {'id': 'time_ideal', 'cat': 'liga', 'peso': 4, 'titulo': f'Seleção da {M["liga"]} até aqui',
            'falas': [('rogerio', 'A seleção do campeonato até agora, pelas notas: ' + '; '.join(f'{n} ({t})' for _, n, t in ti) + '.'),
                      ('helena', f'O {M["nos"]} tem {len(nossos)} nomes: {_lista(nossos)}.' if nossos else f'Nenhum jogador do {M["nos"]} entrou. Diz muito.'),
                      ('toninho', 'Faltou eu nessa seleção aí! No meu tempo eu tava em todas.')]}


# ----- copas
CONTINENTAIS = {3: 'UEFA Champions League', 4: 'UEFA Champions League', 0x0A: 'Libertadores'}


def _mata_mata(M):
    """Jogos do usuário no mata-mata continental (Champions comp 4) nesta temporada."""
    return [p for p in M['jogos'] if p['comp'] == 4 and tuple(p['data']) >= M['ini']]


@pauta
def noite_europeia(M, rnd):
    """O jogo continental mais recente (mesmo que não seja o último jogo): resultado, confronto de ida e volta,
    classificado ou eliminado, destaque. 11/10/2026: o programa só falava do último jogo e a Champions sumia."""
    ti, s = M['ti'], M['s']
    eur = [p for p in M['jogos'] if p['comp'] in CONTINENTAIS and 0 <= _dias(M['hoje'], tuple(p['data'])) <= 12]
    if not eur:
        return None
    p = eur[-1]
    v = _tie(M)
    if v and v['tipo'] and v['num_volta'] == p.get('num'):   # virada/vexame: a pauta própria cobre (virada_historica)
        return None
    try:   # final: a festa (ou a dor) fica com final_pos
        import marcos
        fin = marcos.final_do_time(M['todas'] + (M['r'].get('agenda') or []), M['ti'])
        if fin and fin['jogado'] and fin['data'] == tuple(p['data']):
            return None
    except Exception:  # noqa: BLE001
        pass
    comp = CONTINENTAIS[p['comp']]
    casa = p['time1'] == ti
    adv = s.name(p['time2'] if casa else p['time1']).strip()
    gp, gc = (p['gols1'], p['gols2']) if casa else (p['gols2'], p['gols1'])
    res = 'V' if gp > gc else 'E' if gp == gc else 'D'
    nossas = p['linhas1'] if casa else p['linhas2']
    top = max((x for x in nossas if x['minutos'] > 0), key=lambda x: (x['nota'] or 5) + 0.6 * x['gols'], default=None)
    top_n = M['P'][(top['reg'], top['pid'])].name.strip() if top and (top['reg'], top['pid']) in M['P'] else None
    f = [('rogerio', f'Noite de {comp}: {M["nos"]} {gp} x {gc} {adv}' + (', fora de casa.' if not casa else ', em casa.'))]
    titulo = f'{comp}: {M["nos"]} {gp} x {gc} {adv}'
    agreg = None
    if p['comp'] == 4:   # mata-mata: ida e volta contra o mesmo adversário
        tie = [x for x in _mata_mata(M) if {x['time1'], x['time2']} == {p['time1'], p['time2']}]
        if len(tie) == 2:
            a = sum(x['gols1'] if x['time1'] == ti else x['gols2'] for x in tie)
            b = sum(x['gols2'] if x['time1'] == ti else x['gols1'] for x in tie)
            agreg = (a, b)
            passou = a > b
            f.append(('rogerio', f'No agregado, {a} a {b}: ' + (f'o {M["nos"]} está classificado!' if passou else
                                                                f'o {M["nos"]} está eliminado.' if a < b else 'empate no agregado, decidido nos detalhes.')))
            titulo = (f'Classificado! {M["nos"]} passa pelo {adv}' if passou else f'Eliminado: {adv} tira o {M["nos"]}' if a < b else titulo)
        elif len(tie) == 1:
            f.append(('rogerio', f'Foi o jogo de ida. ' + ('Vantagem para a volta.' if res == 'V' else 'Tudo aberto para a volta.' if res == 'E'
                                                          else 'Vai ser preciso buscar o resultado na volta.')))
    if top_n:
        f.append(('helena', f'O destaque foi {top_n}, nota {_n(top["nota"] or 0)}' + (f', com {top["gols"]} gol{"s" if top["gols"] > 1 else ""}' if top['gols'] else '') + '.'))
    f.append(('carlao', rnd.choice(['Noite europeia é outra coisa! Ali se separa time bom de time grande.',
                                    'Na Europa não tem jogo fácil. Quem vacila um minuto, volta para casa.'])
              if res != 'D' else 'Na Europa não se perdoa erro. Tem que ter cabeça fria na volta.'))
    f.append(('toninho', rnd.choice([f'O {adv} achou que ia passear? Voltou com a mala cheia de gols!' if res == 'V' else
                                     f'Contra o {adv} faltou aquele algo a mais. Na Europa, pagou caro!' if res == 'D' else
                                     f'Empate com o {adv}? Isso é jogo de xadrez, e eu prefiro dama!'])))
    pj = M['pj']
    prox = pj.get('competicao') == comp and pj.get('adversario')
    enq = (_enquete(f'O {M["nos"]} ganha a {comp}?', [('Sim, é o favorito', 1.2), ('Não', 0.8)], rnd) if (agreg and agreg[0] > agreg[1]) or res == 'V'
           else _enquete(f'O {M["nos"]} reverte na volta?', [('Reverte', 1.0), ('Já era', 0.8)], rnd))
    return {'id': 'noite_europeia', 'cat': 'copa', 'peso': 10.5 if agreg else 9.5, 'titulo': titulo, 'falas': f
            + ([('beto', f'O próximo passo é o {pj["adversario"]}. O CT já respira {comp}.')] if prox else []),
            'enquete': enq,
            'posts': [(_torc(M), f'{"CLASSIFICADO" if agreg and agreg[0] > agreg[1] else "NOITE EUROPEIA"}! {M["nos"]} {gp} x {gc} {adv} ⭐🏆'),
                      ('@resenha_fc', f'{comp}: {M["nos"]} {gp} x {gc} {adv}' + (f' (agregado {agreg[0]} a {agreg[1]})' if agreg else '') + '.')]
            + ([('@numerosdabola', f'{top_n} foi o melhor em campo contra o {adv}: nota {_n(top["nota"] or 0)}.')] if top_n else [])}


def _tie(M):
    try:
        import viradas
        return viradas.do_time(M['todas'], M['ti'], M['hoje'], dias=10)
    except Exception:  # noqa: BLE001
        return None


@pauta
def virada_historica(M, rnd):
    """VIRADA (ou vexame) no mata-mata: a mesa vai à loucura (viradas.py; remontadas reais para comparar)."""
    v = _tie(M)
    if not v or not v['tipo']:
        return None
    import viradas
    adv = M['s'].name(v['adv']).strip()
    i, a, vo = v['ida'], v['agg'], v['volta']
    if v['tipo'] == 'virada':
        real = viradas.comparacao(v['deficit'])
        f = [('rogerio', f'Senhoras e senhores, que noite! O {M["nos"]} perdeu a ida por {i[1]} a {i[0]} para o {adv} e, na volta, '
                         f'fez {vo[0]} a {vo[1]}. Virada no agregado: {a[0]} a {a[1]}!'),
             ('carlao', rnd.choice(['Eu estou arrepiado até agora! Isso é camisa, é raça, é sangue! Ninguém desistiu!',
                                    'Quando todo mundo deu o time como morto, esse grupo levantou. Isso não se ensina, meu amigo!'])),
             ('helena', f'Comparação inevitável: o {real[0]}, que {real[3]}. Reverter {v["deficit"]} gols de desvantagem é para poucos.'),
             ('beto', 'No vestiário foi uma loucura: tinha jogador chorando, gente pulando, o técnico abraçado com a comissão.'),
             ('toninho', rnd.choice([f'O {adv} já tinha reservado o hotel da próxima fase! Pode cancelar, meu filho!',
                                     f'O torcedor do {adv} vai ter pesadelo com essa noite pelos próximos dez anos!']))]
        return {'id': 'virada_historica', 'cat': 'jogo', 'peso': 15, 'titulo': f'VIRADA HISTÓRICA contra o {adv}!', 'falas': f,
                'enquete': _enquete('Foi a maior noite da história do clube?', [('Sim, a maior!', 1.6), ('Uma das maiores', 1.0), ('Ainda tem coisa maior', 0.3)], rnd),
                'posts': [(_torc(M), f'EU NÃO ACREDITO!!! {vo[0]} A {vo[1]}!!! VIRAMOS CONTRA O {adv.upper()}!!! 😭🔥🔥'),
                          (_torc(M), f'Quem saiu do estádio antes do fim nunca vai se perdoar. NOITE HISTÓRICA! ⭐'),
                          ('@numerosdabola', f'{M["nos"]} reverteu {v["deficit"]} gols de desvantagem: {a[0]} a {a[1]} no agregado contra o {adv}. 📊'),
                          (f'@{_slug(adv)}_raiz', 'Não tenho palavras. Vergonha. 😞'),
                          ('@resenha_fc', f'Isso aqui lembra o {real[0]} em cima do {real[1]}. QUE NOITE! 🤯')]}
    f = [('rogerio', f'Noite para esquecer: o {M["nos"]} venceu a ida por {i[0]} a {i[1]} e conseguiu ser eliminado pelo {adv}, '
                     f'que fez {vo[1]} a {vo[0]} na volta.'),
         ('carlao', 'Isso é inadmissível! Time que tem vantagem de dois gols não pode entrar de salto alto!'),
         ('helena', f'Perder uma vantagem de {v["deficit"]} gols mostra falha de gestão de jogo. O time recuou demais.'),
         ('toninho', rnd.choice(['Esse time conseguiu perder um jogo que estava ganho na semana passada! É talento!',
                                 'Já vi muita coisa no futebol, mas isso aí vai para o museu do vexame!'])),
         ('beto', 'O clima no CT é de velório. A diretoria vai cobrar explicações.')]
    return {'id': 'virada_historica', 'cat': 'jogo', 'peso': 14, 'titulo': f'Vexame: eliminação para o {adv}', 'falas': f,
            'enquete': _enquete('De quem é a culpa da eliminação?', [('Do técnico', 1.0), ('Dos jogadores', 1.0), ('Da diretoria', 0.3)], rnd),
            'posts': [(_torc(M), 'Não dá para acreditar. Que vergonha. 😡'), ('@zoeira_fc', f'{M["nos"]} conseguiu perder com vantagem de {v["deficit"]}. Inédito 🤡'),
                      (f'@{_slug(adv)}_raiz', 'VIRAMOS!!! A NOITE É NOSSA!!! 🔥')]}


@pauta
def final_pre(M, rnd):
    """Semana de FINAL (marcos.py): o programa vira esquenta."""
    pj = M['pj']
    if not pj.get('final') or pj.get('parcial'):
        return None
    c, adv = pj['competicao'], pj['adversario']
    return {'id': 'final_pre', 'cat': 'proximo', 'peso': 14, 'titulo': f'Semana de final: {c}',
            'falas': [('rogerio', f'Atenção: é semana de FINAL! {pj["casa"]} x {pj["fora"]}, valendo a taça da {c}. Jogo único, sem amanhã.'),
                      ('carlao', rnd.choice(['Final não se joga, se vence! Eu perdi uma final na carreira e até hoje acordo pensando nela.',
                                             'Em final, o craque aparece e o medroso some. Quero ver quem vai pedir a bola!'])),
                      ('helena', f'Taticamente, final costuma ser travada. Quem fizer o primeiro gol obriga o outro a se expor.' +
                       (f' Pelos números: {pj["prob"]["casa"]}% para o {pj["casa"]}, {pj["prob"]["empate"]}% de empate e {pj["prob"]["fora"]}% para o {pj["fora"]}.' if pj.get('prob') else '')),
                      ('beto', 'O CT está diferente. Silêncio nos treinos, concentração total. O grupo sabe o tamanho disso.'),
                      ('toninho', f'O torcedor do {adv} já está ensaiando o choro! Pode preparar o lencinho!')],
            'enquete': _enquete(f'Quem fica com a {c}?', [(M['nos'], 1.3), (adv, 0.8)], rnd),
            'posts': [(_torc(M), f'FINAL!!! VAMOS BUSCAR ESSA TAÇA!!! 🏆🔥'), (f'@{_slug(adv)}_raiz', 'A taça já tem dono, e não é vocês 😤'),
                      ('@resenha_fc', f'Final da {c}: {pj["casa"]} x {pj["fora"]}. Palpite? 🏆')]}


@pauta
def final_pos(M, rnd):
    """Depois da FINAL: campeão (festa) ou vice (dor)."""
    try:
        import marcos
        from proximo_jogo import nome_comp
        fin = marcos.final_do_time(M['todas'] + (M['r'].get('agenda') or []), M['ti'])
    except Exception:  # noqa: BLE001
        return None
    if not fin or not fin['jogado'] or fin['campeao'] is None or not 0 <= _dias(M['hoje'], fin['data']) <= 10:
        return None
    c, adv = nome_comp(fin['comp']), M['s'].name(fin['adv']).strip()
    pl = f'{fin["gp"]} a {fin["gc"]}'
    if fin['campeao']:
        f = [('rogerio', f'É CAMPEÃO! O {M["nos"]} venceu o {adv} por {pl} e conquistou a {c}! Que noite!'),
             ('carlao', 'Eu falei! Time grande ganha final! Esse grupo está na história, ninguém tira isso deles!'),
             ('helena', 'O título coroa uma temporada de regularidade. Na final, o time soube sofrer e decidir.'),
             ('beto', 'No vestiário teve banho de champanhe, o técnico jogado para o alto e a taça passando de mão em mão.'),
             ('toninho', f'O {adv} vai assistir à festa pela televisão! E o torcedor rival vai fingir que não viu!')]
        return {'id': 'final_pos', 'cat': 'jogo', 'peso': 16, 'titulo': f'CAMPEÃO DA {c.upper()}!', 'falas': f,
                'enquete': _enquete('Qual foi o título mais importante da era recente?', [(c, 1.4), ('Outro título', 0.8)], rnd),
                'posts': [(_torc(M), f'É CAMPEÃO!!! A {c.upper()} É NOSSA!!! 🏆🏆🏆'), (_torc(M), 'Chorei, pulei, gritei. NOITE ETERNA ⭐'),
                          ('@numerosdabola', f'{M["nos"]} {pl} {adv}: campeão da {c}. 🏆'), (f'@{_slug(adv)}_raiz', 'Hoje não. Hoje dói. 😞')]}
    f = [('rogerio', f'Dor no fim: o {M["nos"]} perdeu a final da {c} para o {adv}, {pl}.'),
         ('carlao', 'Perder final é a pior dor do futebol. Mas tem que levantar a cabeça e voltar mais forte.'),
         ('helena', 'Em jogo único, um detalhe muda tudo. O time não conseguiu impor o jogo nos momentos decisivos.'),
         ('toninho', 'Medalha de prata é aquela que você ganha para lembrar que perdeu!')]
    return {'id': 'final_pos', 'cat': 'jogo', 'peso': 15, 'titulo': f'Vice da {c}', 'falas': f,
            'enquete': _enquete('O que faltou na final?', [('Experiência', 1.0), ('Escalação', 0.9), ('Sorte', 0.7)], rnd),
            'posts': [(_torc(M), 'Dói demais. Mas a gente volta. 💔'), (f'@{_slug(adv)}_raiz', 'CAMPEÕES!!! 🏆')]}


@pauta
def campeao_liga(M, rnd):
    try:
        import marcos
        tl = marcos.titulo_liga(M['tab'])
    except Exception:  # noqa: BLE001
        return None
    if not tl or not tl['campeao']:
        return None
    ult_liga = max((tuple(p['data']) for p in M['jogos'] if (M['r'].get('_comp_liga') is None or p['comp'] == M['r'].get('_comp_liga'))
                    and not (100 <= p['comp'] <= 110) and p['comp'] not in (56, 3, 4)), default=None)
    if not ult_liga or _dias(M['hoje'], ult_liga) > 10:   # a festa do título fica no fim da temporada, não na pré-temporada
        return None
    extra = f', com {tl["restam"]} rodadas de antecedência' if tl['restam'] > 0 else ''
    return {'id': 'campeao_liga', 'cat': 'tabela', 'peso': 13, 'titulo': f'Campeão da {M["liga"]}!',
            'falas': [('rogerio', f'Está decidido: o {M["nos"]} é campeão da {M["liga"]}{extra}, com {tl["pts"]} pontos!'),
                      ('helena', f'Campanha histórica: {tl["vantagem"]} pontos de vantagem. Os números não deixam dúvida.'),
                      ('carlao', 'Campeonato de pontos corridos premia o melhor. E não teve para ninguém!'),
                      ('toninho', 'Os rivais já estão pedindo para começar o ano que vem agora!')],
            'enquete': _enquete('Qual foi o craque do título?', [(j['nome'], j['t_gols'] + 1) for j in sorted(M['J'], key=lambda j: -j['t_gols'])[:3]], rnd),
            'posts': [(_torc(M), f'CAMPEÃO DA {M["liga"].upper()}!!! 🏆🏆'), ('@numerosdabola', f'{M["nos"]}: {tl["pts"]} pontos e o título. 📊')]}


@pauta
def virada_mundo(M, rnd):
    try:
        import viradas
        vs = viradas.no_mundo(M['todas'], M['hoje'], 10, exceto=M['ti'])
    except Exception:  # noqa: BLE001
        return None
    if not vs:
        return None
    v = vs[0]
    t, adv = M['s'].name(v['time']).strip(), M['s'].name(v['adv']).strip()
    return {'id': 'virada_mundo', 'cat': 'liga', 'peso': 4 + v['deficit'] * 0.8, 'titulo': f'A virada do {t}',
            'falas': [('rogerio', f'Pelo mundo: o {t} perdeu a ida para o {adv} por {v["ida"][1]} a {v["ida"][0]} e virou: {v["agg"][0]} a {v["agg"][1]} no agregado.'),
                      ('helena', f'Reverter {v["deficit"]} gols fora do script. O {adv} administrou mal a vantagem.'),
                      ('toninho', f'O {adv} já estava comprando passagem para a próxima fase! Ficou no aeroporto!')],
            'posts': [('@resenha_fc', f'VIRADA! {t} elimina o {adv}: {v["agg"][0]} a {v["agg"][1]} no agregado 🤯')]}


@pauta
def copa_grupo(M, rnd):
    if _mata_mata(M):   # já é mata-mata: "situação no grupo" ficou para trás
        return None
    for o in M['outras']:
        g = next((t for t in o.get('grupo') or [] if t.get('eu')), None)
        if not g or g['j'] < 1:
            continue
        return {'id': 'copa_grupo', 'cat': 'copa', 'peso': 6, 'titulo': f'{o["competicao"]}: situação no grupo',
                'falas': [('rogerio', f'Na {o["competicao"]}, o {M["nos"]} é o {g["pos"]}º do grupo, com {g["pts"]} pontos em {g["j"]} jogos.'),
                          ('helena', 'Na fase de grupos, o saldo de gols costuma decidir. Não dá para tirar o pé.'),
                          ('carlao', 'Copa é outra história. Noite europeia não perdoa vacilo.' if 'Champions' in o['competicao']
                           else 'Copa é mata-mata no coração. Tem que ter casca.')]}
    return None


@pauta
def copa_favoritos(M, rnd):
    for o in M['outras']:
        times = {g['time'] for g in o.get('grupo') or []}
        comp = next((p['comp'] for p in M['jogos'][::-1] if M['s'].name(p['time1'] if p['time1'] != M['ti'] else p['time2']).strip() in times), None)
        if comp is None:
            continue
        idx = {t for p in M['todas'] if p['comp'] == comp for t in (p['time1'], p['time2'])}
        fav = sorted((i for i in idx if i in M['forca']), key=lambda i: -M['forca'][i])[:3]
        if len(fav) < 3:
            continue
        nomes = [M['s'].name(i).strip() for i in fav]
        return {'id': 'copa_favoritos', 'cat': 'copa', 'peso': 4, 'titulo': f'Favoritos na {o["competicao"]}',
                'falas': [('rogerio', f'Pela força dos elencos, os favoritos na {o["competicao"]} são {_lista(nomes)}.'),
                          ('helena', f'O {nomes[0]} tem o elenco mais forte no papel, mas copa se decide em detalhes.'),
                          ('toninho', 'Favorito em copa é igual previsão do tempo: ninguém acerta!')],
                'enquete': _enquete(f'Quem ganha a {o["competicao"]}?', [(n, 4 - i) for i, n in enumerate(nomes)], rnd)}
    return None


# ----- jogadores do elenco
def _J(M, cond):
    return [j for j in M['J'] if cond(j)]


@pauta
def artilheiro_time(M, rnd):
    js = sorted(_J(M, lambda j: j['t_gols'] >= 5), key=lambda j: -j['t_gols'])
    if not js:
        return None
    a = js[0]
    return {'id': 'artilheiro_time', 'cat': 'jogador', 'peso': 5, 'titulo': f'{a["nome"]}, o homem-gol',
            'falas': [('rogerio', f'{a["nome"]} já tem {a["t_gols"]} gols em {a["t_jogos"]} jogos na temporada. Está entre os melhores?'),
                      ('helena', f'Média de {_n(a["t_gols"] / max(1, a["t_jogos"]))} gol por jogo. É número de artilheiro de elite.'),
                      ('toninho', f'O {a["nome"]} tá fazendo gol até em treino de pênalti com goleiro de olho fechado!')],
            'posts': [(_torc(M), f'{a["nome"]} é diferenciado demais, {a["t_gols"]} gols! 🐐')]}


@pauta
def em_alta(M, rnd):
    js = sorted(_J(M, lambda j: j['r_nota'] and j['t_nota'] and j['t_jogos'] >= 5 and j['r_nota'] >= j['t_nota'] + 0.3),
                key=lambda j: -(j['r_nota'] - j['t_nota']))
    if not js:
        return None
    j = js[0]
    return {'id': 'em_alta', 'cat': 'jogador', 'peso': 5, 'titulo': f'{j["nome"]} em alta',
            'falas': [('rogerio', f'{j["nome"]} vive grande fase: média {_n(j["r_nota"])} nos últimos jogos, acima dos {_n(j["t_nota"])} da temporada.'),
                      ('beto', f'No CT, o {j["nome"]} tem ficado depois do treino para trabalho extra.'),
                      ('carlao', f'Esse é o {j["nome"]} que eu gosto de ver. Jogando com fome.')]}


@pauta
def em_baixa(M, rnd):
    js = sorted(_J(M, lambda j: j['r_nota'] and j['t_nota'] and j['t_jogos'] >= 5 and j['r_nota'] <= j['t_nota'] - 0.3),
                key=lambda j: j['r_nota'] - j['t_nota'])
    if not js:
        return None
    j = js[0]
    if _cobranca_lenda(M, j['k'], j['nome'], rnd):   # craque famoso em baixa: cobrança maior
        return _com_lenda(M, j, rnd)
    return {'id': 'em_baixa', 'cat': 'jogador', 'peso': 6, 'titulo': f'O que houve com {j["nome"]}?',
            'falas': [('rogerio', f'{j["nome"]} caiu: média {_n(j["r_nota"])} nos últimos jogos, contra {_n(j["t_nota"])} na temporada.'),
                      ('toninho', rnd.choice([f'O {j["nome"]} tá jogando com o freio de mão puxado! Alguém solta isso, pelo amor!',
                                              f'Cadê o {j["nome"]}? Mandaram o sósia jogar no lugar dele!'])),
                      ('carlao', f'Jogador grande não se esconde. O {j["nome"]} tem que chamar a responsabilidade.'),
                      ('helena', 'Às vezes é desgaste físico. Uma rodada de descanso pode resolver.')],
            'enquete': _enquete(f'{j["nome"]} deve ir para o banco?', [('Sim', 1.0), ('Não, é fase', 1.1)], rnd),
            'posts': [('@zoeira_fc', f'{j["nome"]} ultimamente: 📉📉📉')]}


def _com_lenda(M, j, rnd):
    """em_baixa de um jogador famoso: a cobrança é maior (e a resenha, mais quente)."""
    return {'id': 'em_baixa', 'cat': 'jogador', 'peso': 8, 'titulo': f'Crise do craque: {j["nome"]}',
            'falas': [('rogerio', f'{j["nome"]} caiu: média {_n(j["r_nota"])} nos últimos jogos, contra {_n(j["t_nota"])} na temporada. E não é qualquer um: {_resumo(M, j["k"])}.'),
                      _cobranca_lenda(M, j['k'], j['nome'], rnd),
                      ('carlao', f'Calma! Jogador desse tamanho tem crédito eterno. O {j["nome"]} já ganhou tudo por esse clube.'),
                      ('helena', 'Até os maiores oscilam. A questão é se é cansaço físico ou queda técnica, e os números apontam desgaste.')],
            'enquete': _enquete(f'{j["nome"]} está em declínio?', [('Sim, já era', 0.6), ('Não, é fase', 1.3)], rnd),
            'posts': [('@antigoat_fc', f'Cadê o "melhor do mundo"? {j["nome"]} sumiu 👻'),
                      (_torc(M), f'Respeitem a história do {j["nome"]}. Ele volta! 👑')]}


@pauta
def jejum_atacante(M, rnd):
    ti = M['ti']
    for j in sorted(_J(M, lambda j: j['pos'] in ATA and j['ovr'] >= 78), key=lambda j: -j['ovr']):
        n = 0
        for p in reversed(M['jogos']):
            linhas = p['linhas1'] if p['time1'] == ti else p['linhas2']
            x = next((x for x in linhas if (x['reg'], x['pid']) == j['k']), None)
            if not x or x['minutos'] < 45:
                continue
            if x['gols']:
                break
            n += 1
        if n >= 4:
            extra = _cobranca_lenda(M, j['k'], j['nome'], rnd)
            return {'id': 'jejum_atacante', 'cat': 'jogador', 'peso': 9 if extra else 7, 'titulo': f'Jejum do {j["nome"]}',
                    'extra': extra,
                    'falas': [('rogerio', f'{j["nome"]} não marca há {n} jogos como titular. Preocupa?'),
                              ('toninho', rnd.choice([f'O {j["nome"]} não acerta o gol nem se o goleiro sair para buscar água!',
                                                      f'Se o {j["nome"]} cair do barco, não acerta a água!'])),
                              ('helena', f'Atacante vive de confiança. O {j["nome"]} continua finalizando? Isso é o que importa.'),
                              ('carlao', 'Gol é igual ketchup: não sai, não sai, depois sai tudo de uma vez.')],
                    'posts': [('@zoeira_fc', f'{j["nome"]} procurando o gol: 🔍❌ ({n} jogos)'), (_torc(M), f'Força, {j["nome"]}! O gol vai sair.')]}
    return None


@pauta
def garcom(M, rnd):
    js = sorted(_J(M, lambda j: j['t_assist'] >= 4), key=lambda j: -j['t_assist'])
    if not js:
        return None
    g = js[0]
    return {'id': 'garcom', 'cat': 'jogador', 'peso': 4, 'titulo': f'{g["nome"]}, o garçom',
            'falas': [('rogerio', f'{g["nome"]} já deu {g["t_assist"]} assistências. É o cérebro do time?'),
                      ('helena', 'Assistência é a parte visível. O passe antes da assistência também é dele, muitas vezes.'),
                      ('toninho', f'O {g["nome"]} serve mais que garçom de rodízio!')]}


@pauta
def jovem_promessa(M, rnd):
    js = sorted(_J(M, lambda j: j['idade'] <= 21 and (j['t_jogos'] >= 3 or j.get('funcao') == 'Jovem promessa')), key=lambda j: -j['ovr'])
    if not js:
        return None
    j = js[0]
    return {'id': 'jovem_promessa', 'cat': 'jogador', 'peso': 5, 'titulo': f'{j["nome"]}, a joia',
            'falas': [('rogerio', f'{j["nome"]}, {j["idade"]} anos, nota {j["ovr"]}: {j["t_jogos"]} jogos na temporada. É a próxima estrela?'),
                      ('beto', f'Tem clube grande de olho no {j["nome"]}. A diretoria já recusou sondagens.'),
                      ('carlao', 'Garoto tem que jogar com pé no chão. Muita gente boa se perdeu com elogio cedo.'),
                      ('toninho', f'O {j["nome"]} tem cara de quem ainda pede autorização para a mãe para ir ao treino!')],
            'enquete': _enquete(f'{j["nome"]} merece ser titular?', [('Sim', 1.0), ('Ainda não', 0.9)], rnd)}


@pauta
def veterano(M, rnd):
    js = sorted(_J(M, lambda j: j['idade'] >= 33 and j['t_jogos'] >= 4), key=lambda j: -j['t_jogos'])
    if not js:
        return None
    j = js[0]
    ok = j['t_nota'] and j['t_nota'] >= 6.3
    return {'id': 'veterano', 'cat': 'jogador', 'peso': 4, 'titulo': f'{j["nome"]} aos {j["idade"]}',
            'falas': [('rogerio', f'{j["nome"]} tem {j["idade"]} anos e {j["t_jogos"]} jogos na temporada. ' + ('Ainda decide?' if ok else 'Chegou a hora de parar?')),
                      ('carlao', 'Experiência não se compra. Vestiário precisa de gente rodada.' if ok else 'Todo mundo tem a sua hora. Respeito, mas a hora chega.'),
                      ('toninho', f'O {j["nome"]} é tão rodado que jogou contra o meu avô!')]}


@pauta
def reserva_insatisfeito(M, rnd):
    js = sorted(_J(M, lambda j: j['moral'] < 45 and j['status'] in ('Lenda', 'Ídolo', 'Superastro', 'Craque')), key=lambda j: j['moral'])
    if not js:
        return None
    j = js[0]
    return {'id': 'reserva_insatisfeito', 'cat': 'vestiario', 'peso': 6, 'titulo': f'{j["nome"]} insatisfeito',
            'falas': [('rogerio', f'{j["nome"]} ({j["status"]}) anda insatisfeito: ' + (j['motivos'][0] if j.get('motivos') else 'clima ruim') + '.'),
                      ('beto', f'O estafe do {j["nome"]} já procurou a diretoria. A situação é real.'),
                      ('carlao', f'O {j["nome"]} tem que mostrar no treino. Reclamar na imprensa não ganha posição.'),
                      ('helena', 'Jogador insatisfeito rende menos e contamina o grupo. Precisa de conversa.')],
            'enquete': _enquete(f'O {j["nome"]} deve sair?', [('Fica', 1.0), ('Vende', 0.8)], rnd)}


def _conflito(M, tipo):
    return next((c for c in M['conflitos'] if c[0] == tipo), None)


@pauta
def bracadeira(M, rnd):
    c = _conflito(M, 'Braçadeira')
    if not c:
        return None
    a, b = c[2][0], c[2][1]
    return {'id': 'bracadeira', 'cat': 'vestiario', 'peso': 6, 'titulo': 'De quem é a faixa?',
            'falas': [('rogerio', f'{a["nome"]} quer a braçadeira de {b["nome"]}. Quem deve ser o capitão?'),
                      ('carlao', 'Capitão é quem fala no vestiário quando o time perde. Não é quem posa para foto.'),
                      ('beto', 'No CT, o assunto é tratado com cuidado. Os dois são queridos pelo grupo.'),
                      ('toninho', 'Faz par ou ímpar e acaba logo com isso!')],
            'enquete': _enquete('Quem deve ser o capitão?', [(a['nome'], a['lider']), (b['nome'], b['lider'])], rnd)}


@pauta
def ego_salarial(M, rnd):
    c = _conflito(M, 'Ego salarial')
    if not c:
        return None
    rico = c[2][0]
    return {'id': 'ego_salarial', 'cat': 'vestiario', 'peso': 5, 'titulo': 'A folha salarial',
            'falas': [('rogerio', f'Polêmica: {c[1]}.'),
                      ('helena', 'Disparidade salarial sem rendimento correspondente desequilibra qualquer vestiário.'),
                      ('toninho', f'O {rico["nome"]} recebe tanto que o contracheque dele vem com índice!'),
                      ('beto', 'Tem jogador pedindo reunião com a diretoria por causa disso.')]}


@pauta
def contrato(M, rnd):
    hoje = M['hoje']
    js = [j for j in M['J'] if j['contrato'] and 0 <= _dias(tuple(j['contrato']), hoje) <= 365 and j['status'] in ('Lenda', 'Ídolo', 'Superastro', 'Craque')]
    if not js:
        return None
    j = max(js, key=lambda j: j['ovr'])
    c = j['contrato']
    return {'id': 'contrato', 'cat': 'mercado', 'peso': 6, 'titulo': f'Renova ou vende o {j["nome"]}?',
            'falas': [('rogerio', f'O contrato de {j["nome"]} acaba em {c[2]:02d}/{c[1]:02d}/{c[0]}. Renova ou vende?'),
                      ('helena', 'Esperar é o pior cenário: no fim do contrato, o clube perde o jogador de graça.'),
                      ('beto', f'O empresário do {j["nome"]} espera proposta até o fim do mês. Tem clube de fora sondando.'),
                      ('carlao', f'Renova amanhã! Jogador desse nível não se acha na esquina.')],
            'enquete': _enquete(f'O clube deve renovar com {j["nome"]}?', [('Renova!', 1.2), ('Vende', 0.6)], rnd)}


@pauta
def apelidos(M, rnd):
    try:
        import apelidos as ap
        cat = ap.catalogo()
    except Exception:  # noqa: BLE001
        return None
    com = [(j['nome'], cat.get(j.get('apelido') or 0)) for j in M['J'] if cat.get(j.get('apelido') or 0)]
    if len(com) < 2:
        return None
    return {'id': 'apelidos', 'cat': 'resenha', 'peso': 2, 'titulo': 'Os apelidos do elenco',
            'falas': [('rogerio', 'Resenha: os apelidos da torcida. ' + '; '.join(f'{n}, o "{a}"' for n, a in com[:5]) + '.'),
                      ('toninho', 'Eu tinha apelido de "Maestro". Mas era porque eu regia a resenha no ônibus!'),
                      ('beto', 'Os jogadores adoram. Tem gente que já pôs o apelido até na chuteira.')]}


@pauta
def lider_vestiario(M, rnd):
    if not M['lideres']:
        return None
    l = M['lideres'][0]
    return {'id': 'lider_vestiario', 'cat': 'vestiario', 'peso': 3, 'titulo': f'{l["nome"]}, a voz do vestiário',
            'falas': [('rogerio', f'Quem manda no vestiário? Pelos bastidores, {l["nome"]}.'),
                      ('beto', f'Quando o bicho pega, é o {l["nome"]} que chama o grupo para conversar.'),
                      ('carlao', 'Todo time campeão tem um cara assim. Liderança não se treina.')]}


@pauta
def selecao(M, rnd):
    conv = []
    for j in M['J']:
        ds = [x for x in M['selecao'].get(j['k'], []) if 0 <= _dias(M['hoje'], x) <= 30]
        if ds:
            conv.append(j['nome'])
    if not conv:
        return None
    return {'id': 'selecao', 'cat': 'jogador', 'peso': 4, 'titulo': 'Voltando da seleção',
            'falas': [('rogerio', f'{_lista(conv[:4])} defenderam suas seleções neste mês. O desgaste preocupa?'),
                      ('helena', 'Viagem longa e fuso tiram rendimento. Rodízio na volta é recomendável.'),
                      ('carlao', 'Jogador de seleção tem que aguentar. É o preço de ser bom.')]}


# ----- mercado
@pauta
def movimento_elenco(M, rnd):
    """Saída/chegada do NOSSO elenco (saidas.py): a estrela que vai embora, o reforço que chega."""
    movs = [m for m in M['r'].get('movimentos') or [] if m['tipo'] in ('saida', 'chegada')]
    if not movs:
        return None
    import saidas
    top4 = {t['time'] for t in M['tab'][:4]}
    m, n = saidas.principal(movs, M['J'], M['car'].get('ck'), M['nos'], top4)
    nome, dest = m['nome'], m['clube']
    if m['tipo'] == 'chegada':
        f = [('rogerio', f'Reforço no {M["nos"]}: {n["lead"]}'),
             ('helena', f'{nome} chega para disputar posição. A pergunta é quem perde espaço.'),
             ('carlao', 'Contratação boa é a que resolve em campo. Quero ver na primeira dividida.'),
             ('toninho', f'O {nome} já chegou perguntando onde fica a sala de troféus!')]
        return {'id': f'mov|{nome}', 'cat': 'mercado', 'peso': 8, 'titulo': f'Chegou: {nome}', 'falas': f,
                'enquete': _enquete(f'{nome} vai ser titular?', [('Sim', 1.1), ('Vai brigar por espaço', 1.0)], rnd),
                'posts': [(_torc(M), x) for x in n['torcida']]}
    f = [('rogerio', f'A notícia da semana: {n["lead"]}')]
    st = n.get('setor') or saidas.setor(m.get('pos_campo'))
    # quem herda a vaga: o próximo do MESMO setor pela nota (12/10/2026: a conversa respeita a posição)
    herdeiro = max((j for j in M['J'] if j['nome'] != nome and saidas.setor(j['pos']) == st), key=lambda j: j['ovr'], default=None)
    if n['tipo'] == 'sombra' and st in ('gol', 'zaga', 'lateral'):
        f += [('helena', f'O roteiro é conhecido: {n["analogia"]}. ' + {
                  'gol': 'Goleiro reserva quase não joga, perde ritmo e valor de mercado. Sair era questão de tempo.',
                  'zaga': 'Zagueiro precisa de sequência para ganhar entrosamento com o parceiro. Na reserva, isso não acontece.',
                  'lateral': 'Lateral moderno precisa de minutos para ganhar confiança de apoiar o ataque.'}[st]),
              ('carlao', {'gol': f'Goleiro tem que jogar! Atrás do {n["sombra"]}, o {nome} ia virar enfeite de banco.',
                          'zaga': f'Zagueiro bom quer ser o xerife, não o quarto da fila. Com o {n["sombra"]} lá, não tinha jeito.',
                          'lateral': f'Foi atrás de espaço, fez certo. A lateral era do {n["sombra"]}.'}[st]),
              ('beto', 'Apurei que o estafe pedia minutos há meses. A proposta de ser titular resolveu a conversa.'),
              ('toninho', {'gol': f'Agora o {nome} vai poder sujar o uniforme! Aqui só sujava de banco!',
                           'zaga': f'O {nome} vai ter tanto trabalho lá que vai sentir saudade do banco daqui!',
                           'lateral': f'O {nome} vai correr a lateral inteira lá. Aqui ele só corria no aquecimento!'}[st])]
        enq = _enquete(f'O {nome} acertou em sair para jogar?', [('Acertou', 1.3), ('Devia esperar a vez', 0.7)], rnd)
    elif n['tipo'] == 'sombra':
        f += [('helena', f'O roteiro é conhecido: {n["analogia"]}. O {nome} quer ser o primeiro violino, não o segundo.'),
              ('carlao', f'Eu entendo o {nome}. Jogador grande quer ser o dono do time. Ao lado do {n["sombra"]}, isso nunca ia acontecer.'),
              ('beto', f'Apurei que o {nome} já conversava com o estafe sobre isso desde o vice da Bola de Ouro. Ele queria ser o rosto do projeto.'),
              ('toninho', f'Saiu da sombra do {n["sombra"]} e foi para o sol {"da" if saidas.art(dest) == "a" else "do"} {dest.title()}! Só espero que não se queime!')]
        enq = _enquete(f'O {nome} acertou em sair para ser protagonista?', [('Acertou', 1.0), ('Errou, ia ganhar tudo aqui', 1.1)], rnd)
        outros = [x['nome'] for x in movs if x['tipo'] == 'saida' and x['nome'] != nome]
        if outros:
            f.append(('rogerio', f'E não foi só ele: {", ".join(outros)} também deixaram o clube. A diretoria vai ao mercado?'))
    elif n['tipo'] == 'rival':
        f += [('carlao', 'Para o rival? Isso não se faz! Tem coisa que dinheiro nenhum paga.'),
              ('helena', f'Esportivamente, o {dest} se fortalece contra nós. É duplo prejuízo.'),
              ('toninho', f'O {nome} vai ser recebido com festa no primeiro reencontro... festa de vaia!')]
        enq = _enquete(f'{nome} é traidor?', [('Traidor!', 1.2), ('É profissional', 0.8)], rnd)
    else:
        f += [('helena', f'{"O valor é alto: R$ " + saidas._mi(m["valor"]) + " milhões." if m["valor"] >= 30e6 else "Negócio de mercado."} '
                         + (f'Em {saidas.SETOR_TXT[st]}, o substituto natural é {herdeiro["nome"]}, nota {herdeiro["ovr"]}.' if herdeiro else
                            f'E {saidas.SETOR_TXT[st]} fica sem reposição no elenco.')),
              ('carlao', f'Saiu, saiu. Agora o técnico tem que achar a reposição.' if n['tipo'] != 'idolo' else f'Ídolo não se vende. Isso dói no coração do torcedor.'),
              ('toninho', f'Vai com Deus, {nome}! E leva o meu currículo junto, que eu também topo!')]
        enq = _enquete(f'O clube errou em deixar o {nome} sair?', [('Errou', 1.0), ('Fez bem', 0.9)], rnd)
    return {'id': f'mov|{nome}', 'cat': 'mercado', 'peso': 13 if n['tipo'] in ('sombra', 'rival', 'idolo') else 7,
            'titulo': n['titulo'], 'falas': f, 'enquete': enq,
            'posts': [(_torc(M), x) for x in n['torcida']] + [(f'@{_slug(dest)}_raiz', x) for x in n['rival']] +
                     [('@mercadodabola', f'OFICIAL: {nome} ' + (f'vai jogar {"na" if saidas.art(dest) == "a" else "no"}' if m['pendente'] else f'é {"da" if saidas.art(dest) == "a" else "do"}') + f' {dest}.' + (f' Valor: R$ {saidas._mi(m["valor"])} mi' if m['valor'] >= 1e6 else '') + ' ✍️')]}


@pauta
def maior_negocio(M, rnd):
    if not M['negocios']:
        return None
    n = M['negocios'][0]
    return {'id': 'maior_negocio', 'cat': 'mercado', 'peso': 5, 'titulo': f'{n["jogador"]} no {n["para"]}',
            'falas': [('rogerio', f'O negócio da janela: {n["para"]} contratou {n["jogador"]} do {n["de"]} por {_n(n["valor"])} milhões.'),
                      ('helena', f'Pelo perfil, o {n["para"]} buscou o jogador para {n["motivo"].split(";")[0]}.'),
                      ('toninho', f'{_n(n["valor"])} milhões? Por esse preço eu queria que ele lavasse o meu carro também!'),
                      ('beto', 'No mercado, comenta-se que teve leilão até o último minuto.')],
            'posts': [('@mercadodabola', f'OFICIAL: {n["jogador"]} é do {n["para"]}. Valor: {_n(n["valor"])} mi. ✍️')]}


@pauta
def rival_reforcou(M, rnd):
    liga = {t['time'] for t in M['tab']}
    rs = [n for n in M['negocios'] if n['para'] in liga and n['para'] != M['nos']]
    if len(rs) < 2:
        return None
    return {'id': 'rival_reforcou', 'cat': 'mercado', 'peso': 5, 'titulo': 'Os rivais foram às compras',
            'falas': [('rogerio', 'Os rivais se reforçaram: ' + '; '.join(f'{n["para"]} trouxe {n["jogador"]}' for n in rs[:4]) + '.'),
                      ('carlao', f'E o {M["nos"]}? Vai ficar olhando? Rival forte exige resposta!'),
                      ('helena', 'Reforço no meio da temporada precisa de adaptação. O efeito não é imediato.')],
            'enquete': _enquete(f'O {M["nos"]} precisa contratar?', [('Sim, urgente', 1.0), ('O elenco basta', 1.0)], rnd)}


@pauta
def time_precisa(M, rnd):
    e = M['esc']
    if not e or len(e['jogadores']) < 11:
        return None
    js = [j for j in e['jogadores'] if j['nota']]
    if not js:
        return None
    med = sum(j['nota'] for j in js) / len(js)
    fraco = min(js, key=lambda j: j['nota'])
    if fraco['nota'] > med - 4:
        return None
    return {'id': 'time_precisa', 'cat': 'mercado', 'peso': 4, 'titulo': f'Falta um {fraco["pos"]}?',
            'falas': [('rogerio', f'No time titular, o ponto mais fraco é o {fraco["pos"]}: {fraco["nome"]}, nota {fraco["nota"]}, contra média {round(med)} do time.'),
                      ('helena', 'O elo mais fraco é o primeiro a ser atacado pelos adversários.'),
                      ('carlao', 'Contrata! Time com pretensão não pode ter buraco no time titular.'),
                      ('toninho', f'O {fraco["nome"]} tá no time titular por indicação do sindicato!')]}


@pauta
def vender(M, rnd):
    js = sorted(M['J'], key=lambda j: -j['salario'])[:6]
    meds = sorted(j['ovr'] for j in M['J'])
    med = meds[len(meds) // 2] if meds else 80
    alvo = next((j for j in js if j['ovr'] <= med and j['idade'] >= 29), None)
    if not alvo:
        return None
    return {'id': 'vender', 'cat': 'mercado', 'peso': 4, 'titulo': f'Hora de vender o {alvo["nome"]}?',
            'falas': [('rogerio', f'{alvo["nome"]} está entre os maiores salários e tem nota {alvo["ovr"]}, abaixo da média do elenco. Vende?'),
                      ('helena', 'Pela relação custo-benefício, sim. O salário dele paga um reforço.'),
                      ('carlao', 'Não se vende jogador só por planilha. Tem que ver o que ele dá no vestiário.')],
            'enquete': _enquete(f'Vender o {alvo["nome"]}?', [('Vende', 1.0), ('Fica', 0.9)], rnd)}


# ----- prêmios
def _bola_de_ouro(M):
    cands = []
    rk = M['rank']
    for k, e in M['est'].items():
        i = M['clube_de'].get(k)
        f = M['P'].get(k)
        if f is None or i is None or e['jogos'] < 6 or rk.get(i, 999) > 40:
            continue
        try:
            import encaixe
            ovr = encaixe.rating(f, f.pos)
        except Exception:  # noqa: BLE001
            continue
        if ovr < 86:
            continue
        med = _media(e) or 6
        gk = f.pos == 'GK'
        sc = ovr * 0.6 + (e['gols'] * 1.0 + e['assist'] * 0.6 if not gk else 0) + (med - 6) * 12 + max(0, 12 - rk[i]) * 0.4
        cands.append({'sc': sc, 'nome': f.name.strip(), 'time': M['s'].name(i).strip(), 'pos': f.pos, 'gols': e['gols'],
                      'assist': e['assist'], 'jogos': e['jogos'], 'media': med})
    return sorted(cands, key=lambda c: -c['sc'])[:5]


@pauta
def bola_de_ouro(M, rnd):
    top = _bola_de_ouro(M)
    if len(top) < 3:
        return None
    a, b, c = top[:3]
    meu = next((x for x in top if x['time'] == M['nos']), None)
    dono = ((M.get('hall') or {}).get('bolas') or [None])[0]
    seguidas = 0
    if dono:
        anos = sorted(x['ano'] for x in M['hall']['bolas'] if x['nome'] == dono['nome'])
        seguidas = 1
        while len(anos) > seguidas and anos[-1 - seguidas] == anos[-1] - seguidas:
            seguidas += 1
    return {'id': 'bola_de_ouro', 'cat': 'premio', 'peso': 6, 'titulo': 'Corrida pela Bola de Ouro',
            'falas': ([('rogerio', f'O atual dono da Bola de Ouro é {dono["nome"]}, campeão de {dono["ano"]}'
                                   + (f', com {seguidas} seguidas.' if seguidas >= 2 else '.') + ' Ele leva de novo?')] if dono else []) +
                     [('rogerio', 'A corrida da Bola de Ouro, pelos números da temporada: '
                       + '; '.join(f'{x["nome"]} ({x["time"]}): {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos' for x in top[:3]) + '.'),
                      ('helena', f'O {a["nome"]} une regularidade (média {_n(a["media"])}) e clube forte. Hoje é o favorito.'),
                      ('carlao', f'Bola de Ouro se ganha com título. Se o {b["time"]} levantar taça, o {b["nome"]} passa na frente.'),
                      ('toninho', f'Eu dava a Bola de Ouro para o {meu["nome"]}, mas eu sou suspeito!' if meu else
                       f'O {c["nome"]} vai fazer campanha de vereador para ganhar voto!')],
            'enquete': _enquete('Quem merece a Bola de Ouro?', [(f'{x["nome"]} ({x["time"]})', x['sc'] ** 2) for x in top[:4]], rnd),
            'posts': [('@numerosdabola', f'Top 3 da corrida pela Bola de Ouro: {a["nome"]}, {b["nome"]} e {c["nome"]}. 🏆')]}


@pauta
def craque_liga(M, rnd):
    if M['eu'] and M['eu']['j'] < 8:
        return None
    idx = {M['s'].find_team(t['time']) for t in M['tab']} - {None}
    cs = []
    for k, e in M['est'].items():
        if M['clube_de'].get(k) in idx and e['jogos'] >= 6:
            f = M['P'].get(k)
            if f:
                cs.append(((_media(e) or 6) + 0.12 * e['gols'] + 0.08 * e['assist'], f.name.strip(), M['s'].name(M['clube_de'][k]).strip(), e))
    if len(cs) < 3:
        return None
    cs.sort(reverse=True)
    _, nome, time, e = cs[0]
    return {'id': 'craque_liga', 'cat': 'premio', 'peso': 4, 'titulo': f'Craque da {M["liga"]}: {nome}?',
            'falas': [('rogerio', f'Pelos números, o melhor da {M["liga"]} até aqui é {nome}, do {time}: média {_n(_media(e))}, {e["gols"]} gols e {e["assist"]} assistências.'),
                      ('helena', f'Em seguida vêm {cs[1][1]} ({cs[1][2]}) e {cs[2][1]} ({cs[2][2]}).'),
                      ('toninho', f'Se o {nome} jogasse no meu time de pelada, eu deixava ele bater até os laterais!')]}


# ----- clube
@pauta
def trabalho_tecnico(M, rnd):
    dif = M['dif']
    if not dif:
        return None
    dias = dif.get('dias_clube') or 0
    tec = M['r'].get('tecnico') or 'o técnico'
    eu = M['eu']
    apr = round(100 * eu['pts'] / (3 * eu['j'])) if eu and eu['j'] else None
    return {'id': 'trabalho_tecnico', 'cat': 'clube', 'peso': 4, 'titulo': f'O trabalho de {tec}',
            'falas': [('rogerio', f'{tec} completa {dias} dias no clube' + (f', com {apr}% de aproveitamento na liga.' if apr is not None else '.') + ' Que nota vocês dão?'),
                      ('helena', f'O espírito de equipe está em {dif.get("espirito")}. ' + ('Grupo fechado com o técnico.' if (dif.get('espirito') or 0) >= 80 else 'Ainda há gente para conquistar.')),
                      ('carlao', 'Técnico bom é o que tira o melhor de quem tem. O resto é conversa.'),
                      ('toninho', f'O {tec} tem prancheta de ouro ou é sorte de principiante?')]}


@pauta
def clima_vestiario(M, rnd):
    dif = M['dif']
    crise = next((c for c in M['casos'] if c.get('tipo') == 'crise' and c.get('data') and _dias(M['hoje'], tuple(c['data'])) <= 14), None)
    if not crise and dif.get('nivel') not in ('tenso', 'explosivo'):
        return None
    tit = crise['titulo'] if crise else 'vestiário tenso'
    return {'id': 'clima_vestiario', 'cat': 'vestiario', 'peso': 8 if crise else 6, 'titulo': 'Clima no vestiário',
            'falas': [('rogerio', f'Assunto quente: {tit}. O técnico perdeu o vestiário?'),
                      ('beto', 'Apurei que houve reunião fechada. Nem todo mundo saiu satisfeito.'),
                      ('carlao', 'Roupa suja se lava em casa! Vazou, é porque tem gente querendo derrubar alguém.'),
                      ('toninho', 'Esse vestiário tá mais agitado que grupo de família no domingo!')],
            'posts': [('@setorista_beto', f'Bastidores: {tit}. Clima pesado no CT. 👀')]}


@pauta
def disciplina(M, rnd):
    rec = [h for h in M['disc'] if h.get('data') and _dias(M['hoje'], tuple(h['data'])) <= 21]
    if not rec:
        return None
    h = rec[-1]
    return {'id': 'disciplina', 'cat': 'vestiario', 'peso': 6, 'titulo': 'Caso disciplinar',
            'falas': [('rogerio', f'Caso disciplinar: {h.get("titulo", "problema no CT")}. Decisão: {h.get("decisao", "em aberto")}.'),
                      ('carlao', 'Regra é regra. Vale para o craque e para o reserva.'),
                      ('toninho', 'No meu tempo, o atraso era culpa do trânsito. Hoje é culpa do stories!'),
                      ('helena', 'Coerência na punição é o que mantém o grupo unido.')],
            'enquete': _enquete('A punição foi justa?', [('Justa', 1.1), ('Pegou leve', 0.7), ('Exagerou', 0.4)], rnd)}


@pauta
def patrocinio_imagem(M, rnd):
    img = M['pat'].get('imagem')
    if img is None:
        return None
    c = M['pat'].get('contrato')
    if img >= 45 and not c:
        return None
    return {'id': 'patrocinio_imagem', 'cat': 'clube', 'peso': 6 if img < 35 else 3, 'titulo': 'A imagem do clube',
            'falas': [('rogerio', f'A imagem do clube está em {img} de 100.' + (f' A {c["marca"]} acompanha de perto.' if c else '')),
                      ('beto', 'O departamento comercial anda preocupado com as polêmicas.' if img < 45 else 'O comercial está satisfeito: patrocinador gosta de vitória e paz.'),
                      ('helena', 'Imagem afeta receita. Receita afeta elenco. Tudo está ligado.')]}


@pauta
def torcida(M, rnd):
    if not M['socios']:
        return None
    return {'id': 'torcida', 'cat': 'clube', 'peso': 2, 'titulo': 'A força da torcida',
            'falas': [('rogerio', f'O {M["nos"]} tem {M["socios"]:,} sócios-torcedores.'.replace(',', '.') + ' A torcida está jogando junto?'),
                      ('carlao', 'Torcida é o 12º jogador. Quem nunca jogou com estádio cheio não sabe o que é.'),
                      ('toninho', 'A torcida canta tanto que o vizinho do estádio já pediu mudança!')]}


# ----- legado: a carreira dos atletas (legado.py)
def _pf(M, k):
    return (M.get('perfis') or {}).get(k)


def _resumo(M, k, curto=True):
    pf = _pf(M, k)
    if not pf or pf['nivel'] == 'normal':
        return ''
    import legado
    return legado.resumo(pf, curto)


def _cobranca_lenda(M, k, nome, rnd):
    """Fala extra quando quem vai mal é uma lenda: o hater cresce com a fama."""
    pf = _pf(M, k)
    if not pf or pf['nivel'] not in ('mito', 'lenda', 'craque mundial'):
        return None
    return ('toninho', rnd.choice([f'E olha que é o {nome}, hein? {_resumo(M, k).capitalize()} no currículo e jogando isso aí!',
                                   f'O {nome} tá vivendo de passado! Currículo não entra em campo, meu filho!']))


def _apelido(M, j):
    return M['apelido'].get(j.get('apelido') or 0, '')


@pauta
def lenda(M, rnd):
    cands = [(pf['fama'], k) for k, pf in (M.get('perfis') or {}).items() if pf['nivel'] in ('mito', 'lenda')]
    if not cands:
        return None
    _, k = max(cands)
    pf = M['perfis'][k]
    j = next(j for j in M['J'] if j['k'] == k)
    import legado
    brasil = M['selecao_de'].get(k) == 'BRASIL'
    comp = dict(legado.comparacoes(pf, brasil))
    nb = len(pf['bolas'])
    ap = _apelido(M, j)
    quem = f'{j["nome"]}, o "{ap}",' if ap else j['nome']
    f = [('rogerio', f'Hoje a mesa vai falar de história. {quem} soma {legado.resumo(pf, False)}. Onde ele já está na história do futebol?')]
    if pf['bolas_seguidas'] >= 4:
        f.append(('helena', f'{pf["bolas_seguidas"]} Bolas de Ouro seguidas. Na história real, só Lionel Messi fez isso, de 2009 a 2012. É esse o tamanho.'))
    elif nb:
        f.append(('helena', f'São {nb} Bolas de Ouro: ' + ', '.join(str(a) for a in pf['bolas']) + '. E o pódio de outros anos mostra regularidade.'))
    if 'alvo' in comp:
        a = comp['alvo']
        f.append(('carlao', f'Para mim, ainda falta alcançar o {a[0]}, que tem {a[2]}. Quando passar, aí a gente conversa sobre o maior de todos.'))
    if 'superou' in comp:
        s_ = comp['superou']
        f.append(('toninho', f'Já passou o {s_[0]}, que tem {s_[2]}! E ainda tem gente que torce o nariz para ele!'))
    if pf['artilharias']:
        f.append(('beto', f'No CT, os mais novos param o treino para ver o {j["nome"]} finalizar. Foram {len(pf["artilharias"])} artilharias na carreira.'))
    alvo = comp.get('alvo', ('Messi', 8, ''))[0]
    return {'id': 'lenda', 'cat': 'premio', 'peso': 9 if pf['nivel'] == 'mito' else 7, 'titulo': f'{j["nome"]} e a história',
            'falas': f,
            'enquete': _enquete(f'{j["nome"]} já é maior que {alvo}?', [('Já é!', 1.0 + nb / 6), ('Ainda não', 1.0)], rnd),
            'posts': [(_torc(M), f'{nb} BOLAS DE OURO. Respeitem o {j["nome"]}! #GOAT 🐐👑'),
                      ('@antigoat_fc', rnd.choice([f'{j["nome"]} só ganha porque joga no time mais forte. Quero ver no meio da tabela 🤡',
                                                   f'Bola de Ouro virou prêmio de participação, né? {j["nome"]} de novo... 🙄'])),
                      ('@numerosdabola', f'{j["nome"]}: {legado.resumo(pf, False)}. 📊')]}


@pauta
def apuracao_bola(M, rnd):
    rec = M.get('premio_recente')
    if not rec or len(rec['top']) < 3:
        return None
    a, b, c = rec['top'][:3]
    nossos = {j['nome'] for j in M['J']}
    f = [('rogerio', f'Saiu a eleição de melhor jogador do mundo de {rec["ano"]}: {a["nome"]} ({a["clube"]}) com {a["votos"]} votos, '
                     f'{b["nome"]} com {b["votos"]} e {c["nome"]} com {c["votos"]}.')]
    if a['nome'] in nossos:
        k = next(j['k'] for j in M['J'] if j['nome'] == a['nome'])
        pf = _pf(M, k)
        f.append(('carlao', f'Justíssimo! O {a["nome"]} carregou o time nas costas o ano todo.'))
        if pf and len(pf['bolas']) >= 2:
            f.append(('helena', f'Com essa, são {len(pf["bolas"])} Bolas de Ouro. A diferença de votos para o segundo foi de {a["votos"] - b["votos"]}.'))
    else:
        f.append(('helena', f'A diferença para o segundo foi de {a["votos"] - b["votos"]} votos. Eleição sem muita discussão.'))
    if b['nome'] in nossos:
        f.append(('toninho', f'E o {b["nome"]} de novo no quase! Esse aí coleciona medalha de prata!'))
    else:
        f.append(('toninho', f'O {b["nome"]} já tá ensaiando o discurso de "o importante é competir"!'))
    return {'id': 'apuracao_bola', 'cat': 'premio', 'peso': 10, 'titulo': f'Melhor do mundo {rec["ano"]}: {a["nome"]}', 'falas': f,
            'enquete': _enquete('A eleição foi justa?', [('Justíssima', 1.2), ('Roubaram o 2º colocado', 0.6)], rnd),
            'posts': [('@numerosdabola', f'Melhor do mundo {rec["ano"]}: 1º {a["nome"]} ({a["votos"]} votos), 2º {b["nome"]} ({b["votos"]}), 3º {c["nome"]} ({c["votos"]}). 🏆')]}


@pauta
def na_trave(M, rnd):
    nossos = {j['nome'] for j in M['J']}
    tr = [(n, anos) for n, anos in M.get('trave') or [] if n]
    tr.sort(key=lambda x: (x[0] not in nossos, -len(x[1])))
    if not tr:
        return None
    nome, anos = tr[0]
    return {'id': 'na_trave', 'cat': 'premio', 'peso': 6, 'titulo': f'{nome}, sempre na trave',
            'falas': [('rogerio', f'{nome} já foi ao pódio de melhor do mundo em ' + ', '.join(map(str, anos)) + ', mas nunca levou. Falta o quê?'),
                      ('helena', 'Pódio repetido mostra regularidade. O que falta é o ano perfeito, com título grande junto.'),
                      ('toninho', f'O {nome} é o rei do quase! Se tivesse prêmio de vice, já tinha a coleção completa!'),
                      ('carlao', 'Respeita o cara! Estar entre os três melhores do mundo não é para qualquer um.')]}


@pauta
def colecionador(M, rnd):
    cands = [(pf['n_titulos'], k) for k, pf in (M.get('perfis') or {}).items() if pf['n_titulos'] >= 10]
    if not cands:
        return None
    n, k = max(cands)
    pf = M['perfis'][k]
    j = next(j for j in M['J'] if j['k'] == k)
    top = sorted(pf['titulos'].items(), key=lambda x: -x[1])[:3]
    return {'id': 'colecionador', 'cat': 'jogador', 'peso': 4, 'titulo': f'{j["nome"]}, o colecionador de taças',
            'falas': [('rogerio', f'{j["nome"]} já levantou {n} taças: ' + ', '.join(f'{c} ({q})' for c, q in top) + ' entre elas.'),
                      ('beto', f'A sala de troféus do clube tem a cara dessa geração, e o {j["nome"]} está em quase todas as fotos.'),
                      ('toninho', f'O {j["nome"]} já precisa de um armário só para as medalhas!')]}


@pauta
def dinastia(M, rnd):
    tit = (M.get('hall') or {}).get('titulos') or []
    nossos = [t for t in tit if t['campeao'] == M['nos']]
    if len(nossos) < 8:
        return None
    temps = sorted({t['temporada'] for t in nossos})
    por = collections.Counter(t['comp'] for t in nossos)
    return {'id': 'dinastia', 'cat': 'clube', 'peso': 5, 'titulo': 'Dinastia',
            'falas': [('rogerio', f'Desde {temps[0]}, o {M["nos"]} conquistou {len(nossos)} títulos: '
                                  + ', '.join(f'{c} ({q})' for c, q in por.most_common(4)) + '. É uma dinastia?'),
                      ('helena', 'Dinastia se mede por manter o nível com troca de peças. E esse elenco foi renovado sem cair.'),
                      ('carlao', 'Dinastia é isso: ganhar, ganhar e ganhar de novo. O resto é história contada pelos outros.'),
                      ('toninho', 'Os rivais já pediram para mudar o regulamento!')],
            'enquete': _enquete('É a maior dinastia da história do clube?', [('Sim', 1.1), ('Ainda não', 0.8)], rnd)}


@pauta
def artilheiro_serie(M, rnd):
    for k, pf in (M.get('perfis') or {}).items():
        liga = [x for x in pf['artilharias'] if 'Premier' in x[1] or 'Liga' in x[1] or 'Brasileirão' in x[1]]
        if len(liga) >= 3:
            j = next(j for j in M['J'] if j['k'] == k)
            gols = [x[2] for x in liga]
            return {'id': 'artilheiro_serie', 'cat': 'jogador', 'peso': 5, 'titulo': f'{j["nome"]}, dono da artilharia',
                    'falas': [('rogerio', f'{j["nome"]} já foi artilheiro da liga {len(liga)} vezes: '
                                          + ', '.join(f'{t} ({g} gols)' for t, _, g in liga) + '.'),
                              ('helena', f'A melhor marca foi de {max(gols)} gols. Regularidade de artilheiro de elite.'),
                              ('toninho', 'Os zagueiros da liga já fazem terapia em grupo!')]}
    return None


# ----- o mundo (destaques.py): revelações, artilharia do mundo, perigo do adversário, seleção da temporada
_POS_TXT = {'GK': 'goleiro', 'CB': 'zagueiro', 'LB': 'lateral', 'RB': 'lateral', 'DMF': 'volante', 'CMF': 'meia',
            'AMF': 'meia', 'LMF': 'meia', 'RMF': 'meia', 'LWF': 'ponta', 'RWF': 'ponta', 'SS': 'atacante', 'CF': 'centroavante'}


@pauta
def revelacao(M, rnd):
    rv = next((x for x in (M['dest'].get('revelacoes') or []) if x['gols'] + x['assist'] >= 6 and x['jogos'] >= 6), None)
    if not rv:
        return None
    pos = _POS_TXT.get(rv['pos'], 'jogador')
    f = [('rogerio', f'Quem é {rv["nome"]}? O {pos} de {rv["idade"]} anos do {rv["time"]} tem {rv["gols"]} gols e {rv["assist"]} assistências '
                     f'em {rv["jogos"]} jogos. Nota {rv["ovr"]} no game. Ninguém falava dele em agosto.'),
         ('helena', f'É o caso clássico de jogador que rende acima do papel. Média {_n(rv["media"] or 6)} e participação em gol quase toda rodada. '
                    'Isso não é sorte, é encaixe: o time joga para ele.'),
         ('beto', rnd.choice([f'Apurei que já tem olheiro de clube grande indo ver o {rv["nome"]} todo fim de semana.',
                              f'O empresário do {rv["nome"]} já trocou de telefone, de tanto que tocou.'])),
         ('toninho', rnd.choice([f'Esse {rv["nome"]} é o famoso "quem?" que vira "como assim?"! Daqui a pouco tá cobrando caro!',
                                 f'Eu já falava do {rv["nome"]} desde o começo! Mentira, nunca tinha ouvido falar, mas agora eu sou fã!']))]
    if rv['sel_jogos']:
        f.insert(2, ('carlao', f'E já vestiu a camisa da seleção: {rv["sel_jogos"]} jogos. Mérito! Quem faz gol tem que ser chamado, o resto é conversa.'))
    else:
        f.insert(2, ('carlao', f'Tá esperando o que para convocar esse menino? Quem faz {rv["gols"]} gols tem que ser chamado!'))
    if rv['idade'] <= 19:
        f.append(('helena', f'Com {rv["idade"]} anos, o cuidado é não queimar etapa. Tem muito garoto que explode cedo e some.'))
    return {'id': 'revelacao', 'cat': 'liga', 'peso': 6 + (2 if rv['sel_jogos'] else 0), 'titulo': f'Quem é {rv["nome"]}?', 'falas': f,
            'enquete': _enquete(f'{rv["nome"]} merece um clube grande?', [('Já merece', 1.2), ('Precisa provar mais', 0.9)], rnd),
            'posts': [('@scout_global', f'{rv["nome"]}, {rv["idade"]} anos, {rv["time"]}: {rv["gols"]} gols e {rv["assist"]} assistências em {rv["jogos"]} jogos. Anotem esse nome. 📝'),
                      ('@futebol_raiz', f'Ninguém conhecia o {rv["nome"]} no começo da temporada. Hoje é o assunto do futebol. Isso é o esporte. ⚽')]}


@pauta
def artilharia_mundial(M, rnd):
    art = M['dest'].get('artilheiros') or []
    if len(art) < 3 or art[0]['gols'] < 8:
        return None
    a, b, c = art[:3]
    f = [('rogerio', f'Artilharia do mundo, todas as competições de clube: {a["nome"]} ({a["time"]}) com {a["gols"]}, '
                     f'{b["nome"]} ({b["time"]}) com {b["gols"]} e {c["nome"]} ({c["time"]}) com {c["gols"]}.'),
         ('helena', f'O dado do {a["nome"]}: {a["gols"]} gols em {a["jogos"]} jogos. ' + ('Média acima de um gol por jogo. Absurdo.' if a['gols'] > a['jogos'] else 'Ritmo de quem briga pela Chuteira de Ouro.')),
         ('toninho', f'O {a["nome"]} faz gol até no aquecimento! Os goleiros da liga já tão pedindo música no Fantástico de tanto que buscam a bola no fundo!')]
    nosso = next((x for x in art[:6] if x['nosso']), None)
    if nosso and nosso is not a:
        f.append(('carlao', f'E o {nosso["nome"]}, com {nosso["gols"]}? Tem que brigar por isso. Artilharia também é título!'))
    return {'id': 'artilharia_mundial', 'cat': 'liga', 'peso': 4, 'titulo': 'A artilharia do mundo', 'falas': f,
            'posts': [('@numerosdabola', f'Artilharia mundial: {a["nome"]} {a["gols"]} · {b["nome"]} {b["gols"]} · {c["nome"]} {c["gols"]}. 📊⚽')]}


@pauta
def perigo_adversario(M, rnd):
    pj = M['pj']
    adv = pj.get('adversario')
    js = [x for x in ((M['dest'].get('clubes') or {}).get(adv) or []) if x['jogos'] >= 3]
    if not js or js[0]['gols'] + js[0]['assist'] < 3:
        return None
    x = js[0]
    f = [('rogerio', f'Do outro lado, o {adv} tem um nome para vigiar: {x["nome"]}, {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos.'),
         ('helena', f'O {x["nome"]} é a válvula de escape do {adv}. Se a marcação dobrar nele, o time deles perde a principal saída.'),
         ('carlao', f'Comigo, o {x["nome"]} não virava de frente nenhuma vez! Encosta, antecipa e não dá espaço!')]
    if len(js) > 1:
        y = js[1]
        f.append(('beto', f'E tem o {y["nome"]} também: {y["gols"]} gols. A comissão técnica passou o vídeo dos dois no treino.'))
    return {'id': 'perigo_adversario', 'cat': 'proximo', 'peso': 5, 'titulo': f'O perigo do {adv}: {x["nome"]}', 'falas': f,
            'posts': [(f'@{_slug(adv)}_raiz', f'{x["nome"]} vai fazer o que quiser com a defesa de vocês. '
                       + (f'{x["gols"]} gols e contando. 😏' if x['gols'] > 1 else 'Vocês vão ver. 😏'))]}


@pauta
def selecao_temporada(M, rnd):
    import destaques
    sel = M['dest'].get('selecao')
    if not sel or not destaques.fim_de_liga(M['car']) or not 3 <= M['hoje'][1] <= 6:
        return None
    t = sel['time']
    nossos = [x for x in t if x['nosso']]
    mais = max(t, key=lambda x: x['votos'])
    perto = sorted(sel['mencoes'], key=lambda x: -x['votos'])[:2]
    f = [('rogerio', f'Saiu a Seleção da Temporada {M["dest"]["temporada"]}, votada por {sel["jurados"]} jornalistas: '
                     + ', '.join(f'{x["nome"]}' for x in t) + '.'),
         ('helena', f'O {M["nos"]} emplacou {len(nossos)}: ' + (', '.join(x['nome'] for x in nossos) if nossos else 'nenhum') + '. ' +
                    f'O mais votado foi {mais["nome"]}, com {mais["votos"]} votos.'),
         ('carlao', f'Faltou o {perto[0]["nome"]}! {perto[0]["votos"]} votos e ficou de fora? Jornalista vota com o fígado!' if perto else 'Seleção justa. Assino embaixo.'),
         ('toninho', 'Eu votei em mim mesmo, mas anularam!')]
    return {'id': 'selecao_temporada', 'cat': 'premio', 'peso': 10, 'titulo': 'A Seleção da Temporada', 'falas': f,
            'enquete': _enquete('A seleção da imprensa foi justa?', [('Justa', 1.1), ('Esqueceram gente', 0.9)], rnd),
            'posts': [('@numerosdabola', f'Seleção da Temporada: {len(nossos)} do {M["nos"]}. Mais votado: {mais["nome"]} ({mais["votos"]}/{sel["jurados"]}). 🏆')]}


# ----- por POSIÇÃO (12/10/2026): goleiro, zagueiro, lateral, volante têm as suas próprias histórias
def _sem_sofrer(M, k):
    """Jogos oficiais da temporada em que o jogador (goleiro) jogou 60+ minutos e o time não sofreu gol."""
    n = 0
    for p in M['jogos']:
        if tuple(p['data']) < tuple(M['ini']) or 100 <= p['comp'] <= 110 or p['comp'] == 56:
            continue
        nosso1 = p['time1'] == M['ti']
        linhas, sofreu = (p['linhas1'], p['gols2']) if nosso1 else (p['linhas2'], p['gols1'])
        if sofreu == 0 and any((x['reg'], x['pid']) == k and x['minutos'] >= 60 for x in linhas):
            n += 1
    return n


@pauta
def goleiro_paredao(M, rnd):
    gks = [j for j in M['J'] if j['pos'] == 'GK' and j['t_jogos'] >= 4]
    if not gks:
        return None
    g = max(gks, key=lambda j: j['t_jogos'])
    sg = _sem_sofrer(M, g['k'])
    if sg < 3 or sg < g['t_jogos'] * 0.4:
        return None
    f = [('rogerio', f'{g["nome"]} já tem {sg} jogos sem sofrer gol em {g["t_jogos"]} partidas. É o melhor goleiro da liga hoje?'),
         ('helena', f'O número impressiona, mas goleiro também depende da linha da frente. A média de nota dele é {_n(g["t_nota"] or 6)}.'),
         ('carlao', 'Goleiro bom é o que aparece no lance que ninguém espera. Esse aí fecha a porta e ainda organiza a defesa no grito!'),
         ('beto', f'No CT, o preparador de goleiros diz que nunca viu o {g["nome"]} tão concentrado.'),
         ('toninho', f'Os atacantes da liga já pedem para trocar de gol quando enfrentam o {g["nome"]}!')]
    return {'id': 'goleiro_paredao', 'cat': 'jogador', 'peso': 5, 'titulo': f'{g["nome"]}, o paredão', 'falas': f,
            'enquete': _enquete(f'{g["nome"]} é o melhor goleiro da liga?', [('É o melhor', 1.2), ('Tem melhores', 0.8)], rnd),
            'posts': [('@numerosdabola', f'{g["nome"]}: {sg} jogos sem sofrer gol em {g["t_jogos"]}. Paredão. 🧤')]}


@pauta
def zagueiro_artilheiro(M, rnd):
    zs = [j for j in M['J'] if j['pos'] == 'CB' and j['t_gols'] >= 2]
    if not zs:
        return None
    z = max(zs, key=lambda j: j['t_gols'])
    return {'id': 'zagueiro_artilheiro', 'cat': 'jogador', 'peso': 5, 'titulo': f'{z["nome"]}, zagueiro-artilheiro', 'falas': [
        ('rogerio', f'Zagueiro fazendo gol: {z["nome"]} já marcou {z["t_gols"]} vezes na temporada. Arma secreta nas bolas paradas?'),
        ('helena', 'Zagueiro que faz gol desequilibra: o adversário marca os atacantes e esquece quem vem de trás.'),
        ('carlao', f'No meu tempo, zagueiro só subia na área no escanteio do fim do jogo! O {z["nome"]} sobe e resolve. Respeito!'),
        ('toninho', 'Lembra do Sergio Ramos, aos 93 minutos, empatando de cabeça a final da Champions de 2014? Esse é o espírito!')],
        'posts': [(_torc(M), f'{z["nome"]} zagueiro-artilheiro! {z["t_gols"]} gols! 🧱⚽')]}


@pauta
def lateral_garcom(M, rnd):
    ls = [j for j in M['J'] if j['pos'] in ('LB', 'RB') and j['t_assist'] >= 3]
    if not ls:
        return None
    l = max(ls, key=lambda j: j['t_assist'])
    lado = 'esquerda' if l['pos'] == 'LB' else 'direita'
    return {'id': 'lateral_garcom', 'cat': 'jogador', 'peso': 5, 'titulo': f'{l["nome"]}, o lateral que joga de ponta', 'falas': [
        ('rogerio', f'{l["nome"]} já tem {l["t_assist"]} assistências pela {lado}. Lateral ou ponta?'),
        ('helena', 'É o lateral moderno: o Daniel Alves virou um ponta a mais no Barcelona de Guardiola. A questão é quem cobre as costas.'),
        ('carlao', f'Lateral que só ataca deixa buraco atrás! Mas com {l["t_assist"]} assistências, eu deixo ele subir à vontade.'),
        ('toninho', f'O {l["nome"]} passa mais tempo na área adversária que o centroavante!')],
        'posts': [('@numerosdabola', f'{l["nome"]}: {l["t_assist"]} assistências vindo da lateral {lado}. 🎯')]}


@pauta
def volante_carregador(M, rnd):
    vs = [j for j in M['J'] if j['pos'] in ('DMF', 'CMF') and j['t_jogos'] >= 6 and j['t_gols'] + j['t_assist'] <= 2 and (j['t_nota'] or 0) >= 6.0]
    if not vs:
        return None
    v = max(vs, key=lambda j: (j['t_jogos'], j['t_nota']))
    return {'id': 'volante_carregador', 'cat': 'jogador', 'peso': 4, 'titulo': f'{v["nome"]}, o carregador de piano', 'falas': [
        ('rogerio', f'{v["nome"]} quase não aparece nos gols, mas jogou {v["t_jogos"]} jogos com média {_n(v["t_nota"])}. O herói invisível?'),
        ('helena', 'O Kanté foi eleito o melhor da Premier League em 2016/17 sem viver de gol. O volante que rouba e passa simples sustenta o time.'),
        ('carlao', 'Esse é o cara que eu queria do meu lado! Faz o trabalho sujo para os craques brilharem.'),
        ('toninho', f'O {v["nome"]} corre tanto que o GPS do clube pediu férias!')],
        'enquete': _enquete(f'{v["nome"]} é o jogador mais subestimado do elenco?', [('Sim', 1.3), ('Não', 0.7)], rnd)}


# ----- elencos vitoriosos (vitoriosos.py)
@pauta
def obrigacao_vencer(M, rnd):
    V = M.get('vit') or {}
    t, a = V.get('tropeco'), V.get('anterior')
    if not t or not a or _dias(M['hoje'], tuple(t['data'])) > 6:
        return None
    verbo = 'empatou' if t['res'] == 'empate' else 'perdeu'
    f = [('rogerio', f'O {M["nos"]} ganhou {a["n"]} títulos em {a["temporada"]} e agora {verbo} com o {t["adv"]}: {t["gp"]} a {t["gc"]}. Crise ou exagero?'),
         ('carlao', 'Crise! Time campeão tem obrigação de ganhar sempre. Quem ganhou tudo não pode se acomodar, e eu vi gente acomodada!'),
         ('helena', 'Exagero, Carlão. Nenhum time ganha todas. O que preocupa é se isso vira padrão nos próximos jogos.'),
         ('toninho', rnd.choice([f'O torcedor do {M["nos"]} ficou tão mal-acostumado que empate já é velório!',
                                 'Ganharam tanto que o troféu de um ponto eles nem sabem onde guardar!']))]
    return {'id': 'obrigacao_vencer', 'cat': 'momento', 'peso': 9, 'titulo': 'O peso de ser campeão', 'falas': f,
            'enquete': _enquete(f'O {M["nos"]} está acomodado?', [('Sim, está', 0.9), ('Não, foi um tropeço', 1.2)], rnd),
            'posts': [('@secadorprofissional', f'O todo-poderoso {M["nos"]} tropeçou no {t["adv"]} kkkk acabou a mamata? 😂'),
                      (_torc(M), 'Acostumamos a ganhar sempre. Agora é cobrar e apoiar. Bora reagir! 💪')]}


@pauta
def fome_titulos(M, rnd):
    V = M.get('vit') or {}
    a = V.get('anterior')
    oficiais = [p for p in M.get('jogos') or [] if tuple(p['data']) >= tuple(M['ini']) and not (100 <= p['comp'] <= 110 or p['comp'] == 56)]
    if not V.get('obrigacao') or not a or len(oficiais) > 3:
        return None
    return {'id': 'fome_titulos', 'cat': 'clube', 'peso': 6, 'titulo': 'Ainda tem fome?', 'falas': [
        ('rogerio', f'Depois de {a["n"]} títulos em {a["temporada"]} ({", ".join(a["titulos"][:4])}), a pergunta é uma só: esse elenco ainda tem fome?'),
        ('helena', 'O desafio de quem ganha tudo é renovar a motivação. Os times que mantêm o topo trocam peças antes de precisar.'),
        ('carlao', 'Fome se mede no treino de terça-feira. Quero ver quem corre igual no primeiro jogo da temporada!'),
        ('beto', 'No CT, o técnico colou as fotos das taças no vestiário com uma frase: isso é passado.'),
        ('toninho', 'Esse time já ganhou tanta coisa que o próximo título vai ter que ser de xadrez!')],
        'enquete': _enquete('O time repete a temporada?', [('Repete!', 1.2), ('Não dá para ganhar tudo de novo', 0.9)], rnd)}


@pauta
def renovacao_pauta(M, rnd):
    V = M.get('vit') or {}
    rs = list(V.get('renovacoes') or [])
    if not rs or _dias(M['hoje'], tuple(V.get('data') or M['hoje'])) > 14:
        return None
    x = rs[0]
    f = [('rogerio', f'Contrato de {x["nome"]} acaba em {x["meses"]} meses.' + (' E o veterano quer encerrar a carreira aqui.' if x['veterano'] else ' Renova ou não renova?')),
         ('beto', 'Apurei que o estafe já conversou com o clube. Ainda não há acordo.'),
         ('helena', 'Renovação de veterano é equilíbrio: respeito à história sem travar a renovação do elenco.' if x['veterano'] else
                    'Deixar o contrato chegar ao fim é perder o jogador de graça. Gestão nenhuma aceita isso.'),
         ('carlao', f'Ídolo se respeita! Renova com o {x["nome"]} e acabou a conversa!' if x['veterano'] else f'Renova já com o {x["nome"]}! Depois vai chorar quando ele sair de graça.')]
    return {'id': 'renovacao_pauta', 'cat': 'mercado', 'peso': 6, 'titulo': f'O futuro de {x["nome"]}', 'falas': f,
            'enquete': _enquete(f'O clube deve renovar com {x["nome"]}?', [('Renova!', 1.3), ('Hora de seguir em frente', 0.7)], rnd)}


@pauta
def joia_base(M, rnd):
    jo = (M.get('vit') or {}).get('joia')
    if not jo or _dias(M['hoje'], tuple(jo['data'])) > 14:
        return None
    f = [('rogerio', f'A juventude pede passagem: {jo["nome"]}, {jo["idade"]} anos, nota {jo["ovr"]}, quase não joga. Já está pronto?'),
         ('helena', 'Pela nota, ele já compete. O que falta é minuto. Jogador jovem só evolui jogando.'),
         ('carlao', 'Calma! Garoto queimado cedo não volta. Tem que entrar aos poucos, no jogo certo.'),
         ('toninho', f'O {jo["nome"]} tá tão esquecido no banco que já virou parte da mobília!')]
    return {'id': 'joia_base', 'cat': 'jogador', 'peso': 6, 'titulo': f'{jo["nome"]}, a jovem promessa', 'falas': f,
            'enquete': _enquete(f'{jo["nome"]} deve ser titular?', [('Já!', 1.0), ('Aos poucos', 1.1), ('Emprestar', 0.5)], rnd),
            'posts': [(_torc(M), f'Coloca o {jo["nome"]} pra jogar!!! O futuro é agora! 🌱⚽')]}


# ----- departamento médico (lesoes.py, 12/10/2026)
@pauta
def lesao_craque(M, rnd):
    a = M.get('lesao')
    if not a or _dias(M['hoje'], tuple(a['data'])) > 12:
        return None
    n, sub = a['nome'], a.get('sub')
    g = a['grandes'][0] if a.get('grandes') else None
    alvo = (g['classico'] or g['adv']) if g else None
    sem = a['sem_ele']
    f = [('rogerio', f'Notícia ruim no departamento médico: {n} está lesionado' + (f', e o {alvo} vem aí.' if alvo else '.')
          + (f' Ele é o {a["rank"]}º melhor do elenco e fez {a["parte_gols"]}% dos gols do time.' if a['parte_gols'] else '')),
         ('helena', (f'Sem ele nesta temporada: {sem["v"]} vitórias, {sem["e"]} empates, {sem["d"]} derrotas. ' if sem['jogos'] else
                     'O time ainda não jogou sem ele: é território desconhecido. ')
          + (f'O substituto natural é {sub["nome"]}, nota {sub["ovr"]}.' if sub else '')),
         ('carlao', 'Time grande não pode depender de um só! É hora de o grupo mostrar que tem elenco.' if a['rank'] <= 3
          else 'Desfalque importante, mas o elenco tem como cobrir.'),
         ('beto', 'No CT o clima é de apreensão. Ele estava voando nos treinos.'),
         ('toninho', f'O departamento médico vai ter que fazer milagre! Acende uma vela pro {n}!')]
    if a.get('corrida'):
        c = a['corrida']
        f.insert(3, ('helena', f'E na pior hora: {c["pos"]}º lugar na disputa pelo {c["zona"].split(" ")[0]}, com o {c["rival"]["nome"]} na cola.'))
    return {'id': 'lesao_craque', 'cat': 'jogador', 'peso': 9 if a['rank'] <= 3 else 6, 'titulo': f'Sem {n}: e agora?', 'falas': f,
            'enquete': _enquete(f'Sem {n}, o time aguenta?', [('Aguenta, tem elenco', 1.0), ('Vai sentir muito', 1.2),
                                                              ('Hora de contratar', 0.6)], rnd),
            'posts': [(_torc(M), f'Força {n}!!! Volta logo, craque 🙏'), (_torc(M), f'Sem o {n} agora? Que fase...')]}


@pauta
def volta_craque(M, rnd):
    a = M.get('lesao_volta')
    if not a or _dias(M['hoje'], tuple(a['data'])) > 10:
        return None
    n = a['nome']
    f = [('rogerio', f'Boa notícia: {n} está liberado depois de {a["dias_fora"]} dias.'),
         ('carlao', 'Craque é craque: volta e já resolve! Coloca para jogar!'),
         ('helena', 'Cuidado com o ritmo. Voltar de lesão direto em jogo grande é risco de recaída.'),
         ('toninho', f'O {n} voltou mais rápido que o meu salário cai na conta!')]
    return {'id': 'volta_craque', 'cat': 'jogador', 'peso': 7, 'titulo': f'{n} está de volta', 'falas': f,
            'enquete': _enquete(f'{n} volta como titular?', [('Direto no time', 1.1), ('Aos poucos', 1.0)], rnd),
            'posts': [(_torc(M), f'ELE VOLTOU!!! {n} liberado 🔥')]}


# ----- rumores de mercado sobre os nossos (rumores.py)
@pauta
def rumor_mercado(M, rnd):
    R = M.get('rumores') or []
    if not R:
        return None
    x = max(R, key=lambda x: x['calor'])
    j = next((j for j in M['J'] if j['nome'] == x['nome']), None)
    if not j:
        return None
    consulta = x.get('fase') == 'consulta'
    f = [('rogerio', f'Mercado quente: o {x["clube"]} está de olho em {x["nome"]}.' + (' E já teve consulta formal!' if consulta else ' Vende ou não vende?')),
         ('beto', rnd.choice([f'Apurei que olheiros do {x["clube"]} estiveram nos últimos jogos. O estafe do {x["nome"]} sabe de tudo.',
                              f'O empresário do {x["nome"]} anda muito sorridente. Tiro as minhas conclusões.'])),
         ('helena', f'Pelos números, {j["t_gols"]} gols e {j["t_assist"]} assistências na temporada, nota {j["ovr"]}. Perder agora desmonta uma engrenagem.'),
         ('carlao', f'Não vende! Time grande não vende titular no meio do projeto. Se quiser, que pague o que ele vale e mais um pouco!'),
         ('toninho', f'O {x["nome"]} já tá olhando apartamento lá, aposto! Brincadeira... ou não!')]
    return {'id': 'rumor_mercado', 'cat': 'mercado', 'peso': 7 + (2 if consulta else 0), 'titulo': f'{x["clube"]} de olho em {x["nome"]}', 'falas': f,
            'enquete': _enquete(f'O {M["nos"]} deve vender o {x["nome"]}?', [('Não vende!', 1.4), ('Por um caminhão de dinheiro, sim', 0.7)], rnd),
            'posts': [(_torc(M), f'NÃO VENDE O {x["nome"].upper()}!!! #Fica{_slug(x["nome"]).capitalize()} 🙏'),
                      ('@mercadodabola', f'{x["clube"]} monitora {x["nome"]}' + (' e já fez consulta formal. 👀' if consulta else '. Por ora, sondagem. 👀'))]}


# ----- Data FIFA (data_fifa.py)
@pauta
def data_fifa(M, rnd):
    F = M.get('fifa')
    if not F or _dias(M['hoje'], tuple(F['data'])) > 10:
        return None
    conv, esq, cans = F['convocados'], F['esquecidos'], F['cansados']
    if not conv and not esq:
        return None
    f = [('rogerio', f'Data FIFA encerrada: o {M["nos"]} teve {len(conv)} jogadores em campo pelas seleções'
                     + (': ' + ', '.join(f'{x["nome"]} ({x["selecao"].title()})' for x in conv[:5]) if conv else '') + '.')]
    art = max(conv, key=lambda x: x['gols'], default=None)
    if art and art['gols']:
        f.append(('helena', f'O {art["nome"]} marcou {art["gols"]} pela seleção em {art["min"]} minutos. Volta com a confiança lá em cima.'))
    if esq:
        e = esq[0]
        f.append(('carlao', f'E o {e["nome"]} fora? Nota {e["ovr"]}! Eu queria entender o critério desse treinador da seleção!'))
        f.append(('toninho', f'O {e["nome"]} ficou em casa vendo o jogo no sofá. Pelo menos descansou!'))
    if cans:
        c = cans[0]
        f.append(('beto', f'No CT, a preocupação é o {c["nome"]}: {c["min"]} minutos pela seleção e condição {c["condicao"]}. Pode ser poupado.'))
    f.append(('carlao', 'Calendário de seleção é desumano. Quem paga a conta é o clube!'))
    return {'id': 'data_fifa', 'cat': 'jogador', 'peso': 7 + (2 if esq else 0), 'titulo': 'Os nossos nas seleções', 'falas': f,
            'enquete': _enquete(f'{esq[0]["nome"]} merecia ser convocado?' if esq else 'O clube deve liberar os jogadores para todos os jogos?',
                                [('Sim', 1.3), ('Não', 0.7)] if esq else [('Sim, é a seleção', 1.0), ('Não, o clube vem primeiro', 1.0)], rnd),
            'posts': ([(_torc(M), f'{art["nome"]} BRILHANDO PELA SELEÇÃO! {art["gols"]} gol(s)! 🌎🔥')] if art and art['gols'] else []) +
                     ([('@futebol_raiz', f'Não dá pra entender o {esq[0]["nome"]} fora da seleção. Nota {esq[0]["ovr"]}!')] if esq else [])}


# ----- rodada e mês (rodada_mes.py)
@pauta
def selecao_rodada(M, rnd):
    x = (M.get('rd') or {}).get('rodada')
    if not x or _dias(M['hoje'], tuple(x['data'])) > 8:
        return None
    c = x['craque']
    f = [('rogerio', f'Seleção da rodada {x["rodada"]} da {x["liga"]}: o craque foi {c["nome"]}, do {c["time"]}, nota {_n(c["nota"] or 0)}.'),
         ('helena', f'O {M["nos"]} colocou {len(x["nossos"])} no time ideal' + (f': {", ".join(x["nossos"])}.' if x['nossos'] else '. Rodada para esquecer.')),
         ('toninho', rnd.choice([f'Eu escalaria o {c["nome"]} até no meu time de várzea, e olha que lá a concorrência é pesada!',
                                 'Seleção da rodada é igual cardápio de churrascaria: todo mundo acha que faltou alguma coisa!']))]
    if not c['nosso']:
        f.append(('carlao', f'E ninguém do {M["nos"]} foi o craque? Tem que incomodar! Time grande briga até por isso!'))
    return {'id': 'selecao_rodada', 'cat': 'liga', 'peso': 5, 'titulo': f'Seleção da rodada {x["rodada"]}', 'falas': f,
            'enquete': _enquete('Quem foi o craque da rodada?', [(c['nome'], 1.3)] + [(n, 0.7) for n in x['nossos'][:2] if n != c['nome']] + [('Outro', 0.4)], rnd),
            'posts': [('@numerosdabola', f'Craque da rodada {x["rodada"]}: {c["nome"]} ({c["time"]}), nota {_n(c["nota"] or 0)}. ⭐')]}


@pauta
def jogador_mes(M, rnd):
    x = (M.get('rd') or {}).get('mes')
    if not x or _dias(M['hoje'], tuple(x['data'])) > 12:
        return None
    t = x['top']
    f = [('rogerio', f'O jogador de {x["mes"]} na {x["liga"]} é {t["nome"]}, do {t["time"]}: {t["gols"]} gols e {t["assist"]} assistências em {t["jogos"]} jogos.'),
         ('helena', f'Média {_n(t["media"])} no mês. Regularidade de quem não deixou cair em nenhum jogo.')]
    if x.get('nosso') and not t['nosso']:
        n = x['nosso']
        f.append(('beto', f'No {M["nos"]}, o melhor do mês foi o {n["nome"]}: {n["gols"]} gols e {n["assist"]} assistências. No CT, a avaliação é a mesma.'))
    f.append(('toninho', 'Prêmio de jogador do mês devia vir com um cheque! Eu ganhei uma vez e me deram um chaveiro!'))
    return {'id': 'jogador_mes', 'cat': 'premio', 'peso': 6 + (2 if t['nosso'] else 0), 'titulo': f'O jogador de {x["mes"]}', 'falas': f,
            'posts': [(_torc(M) if t['nosso'] else '@futebol_raiz', f'{t["nome"]}, jogador de {x["mes"]}! {t["gols"]} gols no mês 🏅')]}


# ----- a história do clube (historia.py): marcos e o livro dos recordes
@pauta
def marco_historico(M, rnd):
    H = M['hist']
    rec = [m for m in H.get('marcos') or [] if _dias(M['hoje'], tuple(int(x) for x in m['data'].split('-'))) <= 10]
    if not rec:
        return None
    m = rec[0]['texto']
    f = [('rogerio', f'Momento histórico: {m} Os registros do clube começam em {H.get("desde", "—")}.'),
         ('carlao', 'Isso aí não se compra. Número de jogo e de gol com a mesma camisa é respeito conquistado no campo.'),
         ('toninho', rnd.choice(['Daqui a pouco vão ter que fazer estátua! Eu já pedi a minha, mas ninguém me escuta!',
                                 'Tem gente que coleciona figurinha. Esse aí coleciona marca histórica!']))]
    art = (H.get('artilheiros') or [None])[0]
    if art:
        f.insert(2, ('helena', f'Para ter dimensão: o artilheiro da era é {art["nome"]}, com {art["gols"]} gols em {art["jogos"]} jogos desde {art["de"]}.'))
    return {'id': 'marco_historico', 'cat': 'jogador', 'peso': 9, 'titulo': 'Marca histórica', 'falas': f,
            'posts': [(_torc(M), f'{m} HISTÓRICO! 🏆📜'), ('@numerosdabola', f'{m} 📊')]}


@pauta
def livro_recordes(M, rnd):
    H = M['hist']
    R = H.get('recordes') or {}
    ts = H.get('temporadas') or []
    if len(ts) < 2 or not R:
        return None
    escolhas = [k for k in ('gols_temporada', 'assist_temporada', 'seq_vitorias', 'maior_vitoria', 'pontos_liga', 'titulos_temporada') if k in R]
    if not escolhas:
        return None
    k = rnd.choice(escolhas)
    nomes = {'gols_temporada': 'mais gols numa temporada', 'assist_temporada': 'mais assistências numa temporada',
             'seq_vitorias': 'maior sequência de vitórias', 'maior_vitoria': 'maior goleada', 'pontos_liga': 'mais pontos na liga',
             'titulos_temporada': 'mais títulos numa temporada'}
    t = ts[0]
    f = [('rogerio', f'Quadro do livro dos recordes da era: {nomes[k]}. A marca é: {R[k]["texto"]}.'),
         ('helena', f'E a temporada atual, {t["temporada"].replace("-", "/")}? {t["jogos"]} jogos, {t["v"]} vitórias, {t["gp"]} gols marcados.'
                    + (f' O artilheiro até aqui é {t["artilheiro"]["nome"]}, com {t["artilheiro"]["gols"]}.' if t.get('artilheiro') else '')),
         ('carlao', 'Recorde existe para ser quebrado. Esse elenco tem obrigação de mirar nisso!'),
         ('beto', 'No CT tem um quadro com essas marcas na parede do vestiário. Os jogadores olham todo dia.')]
    return {'id': 'livro_recordes', 'cat': 'clube', 'peso': 3, 'titulo': 'O livro dos recordes', 'falas': f}


# ---------------------------------------------------------------- o programa
# edições por fase (11/10/2026): em todo jogo o programa e as redes saem ANTES (pré) e DEPOIS (pós)
POS_SO = {'resultado', 'craque_do_jogo', 'decepcao', 'goleada_nossa', 'derrota_dura', 'goleiro', 'noite_europeia',
          'virada_historica', 'final_pos'}
PRE_SO = {'previa', 'final_pre', 'jogo_grande', 'reforco_adversario', 'classico', 'perigo_adversario'}


def episodio(M, car, rnd=None, fase=None):
    rnd = rnd or random.Random(f'bnm|{car.get("ck")}|{M["hoje"]}|{fase}')
    hist = car.setdefault('bnm_hist', {})
    foco, fora = (PRE_SO, POS_SO) if fase == 'pre' else (POS_SO, PRE_SO) if fase == 'pos' else (set(), set())
    cands = []
    for fn in PAUTAS:
        if fn.__name__ in fora:
            continue
        try:
            p = fn(M, rnd)
        except Exception as e:  # noqa: BLE001 - uma pauta com dado estranho não derruba o programa
            print(f'aviso: pauta {fn.__name__}: {type(e).__name__}: {e}')
            continue
        if not p:
            continue
        if p.get('extra'):   # fala extra (ex.: cobrança quando quem vai mal é uma lenda)
            p['falas'].insert(2, p['extra'])
        if p['id'] in foco:   # a pauta da fase vem primeiro e não sofre o intervalo de 21 dias
            p['peso'] += 4
        else:
            ult = hist.get(p['id'])
            if ult and _dias(M['hoje'], tuple(ult)) < COOLDOWN and p['peso'] < 9 and p['id'] != 'resultado':
                continue
        cands.append(p)
    escolha, por_cat = [], collections.Counter()
    for p in sorted(cands, key=lambda p: -(p['peso'] + rnd.uniform(0, 2.5))):
        if len(escolha) >= MAX_PAUTAS or por_cat[p['cat']] >= 2:
            continue
        escolha.append(p)
        por_cat[p['cat']] += 1
    ordem_cat = ['jogo', 'momento', 'tabela', 'proximo', 'copa', 'liga', 'jogador', 'vestiario', 'mercado', 'clube', 'premio', 'resenha']
    escolha.sort(key=lambda p: ordem_cat.index(p['cat']) if p['cat'] in ordem_cat else 99)
    for p in escolha:
        hist[p['id']] = list(M['hoje'])
    nome = lambda q: PESSOAS[q][0]
    edicao = {'pre': 'edição pré-jogo', 'pos': 'edição pós-jogo'}.get(fase, '')
    blocos = [{'id': 'abertura', 'titulo': 'Abertura', 'falas': [
        {'quem': 'rogerio', 'texto': f'Boa noite! Está no ar o Bola na Mesa{", " + edicao if edicao else ""}. Na bancada, {nome("carlao")}, '
                                     f'{nome("helena")}, {nome("beto")} e {nome("toninho")}. Hoje: ' + _lista(p['titulo'] for p in escolha[:3]) + ' e muito mais.'}]}]
    for p in escolha:
        blocos.append({'id': p['id'], 'titulo': p['titulo'], 'falas': [{'quem': q, 'texto': t} for q, t in p['falas']]})
    blocos.append({'id': 'encerramento', 'titulo': 'Encerramento', 'falas': [
        {'quem': 'rogerio', 'texto': rnd.choice(['É isso! Vote nas enquetes e comente nas redes. Até a próxima!',
                                                  'Fim de papo por hoje. A resenha continua nas redes. Boa noite!'])},
        {'quem': 'toninho', 'texto': rnd.choice(['E quem não gostou, reclama com o Carlão!', 'Fui! E não esqueçam: eu avisei!'])}]})
    enquetes = [p['enquete'] for p in escolha if p.get('enquete')]
    for p in cands:   # a rede tem mais enquetes que o programa
        if p.get('enquete') and p['enquete'] not in enquetes and len(enquetes) < 5:
            enquetes.append(p['enquete'])
    posts = []
    for p in escolha + [c for c in cands if c not in escolha]:
        for a, t in p.get('posts') or []:
            if len(posts) < 14:
                posts.append({'autor': a, 'texto': t, 'pauta': p['id']})
    ctx_r = {}
    try:   # mais vozes na rede (redes_falas.py): torcedores, haters, perfis de números, rivais, scouts; intercaladas
        import redes_falas
        extra, ctx_r = redes_falas.posts(M, fase, rnd, n=max(6, 22 - len(posts)), ja=[p['texto'] for p in posts],
                                         pautas={p['pauta'] for p in posts})
        novos = [{'autor': a, 'texto': t, 'pauta': f'redes|{cat}', 'tom': tom} for a, t, cat, tom in extra]
        mix = []
        while posts or novos:
            for fila in (posts, novos, novos):
                if fila:
                    mix.append(fila.pop(0))
        posts = mix
    except Exception as e:  # noqa: BLE001
        print(f'aviso: redes extras: {type(e).__name__}: {e}')
    em_alta = []
    try:   # 12/10/2026: conta oficial, jogadores, thread, citações, "Em alta" e o ritmo do feed (redes_vivas.py)
        import redes_vivas
        c_r, cats_r = (ctx_r, set()) if ctx_r else ({'nos': M['nos'], 'sigla': M['sigla'], 'torc': f'@{M["sigla"]}_raiz'}, set())
        if ctx_r:
            import redes_falas as _rf
            c_r, cats_r = _rf.contexto(M, fase)
        esp = redes_vivas.especiais(M, fase, rnd, c_r, cats_r)
        for i, x in enumerate(esp):   # espalhados pelo feed, os oficiais primeiro
            posts.insert(min(len(posts), 1 + i * 3), x)
        for x in redes_vivas.citacoes(posts, rnd, c_r):
            posts.insert(min(len(posts), rnd.randint(4, max(4, len(posts)))), x)
        em_alta = redes_vivas.em_alta(M, fase, c_r, cats_r, rnd)
        for x in posts:
            if x['autor'] in redes_vivas.VEICULOS or x['autor'].endswith('_oficial'):
                x['verificado'] = True
        redes_vivas.ritmo(posts, rnd)
    except Exception as e:  # noqa: BLE001
        print(f'aviso: redes vivas: {type(e).__name__}: {e}')
    base = math.log10(M['socios'] or 200_000)
    famosos = [(j['nome'], M['perfis'][j['k']]['fama']) for j in M['J'] if (M.get('perfis') or {}).get(j['k']) and M['perfis'][j['k']]['fama'] >= 25]
    for x in posts:
        fama = max([f for n, f in famosos if n in x['texto']], default=0)   # o fervo cresce com a fama do citado
        x['curtidas'] = int(10 ** (base - 2.2) * rnd.uniform(0.3, 3.0) * (1 + fama / 60))
        x['reposts'] = int(x['curtidas'] * rnd.uniform(0.05, 0.3))
        try:   # comentários embaixo do post
            import redes_falas
            cat = x['pauta'].split('|', 1)[1] if x['pauta'].startswith('redes|') else x['pauta']
            x['respostas'] = redes_falas.respostas(x.pop('tom', None) or redes_falas.tom_de(x['autor'], x['texto']),
                                                   x['autor'], ctx_r or {'sigla': M['sigla'], 'apelido': M['nos']}, rnd, x['curtidas'], cat=cat)
        except Exception:  # noqa: BLE001
            x['respostas'] = []
    try:   # nomes de times como título e "a Fiorentina" nos posts
        import clube
        nomes = {M['nos'], (M.get('ult') or {}).get('adv'), (M.get('pj') or {}).get('casa'), (M.get('pj') or {}).get('fora')}
        nomes |= {t.get('time') for t in M.get('tab') or []}
        nomes |= {(M.get('pj') or {}).get('adversario')} | {x.get('time') for x in (M.get('dest') or {}).get('clubes_lista') or []}
        nomes |= {x.get('clube') for x in M.get('rumores') or []}
        nomes = {n for n in nomes if n}
        posts = clube.concordar_tudo(clube.titulo_nomes(posts, nomes))
        enquetes = clube.concordar_tudo(clube.titulo_nomes(enquetes, nomes))
        blocos = clube.concordar_tudo(clube.titulo_nomes(blocos, nomes))
    except Exception as e:  # noqa: BLE001
        print(f'aviso: nomes nos posts: {e}')
    return {'blocos': blocos, 'enquetes': enquetes[:5], 'posts': posts, 'em_alta': em_alta,
            'bancada': {q: {'nome': n, 'papel': p} for q, (n, p) in PESSOAS.items()}}


def chave_fase(car, r, fase):
    """(chave, data, rótulo) da edição: pós = último jogo; pré = próximo jogo. None se não houver o jogo."""
    import imprensa_db as db
    ck = car.get('ck')
    if fase == 'pos':
        if not r.get('jogos'):
            return None
        p = r['jogos'][-1]
        ti = r['ti']
        adv = (r.get('_nomes_time') or str)(p['time2'] if p['time1'] == ti else p['time1'])
        gp, gc = (p['gols1'], p['gols2']) if p['time1'] == ti else (p['gols2'], p['gols1'])
        return f'bnm|{ck}|pos|{p["num"]}|{db.data_txt(p["data"])}', tuple(p['data']), f'Pós-jogo · {r["time"]} {gp} x {gc} {adv}'
    pj = car.get('proximo_jogo') or {}
    if not pj.get('casa'):
        return None
    return (f'bnm|{ck}|pre|{db.data_txt(pj["data"])}|{pj["casa"]}|{pj["fora"]}', tuple(pj['data']),
            f'Pré-jogo · {pj["casa"]} x {pj["fora"]}')


def materias(car, r, d, snap, ctx=None, log=print, fase=None):
    """Programa + redes (já passados pelo redator). fase 'pre' (antes do próximo jogo) ou 'pos' (depois do último)."""
    import imprensa_db as db
    hoje = tuple(r['hoje'])
    ck = car.get('ck')
    if fase:
        cf = chave_fase(car, r, fase)
        if not cf:
            return []
        chave, data, rotulo = cf
    else:
        chave, data, rotulo = f'bnm|{ck}|{db.data_txt(hoje)}', hoje, 'Programa'
    if db.existe(ck, chave):
        return []
    M = mundo(car, r, d, snap, ctx)
    ep = episodio(M, car, fase=fase)
    ia = False
    try:
        import redator
        ia = redator.reescrever_falas(ep, clube=r['time'], log=log)
    except Exception as e:  # noqa: BLE001
        log(f'aviso: redator do Bola na Mesa: {e}')
    temas = [b['titulo'] for b in ep['blocos'][1:-1]]
    return [{'chave': chave, 'frente': 'bola_na_mesa', 'data': data, 'titulo': 'Bola na Mesa',
             'linha_fina': ' · '.join(temas[:4]), 'corpo': [], 'autor': 'TV · Bola na Mesa', 'ia': ia,
             'dados': {'blocos': ep['blocos'], 'bancada': ep['bancada'], 'fase': fase, 'jogo': rotulo}},
            {'chave': chave.replace('bnm|', 'redes|', 1), 'frente': 'redes', 'data': data, 'titulo': 'Redes',
             'linha_fina': '', 'corpo': [], 'autor': 'Redes sociais', 'ia': ia,
             'dados': {'posts': ep['posts'], 'enquetes': ep['enquetes'], 'em_alta': ep.get('em_alta') or [], 'fase': fase, 'jogo': rotulo}}]


def vivo(dados, pulso, snap, fase, log=print):
    """Edição AO VIVO (Central, sem esperar o save): usa o save da última reunião (save_work) e completa com o que a
    memória mostra — o jogo que acabou (súmula dos dois lados), a tabela e o próximo jogo."""
    import copy
    import glob
    import json
    import os
    import imprensa_db as db
    import vestiario as V
    ck = dados.get('carreira')
    uj = (pulso or {}).get('ultimo_jogo') or {}
    pr = (pulso or {}).get('proximo') or {}
    if fase == 'pos' and (uj.get('num') is None or db.existe(ck, f'bnm|{ck}|pos|{uj["num"]}|{db.data_txt(uj["data"])}')):
        return []
    if fase == 'pre' and (not pr or db.existe(ck, f'bnm|{ck}|pre|{db.data_txt(pr["data"])}|{pr["casa"]}|{pr["fora"]}')):
        return []
    here = os.path.dirname(os.path.abspath(__file__))
    decs = glob.glob(os.path.join(here, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat'))
    if not decs:
        return []
    d = open(max(decs, key=os.path.getmtime), 'rb').read()
    r = V.analisar(d, snap)
    import partidas_save as _ps
    import temporada
    r['agenda'] = _ps.agenda(d)
    temporada.definir(r)
    try:
        est = json.load(open(os.path.join(here, 'historico', 'vestiario_estado.json'), encoding='utf-8'))
        car = copy.deepcopy(est['carreiras'][ck])
    except Exception:  # noqa: BLE001
        return []
    import midia_liga
    car['liga'] = next((L for L in (dados.get('liga'), car.get('liga')) if midia_liga.liga_valida(L)), None)
    try:   # a liga recalculada com o código atual (amistosos fora); a classificação ao vivo do pulso por cima
        painel = midia_liga.cobertura(r, car, tuple(r['hoje']), snap)[0]
        if painel:
            if (pulso or {}).get('classificacao') and not painel.get('pre_temporada'):
                painel['classificacao'] = pulso['classificacao']
            car['liga'] = painel
    except Exception as e:  # noqa: BLE001
        log(f'aviso: liga não recalculada: {e}')
    import datetime as _dt   # saídas/chegadas efetivadas que a reunião guardou (saidas.executadas)
    ex = [dict(h, k=tuple(h['k'])) for h in car.get('mov_executadas') or []
          if (_dt.date(*tuple(r['hoje'])) - _dt.date(*h['data'])).days <= 21]
    vistos = {(m['k'], m['tipo']) for m in ex}
    r['movimentos'] = ex + [m for m in r.get('movimentos') or [] if (tuple(m['k']), m['tipo']) not in vistos]
    if pr:   # o próximo jogo que a memória mostra (prévia pronta da reunião, se houver)
        car['proximo_jogo'] = dados.get('proximo_jogo') if (dados.get('proximo_jogo') or {}).get('casa') == pr['casa'] else \
            {'casa': pr['casa'], 'fora': pr['fora'], 'data': pr['data'], 'adversario': pr['fora'] if pr['casa'] == r['time'] else pr['casa'],
             'competicao': __import__('proximo_jogo').nome_comp(pr['comp']), 'final': pr.get('final'),
             'classico': __import__('classicos').nome(pr['casa'], pr['fora'])}
    if uj.get('num') is not None and not any(p.get('num') == uj['num'] for p in r['jogos']):
        linhas = lambda xs: [{'reg': x['reg'], 'pid': x['pid'], 'gols': x['gols'], 'assist': x['assist'], 'nota': x['nota'],
                              'minutos': x['min'], 'titular': x.get('titular'), 'funcao': 0} for x in xs]
        nosso1 = uj['time1'] == r['ti']
        p = {'num': uj['num'], 'data': tuple(uj['data']), 'comp': uj['comp'], 'rodada': uj['rodada'], 'flag': uj.get('flag'),
             'time1': uj['time1'], 'time2': uj['time2'], 'gols1': uj['gols1'], 'gols2': uj['gols2'],
             'linhas1': linhas(uj['linhas'] if nosso1 else uj['linhas_adv']), 'linhas2': linhas(uj['linhas_adv'] if nosso1 else uj['linhas'])}
        r['jogos'].append(p)
        r['todas_partidas'].append(p)
        if uj.get('ida'):
            ida = dict(uj['ida'], data=tuple(uj['ida']['data']), num=None)
            if not any(tuple(x['data']) == ida['data'] and x['time1'] == ida['time1'] for x in r['todas_partidas']):
                r['todas_partidas'].append(dict(ida, linhas1=[], linhas2=[]))
        g = (pulso.get('ultimos_jogos') or [])[-1:]
        if g:
            r['ultimos'] = (r.get('ultimos') or [])[-5:] + [g[0]]
        r['hoje'] = tuple(uj['data'])
    out = materias(car, r, d, snap, log=log, fase=fase)
    for m in out:
        db.gravar(ck, m)
    if out:
        log(f'Bola na Mesa ao vivo ({fase}): ' + out[0]['linha_fina'])
    return out


import pautas_momento  # noqa: E402,F401  12/10/2026: pautas do momento (registra em PAUTAS)
