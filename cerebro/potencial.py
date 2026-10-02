"""Potencial de evolução (estimado; o potencial real é oculto no PES).

Origem do jogador, comparando a idade na carreira com a idade no EDIT (dados de 2025):
  regen  - está mais novo do que deveria: aposentou e voltou pela base (evolução acelerada no PES)
  gerado - não existe no EDIT (criado pelo jogo ou pelo usuário)
  normal - demais
Projeção de pico: +2,0 pontos por ano até os 22, no máximo +12 (regen/gerado: +2,4 por ano, máximo +14; no PES alguns explodem, outros não), teto 94.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT_DATA = os.path.normpath(os.environ.get(
    'PES2021_EDIT_DATA', os.path.join(HERE, '..', 'EDIT_corrigido_descriptografado', 'data.dat')))
EDIT_YEAR = 2025


def load_edit_ages(path=EDIT_DATA):
    if not os.path.exists(path):
        return {}
    sys.path.insert(0, os.path.join(HERE, '..'))
    import edit21
    return {p['id']: p['age'] for p in edit21.load(path)['players'] if p['id']}


def classify(players, career_year, edit_ages):
    gap = career_year - EDIT_YEAR
    for p in players:
        if p.pid & 0x80000000:
            p.origem = 'gerado'
        elif not edit_ages:
            # Sem o EDIT opcional não há base segura para distinguir regen de jogador normal.
            p.origem = 'normal'
        elif p.pid not in edit_ages:
            p.origem = 'gerado'
        elif p.age < edit_ages[p.pid] + gap - 3:
            p.origem = 'regen'
        else:
            p.origem = 'normal'


def projection(p, current):
    if p.age >= 22:
        return current
    special = getattr(p, 'origem', 'normal') in ('regen', 'gerado')
    rate, cap = (2.4, 14) if special else (2.0, 12)
    return min(94.0, current + min(cap, rate * (22 - p.age)))


def national_team_names(path=EDIT_DATA):
    """Seleções no EDIT do PES 2021 (Gogosz): id < 100 (principais) e 1000..1190 (demais; clubes começam em 1195)."""
    if not os.path.exists(path):
        return set()
    sys.path.insert(0, os.path.join(HERE, '..'))
    import edit21
    return {t['name'] for t in edit21.load(path)['teams'] if 0 < t['id'] < 100 or 1000 <= t['id'] <= 1190}
