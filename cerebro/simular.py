# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Simula uma janela de transferências da nossa IA sobre o estado atual de uma Master League.

Uso:  python simular.py [foto.bin] [times.txt] [time_do_usuario]
Padrão: a foto e a exportação de times mais recentes em ..\\scans, time do usuário MANCHESTER UNITED.
Saída: saida\\janela_transferencias.csv, saida\\encaixe_antes_depois.csv e resumo no terminal.
Nada é escrito no jogo nem no save.
"""
import csv
import glob
import os
import sys
import time

import dados
import encaixe
import mercado
import potencial

HERE = os.path.dirname(os.path.abspath(__file__))
SCANS = os.path.join(HERE, '..', 'scans')


def latest(pattern):
    files = glob.glob(os.path.join(SCANS, pattern))
    return max(files, key=os.path.getmtime) if files else None


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else latest('ml_snap_*.bin')
    teams_file = sys.argv[2] if len(sys.argv) > 2 else latest('ml_teams_[0-9]*.txt')
    user_team = sys.argv[3] if len(sys.argv) > 3 else 'MANCHESTER UNITED'
    t0 = time.time()
    players, teams = dados.load_career(snap, teams_file)
    year = int(sys.argv[4]) if len(sys.argv) > 4 else 2033
    potencial.classify(players.values(), year, potencial.load_edit_ages())
    in_roster = {id(p) for t in teams for p in t.players}
    free = [p for p in players.values() if id(p) not in in_roster and 17 <= p.age <= 33]
    print(f'carreira: {len(players)} jogadores, {len(teams)} times, {len(free)} sem clube | foto {os.path.basename(snap)}')

    before = {t.name: encaixe.evaluate(t) for t in teams}
    moves, clubs = mercado.run_window(players, teams, user_team, free_agents=free,
                                      national=potencial.national_team_names())
    after = {t.name: encaixe.evaluate(t) for t in teams}

    out = os.path.join(HERE, 'saida')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'janela_transferencias.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['rodada', 'jogador', 'idade', 'posição', 'estilo', 'nota_estimada', 'de', 'para', 'valor_milhoes', 'motivo'])
        for m in moves:
            w.writerow([m.rodada, m.jogador, m.idade, m.pos, m.estilo, m.nota, m.de, m.para, m.valor, m.motivo])
    with open(os.path.join(out, 'encaixe_antes_depois.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['time', 'forca_antes', 'forca_depois', 'encaixe_antes', 'encaixe_depois', 'prof_antes',
                    'prof_depois', 'problemas_antes', 'problemas_depois'])
        for name in clubs:
            b, a = before[name], after[name]
            if b and a:
                w.writerow([name, b['forca'], a['forca'], b['encaixe'], a['encaixe'], b['profundidade'],
                            a['profundidade'], ' | '.join(b['problemas']), ' | '.join(a['problemas'])])

    print(f'\n{len(moves)} transferências em {mercado.ROUNDS} rodadas ({time.time() - t0:.0f}s)')
    by_round = {}
    for m in moves:
        by_round[m.rodada] = by_round.get(m.rodada, 0) + 1
    print('por rodada:', by_round, '| com jogador sem clube:', sum(1 for m in moves if m.de == 'sem clube'))
    changed = [n for n in clubs if before[n] and after[n] and
               (after[n]['encaixe'] != before[n]['encaixe'] or after[n]['forca'] != before[n]['forca'])]
    enc_b = sum(before[n]['encaixe'] for n in clubs if before[n]) / len(clubs)
    enc_a = sum(after[n]['encaixe'] for n in clubs if after[n]) / len(clubs)
    print(f'clubes alterados: {len(changed)} | encaixe médio dos clubes da IA: {enc_b:.1f} -> {enc_a:.1f}')
    print('\nnotícias (primeiras 25):')
    for m in moves[:25]:
        origem = 'sem clube' if m.de == 'sem clube' else f'do {m.de}'
        print(f'  [R{m.rodada}] {m.para} contrata {m.jogador} ({m.pos}, {m.idade}a, {m.estilo}) {origem} '
              f'por {m.valor} mi — {m.motivo}')
    print('\nPremier League (antes -> depois):')
    for t in teams[:20]:
        b, a = before[t.name], after[t.name]
        if b and a:
            mark = '' if t.name in clubs else '  (seu time, não mexido)'
            print(f'  {t.name[:24]:24} força {b["forca"]:5} -> {a["forca"]:5} | encaixe {b["encaixe"]:3} -> '
                  f'{a["encaixe"]:3} | prof {b["profundidade"]:3} -> {a["profundidade"]:3}{mark}')
    print(f'\narquivos em {out}')


if __name__ == '__main__':
    main()
