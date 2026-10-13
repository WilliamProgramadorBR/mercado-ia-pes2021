# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Exigências por PERFIL de jogador (etapa 3 da vida futebolística, 10/10/2026).

Cada jogador ganha um perfil a partir do que o jogo já tem: idade, nota, status (Lenda/Ídolo/Superastro/Craque),
função nativa, tempo de clube, liderança, posição. Do perfil saem DESEJOS: bater pênalti, bater falta, braçadeira,
camisa 10 (ou a camisa da posição). Desejo não atendido vira um CASO na Central (mesmo fluxo de disciplina/calendário).

Promessa feita na Central é cobrada pelo SAVE na reunião seguinte (o técnico muda no próprio jogo, Plano de jogo):
  bloco do time do usuário (carreira.BLOCO_USUARIO): +40 falta longa, +41 falta curta, +42 falta 2,
  +43 escanteio esq., +44 escanteio dir., +45 PÊNALTI, +49 CAPITÃO (índices do elenco);
  números de camisa: registro do time +662 (u16 por vaga).            Mapeado com prints em 10/10/2026.
Cumpriu -> moral sobe (e o "dono" anterior do posto pode ficar enciumado); não cumpriu -> moral despenca.
"""
import struct

ALTO = ('Lenda', 'Ídolo', 'Superastro', 'Craque')
ATAQUE = ('CF', 'SS', 'LWF', 'RWF', 'AMF')
CRIACAO = ('AMF', 'CMF', 'LMF', 'RMF', 'SS', 'LWF', 'RWF')
COBRADOR = {'falta_longa': 40, 'falta_curta': 41, 'falta2': 42, 'escanteio_esq': 43, 'escanteio_dir': 44, 'penalti': 45}
NOMES = {'penalti': 'bater os pênaltis', 'falta_longa': 'bater as faltas de longe', 'falta_curta': 'bater as faltas',
         'capitao': 'ser o capitão', 'camisa10': 'vestir a camisa 10'}


def chave(k):
    return f'{k[0]}:{k[1]}'


def estado(d, s, ti):
    """O que está valendo no save: {'penalti': k, 'falta_longa': k, ..., 'capitao': k, 'camisa10': k | None}."""
    import carreira
    sq = s.squad(ti)
    u = carreira.BLOCO_USUARIO
    out = {}
    for nome, off in COBRADOR.items():
        i = d[u + off]
        out[nome] = sq[i] if i < len(sq) else None
    i = d[u + 49]
    out['capitao'] = sq[i] if i < len(sq) else None
    nums = s.numbers(ti)
    out['camisa10'] = next((sq[i] for i in range(len(sq)) if i < len(nums) and nums[i] == 10), None)
    return out


def na_janela(hoje):
    import janela
    try:
        return janela.window_of(tuple(hoje))[1] != 'fora'
    except Exception:  # noqa: BLE001
        return False


def perfil(j, J):
    """Traços e desejos do jogador. Determinístico (não muda de rodada para rodada)."""
    tracos, desejos = [], []
    estrela = j['status'] in ALTO
    melhor_ofensivo = max((o['ovr'] for o in J if o['pos'] in ATAQUE), default=0)
    if estrela and j['idade'] <= 30 and j['pos'] in ATAQUE + CRIACAO:
        tracos.append('vaidoso')
    if j.get('lider', 0) >= 55 or j.get('skill_cap'):
        tracos.append('líder')
    if j['idade'] >= 32 and estrela:
        tracos.append('veterano exigente')
    if j['idade'] <= 21 and j['ovr'] >= 75:
        tracos.append('jovem impaciente')
    if not tracos:
        tracos.append('discreto')
    if 'vaidoso' in tracos and j['pos'] in ATAQUE and j['ovr'] >= melhor_ofensivo - 2:
        desejos.append('penalti')
    if 'vaidoso' in tracos and j['pos'] in CRIACAO:
        desejos.append('falta_longa')
    if 'vaidoso' in tracos and j['pos'] in ('AMF', 'SS', 'CF', 'LWF', 'RWF') and j['ovr'] >= 80:
        desejos.append('camisa10')
    if 'líder' in tracos and (j['status'] in ('Lenda', 'Ídolo') or j.get('lider', 0) >= 65):
        desejos.append('capitao')
    return {'tracos': tracos, 'desejos': desejos}


def merito(j, des):
    """Nota do jogador para o posto, pelos dados do jogo: pênalti/falta pelos atributos de finalização e bola parada,
    braçadeira pela liderança calculada no vestiário, camisa 10 pela nota geral + status."""
    if des == 'penalti':
        return j.get('n_penalti', 0)
    if des == 'falta_longa':
        return j.get('n_falta', 0)
    if des == 'capitao':
        return j.get('lider', 0)
    return j['ovr'] + {'Lenda': 4, 'Ídolo': 3, 'Superastro': 3, 'Craque': 1}.get(j['status'], 0)


ROTULO = {'penalti': 'nota de pênalti', 'falta_longa': 'nota de falta', 'capitao': 'liderança', 'camisa10': 'peso no elenco'}


def _relato(j, desejo, dono, mj=None, md=None):
    n = j['nome']
    outro = dono['nome'] if dono else 'outro jogador'
    return {
        'penalti': f'{n} procurou a comissão técnica: quer ser o batedor oficial de pênaltis. "Decido jogos, preciso '
                   f'dessa responsabilidade." Hoje quem bate é {outro}.',
        'falta_longa': f'{n} quer assumir as faltas de longe. Treina cobranças depois do treino todos os dias. Hoje o '
                       f'cobrador é {outro}.',
        'camisa10': f'{n} pediu a camisa 10. "Ela tem peso, e eu quero esse peso." Hoje ela é de {outro}.',
        'capitao': f'{n} se sente pronto para liderar: quer a braçadeira de capitão. Hoje ela é de {outro}.',
    }[desejo] + (f' Pelos números da comissão ({ROTULO[desejo]}): {n} {mj} x {md} {outro}.' if mj is not None and md is not None else '')


def gerar(r, car, d, s, hoje, rnd):
    """No máximo 1 exigência nova por rodada; o mesmo jogador só a cada 45 dias; o mesmo desejo só depois de 90 dias
    se ele já foi atendido ou recusado."""
    from vestiario import dias
    J = r['J']
    porK = {j['k']: j for j in J}
    ok = estado(d, s, r['ti'])
    hist = car.setdefault('exigencias_hist', {})
    abertos = {k for c in car.get('casos', []) for k in c['envolvidos']}
    abertos |= {c['k'] for c in car.get('compromissos', []) if c['status'] == 'aberto'}
    cands = []
    for j in J:
        kk = chave(j['k'])
        if kk in abertos:
            continue
        pf = perfil(j, J)
        for des in pf['desejos']:
            if ok.get(des) == j['k']:
                continue                                   # já tem
            if des == 'camisa10' and not na_janela(hoje):
                continue                                   # camisa só se troca na janela de transferências
            h = hist.get(f'{kk}|{des}')
            if h and dias(tuple(hoje), tuple(h)) < 90:
                continue
            ultimo = max((v for x, v in hist.items() if x.startswith(kk + '|')), default=None)
            if ultimo and dias(tuple(hoje), tuple(ultimo)) < 45:
                continue
            dono_ = porK.get(ok.get(des))
            gap = merito(j, des) - merito(dono_, des) if dono_ else 99
            # o dono é claramente melhor: não há discussão (antes o pedido surgia mesmo assim)
            if gap < -8 or (gap < -3 and 'vaidoso' not in pf['tracos']):
                continue
            peso = {'penalti': 3, 'camisa10': 2.5, 'capitao': 2, 'falta_longa': 1.5}[des] + j['torcida'] / 50 + max(0, gap) / 4
            cands.append((peso, j, des, pf))
    import dificuldade
    if not cands or rnd.random() > dificuldade.chance(0.55, 0.9):
        return []
    tot = sum(c[0] for c in cands)
    x = rnd.random() * tot
    for peso, j, des, pf in cands:
        x -= peso
        if x <= 0:
            break
    kk = chave(j['k'])
    dono = porK.get(ok.get(des))
    kd = chave(dono['k']) if dono else None
    hist[f'{kk}|{des}'] = list(hoje)
    mj, md = merito(j, des), (merito(dono, des) if dono else None)
    justo = md is None or mj >= md - 3          # disputa legítima x vaidade (o dono é melhor, mas não muito)
    ciume = ([{'k': kd, 'delta': -5, 'rodadas': 3, 'motivo': f'perdeu para {j["nome"]} o direito de {NOMES[des]}'}]
             if dono and dono['status'] in ALTO else
             [{'k': kd, 'delta': -2, 'rodadas': 2, 'motivo': f'perdeu para {j["nome"]} o direito de {NOMES[des]}'}]
             if dono else [])
    return [{
        'id': f'exig|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}|{des}|{kk}', 'tipo': 'exigencia', 'sub': des,
        'data': list(hoje), 'gravidade': 'leve', 'envolvidos': [kk], 'nomes': [j['nome']],
        'titulo': f'{j["nome"]} quer {NOMES[des]}', 'relato': _relato(j, des, dono, mj, md) +
            ('' if justo else ' O grupo vê mais vaidade do que mérito no pedido.'),
        'perfil': pf['tracos'],
        'opcoes': [
            {'id': '1', 'texto': f'Atender: {j["nome"]} vai {NOMES[des]} (mude no jogo ' +
                                 ('em "Editar número do jogador" antes de a janela fechar)' if des == 'camisa10' else 'antes da próxima partida)'),
             'efeitos': [{'k': kk, 'delta': 4, 'rodadas': 2, 'motivo': f'o técnico aceitou que ele vá {NOMES[des]}'}] +
                        ([] if justo else [{'k': '*', 'delta': -1, 'rodadas': 1, 'motivo': 'o grupo viu privilégio: o posto era de quem rende mais'}]),
             'compromisso': {'tipo': 'posto', 'posto': des, 'jogos': 1, 'ate_fim_janela': des == 'camisa10',
                             'ok': {'efeitos': [{'k': kk, 'delta': 5, 'rodadas': 3, 'motivo': f'ganhou o direito de {NOMES[des]}'}] + ciume,
                                    'noticia': f'{j["nome"]} agora vai {NOMES[des]}.' + (f' {dono["nome"]} não gostou.' if dono else '')},
                             'quebra': {'efeitos': [{'k': kk, 'delta': -8, 'rodadas': 3, 'motivo': f'prometeram que ele ia {NOMES[des]} e nada mudou'}],
                                        'noticia': f'{j["nome"]} ouviu um "sim" e nada mudou. Ele está furioso com o técnico.'}},
             'eco': (f'{j["nome"]} ganha moral com o técnico', f'O técnico atendeu: ele vai {NOMES[des]}.')},
            {'id': '2', 'texto': f'Manter {dono["nome"] if dono else "como está"}: ele precisa merecer',
             'efeitos': [{'k': kk, 'delta': (-5 if 'vaidoso' in pf['tracos'] else -3) if justo else -2, 'rodadas': 3 if justo else 2,
                          'motivo': f'o técnico negou o pedido para {NOMES[des]}'}] +
                        ([{'k': kd, 'delta': 2, 'rodadas': 2, 'motivo': 'o técnico manteve a confiança nele'}] if dono else []) +
                        ([] if justo else [{'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'o técnico manteve o critério de mérito'}]),
             'eco': (f'Técnico nega pedido de {j["nome"]}', 'Nos bastidores, o jogador não escondeu a irritação.')},
            {'id': '3', 'texto': 'Vamos conversar de novo daqui a um mês',
             'efeitos': [{'k': kk, 'delta': -1, 'rodadas': 1, 'motivo': 'o técnico adiou a conversa sobre o pedido dele'}],
             'eco': (f'Pedido de {j["nome"]} fica para depois', 'O técnico preferiu não decidir agora.')},
        ]}]


def verificar(car, d, s, ti, r, hoje):
    """Confere compromissos do tipo 'posto' contra o save (cobradores, capitão, camisa). Devolve notícias."""
    import compromissos
    ok = estado(d, s, ti)
    todos = [chave(j['k']) for j in r['J']]
    noticias = []
    for c in car.get('compromissos', []):
        if c['status'] != 'aberto' or c['tipo'] != 'posto':
            continue
        k = tuple(int(v) for v in c['k'].split(':'))
        if ok.get(c['posto']) == k:
            c['status'], fim = 'cumprido', c['ok']
        elif c.get('ate_fim_janela'):
            if na_janela(hoje):
                continue                                    # ainda dá tempo de trocar a camisa
            c['status'], fim = 'quebrado', c['quebra']
        elif tuple(hoje) > tuple(c['desde']) and any(tuple(p['data']) > tuple(c['desde']) for p in r['jogos']):
            c['status'], fim = 'quebrado', c['quebra']      # já houve jogo e ele não assumiu o posto
        else:
            continue
        c['fechado'] = list(hoje)
        compromissos.historias(car, fim.get('efeitos', []), todos, hoje, f'Posto|{c["id"]}|{c["status"]}')
        noticias.append(fim['noticia'])
    return noticias
