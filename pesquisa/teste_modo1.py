"""TESTE do modo 1 do "técnico da IA" (12/10/2026). Tudo na MEMÓRIA do jogo (some ao fechar o jogo).

Descoberta (x64dbg + desmontagem): antes de cada jogo SIMULADO, o jogo chama o técnico da IA com o modo 3
(0x1413321FC: mov dword ptr [rbp+0xE4], 3), que joga fora a escalação guardada e monta outra quase ao acaso.
O modo 1 mantém a escalação guardada (bloco tático de 600 B do clube, +0 = 40 posições) e só troca indisponíveis.

  python teste_modo1.py preparar   -> confere o código, troca o 3 por 1, escreve o melhor XI em ~12 clubes da IA que
                                      jogam no próximo dia com jogos de clubes e guarda o que escreveu em teste_modo1.json
  python teste_modo1.py conferir   -> depois de avançar o dia: compara as súmulas (memória) com o que foi escrito
  python teste_modo1.py desfazer   -> volta o 1 para 3 (o jogo volta ao comportamento original)
"""
import ctypes
import glob
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
AQUI = os.path.dirname(os.path.abspath(__file__))
CER = os.path.join(AQUI, '..', 'cerebro')
sys.path.insert(0, CER)
import aplicar
import ao_vivo as A
import dados
import encaixe
import ia_adversaria as IA
import memoria as M
import pulso
import tatica_save as T
from save_ml import SaveML

ALVO = 0x1413321FC
ORIGINAL = bytes.fromhex('c785e40000000300 0000'.replace(' ', ''))
ARQ = os.path.join(AQUI, 'teste_modo1.json')
M.k32.VirtualProtectEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32,
                                   ctypes.POINTER(ctypes.c_uint32)]
M.k32.FlushInstructionCache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]


def escrever_codigo(h, modo):
    atual = M.ler(h, ALVO, 10)
    if atual[:6] != ORIGINAL[:6] or atual[7:] != ORIGINAL[7:] or atual[6] not in (1, 3):
        raise RuntimeError(f'código diferente do esperado em {ALVO:#x}: {atual.hex(" ")} — nada feito')
    velho = ctypes.c_uint32()
    if not M.k32.VirtualProtectEx(h, ALVO + 6, 1, 0x40, ctypes.byref(velho)):
        raise RuntimeError(f'VirtualProtectEx falhou ({ctypes.get_last_error()})')
    n = ctypes.c_size_t()
    ok = M.k32.WriteProcessMemory(h, ctypes.c_void_p(ALVO + 6), ctypes.create_string_buffer(bytes([modo]), 1), 1, ctypes.byref(n))
    M.k32.VirtualProtectEx(h, ALVO + 6, 1, velho.value, ctypes.byref(ctypes.c_uint32()))
    M.k32.FlushInstructionCache(h, ALVO, 10)
    if not ok or M.ler(h, ALVO + 6, 1)[0] != modo:
        raise RuntimeError('escrita do código não conferiu')
    print(f'código: modo {atual[6]} -> {modo} em {ALVO + 6:#x}')


def save_da_reuniao():
    f = max(glob.glob(os.path.join(CER, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')), key=os.path.getmtime)
    return open(f, 'rb').read(), f


def proximos_jogos(h):
    pid = M.pid_do_jogo()
    pulso._carregar_cache(pid)
    if not pulso._cache['jogos']:
        pulso.jogos(h)
    regs = []
    for b, s in pulso._cache['jogos'] or []:
        for j in pulso._jogos_da_regiao(M.ler(h, b, s) or b''):
            regs.append((b + j['_o'], j))
    hoje = max(tuple(j['data']) for a, j in regs if j['jogado'])
    clubes = [(a, j) for a, j in regs if not j['jogado'] and j['time1'] < 625 and j['time2'] < 625 and tuple(j['data']) > hoje]
    dia = min(tuple(j['data']) for a, j in clubes)
    return hoje, dia, [(a, j) for a, j in clubes if tuple(j['data']) == dia]


def preparar():
    h = A.abrir(escrita=True)
    d, f = save_da_reuniao()
    s = SaveML.__new__(SaveML)
    s.path, s.d, s.base = None, bytearray(d), d.index(b'ARSENAL\x00')
    P = dados.load_players(os.path.join(aplicar.GAME_DIR, 'mercado_snap.bin'))
    hoje, dia, jogos = proximos_jogos(h)
    print(f'hoje {hoje} | próximo dia com jogos de clubes {dia}: {len(jogos)} jogos')
    e = IA._ler_estado()
    b0 = IA._base_memoria(h, d, e, print)
    times = []
    for a, j in jogos:
        times += [j['time1'], j['time2']]
    # os 12 clubes mais fortes que jogam nesse dia (dá para comparar com o rodízio de antes)
    teams = {t.idx: t for t in aplicar.build_teams(s, P, 625)}
    forca = lambda ti: (encaixe.evaluate(teams[ti]) or {}).get('forca', 0) if ti in teams and len(teams[ti].players) >= 14 else 0
    import carreira
    meu = carreira.time_do_usuario(d)[0]
    escolhidos = sorted(set(times) - {meu}, key=lambda ti: -forca(ti))[:12]   # nunca o time do usuário
    registro = {'dia': dia, 'clubes': {}}
    for ti in escolhidos:
        t = teams[ti]
        sq = [tuple(k) for k in s.squad(ti)]
        xi, bench = encaixe.best_xi(t.players, encaixe.formation_slots(t))
        pos_id = {k[1]: i for i, k in enumerate(sq)}          # a ficha pode vir da base (registro diferente): casa pelo id
        ordem = [pos_id[p.pid] for _, p, _ in xi if p.pid in pos_id]
        if len(ordem) != 11:
            continue
        resto = sorted((i for i in range(len(sq)) if i not in ordem and P.get(sq[i])),
                       key=lambda i: -(encaixe.rating(P[sq[i]], P[sq[i]].pos) or 0))
        lista = (ordem + resto + [0xFF] * 40)[:40]
        o = T.bloco(d, ti)
        if M.ler(h, b0 + (o - T.BASE) + 56, 2) != d[o + 56:o + 58]:
            print(f'  {s.name(ti).strip()}: bloco não confere na memória, pulado')
            continue
        addr = b0 + (T.escalacao(d, ti) - T.BASE)        # escalação = +0 do bloco SEGUINTE (fim do registro)
        antes = M.ler(h, addr, 40)
        A.escrever(h, addr, bytes(lista), antes)
        registro['clubes'][str(ti)] = {'nome': s.name(ti).strip(), 'xi': [list(sq[i]) for i in ordem], 'antes': antes.hex(),
                                       'nomes': [P[sq[i]].name for i in ordem]}
        print(f'  {s.name(ti).strip():22s} XI escrito: {", ".join(P[sq[i]].name for i in ordem)}')
    escrever_codigo(h, 1)
    json.dump(registro, open(ARQ, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\npronto: avance o calendário até {dia[2]:02d}/{dia[1]:02d} e rode "conferir"')


def conferir():
    h = A.abrir()
    reg = json.load(open(ARQ, encoding='utf-8'))
    pulso._carregar_cache(M.pid_do_jogo())
    jogos = []
    for b, s_ in pulso._cache['jogos'] or []:
        jogos += pulso._jogos_da_regiao(M.ler(h, b, s_) or b'')
    tot = iguais = 0
    for k, c in reg['clubes'].items():
        ti = int(k)
        j = next((j for j in jogos if j['jogado'] and tuple(j['data']) == tuple(reg['dia']) and ti in (j['time1'], j['time2'])), None)
        if not j:
            print(f'  {c["nome"]:22s} jogo ainda não simulado')
            continue
        x, o = j['_x'], j['_o']
        lado = 0 if j['time1'] == ti else 1
        tit = set()
        for i in range(17):
            r, p, st, pk = struct.unpack_from('<IIII', x, o + 36 + lado * 17 * 16 + 16 * i)
            if r != 0xFFFF and pk & (1 << 21):
                tit.add((r, p))
        n = len(tit & {tuple(v) for v in c['xi']})
        tot += 1
        iguais += n
        print(f'  {c["nome"]:22s} {n}/11 do XI escrito começaram jogando')
    if tot:
        print(f'\nmédia: {iguais / tot:.1f} de 11 (antes do patch, o acaso dava ~4,5)')


def desfazer():
    escrever_codigo(A.abrir(escrita=True), 3)


if __name__ == '__main__':
    {'preparar': preparar, 'conferir': conferir, 'desfazer': desfazer}[sys.argv[1]]()
