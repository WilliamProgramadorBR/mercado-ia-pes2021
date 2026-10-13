# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""O CELULAR DO TÉCNICO (11/10/2026): mensagens de quem vive em volta do clube, com respostas que mexem na moral.

Cada conversa é um CASO (tipo 'celular') e usa o mesmo caminho das decisões de disciplina: a Central registra a
resposta (acoes.caso), o efeito na moral vale na hora e a seta muda no jogo quando a moral cruza a faixa.
Campos a mais: contato {nome, papel, icone}, mensagens [texto, ...]. Sem resposta em 7 dias, vale a última opção
(o "visualizou e não respondeu").

Quem manda mensagem (só quando o momento justifica):
  presidente      depois de 3+ jogos sem vencer, confiança baixa, ou depois de título / goleada grande
  empresário      rumor que virou consulta formal (rumores.py)
  capitão         vestiário tenso/explosivo, ou crise aberta
  auxiliar        jogador importante com condição baixa antes do próximo jogo (ou voltando da Data FIFA)
  jogador         jovem impaciente ou vaidoso com poucos minutos e moral caindo
  ex-jogador      quem saiu do clube nos últimos dias (despedida)
"""
import datetime as dt

PRESIDENTE = 'Presidente'
MAX_ABERTOS = 4


def _d(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def _k(k):
    return f'{k[0]}:{k[1]}'


def _caso(cid, hoje, contato, papel, icone, mensagens, titulo, envolvidos, nomes, opcoes):
    return {'id': cid, 'tipo': 'celular', 'sub': papel, 'data': list(hoje), 'gravidade': 'leve',
            'contato': {'nome': contato, 'papel': papel, 'icone': icone}, 'mensagens': mensagens,
            'titulo': titulo, 'relato': ' '.join(mensagens), 'envolvidos': envolvidos, 'nomes': nomes,
            'opcoes': [dict(o, id=str(i + 1)) for i, o in enumerate(opcoes)]}


def E(k, d, rod, motivo):
    return {'k': k, 'delta': d, 'rodadas': rod, 'motivo': motivo}


def gerar(r, car, hoje, rnd, consultas=()):
    J = r['J']
    abertos = [c for c in car.get('casos') or [] if c['tipo'] == 'celular']
    ultimo = car.setdefault('celular_ultimo', {})   # papel -> data da última mensagem (não lotar o celular)
    nos = r['time']
    tec = r.get('tecnico') or 'professor'
    novos = []

    def pode(papel, dias):
        u = ultimo.get(papel)
        return (not u or _d(hoje, tuple(u)) >= dias) and not any(c['sub'] == papel for c in abertos + novos)

    # ----- empresário: consulta formal de clube grande
    for x in consultas:
        j = next((j for j in J if j['nome'] == x['nome']), None)
        if not j or not pode(f'empresário|{x["nome"]}', 30):
            continue
        tr = set(((j.get('perfil') or {}).get('tracos')) or [])
        quer = bool(tr & {'vaidoso', 'jovem impaciente'}) or j['moral'] < 60
        k = _k(j['k'])
        novos.append(_caso(f'cel|emp|{x["id"]}', hoje, f'Empresário de {j["nome"]}', f'empresário|{x["nome"]}', '💼',
                           [f'Boa tarde, {tec}. Sendo transparente com você: o {x["clube"]} me ligou ontem perguntando pelo {j["nome"]}.',
                            'Não tem proposta no papel ainda, mas o interesse é real. ' + ('Ele ficou balançado, não vou mentir.' if quer else 'Ele está feliz aí, mas é uma camisa pesada.'),
                            'Como você quer que eu conduza?'],
                           f'{x["clube"]} consultou por {j["nome"]}', [k], [j['nome']], [
            {'texto': 'Ele não está à venda. Pode dizer isso a eles.', 'rumor': x['nome'],
             'efeitos': [E(k, -4 if quer else 3, 2, f'o técnico fechou a porta para o {x["clube"]}')],
             'eco': (f'{j["nome"]} fica: técnico barra o {x["clube"]}', 'Nos bastidores, a resposta foi curta.')},
            {'texto': 'Pode ouvir. Se for bom para todo mundo, a gente conversa.',
             'efeitos': [E(k, 5 if quer else -1, 2, 'o técnico deixou o empresário ouvir a proposta'), E('*', -1, 1, f'o grupo soube que {j["nome"]} pode sair')],
             'eco': (f'Porta aberta para {j["nome"]}?', f'O {x["clube"]} foi autorizado a apresentar uma proposta.')},
            {'texto': f'Quero falar com o {j["nome"]} pessoalmente antes de qualquer coisa.',
             'efeitos': [E(k, 2, 2, 'o técnico quis ouvir ele antes de decidir')], 'eco': None},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [E(k, -2, 1, 'o técnico ignorou o empresário dele')], 'eco': None}]))
        ultimo[f'empresário|{x["nome"]}'] = list(hoje)
    # ----- presidente
    ult = r.get('ultimos') or []
    res = ['V' if g['pro'] > g['contra'] else 'E' if g['pro'] == g['contra'] else 'D' for g in ult[-4:]]
    conf = (car.get('diretoria') or {}).get('confianca')
    sem_vencer = 0
    for x in reversed(res):
        if x == 'V':
            break
        sem_vencer += 1
    if pode('presidente', 14) and (sem_vencer >= 3 or (conf is not None and conf < 45)):
        novos.append(_caso(f'cel|pres|{hoje}', hoje, PRESIDENTE, 'presidente', '🏛️',
                           [f'{tec}, boa noite. {sem_vencer} jogos sem vencer' if sem_vencer >= 3 else f'{tec}, boa noite.',
                            'O conselho está me cobrando e a torcida também. Eu confio em você, mas preciso de uma resposta em campo.',
                            'O que você precisa para virar essa chave?'],
                           'O presidente cobra resultados', ['*'], ['elenco'], [
            {'texto': 'Confie no trabalho. O grupo está fechado e a virada vem.', 'efeitos': [E('*', 1, 1, 'o técnico bancou o grupo com o presidente')],
             'eco': ('Técnico garante ao presidente: "a virada vem"', 'Conversa franca nos bastidores.')},
            {'texto': 'Vou cobrar o elenco. Alguns não estão rendendo o que podem.', 'efeitos': [E('*', -2, 1, 'o técnico dividiu a culpa com o elenco')],
             'eco': ('Técnico promete cobrar o elenco', 'Vestiário sente a pressão.')},
            {'texto': 'Preciso de reforços. Com esse elenco curto, fica difícil.', 'efeitos': [E('*', -1, 1, 'o técnico pediu reforços: o grupo ouviu')],
             'eco': ('Técnico pede reforços à diretoria', 'Recado para o mercado.')},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [], 'eco': ('Técnico ignora o presidente', 'O clima na diretoria esfriou.')}]))
        ultimo['presidente'] = list(hoje)
    elif pode('presidente', 21) and ult and ult[-1]['pro'] - ult[-1]['contra'] >= 4:
        g = ult[-1]
        novos.append(_caso(f'cel|pres|{hoje}', hoje, PRESIDENTE, 'presidente', '🏛️',
                           [f'Que noite, {tec}! {g["pro"]} a {g["contra"]} no {g["adversario"]}!', 'Passa o meu abraço para o grupo. O conselho está em festa.'],
                           'O presidente comemora a goleada', ['*'], ['elenco'], [
            {'texto': 'Obrigado, presidente! O mérito é dos jogadores, vou passar o recado.', 'efeitos': [E('*', 2, 1, 'o presidente mandou parabéns ao grupo')], 'eco': None},
            {'texto': 'Obrigado. Mas não tem nada ganho ainda.', 'efeitos': [], 'eco': None},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [], 'eco': None}]))
        ultimo['presidente'] = list(hoje)
    # ----- capitão: vestiário pesado
    cap = next((j for j in J if j.get('capitao')), None)
    nivel = (car.get('dificuldade') or {}).get('nivel')
    crise = next((c for c in car.get('casos') or [] if c['tipo'] == 'crise'), None)
    if cap and pode('capitão', 14) and (nivel in ('tenso', 'explosivo') or crise):
        k = _k(cap['k'])
        assunto = crise['titulo'] if crise else 'o clima no vestiário'
        novos.append(_caso(f'cel|cap|{hoje}', hoje, cap['nome'], 'capitão', '©️',
                           [f'Professor, posso ser sincero? O grupo está pesado por causa d{"a" if crise else "o"} {assunto.lower() if crise else "clima"}.',
                            'Tem gente reclamando pelos cantos. Se você quiser, eu chamo uma conversa só entre os jogadores antes do treino.'],
                           f'{cap["nome"]} alerta: o grupo está pesado', [k], [cap['nome']], [
            {'texto': 'Faz isso, capitão. Confio em você para segurar o grupo.', 'efeitos': [E(k, 4, 2, 'o técnico deu força a ele como líder'), E('*', 1, 1, 'o capitão chamou o grupo para conversar')], 'eco': None},
            {'texto': 'Deixa comigo. Eu resolvo com cada um.', 'efeitos': [E(k, -1, 1, 'o técnico não quis a ajuda dele')], 'eco': None},
            {'texto': 'Quem estiver insatisfeito que fale comigo, não pelos cantos.', 'efeitos': [E('*', -1, 1, 'o técnico endureceu com quem reclama')], 'eco': None},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [E(k, -2, 1, 'o técnico ignorou o alerta do capitão')], 'eco': None}]))
        ultimo['capitão'] = list(hoje)
    # ----- auxiliar técnico: desgaste antes do próximo jogo
    pj = car.get('proximo_jogo') or {}
    fifa = car.get('data_fifa') or {}
    cans = [j for j in J if j.get('condicao') is not None and j['condicao'] < 70 and j['ovr'] >= 84]
    cans.sort(key=lambda j: j['condicao'])
    if cans and pode('auxiliar', 7) and pj.get('adversario'):
        j = cans[0]
        k = _k(j['k'])
        veio_sel = any(x['nome'] == j['nome'] for x in fifa.get('cansados') or [])
        novos.append(_caso(f'cel|aux|{hoje}', hoje, 'Auxiliar técnico', 'auxiliar', '📋',
                           [f'Professor, os dados do físico chegaram. O {j["nome"]} está com condição {j["condicao"]}'
                            + (' depois da seleção.' if veio_sel else '.'),
                            f'Contra o {pj["adversario"]}, se ele começar jogando, o risco de queda de rendimento é alto. Poupo?'],
                           f'{j["nome"]} no limite físico', [k], [j['nome']], [
            {'texto': 'Poupa. Ele começa no banco.', 'efeitos': [E(k, 1, 1, 'foi poupado para recuperar')],
             'compromisso': {'tipo': 'descanso', 'jogos': 1,
                             'ok': {'efeitos': [E(k, 2, 1, 'foi poupado como o auxiliar pediu')], 'noticia': f'{j["nome"]} foi poupado e volta descansado.'},
                             'quebra': {'efeitos': [E(k, -4, 2, 'o técnico disse que ia poupá-lo e o escalou')],
                                        'noticia': f'{j["nome"]} ia ser poupado, mas começou jogando. O departamento físico não gostou.'}}, 'eco': None},
            {'texto': 'Ele joga. É jogo grande e eu preciso dele.', 'efeitos': [E(k, 2, 1, 'o técnico confiou nele mesmo cansado')], 'eco': None},
            {'texto': 'Começa e eu tiro no intervalo.', 'efeitos': [], 'eco': None},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [], 'eco': None}]))
        ultimo['auxiliar'] = list(hoje)
    # ----- jogador pedindo minutos
    impac = [j for j in J if set(((j.get('perfil') or {}).get('tracos')) or []) & {'jovem impaciente', 'vaidoso'}
             and j['moral'] < 68 and j['r_jogos_time'] >= 3 and j['r_min'] < 90 * j['r_jogos_time'] * 0.4]
    impac.sort(key=lambda j: j['moral'])
    if impac and pode('jogador', 10):
        j = impac[0]
        k = _k(j['k'])
        jovem = 'jovem impaciente' in set(((j.get('perfil') or {}).get('tracos')) or [])
        novos.append(_caso(f'cel|jog|{_k(j["k"])}|{hoje}', hoje, j['nome'], 'jogador', '⚽',
                           ['Oi, professor. Desculpa mandar mensagem.',
                            ('Eu sei que sou novo, mas estou treinando forte e quase não entro. Queria saber o que falta para eu ter uma chance.'
                             if jovem else 'Não estou acostumado a ficar no banco. Eu sei o que posso dar para esse time.'),
                            'Posso contar com minutos nos próximos jogos?'],
                           f'{j["nome"]} pede minutos', [k], [j['nome']], [
            {'texto': 'Vai ter. Se continuar assim, você entra nos próximos jogos.', 'efeitos': [E(k, 5, 2, 'o técnico prometeu minutos pelo celular')],
             'compromisso': {'tipo': 'jogar', 'jogos': 2,
                             'ok': {'efeitos': [E(k, 4, 2, 'o técnico cumpriu a promessa de minutos')], 'noticia': f'{j["nome"]} ganhou os minutos prometidos.'},
                             'quebra': {'efeitos': [E(k, -8, 3, 'prometeram minutos pelo celular e ele não jogou')],
                                        'noticia': f'{j["nome"]} ouviu uma promessa de minutos e não saiu do banco. Está magoado.'}}, 'eco': None},
            {'texto': 'Continua trabalhando. A chance vem no momento certo.', 'efeitos': [E(k, -1 if jovem else -3, 2, 'o técnico pediu paciência')], 'eco': None},
            {'texto': 'Quem decide quem joga sou eu. Treina e para de pedir.', 'efeitos': [E(k, -6, 3, 'levou uma resposta dura do técnico')],
             'eco': (f'Clima ruim entre técnico e {j["nome"]}', 'A resposta seca vazou do CT.')},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [E(k, -3, 2, 'o técnico deixou ele no vácuo')], 'eco': None}]))
        ultimo['jogador'] = list(hoje)
    # ----- ex-jogador se despedindo
    for m in car.get('mov_executadas') or []:
        if m.get('tipo') != 'saida' or _d(hoje, tuple(m['data'])) > 10 or not pode(f'ex|{m["nome"]}', 365):
            continue
        novos.append(_caso(f'cel|ex|{m["nome"]}|{hoje}', hoje, m['nome'], f'ex|{m["nome"]}', '👋',
                           [f'Professor, passando para agradecer. Foi uma honra jogar no {nos}.',
                            f'Agora é {m.get("clube") or m.get("destino") or "vida nova"}, mas vou torcer por vocês sempre. Obrigado por tudo.'],
                           f'{m["nome"]} se despede', ['*'], ['elenco'], [
            {'texto': 'Obrigado você. As portas daqui estão sempre abertas.', 'efeitos': [E('*', 1, 1, 'o técnico se despediu com carinho de um ex-companheiro')], 'eco': None},
            {'texto': 'Boa sorte. Só não faz gol na gente. 😄', 'efeitos': [], 'eco': None},
            {'texto': '(visualizou e não respondeu)', 'efeitos': [], 'eco': None}]))
        ultimo[f'ex|{m["nome"]}'] = list(hoje)
        break
    vagas = MAX_ABERTOS - len(abertos)
    return novos[:max(0, min(2, vagas))]
