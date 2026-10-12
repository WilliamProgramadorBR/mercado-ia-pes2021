"""Diretoria / presidente (Central do Técnico, etapa 3a) — NÃO grava nada no save.

Usa a classificação oficial do jogo (liga_save), os resultados (súmulas) e o vestiário para:
  - METAS da temporada (definidas pela força do elenco frente aos rivais da liga);
  - CONFIANÇA da diretoria (0-100), reavaliada a cada mês do calendário do jogo;
  - REUNIÕES: início de temporada (metas), avaliação mensal, emergência (crise) e elogio;
    reuniões com opções são respondidas na Central (diretoria_resposta.txt) e valem na reunião seguinte.
Consequências: confiança + notícias + clima do vestiário (via histórias do vestiário) e, na 3b, o ORÇAMENTO
DE TRANSFERÊNCIAS (gravação testada em 09/10/2026: +R$ 10 mi apareceu no jogo). A diretoria só calcula o ajuste
(dire['ajuste_pendente']); quem grava é o aplicar_vestiario, junto com as setas, com conferência e backup.
Estado em car['diretoria'] (memória do vestiário).
"""
from clube import C as _CLUBE
import datetime as dt
import os
import statistics as st

import dados
import encaixe
import financas_save
import liga_save

HERE = os.path.dirname(os.path.abspath(__file__))
RESPOSTA = os.path.normpath(os.path.join(HERE, '..', '..', 'eFootball PES 2021', 'diretoria_resposta.txt'))
PRESIDENTE = 'O presidente'
BONUS_PROMESSA = 10e6       # R$ ganho/perdido no orçamento quando a promessa de reação é cumprida/quebrada


def _tec():
    return _CLUBE.get('tecnico') or 'O técnico'


def temporada_de(data):
    y, m = data[0], data[1]
    return f'{y}/{(y + 1) % 100:02d}' if m >= 7 else f'{y - 1}/{y % 100:02d}'


COMP_LIGA = {'codigo': None}   # competição da liga do usuário (definida em rodada()); muda o texto das metas


def _meta_por_rank(rank, n):
    c = COMP_LIGA['codigo']
    serie_b = c == 0xA3
    brasil = c in (0x1D, 0xA3)
    if rank == 1:
        return 1, 'Ser campeão da Série B' if serie_b else 'Ser campeão da liga'
    if rank <= 4:
        return 4, ('Subir de divisão (terminar entre os 4 primeiros)' if serie_b else
                   'Terminar entre os 4 primeiros (vaga na Libertadores)' if brasil else
                   'Terminar entre os 4 primeiros (vaga na Champions)')
    if rank <= 6:
        return 6, ('Brigar pelo acesso (terminar entre os 6 primeiros)' if serie_b else
                   'Terminar entre os 6 primeiros (vaga na Libertadores/Sul-Americana)' if brasil else
                   'Terminar entre os 6 primeiros (vaga europeia)')
    if rank <= n // 2:
        return n // 2, 'Terminar na primeira metade da tabela'
    return n - 3, 'Não cair'


def forca_dos_times(d, s, times, snap):
    """Força de cada time da liga: média das 14 melhores notas (foto de memória)."""
    fotos = dados.load_players(snap)
    out = {}
    for t in times:
        notas = sorted((encaixe.rating(fotos[k], fotos[k].pos) for k in s.squad(t) if k in fotos), reverse=True)
        out[t] = st.mean(notas[:14]) if notas else 0
    return out


def _novo_estado(temporada):
    return {'temporada': temporada, 'metas': None, 'confianca': 60, 'avaliacoes': [], 'reuniao': None,
            'ultimo_mes': None, 'promessa': None, 'historico_reunioes': []}


def _reuniao(tipo, titulo, fala, opcoes, hoje):
    return {'id': f'{tipo}|{hoje[0]}-{hoje[1]:02d}-{hoje[2]:02d}', 'tipo': tipo, 'titulo': titulo, 'fala': fala,
            'opcoes': opcoes, 'data': list(hoje), 'criada_em': dt.datetime.now().timestamp()}


def _ler_resposta(reu):
    try:
        if os.path.getmtime(RESPOSTA) > reu.get('criada_em', 0):
            v = open(RESPOSTA, encoding='utf-8').read().strip()[:1]
            return int(v) if v in ('1', '2', '3') else None
    except OSError:
        pass
    return None


def _grupo(car, hid, hoje, peso, rodadas, motivo, J):
    car['historias'][hid] = {'data': list(hoje), 'restam': rodadas, 'peso': peso, 'motivo': motivo,
                             'envolvidos': [f'{j["k"][0]}:{j["k"][1]}' for j in J]}


def rodada(car, d, s, r, snap, hoje):
    """Chamado uma vez por rodada nova (depois da análise do vestiário). Devolve (notícias, resposta_usada)."""
    hoje = tuple(hoje)
    J, ti = r['J'], r['ti']
    temp = temporada_de(hoje)
    dire = car.get('diretoria')
    if not dire or dire.get('temporada') != temp:
        dire = car['diretoria'] = _novo_estado(temp)
    news, usada = [], False
    dire['ajuste_pendente'] = None
    try:
        orc = financas_save.ler(d, ti, referencia=dire.get('orcamento_atual'))['orcamento_transf']
    except RuntimeError:
        orc = None          # sem bloco de finanças confiável: a diretoria não mexe no orçamento
    dire['orcamento_atual'] = orc
    ajuste, motivos_aj = 0, []
    # times da liga principal (a competição com mais jogos do usuário nas súmulas): evita pegar a tabela da copa
    times_liga = None
    try:
        import collections
        meus = [p for p in r.get('todas_partidas') or [] if ti in (p['time1'], p['time2'])][-40:]
        if meus:
            comp = collections.Counter(p['comp'] for p in meus).most_common(1)[0][0]
            COMP_LIGA['codigo'] = comp
            times_liga = {t for p in r['todas_partidas'] if p['comp'] == comp for t in (p['time1'], p['time2'])}
    except Exception:  # noqa: BLE001
        times_liga = None
    tab = liga_save.tabela(d, ti, times=times_liga)
    # pré-temporada: a tabela achada pode ser a FINAL da temporada que acabou (todos com todos os jogos).
    # Ela serve para listar os clubes da liga (metas), mas não para avaliar o trabalho na temporada nova.
    tab_lista = tab
    if tab and hoje[1] in (6, 7, 8) and all(x['v'] + x['e'] + x['d'] == 2 * (len(tab) - 1) for x in tab):
        tab = []
    minha = next((x for x in tab if x['time'] == ti), None)
    dire['tabela'] = [{'pos': x['pos'], 'time': s.name(x['time']), 'pts': x['pts'], 'j': x['v'] + x['e'] + x['d'],
                       'v': x['v'], 'e': x['e'], 'd': x['d'], 'gp': x['gp'], 'gc': x['gc'], 'eu': x['time'] == ti}
                      for x in tab]

    # 1) resposta à reunião anterior
    reu = dire.get('reuniao')
    if reu and reu.get('opcoes'):
        op = _ler_resposta(reu)
        usada = True
        news += _aplicar_resposta(car, dire, reu, op, r, hoje, minha)
        dire['historico_reunioes'].append({**reu, 'resposta': op})
        dire['reuniao'] = None
    elif reu:
        dire['historico_reunioes'].append({**reu, 'resposta': None})
        dire['reuniao'] = None
    dire['historico_reunioes'] = dire['historico_reunioes'][-20:]

    # 2) promessa de reação: cobrada pela TABELA oficial (pontos ganhos desde a promessa)
    pr = dire.get('promessa')
    if pr and minha:
        jn = minha['v'] + minha['e'] + minha['d']
        feitos = jn - pr['j0']
        if feitos >= pr['jogos']:
            pts = minha['pts'] - pr['pts0']
            exigido = round(pr['pontos'] * feitos / pr['jogos'])
            ok = pts >= exigido
            dire['confianca'] = max(0, min(100, dire['confianca'] + (10 if ok else -15)))
            news.append(f'{PRESIDENTE} {"reconhece a reação prometida" if ok else "cobra a reação que não veio"}: '
                        f'{pts} pontos em {feitos} jogos (prometido: {exigido}).')
            dire['promessa'] = None
            ajuste += BONUS_PROMESSA if ok else -BONUS_PROMESSA
            motivos_aj.append('promessa de reação ' + ('cumprida' if ok else 'quebrada'))

    # 3) metas (1ª vez na temporada) -> reunião de início
    if not dire.get('metas') and tab_lista:
        forca = forca_dos_times(d, s, [x['time'] for x in tab_lista], snap)
        rank = sorted(forca, key=lambda t: -forca[t]).index(ti) + 1
        alvo, texto = _meta_por_rank(rank, len(tab_lista))
        dire['metas'] = {'liga_alvo': alvo, 'liga_texto': texto, 'rank_forca': rank, 'moral_minima': 55}
        dire['reuniao'] = _reuniao(
            'inicio', 'Reunião com a diretoria: metas da temporada',
            f'"Temos o {rank}º elenco mais forte da liga. Para esta temporada, a meta é: {texto.lower()}. '
            f'Também quero o vestiário em paz."',
            ['Aceitar as metas', 'Prometer mais do que isso (meta mais alta, confiança sobe agora, cobrança maior)',
             'Pedir paciência (meta mais baixa, a diretoria fica desconfiada)'], hoje)
        news.append(f'Diretoria define as metas da temporada {temp}: {texto.lower()}.')
        dire['ultimo_mes'] = [hoje[0], hoje[1]]
        car['diretoria'] = dire
        return news, usada

    # 4) avaliação mensal (mudou o mês no calendário do jogo)
    if dire.get('metas') and minha and dire.get('ultimo_mes') != [hoje[0], hoje[1]]:
        delta, motivos = _avaliar(dire, minha, r)
        antes = dire['confianca']
        dire['confianca'] = max(0, min(100, antes + delta))
        dire['avaliacoes'].append({'data': list(hoje), 'confianca': dire['confianca'], 'delta': delta,
                                   'posicao': minha['pos'], 'motivos': motivos})
        dire['avaliacoes'] = dire['avaliacoes'][-12:]
        dire['ultimo_mes'] = [hoje[0], hoje[1]]
        c = dire['confianca']
        tom = ('muito satisfeito' if c >= 80 else 'satisfeito' if c >= 60 else 'preocupado' if c >= 40
               else 'irritado')
        news.append(f'{PRESIDENTE} está {tom} com o trabalho de {_tec()} ({minha["pos"]}º lugar, '
                    f'confiança {antes} → {c}).')
        if c < 35 and not dire.get('reuniao'):
            dire['reuniao'] = _reuniao(
                'crise', 'Reunião de emergência com o presidente',
                f'"Estamos em {minha["pos"]}º e a meta era {dire["metas"]["liga_texto"].lower()}. '
                f'Quero explicações e uma reação imediata."',
                ['Pedir confiança no trabalho', 'Prometer reação: 9 pontos nos próximos 4 jogos',
                 'Dizer que o elenco não está correspondendo (o grupo vai saber)'], hoje)
            news.append('Clima tenso: presidente convoca reunião de emergência com o técnico.')
            _grupo(car, f'Diretoria|crise|{hoje}', hoje, -2, 2, 'pressão da diretoria', J)
        elif c >= 85:
            news.append(f'{PRESIDENTE} elogia publicamente o técnico e o elenco.')
            _grupo(car, f'Diretoria|elogio|{hoje}', hoje, +2, 1, 'elogio da diretoria', J)
        # orçamento (3b): prêmio ou corte conforme a confiança do mês
        if orc:
            if c >= 85:
                ajuste += min(0.05 * orc, 30e6); motivos_aj.append('prêmio pela confiança alta')
            elif c < 20:
                ajuste -= min(0.10 * orc, 50e6); motivos_aj.append('corte pela confiança muito baixa')
            elif c < 35:
                ajuste -= min(0.05 * orc, 25e6); motivos_aj.append('corte pela confiança baixa')
    if orc and ajuste:
        ajuste = max(-orc, round(ajuste))
        dire['ajuste_pendente'] = {'delta': ajuste, 'motivo': ', '.join(motivos_aj), 'data': list(hoje),
                                   'antes': orc}
        mi = abs(ajuste) / 1e6
        news.append(f'Diretoria libera R$ {mi:.1f} mi extras para reforços ({", ".join(motivos_aj)}).'
                    if ajuste > 0 else
                    f'Diretoria corta R$ {mi:.1f} mi do orçamento de transferências ({", ".join(motivos_aj)}).')
    car['diretoria'] = dire
    return news, usada


def _avaliar(dire, minha, r):
    m = dire['metas']
    motivos, delta = [], 0
    pos, alvo = minha['pos'], m['liga_alvo']
    if pos <= alvo:
        dv = 4 + min(4, alvo - pos)
        motivos.append(f'dentro da meta ({pos}º, meta: até {alvo}º)')
    else:
        dv = -min(12, 3 * (pos - alvo))
        motivos.append(f'fora da meta ({pos}º, meta: até {alvo}º)')
    delta += dv
    df = round((r['ppg'] - 1.5) * 4)
    delta += df
    motivos.append(f'forma recente: {r["ppg"]:.1f} pontos por jogo')
    medm = st.mean(j['moral'] for j in r['J'])
    rev = sum(1 for j in r['J'] if j['moral'] < 40)
    dvest = round((medm - 60) / 5) - (4 if rev >= 3 else 0)
    delta += dvest
    motivos.append(f'vestiário: moral média {medm:.0f}, {rev} revoltado(s)')
    return max(-15, min(15, delta)), motivos


def _aplicar_resposta(car, dire, reu, op, r, hoje, minha):
    J = r['J']
    news = []
    if op is None:
        dire['confianca'] = max(0, dire['confianca'] - 5)
        return [f'{PRESIDENTE} reclama que o técnico não deu retorno sobre a reunião.']
    if reu['tipo'] == 'inicio':
        m = dire['metas']
        if op == 2:
            m['liga_alvo'] = max(1, {1: 1, 4: 2, 6: 4}.get(m['liga_alvo'], max(1, m['liga_alvo'] - 3)))
            m['liga_texto'] = ('Ser campeão da liga' if m['liga_alvo'] == 1 else
                               f'Terminar entre os {m["liga_alvo"]} primeiros')
            dire['confianca'] = min(100, dire['confianca'] + 8)
            news.append(f'{r.get("tecnico") or "O técnico"} promete mais à diretoria: nova meta é {m["liga_texto"].lower()}.')
        elif op == 3:
            m['liga_alvo'] = min(len(dire.get('tabela') or []) or 20, m['liga_alvo'] + 3)
            m['liga_texto'] = f'Terminar entre os {m["liga_alvo"]} primeiros'
            dire['confianca'] = max(0, dire['confianca'] - 8)
            news.append('Técnico pede paciência à diretoria; a cúpula do clube não gostou.')
        else:
            news.append('Técnico aceita as metas da diretoria para a temporada.')
    elif reu['tipo'] == 'crise':
        if op == 1:
            ganho = 3 if dire['confianca'] >= 25 else -3
            dire['confianca'] = max(0, min(100, dire['confianca'] + ganho))
            news.append(f'{_tec()} pede confiança à diretoria' +
                        (' e ganha um voto de apoio.' if ganho > 0 else ', mas o presidente segue desconfiado.'))
        elif op == 2:
            if minha:
                dire['promessa'] = {'data': list(hoje), 'jogos': 4, 'pontos': 9, 'pts0': minha['pts'],
                                    'j0': minha['v'] + minha['e'] + minha['d']}
            dire['confianca'] = min(100, dire['confianca'] + 4)
            news.append('Técnico promete reação imediata: 9 pontos nos próximos 4 jogos.')
        else:
            dire['confianca'] = min(100, dire['confianca'] + 2)
            _grupo(car, f'Diretoria|culpa|{hoje}', hoje, -5, 2, 'técnico culpou o elenco', J)
            news.append(f'{_tec()} responsabiliza o elenco; jogadores ficam incomodados.')
    return news
