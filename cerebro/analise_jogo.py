# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ANÁLISE PÓS-JOGO COM O PORQUÊ (12/10/2026).

Pedido do usuário: jornalismo que entende o que aconteceu — como o nosso time se comportou, como a máquina se
comportou — e explica o porquê da vitória ou da derrota, com linguagens diferentes (referências dele: ESPN Brasil,
SporTV, CazéTV). Três veículos fictícios, cada um com a sua voz (o redator de IA reescreve no estilo de cada um):
  Mesa Tática         análise de canal de esportes: bloco, linhas, transição, números; frio e técnico;
  Plantão do Esporte  TV aberta: narrativa equilibrada, contexto da tabela e da torcida;
  Resenha Raiz        canal jovem de internet: gíria leve, humor, zoeira — mas com a explicação certa.

O porquê vem de fatos que a Central sabe: o plano que a IA adversária usou (bloco baixo, pressão, marcação individual
em quem, flanco atacado), as notas e os gols dos dois lados, quem desfalcou (lesão), o desgaste e a corrida na liga.
Uma vez por jogo do usuário (chave pelo número da partida).
"""
import json
import os

import clube

HERE = os.path.dirname(os.path.abspath(__file__))
ORD = {2: 'segunda', 3: 'terceira', 4: 'quarta', 5: 'quinta', 6: 'sexta'}


def _gols(n):
    return f'{n} gol' if n == 1 else f'{n} gols'

VEICULOS = {
    'mesa_tatica': ('Mesa Tática', 'programa de análise tática de canal de esportes (estilo ESPN): frio, técnico, explica o '
                    'porquê com bloco, linhas, transição, compactação, marcação e números; nada de torcida'),
    'plantao': ('Plantão do Esporte', 'noticiário esportivo de TV aberta (estilo SporTV): narrativa jornalística equilibrada, '
                'contexto da tabela, da torcida e do momento, frases de efeito moderadas'),
    'resenha': ('Resenha Raiz', 'canal jovem de futebol na internet (estilo CazéTV): linguagem solta, gírias leves, humor e '
                'zoeira com o resultado, emojis com moderação, mas explicando direito por que o jogo foi assim'),
}


def _ia_do_jogo(adv, data):
    try:
        reg = json.load(open(os.path.join(HERE, 'historico', 'ia_adversaria.json'), encoding='utf-8')).get('registro') or []
    except (OSError, ValueError):
        return None
    return next((x for x in reversed(reg) if (x.get('adversario') or '').upper() == adv.upper()
                 and list(x.get('data') or []) == list(data)), None)


def porques(r, car, jogo, P):
    """Lista de razões (peso, chave, frase factual) para o resultado do último jogo."""
    ti = r['ti']
    nos_l, adv_l = (jogo['linhas1'], jogo['linhas2']) if jogo['time1'] == ti else (jogo['linhas2'], jogo['linhas1'])
    gp, gc = (jogo['gols1'], jogo['gols2']) if jogo['time1'] == ti else (jogo['gols2'], jogo['gols1'])
    adv_ti = jogo['time2'] if jogo['time1'] == ti else jogo['time1']
    adv = clube.nome_time(r['_nomes_time'](adv_ti))
    nome = lambda x: (P.get((x['reg'], x['pid'])).name if P and P.get((x['reg'], x['pid'])) else
                      next((j['nome'] for j in r['J'] if tuple(j['k']) == (x['reg'], x['pid'])), '?'))
    jogou = [x for x in nos_l if x['minutos'] > 0]
    res = 'V' if gp > gc else 'E' if gp == gc else 'D'
    out = []
    reg = _ia_do_jogo(r['_nomes_time'](adv_ti).strip(), jogo['data'])
    pl = (reg or {}).get('plano') or {}
    instr = (reg or {}).get('instrucoes') or []
    marcado = next((i[len('Marcação ('):-1] for i in instr if i.startswith('Marcação (')), None)
    if marcado:
        xm = next((x for x in jogou if nome(x) == marcado), None)
        if xm and xm['nota'] and xm['nota'] < 6.5 and xm['gols'] == 0:
            out.append((9, 'marcacao', f'A marcação individual do {adv} anulou {marcado} (nota {xm["nota"]:.1f}, sem gol).'))
        elif xm and (xm['gols'] or (xm['nota'] or 0) >= 7.5):
            out.append((7, 'marcacao_falhou', f'O {adv} colou um marcador em {marcado}, e não adiantou: ele terminou com nota {xm["nota"]:.1f}'
                                              + (f' e {_gols(xm["gols"])}.' if xm['gols'] else '.')))
    if pl:
        if pl.get('linha_defensiva', 5) <= 4 and gp <= 1:
            out.append((8, 'ferrolho', f'O {adv} se fechou com a linha baixa (linha {pl["linha_defensiva"]}, compactação {pl["compactacao"]}) e tirou os espaços: {"nenhum gol nosso" if gp == 0 else "só um gol nosso"}.'))
        if pl.get('linha_defensiva', 5) >= 7 and pl.get('pressao') == 0 and gc >= 2:
            out.append((8, 'pressao', f'A pressão alta do {adv} desde a saída de bola rendeu: {gc} gols marcados.'))
        if pl.get('linha_defensiva', 5) >= 7 and gp >= 3:
            out.append((7, 'costas', f'O {adv} subiu a linha e pagou: a velocidade do nosso ataque achou as costas da defesa ({gp} gols).'))
        if pl.get('estilo_ofensivo') == 0 and gc >= 1 and res != 'V':
            out.append((6, 'contra_ataque', f'O plano do {adv} era sair rápido no contra-ataque, e foi assim que machucou.'))
    if any('lado' in m and 'fraco' in m for m in ((reg or {}).get('motivo') or '').split(' | ')) and gc >= 1:
        lado = next((m for m in reg['motivo'].split(' | ') if 'ponto fraco' in m), '')
        out.append((7, 'flanco', f'O {adv} foi para cima pelo lado {lado.split("lado ")[1].split(" ")[0] if "lado " in lado else "mais frágil"}: ' + lado.split(': ', 1)[-1] + '.'))
    les = car.get('lesao_ultima')
    if les and not any(nome(x) == les['nome'] for x in jogou):
        out.append((8 if les.get('rank', 9) <= 3 else 5, 'desfalque', f'Sem {les["nome"]} ({les["parte_gols"]}% dos gols do time), o ataque perdeu a principal referência.'))
    if jogou:
        melhor = max(jogou, key=lambda x: (x['nota'] or 0) + x['gols'])
        pior = min(jogou, key=lambda x: (x['nota'] or 9))
        out.append((5, 'destaque', f'O melhor do nosso lado foi {nome(melhor)} (nota {melhor["nota"]:.1f}'
                                     + (f', {_gols(melhor["gols"])}' if melhor['gols'] else '') + ').'))
        if pior['nota'] and pior['nota'] < 6.0:
            out.append((6 if res == 'D' else 3, 'pior', f'{nome(pior)} teve uma noite para esquecer (nota {pior["nota"]:.1f}).'))
    arts = [x for x in adv_l if x['gols']]
    if arts:
        quem = [nome(x) + (f' ({x["gols"]} gols)' if x['gols'] > 1 else '') for x in arts]
        lista = quem[0] if len(quem) == 1 else ', '.join(quem[:-1]) + ' e ' + quem[-1]
        out.append((6, 'algoz', f'Do outro lado, {lista} {"decidiu" if len(quem) == 1 else "marcaram"} para o {adv}.'))
    cans = [j for j in r['J'] if j.get('condicao') is not None and j['condicao'] < 70 and any(tuple(j['k']) == (x['reg'], x['pid']) for x in jogou)]
    if len(cans) >= 3:
        out.append((6, 'cansaco', f'O desgaste pesou: {", ".join(j["nome"] for j in cans[:3])} saíram com a condição abaixo de 70.'))
    mo = car.get('momento') or {}
    if mo.get('frases') and (mo.get('clima') in ('crise', 'alerta', 'embalado') or (mo.get('liga') or {}).get('lideranca')):
        fr = [f for f in mo['frases'] if not f.startswith(('Pela frente', 'Próximo desafio', 'Maratona'))]
        if fr:
            out.append((8.5 if mo['clima'] in ('crise', 'alerta') else 6, 'momento', '. '.join(fr[:2]) + '.'))
    co = car.get('corrida')
    if co and co.get('rivais') and not (mo.get('liga') or {}).get('rival'):
        rv = co['rivais'][0]
        out.append((4, 'corrida', f'Na tabela, o time segue em {co["pos"]}º, com o {rv["nome"]} '
                                  + (f'{abs(rv["dif"])} ponto{"s" if abs(rv["dif"]) > 1 else ""} atrás.' if rv['dif'] < 0 else f'{rv["dif"]} ponto{"s" if rv["dif"] > 1 else ""} à frente.' if rv['dif'] else 'empatado em pontos.')))
    out.sort(key=lambda x: -x[0])
    agenda = next((f for f in mo.get('frases') or [] if f.startswith(('Pela frente', 'Próximo desafio'))), None)
    return out, {'adv': adv, 'gp': gp, 'gc': gc, 'res': res, 'reg': reg, 'tecnico': (reg or {}).get('tecnico'),
                 'agenda': agenda, 'clima': mo.get('clima'), 'seq': mo.get('seq') or {}}


def _abertura(veiculo, info, nos):
    a, gp, gc, res, tec = info['adv'], info['gp'], info['gc'], info['res'], info.get('tecnico')
    placar = f'{nos} {gp} x {gc} {a}'
    d = (info.get('seq') or {}).get('d', 0)
    if res == 'D' and d >= 2:   # a sequência vira a manchete
        n = ORD.get(d, f'{d}ª')
        return {'mesa_tatica': (f'{n.capitalize()} derrota seguida: o que explica a queda do {nos}', f'{placar} — o que a prancheta mostra'),
                'plantao': (f'{nos} perde de novo e acende o alerta', f'{placar}: {n} derrota seguida'),
                'resenha': (f'{n.upper()} SEGUIDA?! {placar} 💀', 'A resenha mais sincera do pós-jogo')}[veiculo]
    if veiculo == 'mesa_tatica':
        return ({'V': f'Vitória construída: {placar}', 'E': f'Empate de detalhes: {placar}', 'D': f'Por que o {nos} perdeu: {placar}'}[res],
                f'O que a prancheta explica' + (f' — o plano de {tec}' if tec else ''))
    if veiculo == 'plantao':
        return ({'V': f'{nos} vence o {a} e segue firme', 'E': f'{nos} e {a} ficam no empate', 'D': f'{nos} tropeça diante do {a}'}[res],
                f'{placar}: o resumo da rodada')
    return ({'V': f'DEU BOM! {placar} 🔥', 'E': f'Empatou, mas a gente explica 😅 ({placar})', 'D': f'DEU RUIM: {placar} 💀'}[res],
            'A resenha mais sincera do pós-jogo')


def _corpo(veiculo, razoes, info, nos):
    rs = [t for _, c, t in razoes if c != 'momento']
    mom = next((t for _, c, t in razoes if c == 'momento'), None)
    ag = info.get('agenda')
    d = info.get('seq', {}).get('d', 0)
    if not rs:
        rs = ['Jogo sem grandes histórias táticas: o placar refletiu o que se viu em campo.']
    if veiculo == 'mesa_tatica':
        fim = {'D': 'o adversário teve um plano e executou melhor.', 'E': 'equilíbrio tático, decidido em detalhes.',
               'V': 'o plano funcionou e o time impôs as suas forças.'}[info['res']]
        return (['A leitura do jogo: ' + rs[0]] + rs[1:4] + ([f'O contexto pesa: {mom[0].lower() + mom[1:]}'] if mom else [])
                + ['Conclusão: ' + fim] + ([f'{ag}. A comissão técnica tem pouco tempo para corrigir.'] if ag and info['res'] != 'V' else []))
    if veiculo == 'plantao':
        fecho = {'D': 'A torcida saiu cobrando. Agora é virar a chave para o próximo compromisso.',
                 'E': 'Um ponto que pode fazer falta lá na frente.', 'V': 'A arquibancada aprovou, e o clima é de confiança.'}[info['res']]
        if info['res'] == 'D' and d >= 2:
            fecho = ('A torcida saiu de cabeça baixa, e a cobrança vai aumentar.' if mom
                     else f'É a {ORD.get(d, str(d) + "ª")} derrota seguida, e a torcida saiu de cabeça baixa.')
        return ([mom] if mom else []) + [rs[0]] + rs[1:3] + [fecho] + ([ag + '.'] if ag else [])
    zoeira = {'D': 'Bora, que futebol é cíclico. Mas hoje foi um jogo pra apagar do histórico 🤡',
              'E': 'Nem fede nem cheira. Próximo! 🫠', 'V': 'É ISSO! O torcedor dorme feliz hoje 😎'}[info['res']]
    if info['res'] == 'D' and d >= 2:
        zoeira = 'O grupo do zap da torcida tá pegando fogo 🔥📱' if mom else f'{d} derrotas seguidas, galera. O grupo do zap da torcida tá pegando fogo 🔥📱'
    out = ['Resumindo pra galera: ' + rs[0]] + rs[1:3] + ([f'E o contexto não ajuda: {mom[0].lower() + mom[1:]} 😬'] if mom else []) + [zoeira]
    if ag:
        out.append(f'{ag}. Vai ser semana de coração na mão 🫣' if info['res'] != 'V' else f'{ag}. Segue o baile 💃')
    return out


def da_reuniao(car, r, snap, hoje, log=print):
    """Matérias de análise do último jogo do usuário (uma por veículo), uma vez por partida."""
    jogos = r.get('jogos') or []
    if not jogos:
        return []
    jogo = jogos[-1]
    chave_jogo = f'{jogo.get("num")}|{tuple(jogo["data"])}'
    if car.get('analise_ultimo') == chave_jogo:
        return []
    try:
        import dados
        P = dados.load_players(snap)
    except Exception:  # noqa: BLE001
        P = {}
    razoes, info = porques(r, car, jogo, P)
    car['analise_ultimo'] = chave_jogo
    car['analise_data'] = list(jogo['data'])
    car['analise_porques'] = [{'chave': c, 'texto': t} for _, c, t in razoes[:6]]
    nos = clube.C.get('nome') or r['time']
    ck = car.get('ck')
    out = []
    for v, (nome_v, estilo) in VEICULOS.items():
        titulo, fina = _abertura(v, info, nos)
        titulo, fina = clube.concordar(titulo), clube.concordar(fina)
        out.append({'chave': f'analise|{ck}|{v}|{chave_jogo}', 'frente': 'pos_jogo', 'data': tuple(jogo['data']),
                    'titulo': titulo, 'linha_fina': fina, 'autor': nome_v, 'estilo': estilo,
                    'corpo': clube.concordar_tudo(_corpo(v, razoes, info, nos)), 'dados': {'porques': car['analise_porques'], 'veiculo': v}})
    log(f'análise do jogo: {len(razoes)} razões ({", ".join(c for _, c, _ in razoes[:4])})')
    return out
