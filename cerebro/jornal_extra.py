# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Jornal com mais corpo (11/10/2026): as capas das Bancas ganham texto de abertura, ASPAS de jogadores (o que ele
"disse" na zona mista, coerente com o fato e com o jeito dele: vaidoso, líder, jovem impaciente...) e quadros com a
liga, a artilharia, a corrida da Bola de Ouro e a revelação da temporada (destaques.py).

Também traz os FATOS DO MUNDO para a capa: a revelação que ninguém conhecia, a corrida da Bola de Ouro, o artilheiro
do mundo e a Seleção da Temporada votada pela imprensa.
"""
import datetime as dt

from clube import C as CL

POS_TXT = {'GK': 'goleiro', 'CB': 'zagueiro', 'LB': 'lateral', 'RB': 'lateral', 'DMF': 'volante', 'CMF': 'meia',
           'AMF': 'meia', 'LMF': 'meia', 'RMF': 'meia', 'LWF': 'ponta', 'RWF': 'ponta', 'SS': 'atacante', 'CF': 'centroavante'}


def _dias(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def _met(m):
    return {'gols': 'gols', 'jogos': 'jogos', 'assist': 'assistências'}[m['metrica']]


def _tracos(j):
    return set(((j or {}).get('perfil') or {}).get('tracos') or [])


# ---------------------------------------------------------------- fatos do mundo
def fatos_mundo(car, hoje):
    """Fatos para as capas a partir de car['mundo'] (com intervalo para não repetir a mesma capa toda rodada)."""
    import destaques
    res = car.get('mundo')
    if not res:
        return []
    vistos = car.setdefault('midia_mundo', {})
    F = []

    def pode(chave, dias):
        ult = vistos.get(chave)
        return not ult or _dias(hoje, tuple(ult)) >= dias

    def marca(chave):
        vistos[chave] = list(hoje)

    rv = next((x for x in res.get('revelacoes') or [] if x['gols'] + x['assist'] >= 6 and x['jogos'] >= 6), None)
    if rv and pode(f'rev|{rv["nome"]}', 28):
        marca(f'rev|{rv["nome"]}')
        F.append({'tipo': 'revelacao', 'peso': 2.2 + (1.0 if rv['sel_jogos'] else 0) + max(0, 20 - rv['idade']) * 0.2,
                  'sub': rv['nome'], 'x': rv})
    bo = res.get('bola_de_ouro') or []
    if len(bo) >= 3 and res.get('max_jogos', 0) >= 10 and pode('bola', 30):
        marca('bola')
        F.append({'tipo': 'bola_ouro', 'peso': 1.9 + (0.8 if any(x['nosso'] for x in bo[:3]) else 0), 'top': bo[:3]})
    art = (res.get('artilheiros') or [None])[0]
    if art and art['gols'] >= 10 and not art['nosso'] and pode(f'art|{art["nome"]}', 35):
        marca(f'art|{art["nome"]}')
        F.append({'tipo': 'artilheiro_mundo', 'peso': 1.5, 'x': art})
    sel = res.get('selecao')
    if sel and destaques.fim_de_liga(car) and 3 <= hoje[1] <= 6 and pode(f'sel|{res["temporada"]}', 999):
        marca(f'sel|{res["temporada"]}')
        nossos = [x for x in sel['time'] if x['nosso']]
        F.append({'tipo': 'selecao', 'peso': 6 + len(nossos) * 0.4, 'sel': sel, 'nossos': nossos, 'temporada': res['temporada']})
    return F


def manchete(f, tom, rnd):
    t = f['tipo']
    if t == 'premio_mundo':   # 13/10/2026: a noite da Bola de Ouro (premiacao.py)
        import premiacao
        return premiacao.manchete(f, tom, rnd)
    if t == 'revelacao':
        x = f['x']
        conv = ' e já foi chamado para a seleção' if x['sel_jogos'] else ''
        return {'sensacionalista': (rnd.choice([f'QUEM É {x["nome"].upper()}?', f'{x["nome"].upper()}, O FENÔMENO QUE NINGUÉM VIU CHEGAR']),
                                    f'Nota {x["ovr"]}, {x["idade"]} anos e {x["gols"]} gols pelo {x["time"]}{conv}.'),
                'analítico': (f'{x["nome"]}: {x["gols"]} gols com nota {x["ovr"]}',
                              f'{x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos: o {POS_TXT.get(x["pos"], "jogador")} do {x["time"]} rende muito acima do esperado{conv}.'),
                'torcedor': (f'Traz o {x["nome"]}!', f'{x["idade"]} anos, {x["gols"]} gols pelo {x["time"]}. A torcida já pede a contratação.')}[tom]
    if t == 'bola_ouro':
        a, b, c = f['top']
        meu = next((x for x in f['top'] if x['nosso']), None)
        return {'sensacionalista': (f'{a["nome"].upper()} NA FRENTE PELA BOLA DE OURO', f'{b["nome"]} e {c["nome"]} correm atrás. A briga esquentou.'),
                'analítico': ('Bola de Ouro: a corrida pelos números', f'{a["nome"]} ({a["gols"]} gols, {a["assist"]} assist.), {b["nome"]} ({b["gols"]}, {b["assist"]}) e {c["nome"]} ({c["gols"]}, {c["assist"]}).'),
                'torcedor': (f'A Bola de Ouro é do {meu["nome"]}!' if meu else f'{a["nome"]} é o favorito à Bola de Ouro',
                             'A torcida já faz campanha.' if meu else f'{b["nome"]} e {c["nome"]} vêm logo atrás.')}[tom]
    if t == 'artilheiro_mundo':
        x = f['x']
        return {'sensacionalista': (f'{x["nome"].upper()}, MÁQUINA DE GOLS', f'{x["gols"]} gols em {x["jogos"]} jogos pelo {x["time"]}. Ninguém marca mais no mundo.'),
                'analítico': (f'O artilheiro do mundo: {x["nome"]}', f'{x["gols"]} gols em {x["jogos"]} jogos, média de {_n(x["gols"] / max(1, x["jogos"]))} por partida.'),
                'torcedor': (f'{x["nome"]} não para de marcar', f'{x["gols"]} gols pelo {x["time"]}. Zagueiro nenhum segura.')}[tom]
    if t == 'obrigacao':
        a = f['ant']
        return {'sensacionalista': (f'O {CL["apelido"].upper()} ESQUECEU COMO GANHAR?', f'{f["gp"]} x {f["gc"]} com o {f["adv"]}. Quem ganhou {a["n"]} títulos não pode tropeçar assim.'),
                'analítico': (f'O peso de ser campeão: {f["res"]} com o {f["adv"]}', f'Depois de {a["n"]} títulos em {a["temporada"]}, cada ponto perdido vira manchete.'),
                'torcedor': ('Acordem, campeões!', f'{f["gp"]} x {f["gc"]} com o {f["adv"]}. A torcida acostumou mal e cobra.')}[tom]
    if t == 'renovacao':
        n, m = f['nome'], f['meses']
        if f['veterano']:
            return {'sensacionalista': (f'{n.upper()} QUER ENCERRAR A CARREIRA AQUI!', f'Aos {f["idade"]} anos, o contrato acaba em {m} meses. O clube vai renovar?'),
                    'analítico': (f'O futuro de {n}', f'{f["idade"]} anos, contrato até daqui a {m} meses: renovar o veterano ou abrir espaço?'),
                    'torcedor': (f'Renova com o {n}!', 'Ídolo merece se despedir em casa.')}[tom]
        return {'sensacionalista': (f'{n.upper()} PODE SAIR DE GRAÇA!', f'O contrato acaba em {m} meses e ninguém fala em renovação.'),
                'analítico': (f'Contrato de {n}: {m} meses', 'Renovar agora ou correr o risco de perder o jogador sem receber nada.'),
                'torcedor': (f'Renova com o {n} já!', f'Faltam {m} meses. A torcida não quer perder mais um.')}[tom]
    if t == 'joia_base':
        n = f['nome']
        return {'sensacionalista': (f'A JOIA {n.upper()} ESTÁ ESQUECIDA NO BANCO!', f'{f["idade"]} anos, nota {f["ovr"]} e quase sem jogar. A juventude pede passagem.'),
                'analítico': (f'O caso {n}: talento sem minutos', f'{f["idade"]} anos e nota {f["ovr"]}: desenvolver jogando ou emprestar?'),
                'torcedor': (f'Coloca o {n} pra jogar!', 'A arquibancada quer ver a jovem promessa em campo.')}[tom]
    if t == 'rumor':
        x, n = f['x'], f['x']['nome']
        if f['fase'] == 'consulta':
            return {'sensacionalista': (f'BOMBA: {x["clube"].upper()} FAZ CONSULTA POR {n.upper()}!', 'O empresário já foi procurado. O técnico decide o que responder.'),
                    'analítico': (f'{x["clube"]} formaliza interesse em {n}', 'A consulta oficial muda o patamar da negociação.'),
                    'torcedor': (f'NÃO VENDE O {n.upper()}!', f'O {x["clube"]} quer levar um dos nossos. A torcida faz campanha: fica, {n}!')}[tom]
        return {'sensacionalista': (f'{x["clube"].upper()} DE OLHO EM {n.upper()}!', 'Olheiros foram vistos no último jogo. O assédio começou.'),
                'analítico': (f'Mercado: {x["clube"]} monitora {n}', 'Por ora é sondagem; nada formal chegou ao clube.'),
                'torcedor': (f'Fica, {n}!', f'O {x["clube"]} está rondando. A torcida já se mobiliza nas redes.')}[tom]
    if t == 'data_fifa':
        conv, esq = f['convocados'], f['esquecidos']
        art = max(conv, key=lambda x: x['gols'], default=None)
        if esq and (not art or not art['gols']):
            e = esq[0]
            return {'sensacionalista': (f'ESQUECIDO! {e["nome"].upper()} FORA DA SELEÇÃO', f'Nota {e["ovr"]} e nem foi chamado. Recado ou injustiça?'),
                    'analítico': (f'Data FIFA: a ausência de {e["nome"]}', f'{len(conv)} jogadores do {CL["curto"]} defenderam as seleções; {e["nome"]} ficou de fora.'),
                    'torcedor': (f'Injustiça com o {e["nome"]}!', 'A torcida não entendeu a ausência na seleção.')}[tom]
        if art and art['gols']:
            return {'sensacionalista': (f'{art["nome"].upper()} BRILHA PELA SELEÇÃO!', f'{art["gols"]} gol{"s" if art["gols"] > 1 else ""} na Data FIFA. E volta para o clube embalado.'),
                    'analítico': (f'Data FIFA: {len(conv)} do {CL["curto"]} nas seleções', f'{art["nome"]} marcou {art["gols"]}; minutos somados: {sum(x["min"] for x in conv)}.'),
                    'torcedor': (f'Orgulho: {art["nome"]} decide pela seleção', f'{len(conv)} dos nossos defenderam seus países.')}[tom]
        return {'sensacionalista': ('DATA FIFA: O CLUBE PAGA A CONTA?', f'{len(conv)} jogadores voltam das seleções; o desgaste preocupa.'),
                'analítico': (f'Data FIFA: {len(conv)} do {CL["curto"]} nas seleções', f'{sum(x["min"] for x in conv)} minutos somados.'),
                'torcedor': ('Os nossos defenderam seus países', f'{len(conv)} convocados voltam ao clube.')}[tom]
    if t == 'rodada' and f['modo'] == 'tdm':
        x, n = f['top'], len(f['nossos'])
        return {'sensacionalista': (f'{n} DO {CL["apelido"].upper()} NO TIME DO MÊS!' if n else f'TIME DO MÊS SEM NINGUÉM DO {CL["apelido"].upper()}!',
                                    f'{f["mes"].capitalize()} na {f["liga"]}: {x["nome"]} tem a maior nota ({_n(x["nota"])}).'),
                'analítico': (f'O Time do mês de {f["mes"]}', f'A escolha oficial e a da imprensa coincidem em {f["ambos"]} dos 11 nomes.'),
                'torcedor': (f'{n} dos nossos no Time do mês!' if n else 'Esqueceram de nós no Time do mês?', ', '.join(f['nossos'][:5]) + '.' if n else 'A torcida não gostou.')}[tom]
    if t == 'rodada':
        if f['modo'] == 'rodada':
            c = f['craque']
            return {'sensacionalista': (f'{c["nome"].upper()} É O CRAQUE DA RODADA!', f'Nota {_n(c["nota"] or 0)} pelo {c["time"]} na rodada {f["rodada"]} da {f["liga"]}.'),
                    'analítico': (f'Seleção da rodada {f["rodada"]}', f'{c["nome"]} ({c["time"]}) lidera o time ideal; o {CL["curto"]} emplacou {len(f["nossos"])}.'),
                    'torcedor': (f'{len(f["nossos"])} dos nossos na seleção da rodada!' if f['nossos'] else f'Rodada {f["rodada"]}: {c["nome"]} brilhou',
                                 ', '.join(f['nossos'][:4]) + '.' if f['nossos'] else 'Nenhum dos nossos foi lembrado.')}[tom]
        x = f['top']
        return {'sensacionalista': (f'{x["nome"].upper()}, O DONO DE {f["mes"].upper()}!', f'{x["gols"]} gols e {x["assist"]} assistências pelo {x["time"]} no mês.'),
                'analítico': (f'O jogador de {f["mes"]}: {x["nome"]}', f'Média {_n(x["media"])} em {x["jogos"]} jogos, {x["gols"]} gols e {x["assist"]} assistências.'),
                'torcedor': (f'{x["nome"]} é o melhor de {f["mes"]}!' if x['nosso'] else f'{f["mes"].capitalize()} foi do {x["nome"]}',
                             f'{x["gols"]} gols no mês.' + (f' Nosso destaque: {f["nosso"]["nome"]}.' if f.get('nosso') and not x['nosso'] else ''))}[tom]
    if t == 'marco':
        m = f['m']
        if m['tipo'] == 'recorde':
            a = m['anterior']
            return {'sensacionalista': (f'{m["nome"].upper()} QUEBRA O RECORDE!', f'{m["valor"]} {_met(m)} na temporada. O recorde de {a["nome"]} ({a["valor"]}) caiu.'),
                    'analítico': (f'Recorde: {m["valor"]} {_met(m)} numa temporada', f'{m["nome"]} supera a marca de {a["nome"]} ({a["valor"]}, em {a["temporada"]}).'),
                    'torcedor': (f'{m["nome"]} entra para a história!', f'Ninguém fez mais {_met(m)} numa temporada com esta camisa: {m["valor"]}.')}[tom]
        return {'sensacionalista': (f'{m["valor"]} {_met(m).upper()}! {m["nome"].upper()} ENTRA PARA A HISTÓRIA', f'Marca atingida em {m["temporadas"]} temporadas pelo {CL["apelido"]}.'),
                'analítico': (f'{m["nome"]} chega a {m["valor"]} {_met(m)} pelo clube', f'Em {m["temporadas"]} temporadas registradas.'),
                'torcedor': (f'Parabéns, {m["nome"]}! São {m["valor"]} {_met(m)}!', 'Uma marca para a galeria do clube.')}[tom]
    if t == 'selecao':
        n, temp = len(f['nossos']), f['temporada']
        return {'sensacionalista': (f'{n} DO {CL["apelido"].upper()} NA SELEÇÃO DO ANO!' if n else f'{CL["apelido"].upper()} FORA DA SELEÇÃO DO ANO!',
                                    f'A imprensa votou os 11 melhores de {temp}.'),
                'analítico': (f'A Seleção da Temporada {temp}', f'{f["sel"]["jurados"]} jornalistas votaram num 4-3-3; o {CL["nome"]} emplacou {n}.'),
                'torcedor': (f'{n} dos nossos entre os melhores do mundo!' if n else 'Injustiça na seleção do ano',
                             ', '.join(x['nome'] for x in f['nossos'][:5]) + '.' if n else 'Nenhum dos nossos foi lembrado.')}[tom]
    return None


# ---------------------------------------------------------------- aspas
def _j(r, nome):
    return next((j for j in r['J'] if j['nome'] == nome), None)


def aspas(f, r, car, rnd):
    """{'quem', 'papel', 'texto'} ou None: a fala de um jogador ligada ao fato da manchete."""
    t = f['tipo']
    if t == 'premio_mundo':
        import premiacao
        return premiacao.aspas(f, rnd)
    J = r['J']
    cap = next((j for j in J if j.get('capitao')), None)
    pj = car.get('proximo_jogo') or {}

    def de(j, texto, papel=None):
        if not j:
            return None
        return {'quem': j['nome'], 'papel': papel or f'{POS_TXT.get(j["pos"], "jogador")} do {CL["curto"]}', 'texto': texto}
    if t == 'resultado':
        g = f['jogo']
        j = f['melhor'][0] if f.get('melhor') else None
        gols = dict((m['nome'], n) for m, n in f.get('marcadores') or [])
        tr = _tracos(j)
        if g['pro'] == g['contra']:
            return de(j or cap, rnd.choice(['Faltou o último passe. Dá para tirar coisa boa, mas a gente queria a vitória.',
                                             'Empate não é o que a gente veio buscar. Tem que transformar volume em gol.']))
        if j and gols.get(j['nome'], 0) >= 2:
            return de(j, rnd.choice([f'Fazer {gols[j["nome"]]} gols é bom, mas o que importa são os três pontos.',
                                     'Quando a bola sobra na área, o atacante tem que estar lá. Hoje estava.']))
        if 'vaidoso' in tr:
            return de(j, rnd.choice(['Eu sabia que ia decidir. Quando a bola chega em mim, eu resolvo.',
                                     'Jogo grande é para jogador grande. Hoje mostrei de novo.']))
        if 'líder' in tr or (j and j.get('capitao')):
            return de(j, rnd.choice(['Ninguém ganha sozinho. Hoje cada um correu pelo outro.',
                                     'O grupo está fechado. Vitória de quem trabalha calado durante a semana.']))
        return de(j, rnd.choice([f'A torcida empurrou a gente do começo ao fim. Essa é para eles.',
                                 'Vitória importante. Agora é descansar e pensar no próximo jogo.',
                                 f'Contra o {g["adversario"]} nunca é fácil. Fizemos o que o professor pediu.']))
    if t == 'derrota':
        j = cap or max(J, key=lambda x: x.get('lider', 0), default=None)
        return de(j, rnd.choice(['Não tem desculpa. Erramos e vamos corrigir. A torcida merece mais.',
                                 'Tem que ter vergonha na cara. A gente deve uma resposta, e ela vem no próximo jogo.',
                                 'Dia ruim de todo mundo, a começar por mim. Cabeça erguida e trabalho.']),
                  'capitão do ' + CL['curto'] if j and j.get('capitao') else None)
    if t == 'sequencia':
        j = cap
        return de(j, 'O segredo é não olhar para trás. Cada jogo é uma final.' if f.get('bom') else
                  'Fase ruim se sai com trabalho. Ninguém aqui vai se esconder.', 'capitão do ' + CL['curto'] if j else None)
    if t == 'titulo':
        art = max(J, key=lambda x: x['t_gols'], default=None)
        j = rnd.choice([x for x in (cap, art) if x]) if (cap or art) else None
        if f.get('campeao'):
            return de(j, rnd.choice(['Esse título é de cada torcedor que acreditou quando ninguém acreditava.',
                                     'Sonhei com isso a vida inteira. Agora ninguém tira da gente.',
                                     'Trabalhamos o ano inteiro para esta noite. Valeu cada treino.']))
        return de(j, 'Dói muito. Mas este grupo vai voltar mais forte, pode escrever.')
    if t == 'virada':
        return de(cap, rnd.choice(['Eu nunca vou esquecer esta noite. Ninguém acreditava, só a gente.',
                                   'No intervalo, falei: ainda dá. E deu. Isso é futebol.'])) if f['tie']['tipo'] == 'virada' else \
            de(cap, 'Não tenho explicação. Peço desculpas à torcida.')
    if t == 'movimento':
        m, n = f['m'], f['n']
        import saidas
        papel = f'{POS_TXT.get(m.get("pos_campo"), "jogador")}, de saída para {saidas.art(m["clube"])} {m["clube"]}' if m['tipo'] == 'saida' else \
            f'reforço do {CL["curto"]}'
        frase = {'sombra': 'Chegou a hora de escrever a minha própria história. Sou grato, mas quero ser protagonista.',
                 'idolo': 'Este clube vai estar sempre no meu coração. Saio, mas uma parte de mim fica.',
                 'dinheiro': 'Foi uma decisão pensando na minha família e no meu futuro.',
                 'rival': 'Sou profissional. Respeito a história, mas é um novo desafio.',
                 'sem_espaco': 'Eu preciso jogar. Saio de cabeça erguida.',
                 'jovem': 'Quero minutos, quero crescer. É o passo certo para a minha carreira.',
                 'veterano': 'Dei tudo o que eu tinha por esta camisa. Agora é outro capítulo.',
                 'chegada': 'Vim para ganhar títulos. Estou pronto para ajudar desde o primeiro treino.',
                 'renovacao': 'Aqui é a minha casa. Não tinha outro lugar onde eu quisesse estar.'}.get(n['tipo'],
                'Agradeço a todos. É hora de um novo desafio.' if m['tipo'] == 'saida' else 'Vim para somar.')
        return {'quem': m['nome'], 'papel': papel, 'texto': frase}
    if t == 'conflito':
        a = f['env'][1] if f['sub'] == 'Ego salarial' else f['env'][0]
        frase = {'Braçadeira': 'Eu me sinto um líder neste grupo. Mas quem decide é o treinador, e eu respeito.',
                 'Ego salarial': 'Não é só dinheiro, é reconhecimento. Eu sei o que entrego em campo.',
                 'Posição': 'Eu quero jogar. Treino todo dia para isso. Não sou de ficar no banco calado.'}.get(f['sub'],
                'Estou chateado, não vou mentir. Mas vou resolver internamente.')
        return de(a, frase)
    if t == 'baixa':
        return de(f['j'], 'Fase ruim todo mundo tem. Já passei por coisa pior e dei a volta por cima.')
    if t == 'destaque':
        j = f['j']
        tr = _tracos(j)
        return de(j, 'Estou no melhor momento da carreira, e quero mais. Ninguém aqui está satisfeito.' if 'vaidoso' not in tr else
                  'Os números falam por mim. Mas o que eu quero mesmo são os títulos.')
    if t == 'contrato':
        return de(f['j'], rnd.choice(['Meu desejo é ficar, mas isso depende do clube. A bola está com eles.',
                                      'Estou focado em jogar. Contrato é com o meu empresário.']))
    if t == 'proximo':
        c = pj.get('classico')
        return de(cap, f'{c} não se joga, se ganha. A semana é diferente, todo mundo sente.' if c else
                  rnd.choice(['Jogo grande a gente gosta de jogar. Respeito, mas medo nenhum.',
                              f'O {pj.get("adversario", "adversário")} é forte, mas em casa a gente impõe o nosso jogo.']),
                  'capitão do ' + CL['curto'] if cap else None)
    if t == 'pre':
        return de(cap, rnd.choice(['A meta é ganhar tudo de novo. Quem veste esta camisa não pode pensar pequeno.',
                                   'Pré-temporada é onde se ganha o campeonato. Estamos trabalhando forte.']),
                  'capitão do ' + CL['curto'] if cap else None)
    if t == 'pressao':
        return de(cap, 'O grupo está fechado com o treinador. A responsabilidade é nossa, de quem entra em campo.',
                  'capitão do ' + CL['curto'] if cap else None)
    if t == 'disciplina' and f.get('j'):
        return de(f['j'], 'Errei e já pedi desculpas ao grupo. Não vai se repetir.')
    if t == 'revelacao':
        x = f['x']
        return {'quem': x['nome'], 'papel': f'{POS_TXT.get(x["pos"], "jogador")} do {x["time"]}',
                'texto': rnd.choice(['Eu só penso em jogar. O resto é consequência.',
                                     'Ninguém falava de mim no começo da temporada. Agora eu quero que falem pelo que eu faço em campo.',
                                     'Sonho com a seleção, sim. Mas primeiro tenho que continuar fazendo gol.'])}
    if t == 'bola_ouro':
        meu = next((x for x in f['top'] if x['nosso']), None)
        if meu:
            return {'quem': meu['nome'], 'papel': f'{POS_TXT.get(meu["pos"], "jogador")} do {CL["curto"]}',
                    'texto': 'Prêmio individual é consequência do coletivo. Se o time ganhar, a gente fica perto.'}
    if t == 'obrigacao':
        return de(cap, rnd.choice(['Quem ganhou o que a gente ganhou não pode aceitar isso. A cobrança é justa.',
                                   'Ninguém aqui está acomodado. Foi um tropeço, e a resposta vem no próximo jogo.']), f'capitão do {CL["curto"]}' if cap else None)
    if t == 'renovacao':
        j = _j(r, f['nome'])
        return de(j, 'Meu sonho é terminar a carreira aqui. Já falei isso para todo mundo.' if f['veterano'] else
                  rnd.choice(['Estou feliz aqui. O resto é com o meu empresário e com o clube.', 'Quero ficar, mas preciso me sentir valorizado.']))
    if t == 'joia_base':
        j = _j(r, f['nome'])
        return de(j, rnd.choice(['Estou pronto. Só preciso de uma chance.', 'Treino todo dia para mostrar ao professor que posso ajudar.']))
    if t == 'rumor':
        j = f.get('j')
        tr = _tracos(j)
        frase = (['Fico feliz com o interesse, não vou mentir. Mas agora o foco é aqui.', 'Todo jogador sonha com um clube assim. Vamos ver.']
                 if tr & {'vaidoso', 'jovem impaciente'} else
                 ['Tenho contrato e sou feliz aqui. Não penso em sair.', 'Isso é com o meu empresário. Eu só penso no próximo jogo.'])
        return de(j, rnd.choice(frase)) if j else None
    if t == 'data_fifa':
        art = max(f['convocados'], key=lambda x: x['gols'], default=None)
        if f['esquecidos'] and (not art or not art['gols']):
            e = f['esquecidos'][0]
            return de(_j(r, e['nome']), rnd.choice(['Respeito a decisão do treinador da seleção. Vou continuar trabalhando para voltar.',
                                                     'Não vou mentir: doeu. Mas a resposta eu dou em campo, aqui no clube.']))
        if art:
            return de(_j(r, art['nome']), 'Vestir a camisa da seleção é outra coisa. Agora é recuperar e voltar a ajudar o clube.'
                      if not art['gols'] else 'Fazer gol pela seleção é um sonho de criança. Volto para o clube com a confiança lá em cima.')
        return None
    if t == 'rodada':
        x = f['craque'] if f['modo'] == 'rodada' else f['top']
        papel = f'{POS_TXT.get(x["pos"], "jogador")} do {x["time"]}'
        return {'quem': x['nome'], 'papel': papel, 'texto': rnd.choice(
            ['Fico feliz com o reconhecimento, mas o mérito é do grupo.', 'Trabalho a semana inteira para isso. É só o começo.',
             'Prêmio bom é o que vem junto com vitória. Hoje vieram os dois.'])}
    if t == 'marco':
        m = f['m']
        j = _j(r, m['nome'])
        frase = {'gols': ['Cada gol com esta camisa tem um peso diferente. Quero muitos mais.',
                          'Quando cheguei aqui, nunca imaginei esse número. Dedico à torcida.'],
                 'jogos': ['Vestir esta camisa tantas vezes é um orgulho que não cabe no peito.',
                           'Jogo após jogo, o que me move é a mesma fome do primeiro dia.'],
                 'assist': ['Para mim, um passe para gol vale tanto quanto o gol.', 'Fico feliz de ver os companheiros comemorando. É o meu jeito de jogar.']}[m['metrica']]
        if m['tipo'] == 'recorde':
            frase = ['Recorde é bonito, mas o que eu quero mesmo é título.', 'Entrar para a história deste clube é o maior prêmio.']
        return de(j, rnd.choice(frase)) if j else {'quem': m['nome'], 'papel': f'jogador do {CL["curto"]}', 'texto': rnd.choice(frase)}
    if t == 'selecao' and f['nossos']:
        x = max(f['nossos'], key=lambda x: x['votos'])
        return {'quem': x['nome'], 'papel': f'{POS_TXT.get(x["pos"], "jogador")} do {CL["curto"]}, {x["votos"]} votos',
                'texto': 'Estar entre os 11 melhores do mundo é uma honra. Divido com os meus companheiros.'}
    if t == 'tabela' and cap:
        return de(cap, 'Tabela a gente olha no final. Agora é jogo a jogo.' if f['pos'] == 1 else
                  'Ainda tem muito campeonato. Ninguém aqui jogou a toalha.', f'capitão do {CL["curto"]}')
    return None


# ---------------------------------------------------------------- texto de abertura
def texto(f, r, car):
    t = f['tipo']
    if t == 'premio_mundo':
        import premiacao
        return premiacao.texto(f)
    tab = ((car.get('liga') or {}).get('classificacao') or [])
    eu = next((x for x in tab if x.get('eu')), None)
    if t in ('resultado', 'derrota'):
        g = f['jogo']
        marc = ', '.join(j['nome'] + (f' ({n})' if n > 1 else '') for j, n in f.get('marcadores') or [])
        mel = f.get('melhor')
        partes = [f'O {CL["nome"]} {"venceu" if g["pro"] > g["contra"] else "empatou com" if g["pro"] == g["contra"] else "perdeu para"} o {g["adversario"]}'
                  f' por {max(g["pro"], g["contra"])} a {min(g["pro"], g["contra"])}' + (f' {CL["em_estadio"]}' if g['casa'] else ', fora de casa') + '.']
        if marc:
            partes.append(f'Gols do {CL["curto"]}: {marc}.')
        if mel:
            partes.append(f'{mel[0]["nome"]} teve a melhor nota do time ({_n(mel[1])}).')
        if eu and eu.get('j'):
            partes.append(f'Na tabela, o time é o {eu["pos"]}º, com {eu["pts"]} pontos em {eu["j"]} jogos.')
        return ' '.join(partes)
    if t == 'revelacao':
        x = f['x']
        return (f'{x["nome"]} tem {x["idade"]} anos, joga de {POS_TXT.get(x["pos"], "jogador")} no {x["time"]} e tem nota {x["ovr"]} no game. '
                f'Nada disso explica os números: {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos'
                + (f', média {_n(x["media"])}' if x['media'] else '') + '.'
                + (f' Já estreou pela seleção ({x["sel_jogos"]} jogos, {x["sel_gols"]} gols).' if x['sel_jogos'] else ''))
    if t == 'bola_ouro':
        return 'Pelos números da temporada: ' + '; '.join(
            f'{x["nome"]} ({x["time"]}), {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos' for x in f['top']) + '.'
    if t == 'artilheiro_mundo':
        x = f['x']
        return f'{x["nome"]}, {POS_TXT.get(x["pos"], "atacante")} do {x["time"]}, lidera a artilharia do mundo com {x["gols"]} gols em {x["jogos"]} jogos oficiais.'
    if t == 'selecao':
        por = {}
        for x in f['sel']['time']:
            por.setdefault(x['slot'], []).append(x['nome'])
        return (f'Gol: {", ".join(por["GK"])}. Defesa: {", ".join(por["RB"] + por["CB"] + por["LB"])}. '
                f'Meio: {", ".join(por["MEI"])}. Ataque: {", ".join(por["ATA"])}.')
    if t == 'tabela' and eu:
        lider = tab[0]
        return (f'O {CL["nome"]} soma {eu["pts"]} pontos em {eu["j"]} jogos: {eu.get("v", 0)} vitórias, {eu.get("e", 0)} empates e '
                f'{eu.get("d", 0)} derrotas, {eu["gp"]} gols marcados e {eu["gc"]} sofridos.'
                + ('' if eu['pos'] == 1 else f' O líder {lider["time"]} tem {lider["pts"]}.'))
    if t == 'proximo':
        pj = f['pj']
        return (f'{pj["casa"]} x {pj["fora"]}, {pj["data"][2]:02d}/{pj["data"][1]:02d}, pela {pj["competicao"]}. '
                f'Probabilidades: {pj["prob"]["casa"]}% {pj["casa"]}, {pj["prob"]["empate"]}% empate, {pj["prob"]["fora"]}% {pj["fora"]}. '
                f'Placar provável: {pj["placar_provavel"]}.')
    if t == 'movimento':
        m, n = f['m'], f['n']
        partes = [n['lead']]
        if n.get('analogia'):
            partes.append(f'A comparação é inevitável: {n["analogia"]}.')
        j = _j(r, m['nome'])
        if j and (j['t_gols'] or j['t_assist']):
            partes.append(f'Na temporada, foram {j["t_gols"]} gols' + (f' e {j["t_assist"]} assistências' if j['t_assist'] else '')
                          + f' em {j["t_jogos"]} jogos.')
        return ' '.join(partes)
    if t == 'conflito':
        a = f['env'][0]
        extra = f' Moral de {a["nome"]}: {a["moral"]} de 100.' if a.get('moral') is not None else ''
        return f'{f["texto"]}.{extra} O assunto tomou conta dos corredores {CL["em_ct"]}.'.replace('..', '.')
    if t == 'sequencia':
        return (f'São {f["n"]} vitórias seguidas, com o time somando pontos jogo após jogo.' if f['bom'] else
                f'São {f["n"]} jogos sem vencer. A cobrança cresce a cada rodada.') + \
            (f' Na tabela, o {CL["curto"]} é o {eu["pos"]}º, com {eu["pts"]} pontos.' if eu and eu.get('j') else '')
    if t == 'destaque':
        j = f['j']
        return (f'{j["nome"]} vive grande fase: {j["t_gols"]} gols e {j["t_assist"]} assistências em {j["t_jogos"]} jogos na temporada, '
                f'média {_n(j["r_nota"])} nos últimos jogos e moral {j["moral"]} de 100.')
    if t == 'baixa':
        j = f['j']
        return f'{j["nome"]} está com a moral em {j["moral"]} de 100. Os motivos: ' + '; '.join(j['motivos'][:3]) + '.'
    if t == 'contrato':
        j = f['j']
        return f'O contrato de {j["nome"]} termina em {f["meses"]} meses. Na temporada, {j["t_jogos"]} jogos, {j["t_gols"]} gols e {j["t_assist"]} assistências.'
    if t == 'virada':
        v = f['tie']
        return (f'Na ida, {v["ida"][0]} a {v["ida"][1]}. Na volta, {v["volta"][0]} a {v["volta"][1]}. '
                f'No agregado, {v["agg"][0]} a {v["agg"][1]} contra o {f["adv"]}.')
    if t == 'titulo':
        if f.get('liga'):
            return f'Título da {f["comp"]} com {f["pts"]} pontos' + (f' e {f["restam"]} rodadas de antecedência.' if f.get('restam') else '.')
        return f'Final da {f["comp"]} contra o {f["adv"]}: {f["placar"]}.'
    if t == 'disciplina':
        return f['caso']['relato']
    if t == 'pressao':
        return f'A confiança da diretoria no técnico está em {f["conf"]} de 100. A meta: {((f.get("meta") or {}).get("liga_texto") or "brigar no topo").lower()}.'
    if t == 'obrigacao':
        a = f['ant']
        return (f'Em {a["temporada"]}, o {CL["curto"]} levantou {a["n"]} taças: {", ".join(a["titulos"])}. '
                f'Por isso, o {f["gp"]} x {f["gc"]} com o {f["adv"]} soou como alarme. Quem ganha tudo descobre que ganhar vira obrigação.')
    if t == 'renovacao':
        return (f'O contrato de {f["nome"]} ({f["idade"]} anos) termina em {f["meses"]} meses. '
                + ('O veterano quer encerrar a carreira no clube.' if f['veterano'] else 'Sem renovação, ele pode sair sem deixar nada no caixa.'))
    if t == 'joia_base':
        return f'{f["nome"]} tem {f["idade"]} anos, joga de {POS_TXT.get(f["pos"], "jogador")} e tem nota {f["ovr"]}. Na temporada, entrou em {f["jogos"]} jogos.'
    if t == 'rumor':
        x, j = f['x'], f.get('j') or {}
        return (f'O {x["clube"]} acompanha {x["nome"]}' + (f', que soma {j.get("t_gols", 0)} gols e {j.get("t_assist", 0)} assistências na temporada' if j.get('t_jogos') else '')
                + (f' e tem nota {j["ovr"]}' if j.get('ovr') else '') + '. ' + ('A consulta formal já chegou ao empresário.' if f['fase'] == 'consulta' else 'Por enquanto, é sondagem.'))
    if t == 'data_fifa':
        partes = [f'{x["nome"]} ({x["selecao"].title()}: {x["jogos"]} jogos, {x["min"]} min' + (f', {x["gols"]} gols' if x['gols'] else '') + ')'
                  for x in f['convocados'][:5]]
        return ('Na Data FIFA: ' + '; '.join(partes) + '.' if partes else '') + \
            (f' Ficou de fora: {", ".join(x["nome"] for x in f["esquecidos"][:3])}.' if f['esquecidos'] else '') + \
            (f' Voltam desgastados: {", ".join(x["nome"] for x in f["cansados"][:3])}.' if f['cansados'] else '')
    if t == 'rodada' and f['modo'] == 'tdm':
        return (f'Time do mês de {f["mes"]} na {f["liga"]}: a maior nota é de {f["top"]["nome"]} ({f["top"]["time"]}, {_n(f["top"]["nota"])}).'
                + (f' Do {CL["curto"]}: {", ".join(f["nossos"])}.' if f['nossos'] else '') + f' A imprensa acertou {f["ambos"]} dos 11.')
    if t == 'rodada':
        if f['modo'] == 'rodada':
            c = f['craque']
            return (f'Rodada {f["rodada"]} da {f["liga"]}: o craque foi {c["nome"]} ({c["time"]}), nota {_n(c["nota"] or 0)}.'
                    + (f' Do {CL["curto"]}, entraram na seleção: {", ".join(f["nossos"])}.' if f['nossos'] else ''))
        x = f['top']
        return (f'Jogador de {f["mes"]} na {f["liga"]}: {x["nome"]} ({x["time"]}), {x["gols"]} gols e {x["assist"]} assistências em {x["jogos"]} jogos.'
                + (f' No {CL["curto"]}, o melhor do mês foi {f["nosso"]["nome"]}.' if f.get('nosso') and not x['nosso'] else ''))
    if t == 'marco':
        m = f['m']
        return m['texto'] + (f' São {m["temporadas"]} temporadas com a camisa do {CL["curto"]} desde o início dos registros.' if m['tipo'] == 'marco' else '')
    if t == 'pre':
        return f'A meta da diretoria para a temporada: {((f.get("meta") or {}).get("liga_texto") or "brigar no topo").lower()}. O elenco se reapresenta e os amistosos dão o ritmo.'
    return ''


# ---------------------------------------------------------------- quadros
def quadros(tom, r, car):
    res = car.get('mundo') or {}
    L = car.get('liga') or {}
    tab = L.get('classificacao') or []
    out = []
    if tab and any(t.get('j') for t in tab):
        eu = next((t for t in tab if t.get('eu')), None)
        linhas = tab[:4] + ([eu] if eu and eu['pos'] > 4 else [])
        out.append({'id': 'tabela', 'titulo': f'Tabela · {L.get("competicao", "liga")}',
                    'linhas': [{'a': f'{t["pos"]}º {t["time"]}', 'b': f'{t["pts"]} pts', 'eu': bool(t.get('eu'))} for t in linhas]})
    if L.get('artilheiros'):
        out.append({'id': 'artilharia', 'titulo': 'Artilharia da liga',
                    'linhas': [{'a': f'{a["nome"]} ({a["time"]})', 'b': str(a['gols']), 'eu': a['time'] == r['time']} for a in L['artilheiros'][:4]]})
    if len(res.get('bola_de_ouro') or []) >= 3 and res.get('max_jogos', 0) >= 6:
        out.append({'id': 'bola', 'titulo': 'Corrida da Bola de Ouro',
                    'linhas': [{'a': f'{i + 1}º {x["nome"]} ({x["time"]})', 'b': f'{x["gols"]}G {x["assist"]}A', 'eu': x['nosso']}
                               for i, x in enumerate(res['bola_de_ouro'][:4])]})
    rv = (res.get('revelacoes') or [None])[0]
    if rv:
        out.append({'id': 'revelacao', 'titulo': 'A sensação', 'linhas': [
            {'a': f'{rv["nome"]} · {rv["idade"]} anos · {rv["time"]}', 'b': f'nota {rv["ovr"]}'},
            {'a': f'{rv["jogos"]} jogos, {rv["gols"]} gols, {rv["assist"]} assistências', 'b': (f'seleção ✓' if rv['sel_jogos'] else '')}]})
    art = (res.get('artilheiros') or [])[:4]
    if art and art[0]['gols'] >= 3:
        out.append({'id': 'mundo', 'titulo': 'Artilharia do mundo',
                    'linhas': [{'a': f'{x["nome"]} ({x["time"]})', 'b': str(x['gols']), 'eu': x['nosso']} for x in art]})
    J = sorted((j for j in r['J'] if j['t_gols'] + j['t_assist']), key=lambda j: -(j['t_gols'] + 0.6 * j['t_assist']))[:4]
    if J:
        out.append({'id': 'nossos', 'titulo': f'Os números do {CL["apelido"]}',
                    'linhas': [{'a': j['nome'], 'b': f'{j["t_gols"]}G {j["t_assist"]}A', 'eu': True} for j in J]})
    pref = {'analítico': ['tabela', 'bola', 'artilharia', 'mundo'], 'sensacionalista': ['revelacao', 'bola', 'mundo', 'tabela'],
            'torcedor': ['nossos', 'tabela', 'revelacao', 'artilharia']}[tom]
    por = {q['id']: q for q in out}
    return [por[i] for i in pref if i in por][:2]
