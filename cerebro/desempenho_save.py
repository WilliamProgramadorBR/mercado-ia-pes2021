# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""DESEMPENHO DO CLUBE no save (20/10/2026): a tela "Informações do time > Desempenho do clube" em números
(SOMENTE LEITURA). Conferido campo a campo com as três telas do jogo (Man Utd 2035/36, 32 jogos).

Bloco de 76 u32 (0xcad8f8 nos saves de 2035/36; achado por coerência se mudar de lugar), só do time do usuário e só
de partidas JOGADAS (simuladas não entram, como nas estatísticas por jogador):
  0-8    área de jogo (3x3: linha de cima = terço de ataque; colunas esquerda, centro, direita). As "áreas de ataque"
         da tela (35/28/37%) são as COLUNAS somadas.
  9-17   áreas de desarme (3x3, mesma orientação)
  18     posse: soma das % x 100 de cada jogo
  19-26  8 números sem nome ainda;  41-46  6 números sem nome ainda
  27-40  cruzamentos (certos), passes (certos), chutes (no gol), chutes sofridos (no gol), interceptações,
         desarmes (certos), faltas, impedimentos, defesas
  47-53  gols FEITOS por período (0-15 ... 76-90, prorrogação);  54-60  gols SOFRIDOS por período
  61-67  tipos dos gols feitos;  68-74  tipos dos sofridos (drible, passe, cruzamento, passe em profundidade, jogada
         ensaiada, pênalti e um 7º que a tela não mostra — fecha a soma)
  75     0xFFFF (fim)
Logo depois (+0x44c) vem a tabela da TEMPORADA por jogador (estatisticas_save: 108 B por jogador).

O jogo zera o bloco na virada de temporada; em 2034/35 a carreira do usuário ficou SEM números (nem por jogador) e
em 2033/34 o bloco do time ficou parado em janeiro — por isso "sem dado" é AUSENTE, nunca zero.

Histórico (historico/desempenho_hist.json): uma foto por reunião (save) quando os números mudam; a diferença entre
duas fotos da mesma temporada = os jogos disputados entre elas. janela() devolve os últimos N jogos ANTES de uma
data — é o que alimenta o olheiro, a imprensa e (com teste) a rede, sem olhar o futuro.
"""
import glob
import json
import os
import struct
import time

import estatisticas_save as est

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ_HIST = os.path.join(HERE, 'historico', 'desempenho_hist.json')
POS_PADRAO = 0xcad8f8
N = 76
OFF_JOGADORES = 0x44c
PERIODOS = ('0-15', '16-30', '31-45', '46-60', '61-75', '76-90', 'prorrogação')
TIPOS = ('drible', 'passe', 'cruzamento', 'passe em profundidade', 'jogada ensaiada', 'pênalti', 'outros')
SIMPLES = ('cruzamentos', 'cruzamentos_ok', 'passes', 'passes_ok', 'chutes', 'chutes_gol', 'chutes_sofridos',
           'chutes_sofridos_gol', 'interceptacoes', 'desarmes', 'desarmes_ok', 'faltas', 'impedimentos', 'defesas')
CAMPOS_JOG = ('jogos', 'gols', 'assist', 'minutos', 'chutes', 'chutes_gol', 'dribles', 'dribles_ok', 'recebidos',
              'recebidos_ok', 'passes', 'passes_ok', 'desarmes', 'interceptacoes')
MIN_JOGOS = 6   # abaixo disso, porcentagem é sorte: o olheiro e a imprensa não usam


def _coerente(v):
    gp, gs, tf, ts = v[47:54], v[54:61], v[61:68], v[68:75]
    return (v[75] == 0xFFFF and sum(gp) == sum(tf) and sum(gs) == sum(ts) and max(v[:75]) < 10 ** 7
            and v[28] <= v[27] and v[30] <= v[29] and v[32] <= v[31] and v[34] <= v[33] and v[37] <= v[36])


def achar(d):
    """Posição do bloco (o padrão; senão procura pelo marcador 0xFFFF + coerência). None se não houver."""
    if len(d) >= POS_PADRAO + 4 * N and _coerente(struct.unpack_from(f'<{N}I', d, POS_PADRAO)):
        return POS_PADRAO
    marca = struct.pack('<I', 0xFFFF)
    i = d.find(marca, 0xB00000)
    while 0 <= i < 0xE00000:
        o = i - 4 * 75
        if o >= 0 and o % 4 == 0 and _coerente(struct.unpack_from(f'<{N}I', d, o)):
            return o
        i = d.find(marca, i + 1)
    return None


def campos(v):
    """76 números -> dicionário com nomes (vale para o acumulado ou para uma diferença entre duas fotos)."""
    out = {'area_jogo': list(v[0:9]), 'area_desarme': list(v[9:18]), 'posse_soma': v[18],
           'gols_periodo': list(v[47:54]), 'sofridos_periodo': list(v[54:61]),
           'tipos_feitos': list(v[61:68]), 'tipos_sofridos': list(v[68:75]),
           'sem_nome_a': list(v[19:27]), 'sem_nome_b': list(v[41:47])}
    out.update(zip(SIMPLES, v[27:41]))
    return out


def ler(d):
    """{'pos', 'valores' (76), 'vazio'} ou None se o bloco não existir neste save."""
    o = achar(d)
    if o is None:
        return None
    v = list(struct.unpack_from(f'<{N}I', d, o))
    return {'pos': o, 'valores': v, 'vazio': not any(v[:75])}


def jogadores(d, o, chaves=None):
    """Tabela da temporada por jogador logo depois do bloco: {(reg, pid): {campos}}."""
    out, a = {}, o + OFF_JOGADORES
    while a + est.REC <= len(d):
        j = est.ler(d, a)
        k = (j['reg'], j['pid'])
        if not est._plausivel(j) or (chaves is not None and k not in chaves) or k == (0, 0):
            break
        j['desarmes'] = j.get('desarmes', 0)
        out[k] = {c: j.get(c, 0) for c in CAMPOS_JOG}
        a += est.REC
    return out


# ------------------------------------------------------------------ leitura humana (acumulado ou trecho)
def _parte(xs):
    t = sum(xs)
    return [round(x / t, 3) for x in xs] if t else [0.0] * len(xs)


def resumo(v, jog=None, jogos=None, nomes=None):
    """Indicadores com sentido de futebol a partir de 76 números (acumulado ou diferença) e da tabela por jogador.
    jogos: quantos jogos o trecho cobre (senão: o máximo de jogos de um jogador)."""
    b = campos(v)
    if jogos is None and jog:
        jogos = max((j['jogos'] for j in jog.values()), default=0)
    jogos = jogos or 0
    aj, ad = b['area_jogo'], b['area_desarme']
    col = [aj[0] + aj[3] + aj[6], aj[1] + aj[4] + aj[7], aj[2] + aj[5] + aj[8]]
    lin = [sum(aj[0:3]), sum(aj[3:6]), sum(aj[6:9])]
    lin_d = [sum(ad[0:3]), sum(ad[3:6]), sum(ad[6:9])]
    gf, gs = sum(b['gols_periodo']), sum(b['sofridos_periodo'])
    pj = (lambda x: round(x / jogos, 2)) if jogos else (lambda x: None)
    r = {'jogos': jogos, 'gols': gf, 'sofridos': gs,
         'lados': dict(zip(('esquerda', 'centro', 'direita'), _parte(col))),
         'terco_ataque': _parte(lin)[0], 'terco_defesa': _parte(lin)[2],
         'desarme_alto': _parte(lin_d)[0], 'desarme_baixo': _parte(lin_d)[2],
         'posse': round(b['posse_soma'] / jogos / 100, 1) if jogos else None,
         'chutes_pj': pj(b['chutes']), 'chutes_gol_pj': pj(b['chutes_gol']),
         'chutes_sofridos_pj': pj(b['chutes_sofridos']), 'chutes_sofridos_gol_pj': pj(b['chutes_sofridos_gol']),
         'precisao_passe': round(b['passes_ok'] / b['passes'], 3) if b['passes'] else None,
         'cruzamentos_pj': pj(b['cruzamentos']), 'interceptacoes_pj': pj(b['interceptacoes']),
         'gols_periodo': dict(zip(PERIODOS, b['gols_periodo'])), 'sofridos_periodo': dict(zip(PERIODOS, b['sofridos_periodo'])),
         'tipos_feitos': dict(zip(TIPOS, b['tipos_feitos'])), 'tipos_sofridos': dict(zip(TIPOS, b['tipos_sofridos'])),
         'enfiada_sofridos': round((b['tipos_sofridos'][1] + b['tipos_sofridos'][3]) / gs, 3) if gs else None,
         'bola_parada_feitos': round((b['tipos_feitos'][4] + b['tipos_feitos'][5]) / gf, 3) if gf else None,
         'reta_final_feitos': round(b['gols_periodo'][5] / gf, 3) if gf else None,
         'reta_final_sofridos': round(b['sofridos_periodo'][5] / gs, 3) if gs else None,
         'fim_1t_sofridos': round(b['sofridos_periodo'][2] / gs, 3) if gs else None}
    if jog:
        tot = {c: sum(j[c] for j in jog.values()) for c in ('chutes', 'dribles', 'recebidos', 'gols')}
        dep = []
        for k, j in jog.items():
            if not j['jogos']:
                continue
            dep.append({'k': list(k), 'nome': (nomes or {}).get(k), 'jogos': j['jogos'], 'gols': j['gols'],
                        'parte_chutes': round(j['chutes'] / tot['chutes'], 3) if tot['chutes'] else 0,
                        'parte_dribles': round(j['dribles'] / tot['dribles'], 3) if tot['dribles'] else 0,
                        'parte_recebidos': round(j['recebidos'] / tot['recebidos'], 3) if tot['recebidos'] else 0,
                        'chutes': j['chutes'], 'conversao': round(j['gols'] / j['chutes'], 3) if j['chutes'] else None,
                        'dribles': j['dribles'], 'drible_ok': round(j['dribles_ok'] / j['dribles'], 3) if j['dribles'] else None})
        dep.sort(key=lambda x: -(x['parte_chutes'] + x['parte_dribles'] + x['parte_recebidos']))
        r['protagonistas'] = dep[:5]
    return r


# ------------------------------------------------------------------ histórico (uma foto por reunião)
def _ler_hist():
    try:
        with open(ARQ_HIST, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _gravar_hist(h):
    os.makedirs(os.path.dirname(ARQ_HIST), exist_ok=True)
    tmp = ARQ_HIST + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(h, f)
    for _ in range(40):
        try:
            os.replace(tmp, ARQ_HIST)
            return
        except PermissionError:
            time.sleep(0.05)


def foto(d, ti=None):
    """(time, foto) deste save: {'data', 'valores', 'jogadores': {'reg:pid': [CAMPOS_JOG...]}} ou (time, None)."""
    import carreira
    import partidas_save as ps
    ti_, nome = carreira.time_do_usuario(d)
    ti = ti_ if ti is None else ti
    b = ler(d)
    if b is None or b['vazio']:
        return nome, None
    jog = jogadores(d, b['pos'])
    js_ = sorted((p['data'] for p in ps.todas(d, *ps.FAIXA) if ti in (p['time1'], p['time2'])))
    return nome, {'data': list(js_[-1]) if js_ else None, 'valores': b['valores'],
                  'jogadores': {f'{k[0]}:{k[1]}': [j[c] for c in CAMPOS_JOG] for k, j in jog.items()}}


def registrar(d, h=None, quando=None, gravar=True):
    """Guarda a foto deste save no histórico (só se os números mudaram). Devolve a foto nova ou None."""
    nome, f = foto(d)
    if f is None:
        return None
    h = _ler_hist() if h is None else h
    lst = h.setdefault(nome, [])
    if lst and lst[-1]['valores'] == f['valores']:
        return None
    f['quando'] = quando or time.strftime('%Y-%m-%d %H:%M:%S')
    lst.append(f)
    h[nome] = lst[-600:]
    if gravar:
        _gravar_hist(h)
    return f


def fechar_temporada(f, ck, hoje, time_nome=None):
    """Grava (ou atualiza) a temporada desta foto no banco permanente (imprensa.db, hist_desempenho), como a história
    do clube faz: a última reunião antes da virada deixa a temporada completa guardada. Só grava se o último jogo da
    foto for DESTA temporada (na virada as súmulas somem e o bloco zera) e se não tiver MENOS jogos que o já guardado."""
    if not f or not ck or not f.get('data'):
        return None
    import json as _json
    import destaques
    import historia
    import imprensa_db as db
    ini = destaques.ini_temporada(tuple(hoje))
    if tuple(f['data'][:3]) < tuple(ini[:3]):
        return None
    t = historia.tkey(ini)
    jogos = max((v[0] for v in f['jogadores'].values()), default=0)
    with db.conectar() as c:
        x = c.execute('SELECT jogos FROM hist_desempenho WHERE carreira = ? AND temporada = ?', (ck, t)).fetchone()
        if x and (x['jogos'] or 0) > jogos:
            return None
        c.execute('INSERT OR REPLACE INTO hist_desempenho VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (ck, t, time_nome, jogos, db.data_txt(f['data']), _json.dumps(f['valores']),
                   _json.dumps({'campos': CAMPOS_JOG, 'jogadores': f['jogadores']}), db._agora()))
    return t


def temporadas_fechadas(ck):
    """{temporada: {'jogos', 'ultimo_jogo', 'resumo'}} do banco permanente, da mais antiga para a mais nova."""
    import json as _json
    import imprensa_db as db
    out = {}
    with db.conectar() as c:
        for x in c.execute('SELECT * FROM hist_desempenho WHERE carreira = ? ORDER BY temporada', (ck,)):
            jg = _json.loads(x['jogadores'])
            jog = {tuple(int(v) for v in k.split(':')): dict(zip(jg['campos'], v)) for k, v in jg['jogadores'].items()}
            out[x['temporada']] = {'jogos': x['jogos'], 'ultimo_jogo': x['ultimo_jogo'],
                                   'resumo': resumo(_json.loads(x['valores']), jog, x['jogos'])}
    return out


def reuniao(d, car, hoje):
    """Gancho da reunião (aplicar_vestiario): foto no histórico (se mudou) + temporada no banco permanente."""
    nome, f = foto(d)
    if f is None:
        return None
    h = _ler_hist()
    lst = h.setdefault(nome, [])
    if not lst or lst[-1]['valores'] != f['valores']:
        f2 = dict(f, quando=time.strftime('%Y-%m-%d %H:%M:%S'))
        lst.append(f2)
        h[nome] = lst[-600:]
        _gravar_hist(h)
    return fechar_temporada(f, (car or {}).get('ck'), hoje, nome)


def reconstruir(pasta=None, log=print):
    """Refaz o histórico com todos os saves descriptografados guardados (save_work/vestiario_*/dec/data.dat)."""
    pasta = pasta or os.path.join(HERE, '..', 'save_work')
    saves = sorted(glob.glob(os.path.join(pasta, 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime)
    h, n = {}, 0
    for p in saves:
        try:
            with open(p, 'rb') as fh:
                d = fh.read()
            if registrar(d, h, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p))), gravar=False):
                n += 1
        except Exception as e:  # noqa: BLE001
            log(f'desempenho: {os.path.basename(os.path.dirname(os.path.dirname(p)))}: {e}')
    for lst in h.values():
        lst.sort(key=lambda f: (f['data'] or [0], f['quando']))
    _gravar_hist(h)
    log(f'desempenho: {n} fotos de {len(saves)} saves ({", ".join(f"{k}: {len(v)}" for k, v in h.items())})')
    return h


def _jog(f):
    return {tuple(int(x) for x in k.split(':')): dict(zip(CAMPOS_JOG, v)) for k, v in f['jogadores'].items()}


def _diferenca(novo, velho):
    """Números do trecho entre duas fotos da MESMA temporada (None se o jogo zerou no meio = virada)."""
    v = [a - b for a, b in zip(novo['valores'][:75], velho['valores'][:75])] + [0xFFFF]
    if min(v[:75]) < 0:
        return None
    jn, jv = _jog(novo), _jog(velho)
    jog = {}
    for k, j in jn.items():
        o = jv.get(k) or dict.fromkeys(CAMPOS_JOG, 0)
        dj = {c: j[c] - o[c] for c in CAMPOS_JOG}
        if min(dj.values()) < 0:
            return None
        jog[k] = dj
    return v, jog


def janela(time_nome, n_jogos=8, ate=None, h=None, max_dias=30):
    """Indicadores dos ÚLTIMOS n_jogos (pelo menos) da temporada, só com fotos ANTES de `ate` (data do jogo):
    {'resumo', 'jogos', 'de', 'ate'} ou None se não houver dado. Usa a última foto antes de `ate` e volta até cobrir
    n_jogos; se a temporada for mais curta, devolve o que tem (o consumidor decide o mínimo).
    max_dias: a última foto precisa ser de até max_dias antes de `ate` (senão é número velho de outra fase/temporada —
    em 2034/35 o jogo não gravou nada e a foto parada de jan/2034 seria usada o ano inteiro)."""
    h = _ler_hist() if h is None else h
    lst = [f for f in h.get(time_nome) or [] if f['data'] and (ate is None or tuple(f['data']) < tuple(ate))]
    if not lst:
        return None
    ult = lst[-1]
    if ate is not None and max_dias is not None:
        import datetime as dt
        try:
            if (dt.date(*ate[:3]) - dt.date(*ult['data'][:3])).days > max_dias:
                return None
        except ValueError:
            return None
    base = None
    for f in reversed(lst[:-1]):
        dif = _diferenca(ult, f)
        if dif is None:
            break
        base = f
        if max((j['jogos'] for j in dif[1].values()), default=0) >= n_jogos:
            break
    if base is None:   # só uma foto na temporada: o acumulado dela
        v, jog = ult['valores'], _jog(ult)
        de = None
    else:
        v, jog = _diferenca(ult, base)
        de = base['data']
    jogos = max((j['jogos'] for j in jog.values()), default=0)
    if not jogos:
        return None
    return {'resumo': resumo(v, jog, jogos), 'jogos': jogos, 'de': de, 'ate': ult['data']}


def temporada(d, nomes=None):
    """Acumulado da temporada direto do save (o que a tela mostra) + protagonistas. None se não houver números."""
    b = ler(d)
    if b is None or b['vazio']:
        return None
    jog = jogadores(d, b['pos'])
    return resumo(b['valores'], jog, nomes=nomes)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'reconstruir':
        reconstruir()
    else:
        p = max(glob.glob(os.path.join(HERE, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime)
        print(json.dumps(temporada(open(p, 'rb').read()), ensure_ascii=False, indent=1)[:3000])
