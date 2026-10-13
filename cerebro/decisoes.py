# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Pedidos dos jogadores e decisões do técnico (Vestiário IA).

A cada reunião (tecla 9 -> salvar -> aplicar), no máximo UM jogador pede uma conversa. O técnico responde no
overlay com 1, 2 ou 3 (o módulo Lua grava vestiario_resposta.txt). Na reunião seguinte:
  - a resposta vira efeito na moral e, quando é promessa, a promessa é COBRADA com dados reais do save:
      minutos  -> súmulas dos próximos 3 jogos do time (>= 45% dos minutos)
      braçadeira -> capitão no save na reunião seguinte (o técnico troca no jogo)
      aumento  -> salário (ou fim de contrato) maior no save em até 75 dias de jogo
  - sem resposta = jogador se sente ignorado.
Tudo fica em car['pedido'], car['promessas'], car['liberados'] (memória do vestiário) e os efeitos viram
"histórias" (car['historias']) que o aplicar_vestiario já soma na moral.
"""
from clube import C
from clube import C as _CLUBE
import datetime as dt

ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')
PRAZO_JOGOS = 3
PRAZO_DIAS_AUMENTO = 75
MINUTOS_PROMETIDOS = 0.45


def _tec():
    return _CLUBE.get('tecnico') or 'O técnico'


def _k(k):
    return f'{k[0]}:{k[1]}'


def _dias(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def _efeito(car, hid, hoje, peso, rodadas, motivo, envolvidos):
    car['historias'][hid] = {'data': hoje, 'restam': rodadas, 'peso': peso, 'motivo': motivo,
                             'envolvidos': list(envolvidos)}


def _por_chave(J):
    return {_k(j['k']): j for j in J}


# ---------------------------------------------------------------- pedidos
def _candidatos(r, car, hoje):
    J = r['J']
    ocupados = {p['jogador'] for p in car.get('promessas', []) if p['status'] == 'aberta'}
    recentes = {kk for kk, d in car.get('ultimo_pedido', {}).items() if _dias(hoje, d) < 30}
    tema_recente = {kt for kt, d in car.get('pedido_temas', {}).items() if _dias(hoje, d) < 90}
    cap = r['capitao']
    out = []
    for j in J:
        kk = _k(j['k'])
        if kk in ocupados or kk in recentes or kk in car.get('liberados', []):
            continue
        if j['status'] not in ALTO and j['moral'] >= 30:
            continue
        txt = ' '.join(j['motivos'])
        if 'braçadeira' in txt and cap and f'{kk}|braçadeira' not in tema_recente:
            out.append((j['moral'] - 5, 'braçadeira', j))
        elif 'joga pouco' in txt and f'{kk}|minutos' not in tema_recente:
            out.append((j['moral'], 'minutos', j))
        elif 'ganha menos' in txt and f'{kk}|salario' not in tema_recente:
            out.append((j['moral'] + 3, 'salario', j))
        elif 'contrato acaba' in txt and j['status'] in ALTO and f'{kk}|contrato' not in tema_recente:
            out.append((j['moral'] + 5, 'contrato', j))
    return sorted((c for c in out if c[0] < 45), key=lambda c: c[0])


def novo_pedido(r, car, hoje):
    """Escolhe o pedido mais grave da rodada (ou nenhum). Devolve o dict do pedido."""
    c = _candidatos(r, car, hoje)
    if not c:
        return None
    _, tipo, j = c[0]
    cap = r['capitao']
    pct = j['r_min'] / max(1, 90 * j['r_jogos_time'])
    if tipo == 'braçadeira':
        fala = f'"Estou há {j["anos"]:.0f} anos aqui. A braçadeira tinha que ser minha, não do {cap["nome"]}."'
        op = ['Devolver a braçadeira a ele (troque o capitão no jogo antes da próxima reunião)',
              f'Manter {cap["nome"]} e explicar a escolha',
              'Dar a ele um papel de líder sem a faixa (vice-capitão)']
    elif tipo == 'minutos':
        fala = f'"Joguei só {pct:.0%} dos minutos. Um jogador como eu não pode ficar no banco."'
        op = [f'Prometer mais minutos (cobrado nos próximos {PRAZO_JOGOS} jogos: pelo menos 45%)',
              'Ele vai ter que lutar pela vaga como todo mundo',
              'Liberar para negociar (coloque-o na lista de transferências no jogo)']
    elif tipo == 'salario':
        fala = '"Tem gente ganhando bem mais do que eu jogando menos. Quero ser valorizado."'
        op = [f'Prometer renovação com aumento (faça no jogo em até {PRAZO_DIAS_AUMENTO} dias)',
              'Salário é questão de mérito, não de comparação',
              'Liberar para negociar (coloque-o na lista de transferências no jogo)']
    else:
        c_ = j['contrato']
        fala = f'"Meu contrato acaba em {c_[2]:02d}/{c_[1]:02d}/{c_[0]}. Preciso saber do meu futuro."'
        op = [f'Prometer renovação (faça no jogo em até {PRAZO_DIAS_AUMENTO} dias)',
              'Decidir só no fim da temporada',
              'Liberar para negociar (coloque-o na lista de transferências no jogo)']
    pid = f'{tipo}|{_k(j["k"])}|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}'
    car.setdefault('ultimo_pedido', {})[_k(j['k'])] = hoje
    car.setdefault('pedido_temas', {})[f'{_k(j["k"])}|{tipo}'] = hoje
    return {'id': pid, 'tipo': tipo, 'jogador': _k(j['k']), 'nome': j['nome'], 'status': j['status'],
            'fala': fala, 'opcoes': op, 'data': hoje, 'capitao': _k(cap['k']) if cap else None,
            'cap_nome': cap['nome'] if cap else None, 'salario': j['salario'], 'contrato': j['contrato']}


def texto_pedido(p):
    linhas = [f'DECISÃO — {p["nome"]} ({p["status"]}) pede uma conversa:', '  ' + p['fala']]
    linhas += [f'  {i} = {o}' for i, o in enumerate(p['opcoes'], 1)]
    linhas.append('  (aperte 1, 2 ou 3 com o overlay aberto; vale na próxima reunião)')
    return linhas


# ---------------------------------------------------------------- respostas
def aplicar_resposta(car, p, opcao, r, hoje):
    """Efeito imediato da resposta + promessa (se houver). Devolve lista de notícias."""
    J = r['J']
    todos = [_k(j['k']) for j in J]
    jk, nome = p['jogador'], p['nome']
    lenda = p['status'] in ('Lenda', 'Ídolo')
    hid = f'Decisao|{p["id"]}'
    news = []
    if opcao is None:
        _efeito(car, hid, hoje, -8, 3, 'sente que o técnico o ignorou', [jk])
        return [f'{nome} reclama: pediu uma conversa com {_tec()} e não foi recebido.']
    t = p['tipo']
    if opcao == 3 and t != 'braçadeira':
        _efeito(car, hid, hoje, +6, 2, 'liberado para negociar', [jk])
        car.setdefault('liberados', []).append(jk)
        car.setdefault('fichas', {})[jk] = {'nome': nome, 'status': p['status']}
        news.append(f'{C["curto"]} libera {nome} para negociar uma saída.')
        if lenda:
            _efeito(car, hid + '|grupo', hoje, -2, 1, f'saída anunciada de {nome}', todos)
            news.append(f'Torcida protesta contra a possível saída de {nome}, {p["status"].lower()} do clube.')
        return news
    if t == 'minutos':
        if opcao == 1:
            _efeito(car, hid, hoje, +12, 3, 'recebeu promessa de minutos', [jk])
            car.setdefault('promessas', []).append({'id': p['id'], 'tipo': 'minutos', 'jogador': jk, 'nome': nome,
                                                    'data': p['data'], 'status': 'aberta'})
            news.append(f'{_tec()} promete mais espaço a {nome}: "Ele vai ter os minutos que merece."')
        else:
            _efeito(car, hid, hoje, -6 if lenda else -3, 2, 'ouviu que precisa lutar pela vaga', [jk])
            jovens = [_k(j['k']) for j in J if j['status'] in ('Promessa', 'Elenco')]
            _efeito(car, hid + '|grupo', hoje, +2, 1, 'técnico cobra meritocracia', jovens)
            news.append(f'Sem privilégios: {_tec()} diz que {nome} terá de brigar pela posição.')
    elif t == 'braçadeira':
        cap_nome = p['cap_nome']
        if opcao == 1:
            _efeito(car, hid, hoje, +8, 1, 'braçadeira prometida', [jk])
            car.setdefault('promessas', []).append({'id': p['id'], 'tipo': 'capitao', 'jogador': jk, 'nome': nome,
                                                    'capitao_antes': p['capitao'], 'cap_nome': cap_nome,
                                                    'data': p['data'], 'status': 'aberta'})
            news.append(f'Reviravolta: {nome} deve voltar a usar a braçadeira do {C["curto"]}.')
        elif opcao == 2:
            _efeito(car, hid, hoje, -5, 2, 'técnico manteve o capitão', [jk])
            if p['capitao']:
                _efeito(car, hid + '|cap', hoje, +4, 2, 'confirmado como capitão', [p['capitao']])
            news.append(f'{_tec()} banca {cap_nome} como capitão e pede respeito a {nome}.')
        else:
            _efeito(car, hid, hoje, +6, 3, 'ganhou papel de liderança', [jk])
            news.append(f'{nome} vira vice-capitão e ganha voz ativa no vestiário.')
    else:   # salario / contrato
        if opcao == 1:
            _efeito(car, hid, hoje, +10, 3, 'recebeu promessa de renovação', [jk])
            car.setdefault('promessas', []).append({'id': p['id'], 'tipo': 'renovacao', 'jogador': jk, 'nome': nome,
                                                    'salario': p['salario'], 'contrato': p['contrato'],
                                                    'data': p['data'], 'status': 'aberta'})
            news.append(f'Diretoria acena com renovação para {nome}.')
        else:
            _efeito(car, hid, hoje, -6 if t == 'salario' else -4, 2, 'pedido recusado', [jk])
            news.append(f'{nome} não gosta da resposta do clube sobre seu futuro.')
    return news


# ---------------------------------------------------------------- promessas
def cobrar_promessas(car, r, hoje):
    """Avalia promessas abertas com os dados do save. Devolve notícias."""
    J = _por_chave(r['J'])
    todos = list(J)
    news = []
    # liberados que já saíram do elenco: despedida
    for jk in list(car.get('liberados', [])):
        if jk not in J:
            car['liberados'].remove(jk)
            info = car.get('fichas', {}).get(jk, {})
            nome = info.get('nome', 'O jogador liberado')
            if info.get('status') in ('Lenda', 'Ídolo'):
                news.append(f'Fim de uma era: {nome} deixa o {C["curto"]}. Torcida se despede do {info["status"].lower()}.')
                _efeito(car, f'Saida|{jk}|{hoje}', hoje, -3, 1, f'saída de {nome}', todos)
            else:
                news.append(f'{nome} deixa o {C["curto"]} após ser liberado pela comissão técnica.')
    for pr in car.get('promessas', []):
        if pr['status'] != 'aberta':
            continue
        jk, nome = pr['jogador'], pr['nome']
        j = J.get(jk)
        hid = f'Promessa|{pr["id"]}'
        cumpriu = None
        if pr['tipo'] == 'minutos':
            reg, pid = map(int, jk.split(':'))
            jogos = [p for p in r['jogos'] if p['data'] > tuple(pr['data'])][:PRAZO_JOGOS]
            if len(jogos) >= PRAZO_JOGOS:
                minutos = sum(x['minutos'] for p in jogos for x in p['linhas1'] + p['linhas2']
                              if (x['reg'], x['pid']) == (reg, pid))
                cumpriu = minutos >= MINUTOS_PROMETIDOS * 90 * PRAZO_JOGOS
                pr['minutos'] = minutos
        elif pr['tipo'] == 'capitao':
            cumpriu = bool(r['capitao']) and _k(r['capitao']['k']) == jk
            if cumpriu and pr.get('capitao_antes'):
                _efeito(car, hid + '|ex', hoje, -10, 3, 'perdeu a braçadeira', [pr['capitao_antes']])
        elif pr['tipo'] == 'renovacao' and j:
            melhorou = j['salario'] > pr['salario'] or (j['contrato'] and pr['contrato'] and
                                                        tuple(j['contrato']) > tuple(pr['contrato']))
            if melhorou:
                cumpriu = True
            elif _dias(hoje, pr['data']) > PRAZO_DIAS_AUMENTO:
                cumpriu = False
        if cumpriu is None:
            continue
        pr['status'] = 'cumprida' if cumpriu else 'quebrada'
        pr['avaliada_em'] = hoje
        if cumpriu:
            _efeito(car, hid, hoje, +10, 3, 'promessa cumprida', [jk])
            news.append({'minutos': f'Promessa cumprida: {nome} voltou a ter espaço e elogia a palavra do técnico.',
                         'capitao': f'{nome} volta a ser o capitão do {C["curto"]}.',
                         'renovacao': f'{nome} renova e se diz valorizado pelo clube.'}[pr['tipo']])
        else:
            _efeito(car, hid, hoje, -18, 4, 'promessa quebrada', [jk])
            _efeito(car, hid + '|grupo', hoje, -3, 1, 'técnico não cumpriu a palavra', todos)
            news.append({'minutos': f'{nome} desabafa: "Me prometeram minutos e continuei no banco."',
                         'capitao': f'{nome} se sente enganado: a braçadeira prometida nunca chegou.',
                         'renovacao': f'{nome} cobra a renovação prometida que não saiu.'}[pr['tipo']] +
                        ' O vestiário questiona a palavra do treinador.')
    return news
