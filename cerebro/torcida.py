# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ARQUIBANCADA (12/10/2026): o termômetro da torcida.

Humor de 0 a 100, recalculado a cada reunião, a partir do que a arquibancada sente:
  forma (últimos 5 jogos oficiais), tabela x meta, títulos recentes, ídolo que saiu, estrela assediada (rumores),
  crises e casos no vestiário, a obrigação de quem ganhou tudo (vitoriosos.py) e a joia da base esquecida.
Daí saem: o ESTADO (em festa, confiante, exigente, impaciente, revoltada), as FAIXAS no estádio, o CANTO do momento e o
PÚBLICO estimado (capacidade do estádio x ocupação pelo humor). Quando o humor despenca, protesto vira notícia.
car['torcida'] = {...}; a série do humor entra em car['serie'] (gráfico).
"""
import datetime as dt
import random

from clube import C as CL

NAO_OFICIAL = set(range(100, 111)) | {56}
CAPACIDADE = {'MANCHESTER UNITED': 74310, 'FLAMENGO': 78838, 'FLUMINENSE': 78838, 'ATLÉTICO DE MADRID': 70460, 'REAL MADRID': 83186,
              'BARCELONA': 99354, 'LIVERPOOL': 61276, 'ARSENAL': 60704, 'CHELSEA': 40343, 'MANCHESTER CITY': 53400,
              'TOTTENHAM HOTSPUR': 62850, 'NEWCASTLE UNITED': 52305, 'WOLVERHAMPTON WANDERERS': 31750, 'ASTON VILLA': 42640,
              'EVERTON': 52888, 'WEST HAM UNITED': 62500, 'BAYERN MÜNCHEN': 75024, 'BORUSSIA DORTMUND': 81365,
              'JUVENTUS': 41507, 'INTER': 75817, 'MILAN': 75817, 'PARIS SAINT-GERMAIN': 47929, 'BENFICA': 64642, 'PORTO': 50033,
              'AJAX': 55865, 'CORINTHIANS': 49205, 'PALMEIRAS': 43713, 'SÃO PAULO': 66795, 'SANTOS': 16068, 'GRÊMIO': 55662,
              'INTERNACIONAL': 50128, 'ATLÉTICO MINEIRO': 46000, 'CRUZEIRO': 61846, 'BOTAFOGO': 44661, 'VASCO DA GAMA': 21880,
              'MIRASSOL': 15000, 'BAHIA': 47907, 'BOCA JUNIORS': 54000, 'RIVER PLATE': 84567}
ESTADOS = [(80, 'em festa'), (62, 'confiante'), (45, 'exigente'), (28, 'impaciente'), (0, 'revoltada')]


def _d(a, b):
    return (dt.date(*a) - dt.date(*b)).days


def calcular(car, r, hoje, rnd=None):
    rnd = rnd or random.Random(f'torcida|{car.get("ck")}|{hoje}')
    ti = r['ti']
    motivos = []
    h = 55.0
    jogos = [p for p in r.get('jogos') or [] if p['comp'] not in NAO_OFICIAL][-5:]
    pts = 0
    for p in jogos:
        gp, gc = (p['gols1'], p['gols2']) if p['time1'] == ti else (p['gols2'], p['gols1'])
        pts += 3 if gp > gc else 1 if gp == gc else 0
    if jogos:
        forma = pts / (3 * len(jogos))
        h += (forma - 0.55) * 40
        motivos.append(f'{pts} de {3 * len(jogos)} pontos nos últimos {len(jogos)} jogos')
    tab = (car.get('diretoria') or {}).get('tabela') or []
    eu = next((t for t in tab if t.get('eu')), None)
    meta = ((car.get('diretoria') or {}).get('metas') or {}).get('liga_alvo')
    if eu and eu.get('j', 0) >= 3:
        if eu['pos'] == 1:
            h += 8
            motivos.append('líder da liga')
        elif meta and eu['pos'] > meta:
            h -= min(16, 6 + 2 * (eu['pos'] - meta))
            motivos.append(f'{eu["pos"]}º lugar, abaixo da meta ({meta}º)')
    V = car.get('vitoriosos') or {}
    if V.get('obrigacao'):
        h += 6
        motivos.append(f'{(V.get("anterior") or {}).get("n", "vários")} títulos na temporada passada')
        t = V.get('tropeco')
        if t and _d(hoje, tuple(t['data'])) <= 10:
            h -= 10
            motivos.append(f'o tropeço com o {t["adv"]} ({t["gp"]} x {t["gc"]}) ainda incomoda: ganhar virou obrigação')
    tit = (car.get('historia') or {}).get('temporadas') or []
    tacas = [c for c in (tit[0].get('titulos') or []) if 'pré-temporada' not in c] if tit else []
    if tacas and _d(hoje, tuple(tit[0].get('ultimo_jogo') or hoje)) <= 30:
        h += 6
        motivos.append('taça recente: ' + ', '.join(tacas[-2:]))
    saidas = [m for m in car.get('mov_executadas') or [] if m.get('tipo') == 'saida' and _d(hoje, tuple(m['data'])) <= 30]
    idolos = [m for m in saidas if (m.get('prev') or {}).get('status') in ('Lenda', 'Ídolo') or m.get('valor', 0) >= 50e6]
    if idolos:
        h -= 7
        motivos.append(f'a saída de {idolos[0]["nome"]} ainda dói')
    rum = [x for x in car.get('rumores') or [] if x.get('ativo') and x.get('calor', 0) >= 50]
    if rum:
        h -= 3
        motivos.append(f'medo de perder {rum[0]["nome"]} para o {rum[0]["clube"]}')
    crises = [c for c in car.get('casos') or [] if c['tipo'] == 'crise']
    if crises:
        h -= 6
        motivos.append(f'crise no vestiário: {crises[0]["titulo"]}')
    h = max(0, min(100, round(h)))
    estado = next(n for lim, n in ESTADOS if h >= lim)
    ocup = min(1.0, 0.62 + h / 260)
    cap = CAPACIDADE.get((r.get('time') or '').upper(), 40000)
    publico = int(cap * ocup * rnd.uniform(0.97, 1.0))
    faixas = _faixas(car, r, h, estado, idolos, rum, V, rnd)
    canto = _canto(h, r, rnd)
    ant = car.get('torcida') or {}
    T = {'data': list(hoje), 'humor': h, 'estado': estado, 'motivos': motivos, 'publico': publico, 'capacidade': cap,
         'ocupacao': round(100 * publico / cap), 'faixas': faixas, 'canto': canto, 'anterior': ant.get('humor')}
    car['torcida'] = T
    noticias = []
    if ant.get('estado') and ant['estado'] != estado:
        noticias.append(f'ARQUIBANCADA: a torcida está {estado}' + (f' ({motivos[-1]}).' if motivos else '.'))
        if estado == 'revoltada':
            noticias.append(f'PROTESTO: faixas contra o time {CL.get("em_estadio", "no estádio")}. A diretoria acompanha de perto.')
    return T, noticias


def _faixas(car, r, h, estado, idolos, rum, V, rnd):
    ap = (CL.get('apelido') or r['time']).upper()
    J = r['J']
    out = []
    if rum:
        out.append(f'FICA, {rum[0]["nome"].upper()}!')
    if idolos:
        out.append(f'OBRIGADO, {idolos[0]["nome"].upper()}. ETERNO.')
    art = max(J, key=lambda j: j['t_gols'], default=None)
    if art and art['t_gols'] >= 3 and h >= 45:
        out.append(f'{art["nome"].upper()}, O NOSSO REI')
    jo = (V.get('joia') or {})
    if jo:
        out.append(f'{jo["nome"].upper()}: O FUTURO É AGORA')
    pj = car.get('proximo_jogo') or {}
    if pj.get('classico'):
        out.append(f'SEMANA DE {pj["classico"].upper()}: SÓ VALE VENCER')
    if pj.get('final'):
        out.append(f'É FINAL. É A NOSSA VIDA.')
    if estado == 'em festa':
        out += [f'AQUI É {ap}!', 'O MAIOR DA INGLATERRA NÃO DORME' if CL.get('curto') == 'Man Utd' else 'NINGUÉM SEGURA ESSE TIME']
    elif estado == 'confiante':
        out += [f'ACREDITAMOS EM VOCÊS, {ap}', 'JOGO A JOGO, ATÉ A TAÇA']
    elif estado == 'exigente':
        out += ['CAMPEÃO NÃO EMPATA' if V.get('obrigacao') else 'RAÇA E CORAÇÃO', 'QUEREMOS MAIS']
    elif estado == 'impaciente':
        out += ['RESPEITO À CAMISA', 'ACORDA, TIME!']
    else:
        tec = r.get('tecnico') or 'TÉCNICO'
        out += ['TIME SEM ALMA', f'{tec.upper()}, A PACIÊNCIA ACABOU']
    vistos, fin = set(), []
    for f in out:
        if f not in vistos:
            vistos.add(f)
            fin.append(f)
    return fin[:4]


def _canto(h, r, rnd):
    ap = CL.get('apelido') or r['time']
    if h >= 80:
        return rnd.choice([f'Ô, ô, ô... o {ap} voltou! O {ap} voltou!', f'Ninguém cala esse grito: é campeão, é {ap}!'])
    if h >= 62:
        return rnd.choice([f'Vamos, {ap}, vamos ganhar! Essa torcida não para de cantar!', f'Domingo eu vou ao estádio ver o {ap} jogar!'])
    if h >= 45:
        return rnd.choice(['Joga com raça, joga com amor! É a torcida que te pede, por favor!', f'Ei, {ap}, a torcida quer vitória!'])
    if h >= 28:
        return rnd.choice(['Ô, time sem vergonha, a torcida quer raça!', 'Silêncio na arquibancada. Só o bumbo, em ritmo de cobrança.'])
    return rnd.choice(['Time sem vergonha! Time sem vergonha!', 'Vergonha! Vergonha! Vergonha!'])
