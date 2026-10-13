# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Diário de ações da Central do Técnico (event sourcing simples) + efeitos ao vivo.

  - Toda ação feita na Central vira UMA linha em historico/central_acoes.jsonl (só acrescenta; trava 'diario').
  - Se a ação mexe numa alavanca do jogo (hoje: moral -> seta de condição), o efeito é escrito NA HORA na memória
    do jogo (ao_vivo.py) e o resultado também vai para o diário ({'tipo': 'ao_vivo', ...}).
  - A reunião do vestiário (aplicar_vestiario) CONSOME o diário a partir de um cursor guardado no estado da
    carreira (car['acoes_cursor']): efeitos de moral viram "histórias" com duração, polêmicas esquentam/esfriam,
    e o livro das setas fica sabendo o que a Central escreveu.
  - Enquanto a reunião não acontece, a Central mostra a PROJEÇÃO: central.json + eventos ainda não consumidos.

Tipos de evento: coletiva | ao_vivo | ao_vivo_erro
"""
import datetime as dt
import json
import os

from trava import trava

HERE = os.path.dirname(os.path.abspath(__file__))
DIARIO = os.environ.get('CENTRAL_DIARIO') or os.path.join(HERE, 'historico', 'central_acoes.jsonl')
SEM_MEMORIA = os.environ.get('CENTRAL_SEM_MEMORIA') == '1'   # testes: calcula tudo, não escreve no jogo


class Recusada(Exception):
    """Ação inválida (409/400 na Central)."""


def chave(k):
    return f'{k[0]}:{k[1]}'


# ------------------------------------------------------------------ diário
def ler():
    try:
        with open(DIARIO, encoding='utf-8') as f:
            return [json.loads(l) for l in f if l.strip()]
    except OSError:
        return []


def registrar(ev):
    with trava('diario'):
        n = len(ler())
        ev = {'n': n, 'quando': dt.datetime.now().isoformat(timespec='seconds'), **ev}
        os.makedirs(os.path.dirname(DIARIO), exist_ok=True)
        with open(DIARIO, 'a', encoding='utf-8') as f:
            f.write(json.dumps(ev, ensure_ascii=False) + '\n')
    return ev


# ------------------------------------------------------------------ consumo (reunião do vestiário)
def consumir(car, J, hoje):
    """Incorpora no estado da carreira os eventos novos do diário. Devolve os ecos (para a mídia da rodada)."""
    import compromissos
    evs = ler()
    cursor = car.get('acoes_cursor', 0)
    todos = [chave(j['k']) for j in J]
    ecos = []
    falhou = {e['ref'] for e in evs if e['tipo'] == 'ao_vivo_erro'}
    for e in evs[cursor:]:
        if e.get('carreira') != car.get('ck') or e.get('ensaio'):
            continue
        if e['tipo'] == 'treino' and e['n'] in falhou:
            continue   # o treino não chegou ao jogo (carreira não carregada): não vale
        if e['tipo'] in ('coletiva', 'caso', 'treino'):
            compromissos.historias(car, e.get('efeitos', []), todos, hoje, f'{e["tipo"].capitalize()}|{e["n"]}')
            if e.get('eco'):
                ecos.append({'manchete': e['eco'][0], 'fina': e['eco'][1]})
        if e['tipo'] == 'coletiva':
            car.setdefault('coletivas_hist', []).append({
                'data': e.get('data'), 'jornal': e.get('jornal'), 'pergunta': e.get('texto_pergunta'),
                'resposta': e.get('texto_resposta'), 'eco': e['eco'][0]})
            car['coletivas_hist'] = car['coletivas_hist'][-30:]
        elif e['tipo'] == 'caso':
            car['casos'] = [c for c in car.get('casos', []) if c['id'] != e['caso']]
            if e.get('promessa'):   # promessa de renovação pelo celular: conferida no save (decisoes.cobrar_promessas)
                car.setdefault('promessas', []).append({**e['promessa'], 'id': f'{e["caso"]}|{e["n"]}', 'data': e.get('data') or list(hoje),
                                                        'status': 'aberta'})
            if e.get('rumor'):   # "não está à venda": o rumor esfria (rumores.py)
                import rumores
                rumores.esfriar(car, e['rumor'])
            if e.get('caso_tipo') == 'celular':   # histórico das conversas (aba Celular)
                car.setdefault('celular_hist', []).append({'id': e['caso'], 'data': e.get('data') or list(hoje), 'contato': e.get('contato'),
                                                           'mensagens': e.get('mensagens') or [], 'resposta': e.get('texto_resposta')})
                car['celular_hist'] = car['celular_hist'][-25:]
            for c in e.get('compromissos', []):
                car.setdefault('compromissos', []).append({**c, 'desde': e.get('data') or list(hoje), 'status': 'aberto'})
            if e.get('caso_tipo') == 'disciplina':
                for k in e.get('envolvidos', []):
                    car.setdefault('disciplina_hist', []).append({
                        'k': k, 'data': e.get('data') or list(hoje), 'sub': e.get('sub'), 'gravidade': e.get('gravidade'),
                        'decisao': e.get('texto_resposta'), 'titulo': e.get('titulo')})
                car['disciplina_hist'] = car['disciplina_hist'][-60:]
            if e.get('imagem'):
                import crises
                crises.mexer_imagem(car, e['imagem'], e.get('titulo', ''), hoje)
            if e.get('rescindir'):
                pat = car.setdefault('patrocinio', {})
                c = pat.get('contrato')
                if c:
                    pat['historico'] = (pat.get('historico') or []) + [{**c, 'posicao_final': None, 'rescindido': list(hoje)}]
                    pat['contrato'] = None
                    if not any(x['tipo'] == 'ao_vivo_verba' and x.get('ref') == e['n'] for x in evs):
                        pat['verba_pendente'] = -int(c['anual'] * 0.5)   # metade do aporte sai da verba
            if e.get('patrocinio'):
                pat = car.setdefault('patrocinio', {})
                pat['contrato'] = {**e['patrocinio'], 'assinado': e.get('data')}
                if not any(x['tipo'] == 'ao_vivo_verba' and x.get('ref') == e['n'] for x in evs):
                    pat['verba_pendente'] = e['patrocinio']['anual']   # não chegou ao jogo: tenta na reunião
            if e.get('multa') or e.get('orcamento'):
                car.setdefault('multas_pendentes', {})[str(e['n'])] = sum((e.get('multa') or {}).values()) + (e.get('orcamento') or 0)
        elif e['tipo'] == 'treino':
            car.setdefault('calendario', {})['treino'] = {'data': e.get('data'), 'plano': e.get('plano')}
        elif e['tipo'] == 'ao_vivo':
            for k, (antes, depois) in e.get('setas', {}).items():
                m = car['setas'].get(k)
                if m:
                    m['gravada'] = depois
                else:
                    car['setas'][k] = {'original': antes, 'gravada': depois}
        elif e['tipo'] == 'ao_vivo_verba':
            pat = car.setdefault('patrocinio', {})
            pat.pop('verba_pendente', None)
            pat.setdefault('verba_hist', []).append({'data': e.get('data'), 'antes': e['antes'], 'depois': e['depois'],
                                                    'motivo': e.get('motivo')})
        elif e['tipo'] == 'ao_vivo_orcamento':
            car.get('multas_pendentes', {}).pop(str(e['ref']), None)
            dire = car.setdefault('diretoria', {})
            dire.setdefault('orcamento_hist', []).append({'data': e.get('data'), 'antes': e['antes'], 'delta': e['valor'],
                                                         'depois': e['depois'], 'motivo': e.get('motivo', 'multa disciplinar')})
            dire['orcamento_hist'] = dire['orcamento_hist'][-24:]
            dire['orcamento_atual'] = e['depois']
        elif e['tipo'] == 'ao_vivo_erro' and e.get('multa'):
            # não deu para pôr a multa no jogo agora: vai junto com o próximo ajuste de orçamento no save/memória
            car.get('multas_pendentes', {}).pop(str(e['ref']), None)
            car['multas_falhas'] = car.get('multas_falhas', 0) + e['multa']
    car['acoes_cursor'] = len(evs)
    return ecos


# ------------------------------------------------------------------ projeção (Central)
def _humor(m):
    return 'Motivado' if m >= 80 else 'Satisfeito' if m >= 60 else 'Insatisfeito' if m >= 40 else 'Revoltado'


def projetar(dados, estado):
    """central.json + eventos ainda não consumidos pela reunião. Altera `dados` no lugar."""
    ck = dados.get('carreira')
    car = (estado.get('carreiras') or {}).get(ck, {}) if ck else {}
    evs = ler()
    cursor = car.get('acoes_cursor', 0)
    porK = {f'{j["reg"]}:{j["pid"]}': j for j in dados.get('jogadores', [])}
    falhou_t = {e['ref'] for e in evs if e['tipo'] == 'ao_vivo_erro'}
    for e in evs[cursor:]:
        if e.get('carreira') != ck or e.get('ensaio') or (e['tipo'] == 'treino' and e['n'] in falhou_t):
            continue
        for ef in e.get('efeitos', []) if e['tipo'] in ('coletiva', 'caso', 'treino') else []:
            if 'k' not in ef:
                continue
            for j in (porK.values() if ef['k'] == '*' else [porK.get(ef['k'])]):
                if j:
                    j['moral'] = max(0, min(100, j['moral'] + ef['delta']))
                    j['humor'] = _humor(j['moral'])
                    j['motivos'] = j['motivos'] + [ef['motivo']]
        if e['tipo'] == 'ao_vivo':
            for k, (_a, depois) in e.get('setas', {}).items():
                if k in porK:
                    porK[k]['seta'] = depois
            for k, (_a, depois) in e.get('condicoes', {}).items():
                if k in porK:
                    porK[k]['condicao'] = depois
        elif e['tipo'] == 'ao_vivo_orcamento' and dados.get('diretoria'):
            dados['diretoria']['orcamento_atual'] = e['depois']
    col = dados.get('coletiva')
    dados['coletiva_respostas'] = {e['pergunta']: e['opcao'] for e in evs
                                   if e['tipo'] == 'coletiva' and col and e.get('coletiva') == col['id']
                                   and e.get('carreira') == ck}
    ids = {c['id'] for c in dados.get('casos', [])}
    dados['casos_respostas'] = {e['caso']: e['opcao'] for e in evs
                                if e['tipo'] == 'caso' and e.get('caso') in ids and e.get('carreira') == ck}
    falhou = {e['ref'] for e in evs if e['tipo'] == 'ao_vivo_erro'}
    dados['treino_feito'] = next((e['plano'] for e in reversed(evs) if e['tipo'] == 'treino' and e.get('carreira') == ck
                                  and e.get('data') == dados.get('data_jogo') and e['n'] not in falhou), None)
    dados['eventos'] = [e for e in evs if e.get('carreira') == ck][-25:]
    return dados


# ------------------------------------------------------------------ ações
def coletiva(corpo, dados):
    """Resposta a uma pergunta da coletiva. Registra o evento; o efeito ao vivo é feito por efeitos_ao_vivo()."""
    col = dados.get('coletiva')
    if not col or corpo.get('coletiva') != col['id']:
        raise Recusada('essa coletiva já acabou (houve rodada nova)')
    p = next((p for p in col['perguntas'] if p['id'] == corpo.get('pergunta')), None)
    o = next((o for o in (p or {}).get('opcoes', []) if o['id'] == str(corpo.get('opcao'))), None)
    if not p or not o:
        raise Recusada('pergunta ou resposta inválida')
    with trava('coletiva'):
        if any(e['tipo'] == 'coletiva' and e.get('coletiva') == col['id'] and e['pergunta'] == p['id']
               and e.get('carreira') == dados.get('carreira') for e in ler()):
            raise Recusada('essa pergunta já foi respondida')
        return registrar({'tipo': 'coletiva', 'carreira': dados.get('carreira'), 'coletiva': col['id'],
                          'pergunta': p['id'], 'opcao': o['id'], 'efeitos': o['efeitos'], 'eco': o['eco'],
                          'texto_pergunta': p['texto'], 'texto_resposta': o['texto'], 'jornal': p['jornal_nome'],
                          'data': dados.get('data_jogo')})


def caso(corpo, dados):
    """Decisão num caso de disciplina ou de calendário (opções montadas por disciplina.py / calendario.py)."""
    c = next((c for c in dados.get('casos', []) if c['id'] == corpo.get('caso')), None)
    if not c:
        raise Recusada('esse caso não está mais aberto')
    o = next((o for o in c['opcoes'] if o['id'] == str(corpo.get('opcao'))), None)
    if not o:
        raise Recusada('opção inválida')
    comps = list(o.get('compromissos') or []) + list(o.get('compromisso_lista') or [])
    if o.get('compromisso'):
        comps.append({**o['compromisso'], 'k': c['envolvidos'][0], 'nome': c['nomes'][0]})
    with trava('casos'):
        evs = ler()
        if any(e['tipo'] == 'caso' and e.get('caso') == c['id'] and e.get('carreira') == dados.get('carreira') for e in evs):
            raise Recusada('esse caso já foi decidido')
        comps = [{**x, 'id': f'{len(evs)}|{i}', 'origem': c['id']} for i, x in enumerate(comps)]
        return registrar({'tipo': 'caso', 'carreira': dados.get('carreira'), 'caso': c['id'], 'caso_tipo': c['tipo'],
                          'sub': c.get('sub'), 'gravidade': c.get('gravidade'), 'envolvidos': c['envolvidos'],
                          'titulo': c['titulo'], 'opcao': o['id'], 'texto_resposta': o['texto'],
                          'efeitos': o.get('efeitos', []), 'multa': o.get('multa'), 'carreira_mud': o.get('carreira'),
                          'orcamento': o.get('orcamento'), 'patrocinio': o.get('patrocinio'),
                          'imagem': o.get('imagem'), 'rescindir': o.get('rescindir'),
                          'compromissos': comps, 'eco': o.get('eco'), 'data': dados.get('data_jogo'), 'rumor': o.get('rumor'), 'promessa': o.get('promessa'),
                          'contato': c.get('contato'), 'mensagens': c.get('mensagens')})


PLANOS = {
    'leve': {'nome': 'Regenerativo', 'cond': 12,
             'eco': ('Semana de recuperação no CT', 'Comissão técnica prioriza a parte física.')},
    'normal': {'nome': 'Normal', 'cond': 0, 'eco': None},
    'intenso': {'nome': 'Intenso', 'cond': -8,
                'eco': ('Treinos em alta intensidade', 'O técnico aperta o elenco antes do próximo jogo.')},
}


def treino(corpo, dados):
    """Plano de treino da semana (1 por rodada): mexe em condição física e seta no jogo, ao vivo.
    leve: condição +12 para todos (+1 de moral no grupo); intenso: condição -8, seta +1 para quem está com seta
    baixa (<= 2), moral >= 55 e até 30 anos; o grupo -1 e os veteranos (31+) -2 de moral."""
    plano = corpo.get('plano')
    if plano not in PLANOS:
        raise Recusada('plano inválido')
    with trava('treino'):
        evs = ler()
        falhou = {e['ref'] for e in evs if e['tipo'] == 'ao_vivo_erro'}   # plano que não chegou ao jogo pode ser refeito
        if any(e['tipo'] == 'treino' and e.get('data') == dados.get('data_jogo') and e.get('carreira') == dados.get('carreira')
               and e['n'] not in falhou for e in evs):
            raise Recusada('o plano desta semana já foi definido')
        P = PLANOS[plano]
        mud, efeitos = {}, []
        for j in dados.get('jogadores', []):
            kk = f'{j["reg"]}:{j["pid"]}'
            m = {}
            if P['cond']:
                m['cond_delta'] = P['cond']
            if plano == 'intenso' and j.get('seta') is not None and j['seta'] <= 2 and j['moral'] >= 55 and j['idade'] <= 30:
                m['seta'] = j['seta'] + 1
            if m:
                mud[kk] = m
            if plano == 'intenso' and j['idade'] >= 31:
                efeitos.append({'k': kk, 'delta': -2, 'rodadas': 1, 'motivo': 'veterano sentiu a semana de treinos puxados'})
        if plano == 'leve':
            efeitos.append({'k': '*', 'delta': 1, 'rodadas': 1, 'motivo': 'semana de treinos leves'})
        elif plano == 'intenso':
            efeitos.append({'k': '*', 'delta': -1, 'rodadas': 1, 'motivo': 'semana de treinos puxados'})
        return registrar({'tipo': 'treino', 'carreira': dados.get('carreira'), 'plano': plano, 'texto_resposta': P['nome'],
                          'efeitos': efeitos, 'carreira_mud': mud, 'eco': P['eco'], 'data': dados.get('data_jogo')})


ACOES = {'coletiva': coletiva, 'caso': caso, 'treino': treino}


def _rec(ancora_hex):
    """Registro 'de mentira' com só os bytes que o ao_vivo usa de âncora (save +72..79 e +84..87)."""
    a = bytes.fromhex(ancora_hex)
    r = bytearray(156)
    r[72:80], r[84:88] = a[:8], a[8:12]
    return bytes(r)


def efeitos_ao_vivo(ev, dados_projetados, log=print):
    """Depois de um evento, escreve no jogo AGORA o que mudou:
      - seta de quem teve a moral mexida e, por isso, muda de seta;
      - condição/seta pedidas diretamente (treino, recuperação) -> ev['carreira_mud'];
      - multa -> orçamento de transferências."""
    import vestiario as V
    import ao_vivo
    porK = {f'{j["reg"]}:{j["pid"]}': j for j in dados_projetados.get('jogadores', [])}
    nomes = {kk: j['nome'] for kk, j in porK.items()}
    alvos = set()
    for ef in ev.get('efeitos', []):
        if 'k' in ef:
            alvos |= set(porK) if ef['k'] == '*' else {ef['k']}
    mud, recs = {}, {}
    for kk in alvos:
        j = porK.get(kk)
        if not j or j.get('seta') is None or j.get('seta_jogo') is None or not j.get('ancora'):
            continue
        alvo = V.seta_alvo(j['seta_jogo'], j['moral'])
        if alvo != j['seta']:
            k = (j['reg'], j['pid'])
            mud[k], recs[k] = {'seta': alvo}, _rec(j['ancora'])
    for kk, m in (ev.get('carreira_mud') or {}).items():
        j = porK.get(kk)
        if not j or not j.get('ancora'):
            continue
        k = (j['reg'], j['pid'])
        mud.setdefault(k, {}).update(m)
        recs[k] = _rec(j['ancora'])
    out = None
    if mud:
        try:
            feito = ao_vivo.ajustar_carreira(mud, recs, escrever_de_verdade=not SEM_MEMORIA, log=log)
            if not feito and ev.get('carreira_mud'):
                raise RuntimeError('jogadores não encontrados na memória (a carreira está carregada no jogo?)')
            if feito:
                out = registrar({'tipo': 'ao_vivo', 'carreira': ev.get('carreira'), 'ref': ev['n'], 'ensaio': SEM_MEMORIA,
                                 'setas': {chave(k): list(v['seta']) for k, v in feito.items() if 'seta' in v},
                                 'condicoes': {chave(k): list(v['cond']) for k, v in feito.items() if 'cond' in v},
                                 'nomes': {chave(k): nomes.get(chave(k), '') for k in feito}})
        except Exception as e:  # noqa: BLE001 - jogo fechado, etc.: o efeito na moral vale na próxima reunião
            out = registrar({'tipo': 'ao_vivo_erro', 'carreira': ev.get('carreira'), 'ref': ev['n'], 'erro': str(e)})
    if ev.get('patrocinio'):
        ref = (dados_projetados.get('diretoria') or {}).get('orcamento_atual')
        try:
            if not ref:
                raise RuntimeError('orçamento atual desconhecido')
            antes, depois = ao_vivo.verba_salarios(ev['patrocinio']['anual'], ref, escrever_de_verdade=not SEM_MEMORIA, log=log)
            out = registrar({'tipo': 'ao_vivo_verba', 'carreira': ev.get('carreira'), 'ref': ev['n'], 'ensaio': SEM_MEMORIA,
                             'antes': antes, 'depois': depois, 'data': ev.get('data'),
                             'motivo': f'patrocínio {ev["patrocinio"]["marca"]}'})
        except Exception as e:  # noqa: BLE001
            out = registrar({'tipo': 'ao_vivo_erro', 'carreira': ev.get('carreira'), 'ref': ev['n'],
                             'erro': f'patrocínio não entrou na verba agora ({e}); entra na próxima reunião'})
    if ev.get('rescindir'):
        c = (dados_projetados.get('patrocinio') or {}).get('contrato')
        ref = (dados_projetados.get('diretoria') or {}).get('orcamento_atual')
        if c and ref:
            try:
                antes, depois = ao_vivo.verba_salarios(-int(c['anual'] * 0.5), ref, escrever_de_verdade=not SEM_MEMORIA, log=log)
                out = registrar({'tipo': 'ao_vivo_verba', 'carreira': ev.get('carreira'), 'ref': ev['n'], 'ensaio': SEM_MEMORIA,
                                 'antes': antes, 'depois': depois, 'data': ev.get('data'),
                                 'motivo': f'rescisão da {c["marca"]}'})
            except Exception as e:  # noqa: BLE001
                out = registrar({'tipo': 'ao_vivo_erro', 'carreira': ev.get('carreira'), 'ref': ev['n'],
                                 'erro': f'rescisão não saiu da verba agora ({e}); sai na próxima reunião'})
    total = sum((ev.get('multa') or {}).values()) + (ev.get('orcamento') or 0)
    if total:
        ref = (dados_projetados.get('diretoria') or {}).get('orcamento_atual')
        try:
            if not ref:
                raise RuntimeError('orçamento atual desconhecido')
            antes, depois = ao_vivo.orcamento(None, ref, escrever_de_verdade=not SEM_MEMORIA, log=log, delta_reais=total)
            out = registrar({'tipo': 'ao_vivo_orcamento', 'carreira': ev.get('carreira'), 'ref': ev['n'],
                             'ensaio': SEM_MEMORIA, 'antes': antes, 'depois': depois, 'valor': total,
                             'data': ev.get('data'), 'motivo': ('multa: ' if total > 0 else 'custo: ') + ev.get('titulo', '')})
        except Exception as e:  # noqa: BLE001
            out = registrar({'tipo': 'ao_vivo_erro', 'carreira': ev.get('carreira'), 'ref': ev['n'],
                             'erro': f'multa não entrou no orçamento agora ({e}); entra no próximo ajuste', 'multa': total})
    return out
