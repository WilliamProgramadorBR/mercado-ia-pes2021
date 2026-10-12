"""OLHEIRO DA IA (12/10/2026): o técnico do computador estuda o time do usuário antes do jogo.

Lê só o que o jogo mostra de verdade:
  - o plano de jogo do usuário (bloco 729: estilo, saída, linha, compactação, instruções avançadas);
  - o elenco: quem decide (gols + assistências na temporada, pelas súmulas), velocidade e jogo aéreo dos
    atacantes (atributos da foto da memória), dribles e jogo aéreo nos números detalhados;
  - a forma recente (gols feitos e sofridos nos últimos jogos).
Devolve um perfil com números e frases ("time de posse, gols concentrados no William, pontas muito rápidos") que a
IA adversária usa para escolher a contra-tática.
"""
import tatica_save as T

ATAQUE = {'CF', 'SS', 'LWF', 'RWF', 'AMF'}


def perfil(d, dados, P, squad):
    """d = save descriptografado; dados = estado da Central (jogadores, últimos jogos); P = fichas; squad = SaveML.squad
    do time do usuário (para achar a posição de cada jogador no elenco)."""
    out = {'frases': []}
    o = T.bloco_usuario(d)
    if o is not None:
        out['plano'] = T.ler_em(d, o)
        out['instrucoes'] = [c for c, _, _ in T.instrucoes(d, None, o=o)]
    pos_elenco = {tuple(k): i for i, k in enumerate(squad)}
    J = [j for j in dados.get('jogadores') or [] if (j.get('temporada') or {}).get('jogos')]
    gols_time = sum(j['temporada'].get('gols', 0) for j in J) or 1
    ameacas = []
    for j in J:
        t = j['temporada']
        k = (j['reg'], j['pid'])
        f = P.get(k) if P else None
        peso = t.get('gols', 0) + 0.6 * t.get('assist', 0)
        if peso <= 0 or k not in pos_elenco:
            continue
        ameacas.append({'nome': j['nome'], 'pos': j.get('pos'), 'idx': pos_elenco[k], 'gols': t.get('gols', 0),
                        'assist': t.get('assist', 0), 'jogos': t['jogos'], 'peso': round(peso / t['jogos'], 2),
                        'parte_gols': round(t.get('gols', 0) / gols_time, 2), 'velocidade': f['speed'] if f else None,
                        'titular': (j.get('minutos_recentes') or 0) >= 0.5})
    ameacas.sort(key=lambda x: (-x['peso'], -x['gols']))
    out['ameacas'] = ameacas[:5]
    atac = [j for j in dados.get('jogadores') or [] if j.get('pos') in ATAQUE and (j.get('minutos_recentes') or 0) >= 0.4]
    vel = [P[(j['reg'], j['pid'])]['speed'] for j in atac if P and (j['reg'], j['pid']) in P]
    out['velocidade_ataque'] = round(sum(vel) / len(vel)) if vel else None
    cf = [P[(j['reg'], j['pid'])] for j in atac if j.get('pos') == 'CF' and P and (j['reg'], j['pid']) in P]
    out['aereo'] = max((round((f['header'] + f['jump']) / 2) for f in cf), default=None)
    # dribles do time por jogo = soma do ritmo de cada um (só partidas JOGADAS entram nos números detalhados)
    num = [j.get('numeros') or {} for j in J]
    out['dribles_por_jogo'] = round(sum((n.get('dribles') or 0) / n['jogos'] for n in num if n.get('jogos')), 1)
    try:   # entrosamento com o plano (familiaridade tática do próprio jogo)
        import familiaridade
        fam = familiaridade.analisar(d, dados.get('jogadores') or [])
    except Exception:  # noqa: BLE001
        fam = None
    if fam:
        out['entrosamento'] = fam['time']
        if fam['time'] < 85:
            out['frases'].append(f'time ainda se acostumando ao plano (entrosamento {fam["time"]})')
    uj = (dados.get('ultimos_jogos') or [])[-5:]
    if uj:
        out['gols_feitos'] = round(sum(x['pro'] for x in uj) / len(uj), 1)
        out['gols_sofridos'] = round(sum(x['contra'] for x in uj) / len(uj), 1)
    # frases para o relatório e para a imprensa
    pl = out.get('plano') or {}
    if pl:
        out['frases'].append(('time de posse' if pl['estilo_ofensivo'] else 'time de contra-ataque')
                             + (', saída curta' if pl['saida_de_bola'] else ', bola longa')
                             + f', linha {pl["linha_defensiva"]}, compactação {pl["compactacao"]}')
    if ameacas and ameacas[0]['parte_gols'] >= 0.3:
        a = ameacas[0]
        out['frases'].append(f'gols concentrados no {a["nome"]} ({a["gols"]} gols, {round(a["parte_gols"] * 100)}% do time)')
    if out['velocidade_ataque'] and out['velocidade_ataque'] >= 86:
        out['frases'].append(f'ataque muito rápido (velocidade média {out["velocidade_ataque"]})')
    if out['aereo'] and out['aereo'] >= 85:
        out['frases'].append(f'centroavante forte no jogo aéreo ({out["aereo"]})')
    if out.get('gols_feitos', 0) >= 2.5:
        out['frases'].append(f'ataque em alta ({out["gols_feitos"]} gols por jogo nos últimos 5)')
    if out.get('gols_sofridos', 0) >= 1.5:
        out['frases'].append(f'defesa vazando ({out["gols_sofridos"]} sofridos por jogo nos últimos 5)')
    return out
