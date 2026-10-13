# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""TÉCNICO DA IA — escalações realistas nos jogos simulados (12/10/2026).

O erro da Konami (achado com x64dbg): antes de cada jogo SIMULADO, o jogo chama o técnico da IA com o modo 3
(0x1413321FC: mov dword ptr [rbp+0xE4], 3), que joga fora a escalação guardada e monta outra quase ao acaso — o
Real Madrid jogava sem Güler, Mastantuono e Tchouaméni e com reservas de nota 76. No modo 1 o jogo MANTÉM a
escalação guardada do clube e só troca quem estiver indisponível (lesão, suspensão).

Este módulo:
  1. aplica o patch 3 -> 1 só na MEMÓRIA do jogo (o PES2021.exe nunca é alterado; ao fechar o jogo, some);
  2. antes de cada jogo, escreve a escalação de cada clube da IA na memória (escalação = fim do registro do clube,
     tatica_save.escalacao): os melhores por posição na formação do clube, com RODÍZIO REALISTA:
       - jogo grande (Champions/Libertadores, final, clássico, briga do topo): sempre os melhores;
       - jogo menor (copa nacional, adversário bem mais fraco) e jogador de linha com 2+ jogos nos últimos 7 dias:
         descansa (no máximo 3 por jogo);
     DIRETOR DE CAMPEONATO (disputa.py): time em disputa na liga (título, vagas, rebaixamento; pressão pelo momento
     da temporada e pela distância de pontos) = 'decisivo' (força máxima; na copa, poupa para a liga); time sem
     objetivo no fim da temporada = 'relax' (2 de linha descansam; nunca contra o usuário);
  3. guarda o que escreveu (historico/escalacao_ia.json) — a súmula do jogo simulado só mostra quem TERMINOU em
     campo (3 substituições), então o cansaço é contado pelas nossas próprias escalações.
Teste (20/10/2035, 11 clubes): os 11 escritos entraram em campo; as 3 diferenças por clube foram substituições.
O time do usuário nunca é tocado. Desliga com "tecnico_ia": false no automacao.json.
"""
import ctypes
import datetime as dt
import json
import os
import time
import zlib

import encaixe
import tatica_save as T

HERE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(HERE, 'historico', 'escalacao_ia.json')
ALVO = 0x1413321FC
ORIGINAL = bytes.fromhex('c785e40000000300' '0000')
COPAS = {23, 24, 25, 26, 27, 28, 31, 53, 54, 55, 59, 68, 123, 124, 125, 142}
GRANDES = {3, 4, 8, 9, 10, 1, 15, 16}          # Champions, Libertadores, Mundial, AFC
MAX_DESCANSOS = 3
N_CLUBES = 625


def _estado():
    try:
        with open(ARQ, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'feitos': {}, 'titulares': {}}


def _gravar(e):
    tmp = ARQ + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(e, f, ensure_ascii=False)
    os.replace(tmp, ARQ)


def nova_sessao():
    """O jogo foi (re)aberto: o que escrevemos na memória da sessão anterior se perdeu (a menos que o jogo tenha
    salvado depois) — esquece os jogos já preparados para escrever tudo de novo. O histórico de titulares fica."""
    e = _estado()
    if e.get('feitos'):
        e['feitos'] = {}
        _gravar(e)


# ---------------------------------------------------------------- patch do modo
def patch(h, log=print):
    """Garante o modo 1 no código do jogo (memória). True se ativo."""
    import memoria as M
    atual = M.ler(h, ALVO, 10)
    if not atual or atual[:6] != ORIGINAL[:6] or atual[7:] != ORIGINAL[7:] or atual[6] not in (1, 3):
        log(f'técnico da IA: código do jogo diferente do esperado em {ALVO:#x} — patch NÃO aplicado')
        return False
    if atual[6] == 1:
        return True
    k = M.k32
    k.VirtualProtectEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
    k.FlushInstructionCache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
    velho = ctypes.c_uint32()
    if not k.VirtualProtectEx(h, ALVO + 6, 1, 0x40, ctypes.byref(velho)):
        log('técnico da IA: sem permissão para o patch')
        return False
    n = ctypes.c_size_t()
    k.WriteProcessMemory(h, ctypes.c_void_p(ALVO + 6), ctypes.create_string_buffer(b'\x01', 1), 1, ctypes.byref(n))
    k.VirtualProtectEx(h, ALVO + 6, 1, velho.value, ctypes.byref(ctypes.c_uint32()))
    k.FlushInstructionCache(h, ALVO, 10)
    ok = M.ler(h, ALVO + 6, 1) == b'\x01'
    log('técnico da IA: patch do modo 1 aplicado na memória' if ok else 'técnico da IA: patch não conferiu')
    return ok


# ---------------------------------------------------------------- escolha
PRESSAO_DECISIVA = 0.45   # disputa na liga (disputa.py) a partir disso: força máxima, nada de poupar


def _importancia(j, ti, forca, nomes, disp=None, user_ti=None):
    """'decisivo', 'grande', 'normal', 'menor' ou 'relax' para o time `ti` neste jogo.
    disp = disputa.mapa: pressão de cada time na liga (título, vagas, rebaixamento)."""
    import classicos
    adv = j['time2'] if j['time1'] == ti else j['time1']
    m = (disp or {}).get(ti) or {}
    liga = j['comp'] == m.get('comp')
    if adv == user_ti:
        return 'grande'                        # contra o time do usuário: sempre força máxima
    if liga and m.get('pressao', 0) >= PRESSAO_DECISIVA:
        return 'decisivo'                      # está dando a vida: cada ponto conta
    if j['comp'] in GRANDES or classicos.nome(nomes.get(j['time1'], ''), nomes.get(j['time2'], '')):
        return 'grande'
    if j['comp'] in COPAS and m.get('pressao', 0) >= 0.6:
        return 'menor'                         # a liga está pegando fogo: copa vira prioridade 2
    if liga and m.get('sem_objetivo') and adv != user_ti:
        return 'relax'                         # fim de temporada sem nada em jogo (nunca contra o usuário)
    dif = (forca.get(ti) or 75) - (forca.get(adv) or 75)
    if j['comp'] in COPAS or dif >= 6:
        return 'menor'
    if dif <= -2:
        return 'grande'      # adversário mais forte: vai com tudo
    return 'normal'


def escalar(team, sq_ids, jogos7, importancia, semente=0, max_desc=MAX_DESCANSOS):
    """(lista de 40 posições no elenco, nomes dos titulares, descansados) para o time."""
    import random
    pos_id = {pid: i for i, pid in enumerate(sq_ids)}
    jogadores = [p for p in team.players if p.pid in pos_id]
    slots = encaixe.formation_slots(team)
    xi, _ = encaixe.best_xi(jogadores, slots)
    descansam = []
    if importancia == 'relax':                 # sem objetivo: dá minutos a quem joga pouco (2 de linha descansam)
        linha = [p for _, p, _ in xi if p.pos != 'GK']
        descansam = random.Random(semente).sample(linha, min(2, max_desc, len(linha)))
    elif importancia == 'poupar':              # vem jogo mais importante em até 4 dias: poupa quem jogou há pouco
        rodados = [p for _, p, _ in xi if jogos7.get(str(p.pid), 0) >= 1 and p.pos != 'GK']
        rodados.sort(key=lambda p: (-jogos7.get(str(p.pid), 0), -encaixe.rating(p, p.pos)))
        descansam = rodados[:max_desc]
    elif importancia == 'menor':
        cansados = [p for _, p, _ in xi if jogos7.get(str(p.pid), 0) >= 2 and p.pos != 'GK']
        cansados.sort(key=lambda p: -jogos7.get(str(p.pid), 0))
        descansam = cansados[:max_desc]
    if descansam:
        xi, _ = encaixe.best_xi([p for p in jogadores if p not in descansam], slots)
    ordem = [pos_id[p.pid] for _, p, _ in xi]
    resto = sorted((pos_id[p.pid] for p in jogadores if pos_id[p.pid] not in ordem),
                   key=lambda i: -max((encaixe.rating(p, p.pos) for p in jogadores if pos_id[p.pid] == i), default=0))
    lista = (ordem + resto + [0xFF] * 40)[:40]
    return lista, [p.name for _, p, _ in xi], [p.name for p in descansam]


def _jogos_recentes(jogos, ti, data_jogo, dias=7):
    """{pid: nº de jogos nos últimos `dias` dias} pelas súmulas da memória (registros do pulso com _x/_o)."""
    import struct
    out = {}
    for x in jogos:
        if not x['jogado'] or ti not in (x['time1'], x['time2']) or '_x' not in x:
            continue
        if not 0 < (data_jogo - dt.date(*x['data'])).days <= dias:
            continue
        lado = 0 if x['time1'] == ti else 1
        for i in range(17):
            reg, pid, _, pk = struct.unpack_from('<IIII', x['_x'], x['_o'] + 36 + lado * 272 + 16 * i)
            if reg != 0xFFFF and pk & 0x7F:
                out[str(pid)] = out.get(str(pid), 0) + 1
    return out


# ---------------------------------------------------------------- duelo estatística x rede (duelo.py)
LIMITE_RODIZIO = {'poupar': 0.6, 'menor': 0.45, 'relax': 0.5}   # gols de saldo que o rodízio pode custar


def _notas_xi(players):
    return [(encaixe.rating(p, p.pos), p.pos == 'GK') for p in players]


def _xi_do_time(t, e, ti, data):
    """Os 11 que vão a campo: a escalação que escrevemos para esta data, ou o melhor XI."""
    hist = e['titulares'].get(str(ti)) or []
    reg = next((h for h in reversed(hist) if h['data'] == str(dt.date(*data))), None)
    if reg:
        por_pid = {p.pid: p for p in t.players}
        xs = [por_pid[pid] for pid in reg['pids'] if pid in por_pid]
        if len(xs) >= 9:
            return xs
    xi, _ = encaixe.best_xi(t.players, encaixe.formation_slots(t))
    return [p for _, p, _ in xi]


def _rodizio_pelo_lider(t, teams, j, ti, s, jogos7, imp, chave, desc, formas, log):
    """Quantos podem descansar: o líder do duelo estima o saldo perdido com o rodízio; acima do limite, poupa menos."""
    import duelo
    lider = duelo.lider('simulados')
    adv_ti = j['time2'] if j['time1'] == ti else j['time1']
    ta = teams.get(adv_ti)
    if not ta or len(ta.players) < 11:
        return len(desc)
    xa_adv = duelo.xi_info(_notas_xi([p for _, p, _ in encaixe.best_xi(ta.players, encaixe.formation_slots(ta))[0]]))
    f_eu, f_adv = formas.antes(ti, j['data']), formas.antes(adv_ti, j['data'])
    eu_casa = j['time1'] == ti
    e_d = duelo.estado()
    sq = [k[1] for k in s.squad(ti)]

    def saldo_com(k):
        _, nomes, _ = escalar(t, sq, jogos7, imp, semente=zlib.crc32(chave.encode()), max_desc=k)
        xs = [p for p in t.players if p.name in nomes][:11]
        xi = duelo.xi_info(_notas_xi(xs))
        a, b, fa, fb = (xi, xa_adv, f_eu, f_adv) if eu_casa else (xa_adv, xi, f_adv, f_eu)
        x = duelo.feat_sim(a, b, fa, fb, j['comp'])
        sd = duelo.saldo('simulados', lider, x, duelo.est_sim(e_d, a, b))
        return sd if eu_casa else -sd
    cheio = saldo_com(0)
    for k in range(len(desc), 0, -1):
        if cheio - saldo_com(k) <= LIMITE_RODIZIO.get(imp, 0.5):
            return k
    return 0


def _palpites(e, prox, teams, s, formas, user_ti):
    import duelo
    with duelo.TRAVA:
        ed = duelo.estado()
        for j in prox:
            if user_ti in (j['time1'], j['time2']):
                continue
            ta, tb = teams.get(j['time1']), teams.get(j['time2'])
            if not ta or not tb or len(ta.players) < 11 or len(tb.players) < 11:
                continue
            xa = duelo.xi_info(_notas_xi(_xi_do_time(ta, e, j['time1'], j['data'])))
            xb = duelo.xi_info(_notas_xi(_xi_do_time(tb, e, j['time2'], j['data'])))
            x = duelo.feat_sim(xa, xb, formas.antes(j['time1'], j['data']), formas.antes(j['time2'], j['data']), j['comp'])
            duelo.prever(ed, 'simulados', duelo.chave(j['data'], j['time1'], j['time2']), j['data'], x, duelo.est_sim(ed, xa, xb),
                         {'casa': s.name(j['time1']).strip(), 'fora': s.name(j['time2']).strip()})
        duelo.gravar(ed)


# ---------------------------------------------------------------- rodada
def preparar(h, d, P, jogos, user_ti, b0, log=print, dias=4):
    """Escreve as escalações dos clubes da IA que jogam nos próximos `dias` dias (uma vez por jogo).
    jogos = registros do pulso (memória); d = save da última reunião; b0 = base dos blocos na memória."""
    import ao_vivo as A
    import memoria as M
    from save_ml import SaveML
    import aplicar
    e = _estado()
    hoje = max((tuple(j['data']) for j in jogos if j['jogado']), default=None)
    if not hoje:
        return 0
    try:   # 12/10/2026: duelo estatística x rede — pontua os palpites dos jogos que já aconteceram
        import duelo
        for arena, novo in duelo.ciclo(jogos, hoje, log):
            log(f'DUELO: {"a REDE NEURAL" if novo == "rede" else "a ESTATÍSTICA"} assumiu a arena {arena}')
    except Exception as ex:  # noqa: BLE001
        log(f'duelo: {ex}')
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    import selecoes
    n_cl = selecoes.primeira(s, N_CLUBES)   # 13/10/2026: onde começam as seleções, sem depender do idioma do patch
    lim = (dt.date(*hoje) + dt.timedelta(days=dias)).timetuple()[:3]
    prox = [j for j in jogos if not j['jogado'] and hoje < tuple(j['data']) <= lim
            and j['time1'] < n_cl and j['time2'] < n_cl]
    pend = []
    for j in prox:
        for ti in (j['time1'], j['time2']):
            chave = f'{dt.date(*j["data"])}|{ti}'
            if ti != user_ti and chave not in e['feitos']:
                pend.append((j, ti, chave))
    if not pend:
        return 0
    teams = {t.idx: t for t in aplicar.build_teams(s, P, n_cl)}
    forca, nomes = {}, {}
    for ti in {ti for j, ti, _ in pend} | {j['time1'] for j, _, _ in pend} | {j['time2'] for j, _, _ in pend}:
        t = teams.get(ti)
        nomes[ti] = s.name(ti).strip()
        if t and len(t.players) >= 14:
            xi, _ = encaixe.best_xi(t.players, encaixe.formation_slots(t))
            forca[ti] = sum(r for _, _, r in xi) / len(xi)
    try:   # quem está dando a vida em cada liga (título, vagas, rebaixamento)
        import disputa
        disp = disputa.mapa(jogos, hoje)
    except Exception as ex:  # noqa: BLE001
        log(f'técnico da IA: disputas indisponíveis ({ex})')
        disp = {}
    import duelo
    formas = duelo.Formas([x for x in jogos if x['jogado']])
    feitos = 0
    for j, ti, chave in pend:
        t = teams.get(ti)
        o = T.bloco(d, ti)
        if not t or len(t.players) < 14 or o is None:
            e['feitos'][chave] = 'pulado'
            continue
        if M.ler(h, b0 + (o - T.BASE) + 56, 2) != d[o + 56:o + 58]:
            continue                                       # memória não confere com o save: não arrisca
        data_jogo = dt.date(*j['data'])
        hist = e['titulares'].get(str(ti), [])
        jogos7 = {}
        for reg in hist:
            if 0 < (data_jogo - dt.date.fromisoformat(reg['data'])).days <= 7:
                for pid in reg['pids']:
                    jogos7[str(pid)] = jogos7.get(str(pid), 0) + 1
        for pid, n in _jogos_recentes(jogos, ti, data_jogo).items():   # quem jogou de fato (súmulas)
            jogos7[pid] = max(jogos7.get(pid, 0), n)
        imp = _importancia(j, ti, forca, nomes, disp, user_ti)
        # GESTÃO DE ELENCO: se o próximo compromisso (até 4 dias) é mais importante, poupa para ele
        seguinte = min((x for x in jogos if not x['jogado'] and ti in (x['time1'], x['time2'])
                        and 0 < (dt.date(*x['data']) - data_jogo).days <= 4), key=lambda x: tuple(x['data']), default=None)
        motivo_poupar = ''
        if seguinte and imp in ('normal', 'menor', 'relax'):
            imp_seg = _importancia(seguinte, ti, forca, nomes, disp, user_ti)
            if imp_seg in ('grande', 'decisivo'):
                adv_seg = seguinte['time2'] if seguinte['time1'] == ti else seguinte['time1']
                motivo_poupar = f' | poupa para {nomes.get(adv_seg) or s.name(adv_seg).strip()} em {seguinte["data"][2]:02d}/{seguinte["data"][1]:02d}'
                imp = 'poupar'
        lista, nomes_xi, desc = escalar(t, [k[1] for k in s.squad(ti)], jogos7, imp, semente=zlib.crc32(chave.encode()))
        if desc:   # 12/10/2026: quem lidera o duelo diz se o rodízio custa caro demais neste jogo
            try:
                k = _rodizio_pelo_lider(t, teams, j, ti, s, jogos7, imp, chave, desc, formas, log)
                if k < len(desc):
                    lista, nomes_xi, desc = escalar(t, [q[1] for q in s.squad(ti)], jogos7, imp, semente=zlib.crc32(chave.encode()), max_desc=k)
            except Exception as ex:  # noqa: BLE001
                log(f'duelo (rodízio): {ex}')
        addr = b0 + (T.escalacao(d, ti) - T.BASE)
        atual = M.ler(h, addr, 40)
        if bytes(lista) != atual:
            A.escrever(h, addr, bytes(lista), atual)
        sq = [k[1] for k in s.squad(ti)]
        e['titulares'][str(ti)] = (hist + [{'data': str(data_jogo), 'pids': [sq[i] for i in lista[:11]]}])[-6:]
        m = disp.get(ti) or {}
        e['feitos'][chave] = (imp + (f' | {m["texto"]}' if imp == 'decisivo' else '') + motivo_poupar
                              + (f' | descansam {", ".join(desc)}' if desc else ''))
        feitos += 1
    try:   # palpites dos dois modelos para os jogos da IA desta janela (o placar do duelo, arena "simulados")
        _palpites(e, prox, teams, s, formas, user_ti)
    except Exception as ex:  # noqa: BLE001
        log(f'duelo (palpites): {ex}')
    # limpa jogos antigos do controle
    e['feitos'] = {k: v for k, v in e['feitos'].items() if dt.date.fromisoformat(k.split('|')[0]) >= dt.date(*hoje) - dt.timedelta(days=10)}
    e['ultima'] = {'quando': time.strftime('%Y-%m-%d %H:%M'), 'hoje': list(hoje), 'escritas': feitos}
    _gravar(e)
    if feitos:
        log(f'técnico da IA: {feitos} escalação(ões) escrita(s) para os jogos até {lim[2]:02d}/{lim[1]:02d}')
    return feitos
