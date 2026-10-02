"""Aplica uma janela de transferências da nossa IA num save de Master League.

Uso:  python aplicar.py <arquivo ML0000000X> <foto_memoria.bin> [--ensaio]
  --ensaio: roda tudo, mas NÃO substitui o save (só gera relatório/notícias).

Passos: backup -> descriptografa cópia -> lê elencos (save) + atributos (foto) -> cérebro ->
        aplica cada transferência conferindo -> criptografa -> confere ida e volta -> substitui o save.
Configuração: mercado_config.json (nesta pasta).
"""
import csv
import datetime as dt
import json
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import time

import dados
import encaixe
import mercado
import janela
import memoria_clubes
import potencial
from save_ml import SaveML

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.environ.get('MERCADO_IA_TOOLS_DIR', os.path.join(HERE, '..')))
DECRYPT = os.path.normpath(os.environ.get(
    'PES2021_DECRYPTER', os.path.join(TOOLS, 'pesXdecrypter', 'decrypter21.exe')))
ENCRYPT = os.path.normpath(os.environ.get(
    'PES2021_ENCRYPTER', os.path.join(TOOLS, 'pesXdecrypter', 'encrypter21.exe')))
BACKUPS = os.path.join(TOOLS, 'Backups', 'mercado_ia')
WORK = os.path.join(TOOLS, 'save_work', 'auto')
HIST = os.path.join(HERE, 'historico')
GAME_DIR = os.path.normpath(os.environ.get(
    'PES2021_GAME_DIR', os.path.join(TOOLS, '..', 'eFootball PES 2021')))
NEWS_FILE = os.path.join(GAME_DIR, 'mercado_noticias.txt')

DEFAULT_CONFIG = {
    'time_do_usuario': 'MANCHESTER UNITED',
    'compradores': 'TODOS',          # "TODOS" ou lista de nomes de clubes
    'max_transferencias': 25,         # por rodada
    'limite_janela_verao': 40,        # total de negócios da nossa IA na janela de verão
    'limite_janela_inverno': 20,
    'bloquear_fora_da_janela': True,
    'contratar_livres': False,        # jogadores sem clube ainda não foram testados no save
    'semente': None,                  # None = cada janela é diferente
}


def load_config():
    path = os.path.join(HERE, 'mercado_config.json')
    if not os.path.exists(path):
        json.dump(DEFAULT_CONFIG, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(json.load(open(path, encoding='utf-8')))
    return cfg


def career_year(snap_path):
    """Ano da carreira: marcador da RealLifeLib (07 6d 01 00 00), ano u16 1 byte antes."""
    d = open(snap_path, 'rb').read()
    i = d.find(b'\x07\x6d\x01\x00\x00')
    if i > 0:
        y = struct.unpack_from('<H', d, i - 1)[0]
        if 2020 <= y <= 2080:
            return y
    return None


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd} -> {r.stderr or r.stdout}')


def build_teams(save, players, n_teams):
    teams = []
    formations_ok = True
    for i in range(n_teams):
        name = save.name(i)
        if not name:
            break
        t = dados.Team(i, name, '', save.squad(i))
        t.players = [players[k] for k in t.squad if k in players]
        if formations_ok:
            try:
                t.formation = save.formation(i)
            except RuntimeError:
                # Compatibilidade com saves nos quais a tabela tática ainda não foi mapeada.
                formations_ok = False
        teams.append(t)
    return teams


def finish_without_moves(reason, log, stamp, ensaio=False):
    """Encerra sem alterar o save, avisando no overlay (no ensaio, o aviso vai para o histórico)."""
    print(reason)
    log.append(reason)
    os.makedirs(HIST, exist_ok=True)
    news = os.path.join(HIST, f'noticias_ensaio_{stamp}.txt') if ensaio else NEWS_FILE
    with open(news, 'w', encoding='utf-8') as f:
        f.write(f'Mercado IA | {dt.datetime.now():%d/%m %H:%M}\n{reason}\n')
    with open(os.path.join(HIST, f'log_{stamp}.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(log))
    return 0


def main():
    ml_path, snap_path = sys.argv[1], sys.argv[2]
    ensaio = '--ensaio' in sys.argv
    cfg = load_config()
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    log = []

    def say(msg):
        print(msg)
        log.append(msg)

    # 1) backup
    os.makedirs(BACKUPS, exist_ok=True)
    backup = os.path.join(BACKUPS, f'{os.path.basename(ml_path)}_{stamp}')
    shutil.copy2(ml_path, backup)
    say(f'backup: {backup}')

    # 2) descriptografa cópia
    work = os.path.join(WORK, stamp)
    os.makedirs(work, exist_ok=True)
    enc_in = os.path.join(work, 'original')
    shutil.copy2(ml_path, enc_in)
    run([DECRYPT, enc_in, os.path.join(work, 'dec')])
    data_path = os.path.join(work, 'dec', 'data.dat')

    # 3) elencos (save) + atributos (foto)
    date = janela.career_date(snap_path)
    win_key, win_kind = janela.window_of(date) if date else (None, 'fora')
    ledger = janela.load()
    career_key = f"{os.path.basename(ml_path)}|{cfg['time_do_usuario']}"
    memory_data = memoria_clubes.load()
    club_memory = memoria_clubes.career(memory_data, career_key)
    if date:
        say(f'data da carreira: {date[2]:02d}/{date[1]:02d}/{date[0]} -> janela: {win_key or "fora da janela"}')
    if win_kind == 'fora' and cfg.get('bloquear_fora_da_janela', True):
        return finish_without_moves(f'Fora da janela de transferências ({date[2]:02d}/{date[1]:02d}): nada feito.'
                                    if date else 'Data da carreira não encontrada: nada feito.', log, stamp, ensaio)
    entry = janela.get(ledger, career_key, win_key) if win_key else {'total': 0, 'chegadas': {}, 'saidas': {}, 'rodadas': 0}
    cap = cfg.get(f'limite_janela_{win_kind}', 40)
    remaining = cap - entry['total']
    if remaining <= 0:
        return finish_without_moves(f'Limite desta janela atingido ({entry["total"]}/{cap} negócios): nada feito.', log, stamp, ensaio)
    say(f'janela {win_key}: {entry["total"]}/{cap} negócios já feitos, {entry["rodadas"]} rodada(s)')

    save = SaveML(data_path)
    players = dados.load_players(snap_path)
    year = date[0] if date else (career_year(snap_path) or 2033)
    potencial.classify(players.values(), year, potencial.load_edit_ages())
    teams = build_teams(save, players, 800)
    say(f'carreira {year}: {len(teams)} times, {len(players)} fichas de jogador na foto')

    # 4) cérebro
    protected = set()
    for t in teams:
        specials = save.special_regs(t.idx)
        protected |= {k for k in t.squad if k[0] in specials}
    buyers = None if cfg['compradores'] == 'TODOS' else set(cfg['compradores'])
    in_roster = {id(p) for t in teams for p in t.players}
    free = [p for p in players.values() if id(p) not in in_roster and 17 <= p.age <= 33] if cfg['contratar_livres'] else []
    seed = cfg['semente'] if cfg['semente'] is not None else random.randrange(1 << 30)
    moves, clubs = mercado.run_window(players, teams, cfg['time_do_usuario'], free_agents=free, seed=seed,
                                      national=potencial.national_team_names(), buyers=buyers,
                                      max_total=min(cfg['max_transferencias'], remaining), protected=protected,
                                      prior_buys=entry['chegadas'], prior_sales=entry['saidas'],
                                      club_memory=club_memory, year=year)
    say(f'cérebro decidiu {len(moves)} transferências (semente {seed})')
    profiles = {}
    for m in moves:
        profiles[m.perfil] = profiles.get(m.perfil, 0) + 1
    if profiles:
        say('perfis compradores: ' + ', '.join(f'{k}={v}' for k, v in sorted(profiles.items())))

    # 5) aplica no save conferindo cada uma
    applied = []
    for m in moves:
        if m.src_idx < 0:
            say(f'  pulado (jogador sem clube ainda não suportado): {m.jogador}')
            continue
        if (m.reg, m.pid) not in save.squad(m.src_idx):
            say(f'  pulado (não está mais no {m.de}): {m.jogador}')
            continue
        try:
            shirt = save.transfer(m.src_idx, m.dst_idx, m.reg, m.pid)
        except AssertionError as e:
            say(f'  pulado ({e}): {m.jogador}')
            continue
        applied.append((m, shirt))
    say(f'aplicadas no save: {len(applied)}')

    # 6) criptografa, confere e substitui
    if applied and not ensaio:
        save.save()
        out_enc = os.path.join(work, 'novo')
        run([ENCRYPT, os.path.join(work, 'dec'), out_enc])
        run([DECRYPT, out_enc, os.path.join(work, 'check')])
        if open(os.path.join(work, 'check', 'data.dat'), 'rb').read() != bytes(save.d):
            raise RuntimeError('conferência de ida e volta falhou; save NÃO foi alterado')
        if os.path.getmtime(ml_path) > os.path.getmtime(backup) + 1:
            raise RuntimeError('o save mudou durante o processamento; save NÃO foi alterado')
        copied = False
        for attempt in range(10):
            try:
                shutil.copy2(out_enc, ml_path)
                copied = True
                break
            except PermissionError:
                time.sleep(1)
        if not copied:
            raise RuntimeError('não foi possível substituir o save após 10 tentativas; backup preservado')
        say('SAVE ATUALIZADO. Carregue a carreira no jogo.')
        if win_key:
            janela.record(entry, [(m.de, m.para) for m, _ in applied])
            janela.save(ledger)
        try:
            memoria_clubes.record(club_memory, applied, year, win_key or 'fora')
            memoria_clubes.save(memory_data)
            say('memória esportiva e econômica dos clubes atualizada')
        except OSError as e:
            # O save já foi validado e aplicado; uma falha no histórico não deve fingir que ele não mudou.
            say(f'AVISO: save atualizado, mas a memória dos clubes não pôde ser gravada: {e}')
    elif ensaio:
        say('modo ensaio: save NÃO foi alterado')

    # 7) notícias e histórico
    os.makedirs(HIST, exist_ok=True)
    with open(os.path.join(HIST, f'janela_{stamp}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['jogador', 'idade', 'posição', 'estilo', 'nota_estimada', 'de', 'para', 'valor_milhoes',
                    'motivo', 'perfil_comprador', 'camisa'])
        for m, shirt in applied:
            w.writerow([m.jogador, m.idade, m.pos, m.estilo, m.nota, m.de, m.para, m.valor, m.motivo,
                        m.perfil, shirt])
    news_path = os.path.join(HIST, f'noticias_ensaio_{stamp}.txt') if ensaio else NEWS_FILE
    with open(news_path, 'w', encoding='utf-8') as f:
        uso = f' | janela {win_key}: {entry["total"]}/{cap}' if win_key else ''
        head = 'ENSAIO (nada aplicado)' if ensaio else f'Mercado IA: {len(applied)} negócios{uso}'
        f.write(f'{head} | {dt.datetime.now():%d/%m %H:%M}\n')
        for m, shirt in applied:
            tipo = 'aposta em' if m.motivo.startswith('aposta') else 'contrata'
            f.write(f'{m.para} {tipo} {m.jogador} ({m.pos}, {m.idade}a) do {m.de} - {m.valor} mi\n')
    with open(os.path.join(HIST, f'log_{stamp}.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(log))
    return 0


if __name__ == '__main__':
    sys.exit(main())
