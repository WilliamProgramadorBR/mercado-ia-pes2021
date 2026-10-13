# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""PULSO AO VIVO da Central (10/10/2026): lê a MEMÓRIA do jogo a cada poucos segundos (SOMENTE LEITURA).

O save só chega depois do salvamento automático, e a reunião completa leva 1-2 min. Mas a memória do jogo tem as
mesmas estruturas, atualizadas na hora:
  - registros de jogo (596 B; +7 = 0x60 jogado / 0x20 agendado) numa região de ~24 MB: resultados e calendário de
    todas as competições (ler 0,02 s, varrer 0,8 s);
  - tabela da liga (mesmo registro de 20 B do save, liga_save);
  - bloco de finanças (orçamento de transferências e verba de salários).
O pulso grava historico/pulso_<slot>.json; a Central mistura isso por cima da última reunião (central.py).
Data atual = data do jogo mais recente já disputado no mundo (sempre há rodada em alguma liga).
"""
import json
import os
import struct
import time

import liga_save as LS
import memoria as M
import partidas_save as ps

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, 'historico')
REC = ps.REC
CACHE = os.path.join(HIST, 'pulso_cache.json')
_cache = {'jogos': None, 'tabela': None, 'financas': None, 'pid': None}


_dicas = []   # endereços da sessão anterior do jogo: a nova busca começa por perto (o heap costuma se repetir)


def _carregar_cache(pid):
    try:
        with open(CACHE, encoding='utf-8') as f:
            c = json.load(f)
        if c.get('pid') == pid:
            _cache.update({k: (tuple(v) if k == 'tabela' and isinstance(v, list) else v) for k, v in c.items()})
        else:
            for k in ('anos', 'n_reg_jogos'):      # referências que valem de uma sessão para outra
                if c.get(k):
                    _cache[k] = c[k]
            _dicas[:] = [x[0] for x in (c.get('jogos') or [])] + ([c['tabela'][0]] if c.get('tabela') else []) +                         ([c['financas']] if c.get('financas') else [])
    except (OSError, ValueError):
        pass
    _cache['pid'] = pid


def _ordenadas(h):
    """Regiões da memória, as mais próximas dos endereços da sessão anterior primeiro."""
    regs = _regioes(h)
    if _dicas:
        regs.sort(key=lambda r: min(abs(r[0] - x) for x in _dicas))
    return regs


def _salvar_cache():
    try:
        with open(CACHE, 'w', encoding='utf-8') as f:
            json.dump(_cache, f)
    except OSError:
        pass


def _regioes(h):
    return [(b, s) for b, s in M.regioes(h) if s <= 96 * 2**20]


def _jogos_da_regiao(x):
    out = []
    for o in range(0, len(x) - REC, 4):
        # +7: jogado 0x60 (liga/grupos), 0x40 ida e 0x50 volta do mata-mata; agendado 0x20, 0x00 ida e 0x10 volta
        f = x[o + 7]
        if f in (0x20, 0x40, 0x50, 0x60, 0x00, 0x10) and x[o + 13:o + 16] == bytes(3) and x[o + 12] <= 3 and ps._cabecalho_ok(x, o):
            if f in (0x00, 0x10) and (x[o + 28] or x[o + 31]):
                continue
            t1, t2 = struct.unpack_from('<II', x, o + 20)
            t1, t2 = t1 & 0x3FFF, t2 & 0x3FFF
            if t1 >= 730 or t2 >= 730 or t1 == t2:
                continue
            y, m, dd = struct.unpack_from('<HBB', x, o + 8)
            out.append({'data': (y, m, dd), 'comp': x[o + 4], 'rodada': x[o + 6], 'jogado': bool(f & 0x40), 'flag': f,
                        'time1': t1, 'time2': t2, 'gols1': x[o + 28], 'gols2': x[o + 31], '_x': x, '_o': o})
    return out


def _sumula(j, ti, lado='nos'):
    """Linhas de um lado no jogo (gols, assistências, nota, minutos), lidas do próprio registro na memória."""
    try:
        p = ps.partida(j['_x'], j['_o'])
    except Exception:  # noqa: BLE001
        return []
    nosso = p['time1'] == ti
    linhas = (p['linhas1'] if nosso else p['linhas2']) if lado == 'nos' else (p['linhas2'] if nosso else p['linhas1'])
    return [{'reg': x['reg'], 'pid': x['pid'], 'gols': x['gols'], 'assist': x['assist'], 'nota': x['nota'],
             'min': x['minutos'], 'titular': x['titular']} for x in linhas if x['minutos'] > 0]


def _final(j, js, liga):
    try:
        import marcos
        return bool(marcos.eh_final(j, js, liga))
    except Exception:  # noqa: BLE001
        return False


def _num(j):
    try:
        return struct.unpack_from('<I', j['_x'], j['_o'])[0]
    except Exception:  # noqa: BLE001
        return None


def jogos(h):
    """Todos os registros de jogo da memória. Eles ficam espalhados (liga numa região, Champions noutra; 10/10/2026):
    na 1ª vez varre o processo e guarda as regiões com registros; depois só relê essas regiões."""
    if _cache['jogos']:
        out = []
        for b, s in _cache['jogos']:
            x = M.ler(h, b, s)
            if x:
                out += _jogos_da_regiao(x)
        if len(out) > 500:
            return out
    regs, out = [], []
    anos = _cache.get('anos') or []
    assinaturas = [bytes([f]) + struct.pack('<H', a) for a in anos for f in (0x60, 0x40, 0x50, 0x20, 0x10)]
    for b, s in _ordenadas(h):
        if s > 64 * 2**20:
            continue
        x = M.ler(h, b, s)
        if not x:
            continue
        # filtro rápido (em C): o registro tem a marca jogado/agendado seguida do ano da carreira
        if assinaturas and not any(x.find(a) >= 0 for a in assinaturas):
            continue
        j = _jogos_da_regiao(x)
        if len(j) >= 5:
            regs.append([b, s])
            out += j
    _cache['jogos'] = regs or None
    if out:   # anos da carreira (para o filtro rápido da próxima sessão)
        ano = max(j['data'] for j in out if j['jogado'])[0] if any(j['jogado'] for j in out) else out[0]['data'][0]
        _cache['anos'] = [ano - 1, ano, ano + 1]
    return out


def tabela(h, ti, times):
    """Classificação atual da liga (mesmo formato do save), achada na memória e guardada em cache."""
    if _cache['tabela']:
        b, s = _cache['tabela']
        x = M.ler(h, b, s)
        t = LS.tabela(x, ti, ini=0, times=times) if x else []
        if t:
            return t
    for b, s in _ordenadas(h):
        if s > 32 * 2**20:
            continue
        x = M.ler(h, b, s)
        if not x:
            continue
        t = LS.tabela(x, ti, ini=0, times=times)
        if t and len(t) >= 10:
            _cache['tabela'] = (b, s)
            return t
    return []


def financas(h, referencia):
    """(orçamento de transferências, verba de salários) em R$, pelo bloco de finanças na memória."""
    import ao_vivo
    if not _cache['financas'] and referencia:
        try:
            a = ao_vivo.achar_orcamento_memoria(h, referencia)
            if len(a) == 1:
                _cache['financas'] = a[0][0]
        except Exception:  # noqa: BLE001
            return None
    if not _cache['financas']:
        return None
    x = M.ler(h, _cache['financas'], 24)
    if not x:
        _cache['financas'] = None
        return None
    return struct.unpack_from('<i', x, 0)[0] * 430, struct.unpack_from('<i', x, 20)[0] * 430


FIN_PAD = b'\x6c\x00\x00\x00\xff\xff\x00\x00'


def _descobrir(h, ti, times, referencia):
    """Passada ÚNICA pela memória (antes eram 3 leituras de ~2,2 GB) achando, ao mesmo tempo, as regiões dos jogos,
    a tabela da liga e o bloco de finanças. Começa pelos endereços da sessão anterior e para quando achou tudo."""
    anos = _cache.get('anos') or []
    assinaturas = [bytes([f]) + struct.pack('<H', a) for a in anos for f in (0x60, 0x40, 0x50, 0x20, 0x10)]
    regs_j, tab, fin = [], None, None
    n_prev = _cache.get('n_reg_jogos') or 0
    lo = hi = None
    if referencia:
        lo, hi = referencia * 0.9 / 430, referencia * 1.1 / 430
    for b, s in _ordenadas(h):
        if s > 64 * 2**20:
            continue
        if tab and (fin or not referencia) and n_prev and len(regs_j) >= n_prev:
            break
        x = M.ler(h, b, s)
        if not x:
            continue
        if not assinaturas or any(x.find(a) >= 0 for a in assinaturas):
            if len(_jogos_da_regiao(x)) >= 5:
                regs_j.append([b, s])
        if not tab and s <= 32 * 2**20:
            t = LS.tabela(x, ti, ini=0, times=times)
            if t and len(t) >= 10:
                tab = (b, s)
        if not fin and lo:
            k = x.find(FIN_PAD)
            while k >= 0 and not fin:
                if k + 48 <= len(x) and lo <= struct.unpack_from('<I', x, k + 44)[0] <= hi:
                    fin = b + k + 44
                k = x.find(FIN_PAD, k + 1)
    if regs_j:
        _cache['jogos'] = regs_j
        _cache['n_reg_jogos'] = len(regs_j)
    if tab:
        _cache['tabela'] = tab
    if fin:
        _cache['financas'] = fin


def ciclo(slot, aux, referencia_orcamento=None):
    pid = M.pid_do_jogo()
    if not pid:
        return None
    if _cache['pid'] != pid:
        _cache.update({'jogos': None, 'tabela': None, 'financas': None})   # n_jogos fica como referência
        _carregar_cache(pid)
    antes = dict(_cache)
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    try:
        if not _cache['jogos'] or not _cache['tabela']:
            _descobrir(h, aux['ti'], None, referencia_orcamento)   # 1 passada só (jogos + tabela + finanças)
        js = jogos(h)
        if not js:
            return None
        ti, nomes, comp = aux['ti'], aux['nomes'], aux.get('comp_liga')
        nome = lambda i: nomes[i] if i < len(nomes) else str(i)
        jogados = [j for j in js if j['jogado']]
        hoje = max(j['data'] for j in jogados) if jogados else None
        if hoje and _cache.get('anos') != [hoje[0] - 1, hoje[0], hoje[0] + 1]:
            _cache['anos'] = [hoje[0] - 1, hoje[0], hoje[0] + 1]
        meus = sorted((j for j in jogados if ti in (j['time1'], j['time2'])), key=lambda j: j['data'])
        ultimos = []
        for j in meus[-6:]:
            casa = j['time1'] == ti
            ultimos.append({'data': list(j['data']), 'casa': casa, 'adversario': nome(j['time2'] if casa else j['time1']),
                            'pro': j['gols1'] if casa else j['gols2'], 'contra': j['gols2'] if casa else j['gols1']})
        prox = next((j for j in sorted(js, key=lambda j: j['data']) if not j['jogado'] and ti in (j['time1'], j['time2'])
                     and (not hoje or j['data'] >= hoje)), None)
        times_liga = {t for j in js if j['comp'] == comp for t in (j['time1'], j['time2'])} if comp is not None else None
        tab = tabela(h, ti, times_liga)
        liga_res = sorted((j for j in jogados if j['comp'] == comp), key=lambda j: (j['data'], j['rodada']))[-10:] \
            if comp is not None else []
        # 12/10/2026: na virada, a memória ainda guarda a tabela FINAL da temporada passada (114 pontos em agosto).
        # Se a liga ainda não teve jogo nesta temporada, não há tabela: a imprensa não pode falar de pontos que não existem.
        if hoje and comp is not None:
            ini = (hoje[0] if hoje[1] >= 7 else hoje[0] - 1, 7, 1)
            if not any(j['comp'] == comp and tuple(j['data']) >= ini for j in jogados):
                tab, liga_res = [], []
        fin = financas(h, referencia_orcamento)
        if dict(_cache) != antes:
            _salvar_cache()
        ult_j = meus[-1] if meus else None
        return {
            'quando': time.time(), 'slot': slot, 'data_jogo': list(hoje) if hoje else None,
            'ultimos_jogos': ultimos,
            # súmula do nosso último jogo: a coletiva pós-jogo nasce no dia do jogo (coletiva_viva.py)
            'ultimo_jogo': {'data': list(ult_j['data']), 'comp': ult_j['comp'], 'rodada': ult_j['rodada'], 'num': _num(ult_j),
                            'time1': ult_j['time1'], 'time2': ult_j['time2'], 'gols1': ult_j['gols1'], 'gols2': ult_j['gols2'],
                            'linhas': _sumula(ult_j, ti), 'linhas_adv': _sumula(ult_j, ti, 'adv'), 'flag': ult_j['flag'],
                            'final': _final(ult_j, js, comp),
                            # jogo de ida (mata-mata): viradas.py precisa dele para saber se houve virada histórica
                            'ida': next(({k: (list(v) if k == 'data' else v) for k, v in j.items() if not k.startswith('_')}
                                         for j in reversed(meus[:-1]) if j['comp'] == ult_j['comp'] and j['flag'] in (0x40, 0x50)
                                         and {j['time1'], j['time2']} == {ult_j['time1'], ult_j['time2']}), None)
                            if ult_j['flag'] in (0x40, 0x50) else None} if ult_j else None,
            'proximo': {'casa': nome(prox['time1']), 'fora': nome(prox['time2']), 'data': list(prox['data']),
                        'comp': prox['comp'], 'rodada': prox['rodada'], 'final': _final(prox, js, comp)} if prox else None,
            'classificacao': [{'pos': x['pos'], 'time': nome(x['time']), 'pts': x['pts'], 'j': x['v'] + x['e'] + x['d'],
                               'v': x['v'], 'e': x['e'], 'd': x['d'], 'gp': x['gp'], 'gc': x['gc'], 'eu': x['time'] == ti}
                              for x in tab],
            'resultados_liga': [{'data': list(j['data']), 'casa': nome(j['time1']), 'fora': nome(j['time2']),
                                 'g1': j['gols1'], 'g2': j['gols2'], 'meu': ti in (j['time1'], j['time2'])} for j in liga_res],
            'orcamento': fin[0] if fin else None, 'verba_salarios': fin[1] if fin else None,
        }
    finally:
        M.k32.CloseHandle(h)


def gravar(slot, dados):
    p = os.path.join(HIST, f'pulso_{slot}.json')
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False)
    os.replace(tmp, p)


def laco(slot_atual, intervalo=4, log=print):
    """Roda para sempre (thread da Central). slot_atual() -> (slot, referência do orçamento) da carreira mostrada."""
    ultimo = None
    while True:
        try:
            slot, ref = slot_atual()
            aux_p = os.path.join(HIST, f'pulso_aux_{slot}.json') if slot else None
            if slot and os.path.exists(aux_p):
                with open(aux_p, encoding='utf-8') as f:
                    aux = json.load(f)
                dados = ciclo(slot, aux, ref)
                if dados:
                    chave = json.dumps({k: v for k, v in dados.items() if k != 'quando'}, sort_keys=True)
                    if chave != ultimo:      # só grava quando algo mudou (a Central empurra para a página)
                        gravar(slot, dados)
                        ultimo = chave
        except Exception as e:  # noqa: BLE001 - o pulso nunca derruba a Central
            log(f'pulso: {e}')
        time.sleep(intervalo)
