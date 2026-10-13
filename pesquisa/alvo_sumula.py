# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Pesquisa do simulador (fase A): acha na MEMÓRIA a súmula de um jogo IA x IA que ainda vai ser simulado e mostra o
endereço da 1ª linha de jogador do mandante — onde colocar o ponto de parada de ESCRITA no x64dbg.
Só leitura. Uso: python alvo_sumula.py   (com o jogo aberto na carreira)
Também: python alvo_sumula.py conferir <endereço hex>  -> mostra se aquele registro já foi jogado e quem jogou."""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cerebro'))
import memoria as M
import partidas_save as ps
import pulso

PID = M.pid_do_jogo()
h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, PID)
if not h:
    sys.exit('o jogo não está aberto')
pulso._carregar_cache(PID)   # regiões dos jogos que o pulso da Central já achou (rápido)


def agendados():
    out = []
    if not pulso._cache['jogos']:
        pulso.jogos(h)                      # varre e guarda as regiões
    for b, s in pulso._cache['jogos'] or []:
        x = M.ler(h, b, s)
        for j in pulso._jogos_da_regiao(x or b''):
            out.append((b + j['_o'], j))
    return out


if len(sys.argv) > 2 and sys.argv[1] == 'conferir':
    a = int(sys.argv[2], 16)
    x = M.ler(h, a - 36, ps.REC)
    print('cabeçalho:', x[:36].hex(' '))
    print('flag +7 =', hex(x[7]), '(0x60 = jogado, 0x20 = agendado)')
    for i in range(17):
        reg, pid, st, pk = struct.unpack_from('<IIII', x, 36 + 16 * i)
        if reg != 0xFFFF and reg:
            print(f'  linha {i}: reg {reg} id {pid} minutos {pk & 0x7F} nota {((pk >> 7) & 0x7F) / 10}')
    sys.exit()

regs = agendados()
jog = [(a, j) for a, j in regs if not j['jogado']]
if not jog:
    sys.exit('nenhum jogo agendado achado na memória (o pulso da Central já achou as regiões?)')
hoje = max((tuple(j['data']) for a, j in regs if j['jogado']), default=None)
clubes = [(a, j) for a, j in jog if j['time1'] < 625 and j['time2'] < 625 and (hoje is None or tuple(j['data']) > hoje)]
if not clubes:
    sys.exit('nenhum jogo entre clubes agendado depois de hoje')
prox = min(tuple(j['data']) for a, j in clubes)   # 1º dia com jogo entre clubes (pula Data FIFA)
dia = [(a, j) for a, j in clubes if tuple(j['data']) == prox]
print(f'último dia jogado: {hoje} | próximo dia com jogos: {prox} | {len(dia)} jogos IA x IA nesse dia')
for a, j in dia[:8]:
    print(f'  registro {a:#x}  comp {j["comp"]:3d}  times {j["time1"]} x {j["time2"]}  -> 1ª linha do mandante em {a + 36:#x}')
a, j = dia[0]
print(f'\nNO x64dbg (barra de comando embaixo):  bphws {a + 36:X}, w, 4')
