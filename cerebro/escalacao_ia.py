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
def _importancia(j, ti, forca, nomes):
    """'grande', 'normal' ou 'menor' para o time `ti` neste jogo."""
    import classicos
    adv = j['time2'] if j['time1'] == ti else j['time1']
    if j['comp'] in GRANDES or classicos.nome(nomes.get(j['time1'], ''), nomes.get(j['time2'], '')):
        return 'grande'
    dif = (forca.get(ti) or 75) - (forca.get(adv) or 75)
    if j['comp'] in COPAS or dif >= 6:
        return 'menor'
    if dif <= -2:
        return 'grande'      # adversário mais forte: vai com tudo
    return 'normal'


def escalar(team, sq_ids, jogos7, importancia):
    """(lista de 40 posições no elenco, nomes dos titulares, descansados) para o time."""
    pos_id = {pid: i for i, pid in enumerate(sq_ids)}
    jogadores = [p for p in team.players if p.pid in pos_id]
    slots = encaixe.formation_slots(team)
    xi, _ = encaixe.best_xi(jogadores, slots)
    descansam = []
    if importancia == 'menor':
        cansados = [p for _, p, _ in xi if jogos7.get(str(p.pid), 0) >= 2 and p.pos != 'GK']
        cansados.sort(key=lambda p: -jogos7.get(str(p.pid), 0))
        descansam = cansados[:MAX_DESCANSOS]
        if descansam:
            xi, _ = encaixe.best_xi([p for p in jogadores if p not in descansam], slots)
    ordem = [pos_id[p.pid] for _, p, _ in xi]
    resto = sorted((pos_id[p.pid] for p in jogadores if pos_id[p.pid] not in ordem),
                   key=lambda i: -max((encaixe.rating(p, p.pos) for p in jogadores if pos_id[p.pid] == i), default=0))
    lista = (ordem + resto + [0xFF] * 40)[:40]
    return lista, [p.name for _, p, _ in xi], [p.name for p in descansam]


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
    lim = (dt.date(*hoje) + dt.timedelta(days=dias)).timetuple()[:3]
    prox = [j for j in jogos if not j['jogado'] and hoje < tuple(j['data']) <= lim
            and j['time1'] < N_CLUBES and j['time2'] < N_CLUBES]
    pend = []
    for j in prox:
        for ti in (j['time1'], j['time2']):
            chave = f'{dt.date(*j["data"])}|{ti}'
            if ti != user_ti and chave not in e['feitos']:
                pend.append((j, ti, chave))
    if not pend:
        return 0
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    teams = {t.idx: t for t in aplicar.build_teams(s, P, N_CLUBES)}
    forca, nomes = {}, {}
    for ti in {ti for j, ti, _ in pend} | {j['time1'] for j, _, _ in pend} | {j['time2'] for j, _, _ in pend}:
        t = teams.get(ti)
        nomes[ti] = s.name(ti).strip()
        if t and len(t.players) >= 14:
            xi, _ = encaixe.best_xi(t.players, encaixe.formation_slots(t))
            forca[ti] = sum(r for _, _, r in xi) / len(xi)
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
        imp = _importancia(j, ti, forca, nomes)
        lista, nomes_xi, desc = escalar(t, [k[1] for k in s.squad(ti)], jogos7, imp)
        addr = b0 + (T.escalacao(d, ti) - T.BASE)
        atual = M.ler(h, addr, 40)
        if bytes(lista) != atual:
            A.escrever(h, addr, bytes(lista), atual)
        sq = [k[1] for k in s.squad(ti)]
        e['titulares'][str(ti)] = (hist + [{'data': str(data_jogo), 'pids': [sq[i] for i in lista[:11]]}])[-6:]
        e['feitos'][chave] = imp + (f' | descansam {", ".join(desc)}' if desc else '')
        feitos += 1
    # limpa jogos antigos do controle
    e['feitos'] = {k: v for k, v in e['feitos'].items() if dt.date.fromisoformat(k.split('|')[0]) >= dt.date(*hoje) - dt.timedelta(days=10)}
    e['ultima'] = {'quando': time.strftime('%Y-%m-%d %H:%M'), 'hoje': list(hoje), 'escritas': feitos}
    _gravar(e)
    if feitos:
        log(f'técnico da IA: {feitos} escalação(ões) escrita(s) para os jogos até {lim[2]:02d}/{lim[1]:02d}')
    return feitos
