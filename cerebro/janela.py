# Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
"""Controle por janela de transferências: o cérebro "lembra" o que já fez em cada janela de cada carreira.

Janelas (data da carreira lida da foto de memória):
  verão   = junho a setembro        -> "AAAA-verao"
  inverno = dezembro a fevereiro    -> "AAAA-inverno" (dezembro conta para a janela do ano seguinte)
  fora    = demais meses            -> nada é feito (como no jogo)
Arquivo: historico/controle_janelas.json  {carreira: {janela: {"total", "chegadas": {clube: n}, "saidas": {...}, "rodadas"}}}
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, 'historico', 'controle_janelas.json')


def career_date(snap_path):
    """(ano, mês, dia) da carreira: logo depois do marcador da RealLifeLib (07 6d 01 00 00)."""
    d = open(snap_path, 'rb').read()
    i = d.find(b'\x07\x6d\x01\x00\x00')
    if i < 0:
        return None
    y, m, dd = struct.unpack_from('<HBB', d, i + 5)
    if 2020 <= y <= 2080 and 1 <= m <= 12 and 1 <= dd <= 31:
        return y, m, dd
    return None


def window_of(date):
    y, m, _ = date
    if 6 <= m <= 9:
        return f'{y}-verao', 'verao'
    if m == 12:
        return f'{y + 1}-inverno', 'inverno'
    if m <= 2:
        return f'{y}-inverno', 'inverno'
    return None, 'fora'


def load():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER, encoding='utf-8'))
    return {}


def save(data):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(data, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def get(data, career, window):
    return data.setdefault(career, {}).setdefault(window, {'total': 0, 'chegadas': {}, 'saidas': {}, 'rodadas': 0})


def record(entry, moves):
    entry['rodadas'] += 1
    for de, para in moves:
        entry['total'] += 1
        entry['chegadas'][para] = entry['chegadas'].get(para, 0) + 1
        if de != 'sem clube':
            entry['saidas'][de] = entry['saidas'].get(de, 0) + 1
