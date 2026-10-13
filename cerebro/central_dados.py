# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Exporta o retrato do vestiário para a Central do Técnico (historico/central.json). SOMENTE LEITURA do jogo.

Chamado no fim de cada reunião (aplicar_vestiario.py) e pelo vestiario.py (relatório avulso).
A Central (central.py) só lê este arquivo + a memória do vestiário; nada aqui grava no save.
"""
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.environ.get('CENTRAL_DADOS')   # testes (sandbox); normal: historico/central_<arquivo da carreira>.json


def arquivo(slot):
    return ARQ or os.path.join(HERE, 'historico', f'central_{slot}.json')
SALARIO_X = 430


def _humor(m):
    return 'Motivado' if m >= 80 else 'Satisfeito' if m >= 60 else 'Insatisfeito' if m >= 40 else 'Revoltado'


def _numeros(e):
    """Resumo das estatísticas nativas (temporada ou mês) para o cartão da Central."""
    if not e or not e.get('minutos'):
        return None
    pc = lambda a, b: round(100 * a / b) if b else None
    return {'jogos': e['jogos'], 'gols': e['gols'], 'assist': e['assist'], 'minutos': e['minutos'],
            'chutes': e['chutes'], 'chutes_gol_pct': pc(e['chutes_gol'], e['chutes']),
            'dribles': e['dribles'], 'dribles_pct': pc(e['dribles_ok'], e['dribles']),
            'passes': e['passes'], 'passes_pct': pc(e['passes_ok'], e['passes']),
            'aereas': e['aereas'], 'aereas_pct': pc(e['aereas_ok'], e['aereas']),
            'desarmes': e['desarmes'], 'interceptacoes': e['interceptacoes']}


def exportar(r, car=None, noticias_rodada=None, setas=None):
    """r = resultado de vestiario.analisar(); car = memória da carreira (aplicar_vestiario); setas = {nome: (base, alvo)}."""
    car = car or {}
    setas = setas or {}
    try:
        import apelidos
        cat = apelidos.catalogo()
    except Exception:  # noqa: BLE001
        cat = {}
    jog = []
    regs = r.get('regs') or {}
    for j in r['J']:
        rj = j['r_jogos_time']
        rec = regs.get(j['k'])
        jog.append({
            # âncora do bloco de carreira na memória (save +72..79 e +84..87): a Central escreve a seta ao vivo
            'ancora': (rec[72:80] + rec[84:88]).hex() if rec else None,
            'nome': j['nome'], 'apelido': cat.get(j.get('apelido') or 0, ''), 'pid': j['k'][1], 'reg': j['k'][0], 'pos': j['pos'], 'idade': j['idade'], 'nota': j['ovr'],
            'status': j['status'], 'funcao': j.get('funcao', ''), 'funcao_prog': j.get('funcao_prog', 0),
            'anos_clube': round(j['anos'], 1), 'moral': j['moral'], 'humor': _humor(j['moral']),
            'torcida': j['torcida'], 'lider': j['lider'], 'capitao': j['capitao'],
            'seta': setas.get(j['nome'], (j.get('seta'), j.get('seta')))[1],
            'seta_jogo': setas.get(j['nome'], (j.get('seta'), j.get('seta')))[0],
            'condicao': j.get('condicao'), 'lesao': j.get('lesao') or 0,
            'perfil': j.get('perfil'),   # condição física do jogo (0-100; barra do Plano de jogo)
            'temporada': {'jogos': j['t_jogos'], 'gols': j['t_gols'], 'assist': j['t_assist'],
                          'nota': round(j['t_nota'], 1)},
            'minutos_recentes': round(j['r_min'] / (90 * rj), 2) if rj else None,
            'salario_rs': j['salario'] * SALARIO_X,
            'contrato_fim': j['contrato'], 'motivos': j['motivos'],
            'numeros': _numeros(j.get('est_temp')), 'numeros_mes': _numeros(j.get('est_mes')),
        })
    midia = car.get('midia') or {}
    dados = {
        'gerado_em': dt.datetime.now().isoformat(timespec='seconds'),
        'carreira': car.get('ck'),
        'slot': (car.get('ck') or 'ML00000000|').split('|')[0],
        'ti': r.get('ti'),
        'tecnico': r.get('tecnico'),
        'laboratorio': bool(car.get('laboratorio')),
        'midia': {k: midia.get(k) for k in ('data', 'capas', 'programa', 'redator')} if midia else None,
        'midia_hist': [{'data': e['data'], 'capas': e['capas']} for e in car.get('midia_hist', [])[:-1]][-6:],
        'coletiva': midia.get('coletiva'),
        'coletivas_hist': car.get('coletivas_hist', [])[-12:],
        # etapa 2: disciplina e calendário
        'casos': car.get('casos', []),
        'compromissos': [c for c in car.get('compromissos', []) if c['status'] == 'aberto'] +
                        [c for c in car.get('compromissos', []) if c['status'] != 'aberto'][-10:],
        'disciplina_hist': car.get('disciplina_hist', [])[-25:],
        'calendario': car.get('calendario'),
        'diretoria_nativa': car.get('diretoria_nativa'),
        'liga': car.get('liga'),
        'mundo': car.get('mundo'),   # números da temporada do mundo (destaques.py)
        'historia': car.get('historia'),   # livro dos recordes do clube (historia.py)
        'data_fifa': car.get('data_fifa'), 'rumores': car.get('rumores') or [], 'celular': car.get('celular_hist') or [], 'vitoriosos': car.get('vitoriosos'), 'serie': car.get('serie') or [], 'torcida': car.get('torcida'),
        'proximo_jogo': car.get('proximo_jogo'),
        'proximos': car.get('proximos') or [],
        'corrida': car.get('corrida'),   # 12/10/2026: disputa do usuário na liga (disputa.py)
        'lesao': car.get('lesao_ultima'), 'lesao_volta': car.get('lesao_volta'),   # departamento médico (lesoes.py)
        'momento': car.get('momento'), 'analise_porques': car.get('analise_porques'), 'analise_data': car.get('analise_data'),
        'movimentos': [{k: v for k, v in m.items() if k != 'pos'} for m in r.get('movimentos') or []],   # saídas/chegadas   # prévias dos próximos 3 jogos (a Central troca pelo pulso)
        'patrocinio': {k: v for k, v in (car.get('patrocinio') or {}).items() if k in ('contrato', 'atratividade', 'historico', 'imagem', 'imagem_hist')},
        'dificuldade': car.get('dificuldade'),
        'time': r['time'], 'data_jogo': r['hoje'], 'pontos_por_jogo': round(r['ppg'], 2),
        'ultimos_jogos': r.get('ultimos', []),
        'capitao': r['capitao']['nome'] if r['capitao'] else None,
        'lideres': [{'nome': j['nome'], 'lider': j['lider']} for j in r['lideres']],
        'jogadores': jog,
        'conflitos': [{'tipo': t, 'texto': txt} for t, txt, _env in r['conflitos']],
        'noticias_rodada': noticias_rodada or [],
        'noticias': car.get('noticias', [])[-30:],
        'pedido': car.get('pedido'),
        'promessas': [p for p in car.get('promessas', []) if p.get('status') == 'aberta'],
        'promessas_fechadas': [p for p in car.get('promessas', []) if p.get('status') != 'aberta'][-10:],
        'diretoria': car.get('diretoria'),
        'insatisfeitos_fora': car.get('insatisfeitos_fora', []),
    }
    try:   # para o pulso ao vivo (pulso.py): nomes dos times e times da liga, sem precisar abrir o save
        nomes = r.get('_nomes_time')
        if nomes:
            import json as _j
            comp = None
            # 12/10/2026: sem amistosos/pré-temporada (o torneio de pré-temporada virava a "liga" do pulso em agosto)
            import midia_liga as _ml
            meus = [p for p in r.get('todas_partidas') or [] if r['ti'] in (p['time1'], p['time2']) and p['comp'] not in _ml.NAO_LIGA]
            if meus:
                import collections as _c
                comp = _c.Counter(p['comp'] for p in meus[-40:]).most_common(1)[0][0]
            aux = {'ti': r['ti'], 'comp_liga': comp, 'nomes': [nomes(i) for i in range(730)]}
            with open(os.path.join(os.path.dirname(arquivo(dados['slot'])), f'pulso_aux_{dados["slot"]}.json'), 'w', encoding='utf-8') as f:
                _j.dump(aux, f, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        pass
    destino = arquivo(dados['slot'])
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    tmp = destino + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.replace(tmp, destino)
    return destino
