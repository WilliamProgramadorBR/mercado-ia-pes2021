# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""AUTÓPSIA DE CADA JOGO DO USUÁRIO (22/10/2026): por que o resultado que os modelos esperavam não aconteceu.

Pedido do usuário: "ela precisa colher os dados e entender por que eu perdi" (0 x 2 para o Watford quando os dois
modelos previam 2 x 0). Para cada jogo já pontuado no duelo, junta:
  números do jogo   diferença entre as fotos do Desempenho do clube antes e depois (desempenho_save): chutes e chutes
                    no gol dos DOIS lados, posse, passes, cruzamentos, desarmes, quando e como saíram os gols;
  súmula            notas dos titulares dos dois times, o melhor e o pior do nosso lado (partidas_save);
  placar merecido   chutes no gol x taxa de conversão (gols por chute no gol dos jogos anteriores, os dois lados);
  veredito          erro total = real - previsto, separado em AZAR (real - merecido: finalização, goleiro) e LEITURA
                    (merecido - previsto: o que o modelo leu errado do jogo); e se a rede PESOU A MÃO (ficou mais longe
                    do merecido que a estatística, ou seja, a correção dela piorou o palpite).
Guardado em historico/autopsias.json (uma por jogo, nunca recalculada depois de completa) — o Painel e a Central
mostram, e o placar merecido entra no treino da rede quando o teste andando no tempo aprova (rede_v3).
Só partidas JOGADAS têm números (o jogo não registra as simuladas); sem números, a autópsia fica só com a súmula.
"""
import json
import os
import time

import desempenho_save as DS

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(HERE, 'historico', 'autopsias.json')
TAXA_PADRAO = 0.40   # gols por chute no gol quando ainda há poucos jogos com números


def _ler():
    try:
        with open(ARQ, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _gravar(a):
    os.makedirs(os.path.dirname(ARQ), exist_ok=True)
    tmp = ARQ + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(a, f, ensure_ascii=False)
    for _ in range(40):
        try:
            os.replace(tmp, ARQ)
            return
        except PermissionError:
            time.sleep(0.05)


def chave(data):
    return '%04d-%02d-%02d' % tuple(data[:3])


def numeros_por_jogo(time_nome, h=None):
    """{(a, m, d): campos do jogo} para os trechos de foto com EXATAMENTE um jogo (data = a do jogo)."""
    h = DS._ler_hist() if h is None else h
    fs = [f for f in h.get(time_nome) or [] if f['data']]
    out = {}
    for a, b in zip(fs, fs[1:]):
        dif = DS._diferenca(b, a)
        if dif and max((x['jogos'] for x in dif[1].values()), default=0) == 1:
            c = DS.campos(dif[0])
            c['posse'] = round(c['posse_soma'] / 100, 1)
            out[tuple(b['data'][:3])] = c
    return out


def taxa_conversao(num, gols_por_data, ate):
    """Gols por chute no gol (os dois lados) nos jogos com números ANTES de `ate`."""
    g = s = 0
    for d, c in num.items():
        if d < tuple(ate[:3]) and d in gols_por_data:
            g += sum(gols_por_data[d])
            s += c['chutes_gol'] + c['chutes_sofridos_gol']
    return round(g / s, 3) if s >= 20 else TAXA_PADRAO


def _sumula(d, ti, data, nomes):
    import partidas_save as ps
    for p in ps.todas(d, *ps.FAIXA):
        if tuple(p['data'][:3]) == tuple(data[:3]) and ti in (p['time1'], p['time2']):
            nos, eles = (p['linhas1'], p['linhas2']) if p['time1'] == ti else (p['linhas2'], p['linhas1'])
            tit = lambda ls: [x for x in ls if x.get('titular') and x.get('nota')]
            media = lambda ls: round(sum(x['nota'] for x in tit(ls)) / len(tit(ls)), 2) if tit(ls) else None
            ln = [dict(x, nome=nomes.get((x['reg'], x['pid']))) for x in nos if x.get('minutos') and x.get('nota')]
            ln.sort(key=lambda x: -x['nota'])
            return {'nota_nos': media(nos), 'nota_eles': media(eles),
                    'melhor': {k: ln[0][k] for k in ('nome', 'nota', 'gols', 'assist')} if ln else None,
                    'pior': {k: ln[-1][k] for k in ('nome', 'nota', 'gols', 'assist')} if ln else None,
                    'autores': [{'nome': x['nome'], 'gols': x['gols']} for x in ln if x.get('gols')]}
    return None


def montar(h_duelo, num, taxa, sumula=None, media_sofridos_gol=None):
    """Autópsia de um jogo pontuado no duelo (h_duelo = entrada do histórico da arena "usuario")."""
    real = h_duelo['real']
    le, lr = h_duelo.get('lam_est') or [0, 0], h_duelo.get('lam_rede') or [0, 0]
    prev_est, prev_rede = le[0] - le[1], lr[0] - lr[1]
    a = {'data': h_duelo['data'], 'adv': h_duelo.get('adv'), 'real': real,
         'previsto': {'estatistica': [round(x, 2) for x in le], 'rede': [round(x, 2) for x in lr],
                      'palpite_est': h_duelo.get('est'), 'palpite_rede': h_duelo.get('rede')},
         'plano_rival': h_duelo.get('plano'), 'decidiu': h_duelo.get('decidiu'), 'sumula': sumula}
    c = num.get(tuple(h_duelo['data'][:3]))
    if c:
        mer = [round(taxa * c['chutes_gol'], 2), round(taxa * c['chutes_sofridos_gol'], 2)]
        s_real, s_mer = real[0] - real[1], mer[0] - mer[1]
        a['numeros'] = {k: c[k] for k in ('chutes', 'chutes_gol', 'chutes_sofridos', 'chutes_sofridos_gol', 'posse',
                                          'passes', 'passes_ok', 'cruzamentos', 'desarmes', 'interceptacoes', 'defesas')}
        a['numeros']['gols_periodo'] = dict(zip(DS.PERIODOS, c['gols_periodo']))
        a['numeros']['sofridos_periodo'] = dict(zip(DS.PERIODOS, c['sofridos_periodo']))
        a['numeros']['tipos_feitos'] = {k: v for k, v in zip(DS.TIPOS, c['tipos_feitos']) if v}
        a['numeros']['tipos_sofridos'] = {k: v for k, v in zip(DS.TIPOS, c['tipos_sofridos']) if v}
        a['merecido'] = mer
        a['taxa'] = taxa
        a['veredito'] = {'erro_est': round(s_real - prev_est, 2), 'erro_rede': round(s_real - prev_rede, 2),
                         'azar': round(s_real - s_mer, 2),               # finalização / goleiro, dos dois lados
                         'leitura_est': round(s_mer - prev_est, 2), 'leitura_rede': round(s_mer - prev_rede, 2),
                         'rede_pesou_a_mao': abs(s_mer - prev_rede) > abs(s_mer - prev_est) + 0.25,
                         'rede_ajudou': abs(s_mer - prev_rede) + 0.25 < abs(s_mer - prev_est)}
        if media_sofridos_gol:
            a['veredito']['chances_do_rival_x_media'] = round(c['chutes_sofridos_gol'] / media_sofridos_gol, 2)
    a['texto'] = texto(a)
    return a


def _n(x):
    return f'{x:.1f}'.replace('.', ',')


def texto(a):
    """Frases curtas para o Painel e a Central."""
    out = []
    pe, pr = a['previsto']['palpite_est'], a['previsto']['palpite_rede']
    r = a['real']
    if pe and pr:
        out.append(f'Previsto: estatística {pe[0]} x {pe[1]}, rede {pr[0]} x {pr[1]}. Deu {r[0]} x {r[1]}.')
    n, v = a.get('numeros'), a.get('veredito')
    if n:
        out.append(f'Chutes: {n["chutes"]} ({n["chutes_gol"]} no gol) contra {n["chutes_sofridos"]} ({n["chutes_sofridos_gol"]} no gol); '
                   f'posse {n["posse"]:.0f}%.')
        m = a['merecido']
        out.append(f'Placar merecido pelas chances: {_n(m[0])} x {_n(m[1])}.')
        if abs(v['azar']) >= 1.0:
            out.append(('Faltou pontaria: ' if v['azar'] < 0 else 'Sobrou eficiência: ')
                       + f'o resultado ficou {_n(abs(v["azar"]))} gol(s) de saldo {"abaixo" if v["azar"] < 0 else "acima"} do que as chances davam.')
        lr = v['leitura_rede']
        if abs(lr) >= 1.0:
            out.append(f'A leitura do jogo errou: pelas chances, o saldo foi {_n(abs(lr))} gol(s) '
                       f'{"melhor" if lr > 0 else "pior"} para você do que a rede esperava.')
        if v.get('chances_do_rival_x_media') and v['chances_do_rival_x_media'] >= 1.3:
            out.append(f'O plano do rival funcionou: ele acertou {n["chutes_sofridos_gol"]} chutes no gol, '
                       f'{_n(v["chances_do_rival_x_media"])}x a média que você costuma sofrer.')
        if n.get('tipos_sofridos'):
            out.append('Gols sofridos: ' + ', '.join(f'{q} de {t}' for t, q in n['tipos_sofridos'].items()) + '.')
        if v['rede_pesou_a_mao']:
            out.append('A rede pesou a mão: a correção dela afastou o palpite do que o jogo mostrou.')
        elif v['rede_ajudou']:
            out.append('A correção da rede ajudou: ficou mais perto do que o jogo mostrou que a estatística.')
    s = a.get('sumula')
    if s and s.get('nota_nos'):
        out.append(f'Notas dos titulares: {_n(s["nota_nos"])} x {_n(s["nota_eles"])}'
                   + (f'; melhor do time: {s["melhor"]["nome"]} ({_n(s["melhor"]["nota"])}), pior: {s["pior"]["nome"]} ({_n(s["pior"]["nota"])})'
                      if s.get('melhor') and s['melhor'].get('nome') else '') + '.')
    return out


def atualizar(d=None, time_nome=None, ti=None, nomes=None, log=print):
    """Faz a autópsia dos jogos pontuados que ainda não têm (ou só têm parcial). Idempotente: chamado a cada reunião."""
    import duelo
    feitas = _ler()
    hist = duelo.estado()['arenas']['usuario']['hist']
    if d is not None and (time_nome is None or ti is None):
        import carreira
        ti, time_nome = carreira.time_do_usuario(d)
    num = numeros_por_jogo(time_nome) if time_nome else {}
    gols = {tuple(x['data'][:3]): x['real'] for x in hist if x.get('real')}
    novas = 0
    for x in hist[-40:]:
        k = chave(x['data'])
        ja = feitas.get(k)
        if ja and ja.get('numeros') and ja.get('sumula'):
            continue
        ant = [c['chutes_sofridos_gol'] for dd, c in num.items() if dd < tuple(x['data'][:3])]
        sumula = (ja or {}).get('sumula') or (_sumula(d, ti, x['data'], nomes or {}) if d is not None else None)
        a = montar(x, num, taxa_conversao(num, gols, x['data']), sumula, sum(ant) / len(ant) if len(ant) >= 5 else None)
        if ja and not a.get('numeros') and ja.get('numeros'):
            continue
        feitas[k] = a
        novas += 1
    if novas:
        _gravar(feitas)
        log(f'autópsia: {novas} jogo(s) analisado(s)')
    try:
        levar_ao_treino(feitas, time_nome)
    except Exception as e:  # noqa: BLE001
        log(f'autópsia: merecido não levado ao treino: {e}')
    return feitas


def levar_ao_treino(feitas=None, time_nome=None):
    """Grava o placar merecido de cada jogo na amostra de treino da rede v3 com a mesma data (o reajuste automático
    decide se treina com ele). Jogos do treino sem autópsia (os do pré-treino) recebem o merecido direto dos números do
    jogo, com a taxa de conversão só dos jogos ANTERIORES. Devolve quantas amostras receberam."""
    import rede_v3
    feitas = _ler() if feitas is None else feitas
    buf = rede_v3.ler_buffer()
    num = numeros_por_jogo(time_nome) if time_nome else {}
    gols = {tuple(a['data'][:3]): [int(a['y'][0]), int(a['y'][1])] for a in buf if a.get('data')}
    n = 0
    for a in buf:
        if not a.get('data'):
            continue
        x = feitas.get(chave(a['data']))
        mer = x.get('merecido') if x else None
        c = num.get(tuple(a['data'][:3]))
        if not mer and c:
            t = taxa_conversao(num, gols, a['data'])
            mer = [round(t * c['chutes_gol'], 2), round(t * c['chutes_sofridos_gol'], 2)]
        if mer and a.get('merecido') != mer:
            a['merecido'] = mer
            n += 1
    if n:
        rede_v3.gravar_buffer(buf)
    return n


def autoavaliacao(n=20):
    """O JULGAMENTO da rede sobre ela mesma nos últimos n jogos com números: quantas vezes a correção dela ajudou ou
    pesou a mão em relação à estatística, e quanto do erro foi leitura do jogo x azar (finalização, goleiro).
    22/10/2026: um fator de confiança único aprendido com esse histórico foi testado andando no tempo e PERDEU (ficava
    em 0-30% e tirava pontos do bolão) — por isso o julgamento é diagnóstico, e o que muda o treino é o placar merecido
    (escolhido pelo reajuste automático)."""
    xs = [x for x in recentes(200) if x.get('veredito')][:n]
    if not xs:
        return None
    v = [x['veredito'] for x in xs]
    med = lambda k: round(sum(abs(y[k]) for y in v) / len(v), 2)
    return {'jogos': len(v), 'ajudou': sum(1 for y in v if y['rede_ajudou']), 'pesou_a_mao': sum(1 for y in v if y['rede_pesou_a_mao']),
            'leitura_rede': med('leitura_rede'), 'leitura_est': med('leitura_est'), 'azar': med('azar'),
            'erro_rede': med('erro_rede'), 'erro_est': med('erro_est')}


def refazer_textos():
    a = _ler()
    for x in a.values():
        x['texto'] = texto(x)
    _gravar(a)
    return len(a)


def recentes(n=10):
    a = _ler()
    return [a[k] for k in sorted(a)[-n:]][::-1]
