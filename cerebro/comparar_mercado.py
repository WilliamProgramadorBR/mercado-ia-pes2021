# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""ENSAIO do mercado COM e SEM encaixe no plano de jogo (12/10/2026) — nada é gravado no jogo.

Mesma foto, mesmo save e mesma semente nas duas rodadas; o relatório mostra os negócios que mudam.
Uso: python comparar_mercado.py [data.dat descriptografado] [foto_memoria.bin] [semente]
     (sem argumentos: o save da última reunião e a foto atual)
"""
import copy
import glob
import os
import sys

import aplicar
import carreira
import dados
import encaixe_plano
import memoria_clubes
import mercado
import potencial
from save_ml import SaveML

HERE = os.path.dirname(os.path.abspath(__file__))


def rodar(save, players, user, seed, memoria, planos):
    teams = aplicar.build_teams(save, players, 800)
    protected = set()
    for t in teams:
        specials = save.special_regs(t.idx)
        protected |= {k for k in t.squad if k[0] in specials}
    moves, _ = mercado.run_window(players, teams, user, seed=seed, national=potencial.national_team_names(),
                                  max_total=40, protected=protected, club_memory=copy.deepcopy(memoria),
                                  planos=planos)
    return moves


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dat = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(os.path.join(HERE, '..', 'save_work', 'vestiario_*', 'dec', 'data.dat')),
                                                     key=os.path.getmtime)
    snap = sys.argv[2] if len(sys.argv) > 2 else os.path.join(aplicar.GAME_DIR, 'mercado_snap.bin')
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 2035
    save = SaveML(dat)
    players = dados.load_players(snap)
    year = aplicar.career_year(snap) or 2035
    potencial.classify(players.values(), year, potencial.load_edit_ages())
    user = carreira.time_do_usuario(bytes(save.d))[1]
    memoria = memoria_clubes.career(memoria_clubes.load(), f'ML00000000|{user}')
    planos = encaixe_plano.planos(bytes(save.d), aplicar.build_teams(save, players, 800))
    sem = rodar(save, players, user, seed, memoria, None)
    com = rodar(save, players, user, seed, memoria, planos)
    chave = lambda m: (m.jogador, m.de, m.para)
    s_sem, s_com = {chave(m) for m in sem}, {chave(m) for m in com}
    print(f'save: {dat}\nsemente {seed} | negócios SEM encaixe: {len(sem)} | COM encaixe: {len(com)} | iguais: {len(s_sem & s_com)}')
    print('\n=== só COM o encaixe no plano ===')
    for m in com:
        if chave(m) not in s_sem:
            print(f'  {m.para:22s} <- {m.jogador} ({m.idade}, {m.pos}, {m.estilo}, nota {m.nota}) de {m.de} por {m.valor} mi | {m.motivo}')
    print('\n=== só SEM o encaixe (deixariam de acontecer) ===')
    for m in sem:
        if chave(m) not in s_com:
            print(f'  {m.para:22s} <- {m.jogador} ({m.idade}, {m.pos}, {m.estilo}, nota {m.nota}) de {m.de} por {m.valor} mi | {m.motivo}')
    com_plano = [m for m in com if 'encaixa no plano' in m.motivo]
    print(f'\nnegócios em que o encaixe pesou: {len(com_plano)} de {len(com)}')


if __name__ == '__main__':
    main()
